import contextlib
import io
import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .execution import SparkExecutionRequest, SparkRuntimeUnavailable, UnconfiguredSparkAdapter
from .models import CaseStudy, Lab, LabAchievement, LabAttempt, LabBookmark, LabDraft
from .python_test_bank import cases_for, program_for, starter_for
from .seed_data import PYTHON_QUESTIONS
from .services import evaluate_submission


class LabEvaluationTests(TestCase):
    def test_exact_output_evaluation(self):
        lab = Lab.objects.create(
            title="Count rows",
            category="sql",
            instructions="Count",
            evaluation_type="exact",
            expected_output="42",
        )
        self.assertEqual(evaluate_submission(lab, " 42 ")["score"], 100)

    def test_manual_review_does_not_execute_code(self):
        lab = Lab.objects.create(
            title="Python pipeline",
            category="python",
            instructions="Build",
            evaluation_type="review",
        )
        result = evaluate_submission(lab, "print('hello')")
        self.assertEqual(result["status"], "needs_review")
        self.assertEqual(result["score"], 0)

    def test_seed_command_upgrades_existing_filter_question_with_twenty_cases(self):
        lab, _created = Lab.objects.get_or_create(
            slug="filter-incomplete-records",
            defaults={
                "title": "Filter incomplete records",
                "category": Lab.Category.PYTHON,
                "instructions": "Filter incomplete rows.",
                "is_published": True,
            },
        )
        lab.starter_content = (
            "rows = [{'customer_id': 'c1', 'amount': 10}, "
            "{'customer_id': '', 'amount': 5}]\n# filter rows"
        )
        lab.public_test_cases = [{"name": "Public example", "expected_output": "[]"}]
        lab.hidden_test_cases = []
        lab.save(update_fields=["starter_content", "public_test_cases", "hidden_test_cases"])

        call_command("seed_labs", stdout=None)

        lab.refresh_from_db()
        self.assertIn("json.loads(input())", lab.starter_content)
        self.assertEqual(len(lab.public_test_cases) + len(lab.hidden_test_cases), 20)
        self.assertEqual(len(lab.hidden_test_cases), 19)

    def test_normalize_headers_starter_is_invoked_with_each_json_headers_array(self):
        cases = cases_for("Normalize CSV headers")
        code = starter_for("Normalize CSV headers").replace(
            "        pass",
            "        import re\n"
            "        normalized.append(re.sub(r'[^a-z0-9]+', '_', header.lower()).strip('_'))",
        )
        runner = (
            code
            + "\nimport json as __lab_json\n"
            + "__lab_data = __lab_json.loads(input())\n"
            + "print(__lab_json.dumps(solve(__lab_data['headers']), separators=(',', ':')))\n"
        )
        compiled = compile(runner, "<normalize-headers-submission>", "exec")
        for case in cases:
            with self.subTest(case=case["name"]):
                output = io.StringIO()
                namespace = {"input": lambda value=case["stdin"]: value}
                with contextlib.redirect_stdout(output):
                    exec(compiled, namespace)
                self.assertEqual(
                    json.loads(output.getvalue()),
                    json.loads(case["expected_output"]),
                )

    def test_every_python_question_has_twenty_distinct_json_stdin_cases(self):
        self.assertEqual(len(PYTHON_QUESTIONS), 36)
        for spec in PYTHON_QUESTIONS:
            title = spec[0]
            with self.subTest(question=title):
                cases = cases_for(title)
                self.assertEqual(len(cases), 20)
                self.assertEqual(len({case["stdin"] for case in cases}), 20)
                self.assertTrue(all(case["expected_output"] for case in cases))
                if title == "Normalize CSV headers":
                    self.assertIn("def solve(headers):", starter_for(title))
                    self.assertNotIn("input()", starter_for(title))
                else:
                    self.assertIn("json.loads(input())", starter_for(title))

    def test_reference_programs_pass_all_configured_python_cases(self):
        for spec in PYTHON_QUESTIONS:
            title = spec[0]
            program = compile(program_for(title), f"<{title}>", "exec")
            for case in cases_for(title):
                with self.subTest(question=title, case=case["name"]):
                    output = io.StringIO()
                    namespace = {"input": lambda value=case["stdin"]: value}
                    with contextlib.redirect_stdout(output):
                        exec(program, namespace)
                    actual = json.loads(output.getvalue())
                    expected = json.loads(case["expected_output"])
                    self.assertEqual(actual, expected)

    def test_seed_command_populates_unique_data_engineering_bank_idempotently(self):
        call_command("seed_labs", stdout=None)
        first_count = Lab.objects.count()
        seeded_question = Lab.objects.filter(category=Lab.Category.PYTHON).first()
        seeded_question.summary = "Admin-authored description."
        seeded_question.save(update_fields=["summary"])
        call_command("seed_labs", stdout=None)
        self.assertEqual(Lab.objects.count(), first_count)
        seeded_question.refresh_from_db()
        self.assertEqual(seeded_question.summary, "Admin-authored description.")
        published = Lab.objects.filter(is_published=True)
        self.assertGreaterEqual(published.filter(category=Lab.Category.PYTHON).count(), 35)
        self.assertGreaterEqual(published.filter(category=Lab.Category.SQL).count(), 40)
        self.assertGreaterEqual(published.filter(category=Lab.Category.PYSPARK).count(), 35)
        self.assertEqual(published.values("slug").distinct().count(), published.count())
        self.assertEqual(CaseStudy.objects.filter(is_published=True).count(), 10)
        normalize_headers = Lab.objects.get(slug="normalize-csv-headers")
        self.assertIn("def solve(headers):", normalize_headers.starter_content)
        required_fields = (
            "instructions", "subcategory", "starter_content", "expected_output",
            "reference_solution", "public_test_cases", "hints", "dataset_definition",
        )
        for field in required_fields:
            self.assertFalse(Lab.objects.filter(is_published=True, **{field: ""}).exists(), field)
        filter_question = Lab.objects.get(slug="filter-incomplete-records")
        self.assertEqual(len(filter_question.public_test_cases), 1)
        self.assertEqual(len(filter_question.hidden_test_cases), 19)
        all_filter_cases = filter_question.public_test_cases + filter_question.hidden_test_cases
        self.assertEqual(len(all_filter_cases), 20)
        self.assertEqual(
            len({case["stdin"] for case in all_filter_cases}),
            20,
            "The filter question should use distinct input data for every case.",
        )
        self.assertTrue(all(case["expected_output"] is not None for case in all_filter_cases))
        python_question = Lab.objects.filter(
            category=Lab.Category.PYTHON, is_published=True
        ).first()
        self.assertIn("source_example", python_question.sample_input)
        self.assertNotEqual(
            python_question.sample_input["source_example"],
            python_question.expected_output,
        )


class LabProgressTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="learner@example.com", password="SafePassword123!"
        )
        self.other_user = get_user_model().objects.create_user(
            email="other@example.com", password="SafePassword123!"
        )
        self.lab = Lab.objects.create(
            title="Build an ETL",
            category=Lab.Category.PYTHON,
            instructions="Transform sample rows.",
            summary="Practice ETL.",
            starter_content="rows = []",
            sample_input={"source_example": "rows = []"},
            expected_output="[]",
            dataset_definition={"format": "Python values", "source_example": "rows = []"},
            execution_mode="python",
            is_published=True,
        )
        self.client.force_login(self.user)

    def test_dashboard_uses_authenticated_user_progress(self):
        LabAttempt.objects.create(
            user=self.user, lab=self.lab, answer="my work", status=LabAttempt.Status.PASSED, score=100
        )
        LabBookmark.objects.create(user=self.user, lab=self.lab)
        response = self.client.get(reverse("labs:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Practical Labs")
        self.assertEqual(response.context["solved_count"], 1)
        self.assertEqual(response.context["attempted_count"], 1)
        self.assertEqual(list(response.context["bookmarked_labs"]), [self.lab])
        self.assertContains(response, 'class="content-card question-solved"')

    def test_drafts_and_bookmarks_are_user_scoped(self):
        save_url = reverse("labs:save_draft", args=[self.lab.slug])
        response = self.client.post(save_url, {"content": "private draft"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(LabDraft.objects.get(user=self.user, lab=self.lab).content, "private draft")
        self.assertFalse(LabDraft.objects.filter(user=self.other_user, lab=self.lab).exists())
        bookmark_url = reverse("labs:bookmark", args=[self.lab.slug])
        self.assertEqual(self.client.post(bookmark_url).json(), {"bookmarked": True})
        self.assertTrue(LabBookmark.objects.filter(user=self.user, lab=self.lab).exists())
        self.assertFalse(LabBookmark.objects.filter(user=self.other_user, lab=self.lab).exists())

    def test_browser_submitted_score_and_solved_status_are_ignored(self):
        response = self.client.post(
            reverse("labs:submit", args=[self.lab.slug]),
            {"answer": "print('not executed')", "score": "100", "status": "passed"},
        )
        self.assertEqual(response.status_code, 302)
        attempt = LabAttempt.objects.get(user=self.user, lab=self.lab)
        self.assertEqual(attempt.status, LabAttempt.Status.NEEDS_REVIEW)
        self.assertEqual(attempt.score, 0)
        self.assertTrue(LabAchievement.objects.filter(user=self.user, key="first_attempt").exists())
        self.assertFalse(LabAchievement.objects.filter(user=self.user, key="first_solve").exists())

    def test_browser_grade_report_records_a_pass_for_configured_python_tests(self):
        self.lab.public_test_cases = [{"name": "sample", "expected_output": "ok"}]
        self.lab.hidden_test_cases = [{"name": "case 1", "stdin": "value", "expected_output": "ok"}]
        self.lab.save(update_fields=["public_test_cases", "hidden_test_cases"])
        response = self.client.post(
            reverse("labs:submit", args=[self.lab.slug]),
            {
                "answer": "print('ok')",
                "browser_report": json.dumps({
                    "mode": "python",
                    "passed": True,
                    "passed_count": 2,
                    "total": 2,
                }),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], LabAttempt.Status.PASSED)
        attempt = LabAttempt.objects.get(user=self.user, lab=self.lab)
        self.assertEqual(attempt.score, 100)
        self.assertEqual(attempt.evaluation_details["verification"], "browser_only")

    def test_browser_grade_report_must_match_configured_test_count(self):
        self.lab.public_test_cases = [{"name": "sample", "expected_output": "ok"}]
        self.lab.hidden_test_cases = [{"name": "case 1", "stdin": "value", "expected_output": "ok"}]
        self.lab.save(update_fields=["public_test_cases", "hidden_test_cases"])
        response = self.client.post(
            reverse("labs:submit", args=[self.lab.slug]),
            {
                "answer": "print('ok')",
                "browser_report": json.dumps({
                    "mode": "python",
                    "passed": True,
                    "passed_count": 1,
                    "total": 1,
                }),
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(LabAttempt.objects.filter(user=self.user, lab=self.lab).exists())

    def test_sql_browser_result_can_save_a_passed_attempt(self):
        self.lab.category = Lab.Category.SQL
        self.lab.execution_mode = "sql"
        self.lab.save(update_fields=["category", "execution_mode"])
        response = self.client.post(
            reverse("labs:submit", args=[self.lab.slug]),
            {
                "answer": "SELECT 1",
                "browser_report": json.dumps({
                    "mode": "sql",
                    "passed": True,
                    "passed_count": 1,
                    "total": 1,
                }),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], LabAttempt.Status.PASSED)
        self.assertEqual(
            LabAttempt.objects.get(user=self.user, lab=self.lab).evaluation_details["verification"],
            "browser_only",
        )

    def test_question_detail_contains_dataset_and_code_workspace(self):
        response = self.client.get(reverse("labs:detail", args=[self.lab.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="code-editor"')
        self.assertContains(response, 'id="test-results"')
        self.assertContains(response, 'id="test-results"')
        self.assertContains(response, "Example input / data")
        self.assertContains(response, "Expected output")
        self.assertContains(response, 'id="program-input"')
        self.assertContains(response, "Pyodide")

    def test_case_study_list_is_authenticated(self):
        response = self.client.get(reverse("labs:case_studies"))
        self.assertEqual(response.status_code, 200)


class SparkAdapterTests(TestCase):
    def test_unconfigured_adapter_explicitly_refuses_real_execution(self):
        with self.assertRaises(SparkRuntimeUnavailable):
            UnconfiguredSparkAdapter().execute(
                SparkExecutionRequest("exercise", "arbitrary code", {})
            )


class LabAIAssistantTests(TestCase):
    def test_ai_action_uses_server_service_and_returns_response(self):
        user = get_user_model().objects.create_user(
            email="ai-learner@example.com", password="SafePassword123!"
        )
        lab = Lab.objects.create(
            title="Review a query",
            category=Lab.Category.SQL,
            instructions="Write an analytical query.",
            is_published=True,
        )
        self.client.force_login(user)
        with patch("apps.labs.views.generate_text", return_value="Use a stable tie breaker.") as generate:
            response = self.client.post(
                reverse("labs:ai_assist", args=[lab.slug]),
                {"action": "review_sql", "code": "SELECT 1", "question": ""},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"answer": "Use a stable tie breaker."})
        self.assertIn("Requested help", generate.call_args.args[0])
