from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .execution import SparkExecutionRequest, SparkRuntimeUnavailable, UnconfiguredSparkAdapter
from .models import CaseStudy, Lab, LabAchievement, LabAttempt, LabBookmark, LabDraft
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
        required_fields = (
            "instructions", "subcategory", "starter_content", "expected_output",
            "reference_solution", "public_test_cases", "hints", "dataset_definition",
        )
        for field in required_fields:
            self.assertFalse(Lab.objects.filter(is_published=True, **{field: ""}).exists(), field)
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

    def test_question_detail_contains_dataset_and_code_workspace(self):
        response = self.client.get(reverse("labs:detail", args=[self.lab.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="code-editor"')
        self.assertContains(response, "Example input / data")
        self.assertContains(response, "Expected output")
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
