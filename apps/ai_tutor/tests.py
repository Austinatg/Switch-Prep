import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from google.genai import errors

from apps.curriculum.models import (
    Module,
    QuizQuestion,
    Section,
    Specialization,
    Topic,
    TopicProgress,
)
from apps.labs.models import Lab, LabAttempt

from .models import (
    AIGlobalUsage,
    AIConversation,
    AIUsage,
    InterviewQuestion,
    InterviewSession,
)
from .services import (
    AIConfigurationError,
    AIQuotaExceededError,
    AIServiceError,
    AIUnavailableError,
    generate_text,
)


class AITutorTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            email="ai-learner@example.com",
            password="SecurePass123!",
            first_name="AI Learner",
        )
        self.other = user_model.objects.create_user(
            email="other-ai@example.com",
            password="SecurePass123!",
            first_name="Other",
        )
        self.specialization = Specialization.objects.create(
            name="AI Test Data Engineering",
            short_description="Test path",
            is_published=True,
        )
        self.module = Module.objects.create(
            specialization=self.specialization,
            title="AI Test Module",
            is_published=True,
        )
        self.section = Section.objects.create(
            module=self.module,
            title="AI Test Section",
            is_published=True,
        )
        self.topic = Topic.objects.create(
            section=self.section,
            title="AI Test Lesson",
            summary="A short lesson context.",
            theory="A data pipeline moves and transforms data.",
            is_published=True,
        )

    def test_anonymous_users_are_redirected_from_ai_pages(self):
        protected_urls = [
            reverse("ai_tutor:dashboard"),
            reverse("ai_tutor:tutor"),
            reverse("ai_tutor:code_assistant"),
            reverse("ai_tutor:learning_path"),
            reverse("ai_tutor:interview_setup"),
            reverse("ai_tutor:interview_history"),
            reverse(
                "ai_tutor:lesson_tutor",
                args=[self.specialization.slug, self.topic.slug],
            ),
        ]
        for url in protected_urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 302)

    def test_authenticated_user_can_open_all_ai_pages(self):
        self.client.force_login(self.user)
        urls = [
            reverse("ai_tutor:dashboard"),
            reverse("ai_tutor:tutor"),
            reverse("ai_tutor:code_assistant"),
            reverse("ai_tutor:learning_path"),
            reverse("ai_tutor:interview_setup"),
            reverse("ai_tutor:interview_history"),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

        lesson_response = self.client.get(
            reverse(
                "ai_tutor:lesson_tutor",
                args=[self.specialization.slug, self.topic.slug],
            ),
            follow=True,
        )
        self.assertEqual(lesson_response.status_code, 200)
        self.assertContains(lesson_response, "AI Test Lesson")
        conversation = AIConversation.objects.get(
            user=self.user,
            lesson_reference=f"{self.specialization.slug}/{self.topic.slug}",
        )
        self.assertIn("A data pipeline moves", conversation.lesson_context)
        with patch("apps.ai_tutor.views.generate_text", return_value="Context-aware response.") as generate:
            response = self.client.post(
                reverse("ai_tutor:send_message", args=[conversation.pk]),
                {"question": "Can you explain it?", "level": "beginner"},
            )
        self.assertEqual(response.status_code, 302)
        self.assertIn("A data pipeline moves", generate.call_args.args[0])

    def test_existing_tutor_route_redirects_to_gemini_tutor(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("tutor"))
        self.assertRedirects(response, reverse("ai_tutor:tutor"))

    def test_conversation_access_is_scoped_to_owner(self):
        conversation = AIConversation.objects.create(user=self.other, title="Private")
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("ai_tutor:conversation", args=[conversation.pk])
        )
        self.assertEqual(response.status_code, 404)

    @override_settings(DATAFORGE_AI_MAX_INPUT_CHARS=4000)
    def test_empty_and_oversized_tutor_questions_are_rejected(self):
        self.client.force_login(self.user)
        route = reverse("ai_tutor:new_conversation")
        with patch("apps.ai_tutor.views.generate_text") as generate:
            empty_response = self.client.post(route, {
                "question": "",
                "level": "beginner",
            })
            oversized_response = self.client.post(route, {
                "question": "x" * 4001,
                "level": "beginner",
            })
        self.assertEqual(empty_response.status_code, 302)
        self.assertEqual(oversized_response.status_code, 302)
        self.assertEqual(AIConversation.objects.count(), 0)
        generate.assert_not_called()

    @override_settings(DATAFORGE_AI_DAILY_LIMIT=1)
    def test_daily_user_request_limit_is_enforced(self):
        self.client.force_login(self.user)
        route = reverse("ai_tutor:new_conversation")
        with patch("apps.ai_tutor.views.generate_text", return_value="A useful answer.") as generate:
            first = self.client.post(route, {
                "question": "Explain a data warehouse.",
                "level": "beginner",
            })
            second = self.client.post(route, {
                "question": "Explain Spark.",
                "level": "beginner",
            })
        self.assertEqual(first.status_code, 302)
        self.assertEqual(second.status_code, 302)
        self.assertEqual(generate.call_count, 1)
        self.assertEqual(AIUsage.objects.get(user=self.user).request_count, 1)
        self.assertContains(
            self.client.get(reverse("ai_tutor:tutor")),
            "AI usage limit reached",
        )

    @override_settings(DATAFORGE_AI_GLOBAL_DAILY_LIMIT=1)
    def test_global_daily_request_limit_is_enforced(self):
        route = reverse("ai_tutor:new_conversation")
        with patch("apps.ai_tutor.views.generate_text", return_value="A useful answer.") as generate:
            self.client.force_login(self.user)
            self.client.post(route, {
                "question": "Explain a data warehouse.",
                "level": "beginner",
            })
            self.client.force_login(self.other)
            self.client.post(route, {
                "question": "Explain Spark.",
                "level": "beginner",
            })
        self.assertEqual(generate.call_count, 1)
        self.assertEqual(AIGlobalUsage.objects.get(date=timezone.localdate()).request_count, 1)

    def test_quota_and_authentication_errors_are_friendly(self):
        self.client.force_login(self.user)
        route = reverse("ai_tutor:new_conversation")
        with patch(
            "apps.ai_tutor.views.generate_text",
            side_effect=AIQuotaExceededError("AI usage limit reached. Please try again later."),
        ):
            response = self.client.post(route, {
                "question": "Explain a data warehouse.",
                "level": "beginner",
            }, follow=True)
        self.assertContains(response, "AI usage limit reached. Please try again later.")

        with patch(
            "apps.ai_tutor.views.generate_text",
            side_effect=AIConfigurationError("Please contact the site administrator."),
        ):
            response = self.client.post(route, {
                "question": "Explain a data warehouse.",
                "level": "beginner",
            }, follow=True)
        self.assertContains(response, "Please contact the site administrator.")

    def test_users_cannot_access_another_users_interview(self):
        session = InterviewSession.objects.create(
            user=self.other,
            category=InterviewSession.Category.SQL,
            difficulty=InterviewSession.Difficulty.BEGINNER,
            total_questions=1,
        )
        response = self.client.get(
            reverse("ai_tutor:interview_result", args=[session.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("ai_tutor:interview_result", args=[session.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_interview_questions_are_created_without_changing_fixed_quiz_bank(self):
        self.client.force_login(self.user)
        question_count = QuizQuestion.objects.count()
        with patch(
            "apps.ai_tutor.views._call_ai",
            return_value=json.dumps([f"Interview question {index}" for index in range(5)]),
        ):
            response = self.client.post(
                reverse("ai_tutor:start_interview"),
                {
                    "category": "sql",
                    "difficulty": "beginner",
                    "total_questions": "5",
                },
            )
        self.assertEqual(response.status_code, 302)
        session = InterviewSession.objects.get(user=self.user)
        self.assertEqual(session.questions.count(), 5)
        self.assertEqual(QuizQuestion.objects.count(), question_count)

    def test_interview_answer_evaluation_is_saved_and_score_completed(self):
        self.client.force_login(self.user)
        session = InterviewSession.objects.create(
            user=self.user,
            category=InterviewSession.Category.SQL,
            difficulty=InterviewSession.Difficulty.BEGINNER,
            total_questions=1,
        )
        question = InterviewQuestion.objects.create(
            session=session,
            question_number=1,
            question_text="What is a primary key?",
        )
        evaluation = {
            "score": 8,
            "explanation": "Correct and clear.",
            "strengths": "Defines uniqueness.",
            "weaknesses": "Could mention nullability.",
            "improved_answer": "A primary key uniquely identifies each row.",
        }
        with patch(
            "apps.ai_tutor.views._call_ai",
            return_value=json.dumps(evaluation),
        ):
            response = self.client.post(
                reverse(
                    "ai_tutor:submit_interview_answer",
                    args=[session.pk, question.question_number],
                ),
                {"answer": "It uniquely identifies a row."},
            )
        self.assertRedirects(
            response,
            reverse("ai_tutor:interview", args=[session.pk]),
        )
        question.refresh_from_db()
        self.assertEqual(question.user_answer, "It uniquely identifies a row.")
        self.assertEqual(question.score, 8)
        self.assertEqual(question.evaluation["strengths"], "Defines uniqueness.")

        response = self.client.post(
            reverse("ai_tutor:next_interview_question", args=[session.pk])
        )
        session.refresh_from_db()
        self.assertEqual(session.status, InterviewSession.Status.COMPLETED)
        self.assertEqual(session.total_score, 80)
        self.assertEqual(
            response.url,
            reverse("ai_tutor:interview_result", args=[session.pk]),
        )
        self.assertContains(
            self.client.get(reverse("ai_tutor:interview_result", args=[session.pk])),
            "Interview review",
        )

    def test_code_assistant_never_executes_submitted_code(self):
        self.client.force_login(self.user)
        with patch("apps.ai_tutor.views._call_ai", return_value="Static review.") as call:
            response = self.client.post(
                reverse("ai_tutor:code_assistant"),
                {
                    "language": "python",
                    "task": "explain",
                    "code": "__import__('os').system('echo not executed')",
                    "instructions": "Explain it",
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Static review.")
        self.assertIn("analyze submitted code as text only", call.call_args.args[2].lower())

    def test_learning_recommendations_use_recorded_progress_and_lab_results(self):
        self.client.force_login(self.user)
        TopicProgress.objects.create(
            user=self.user,
            topic=self.topic,
            is_completed=True,
        )
        lab = Lab.objects.create(
            title="Test SQL Lab",
            category=Lab.Category.SQL,
            instructions="Practice a grouped query.",
            is_published=True,
        )
        LabAttempt.objects.create(
            user=self.user,
            lab=lab,
            answer="SELECT category, COUNT(*) FROM records GROUP BY category",
            status=LabAttempt.Status.PASSED,
            score=90,
        )
        with patch(
            "apps.ai_tutor.views.generate_text",
            return_value="Study the next lesson, then practice the SQL lab.",
        ) as generate:
            response = self.client.post(
                reverse("ai_tutor:learning_path"),
                {"interests": "SQL"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Study the next lesson")
        prompt = generate.call_args.args[0]
        self.assertIn("AI Test Lesson", prompt)
        self.assertIn("completed", prompt)
        self.assertIn("Test SQL Lab", prompt)
        self.assertIn("score 90", prompt)
        self.assertNotIn(self.user.email, prompt)
        self.assertEqual(
            generate.call_args.kwargs["feature"],
            "personalized_learning",
        )

    @override_settings(
        GEMINI_API_KEY="test-key",
        GEMINI_MODEL="test-model",
        DATAFORGE_AI_MAX_INPUT_CHARS=4000,
        DATAFORGE_AI_MAX_OUTPUT_TOKENS=800,
        DATAFORGE_AI_TIMEOUT_MS=12000,
    )
    def test_gemini_quota_and_authentication_errors_are_mapped(self):
        with patch("google.genai.Client") as client_class:
            client_class.return_value.models.generate_content.side_effect = errors.APIError(
                429,
                {"error": {"message": "quota"}},
            )
            with self.assertRaises(AIQuotaExceededError):
                generate_text("A valid prompt", "Tutor instructions")

        with patch("google.genai.Client") as client_class:
            client_class.return_value.models.generate_content.side_effect = errors.APIError(
                403,
                {"error": {"message": "invalid credential"}},
            )
            with self.assertRaises(AIConfigurationError) as raised:
                generate_text("A valid prompt", "Tutor instructions")
        self.assertNotIn("invalid credential", str(raised.exception))

    @override_settings(
        GEMINI_API_KEY="test-key",
        GEMINI_MODEL="test-model",
        DATAFORGE_AI_MAX_INPUT_CHARS=4000,
        DATAFORGE_AI_MAX_OUTPUT_TOKENS=800,
        DATAFORGE_AI_TIMEOUT_MS=12000,
    )
    def test_gemini_failure_logs_safe_diagnostics_without_request_content(self):
        private_prompt = "private conversation prompt"
        with patch("google.genai.Client") as client_class:
            client_class.return_value.models.generate_content.side_effect = errors.APIError(
                429,
                {
                    "error": {
                        "code": 429,
                        "status": "RESOURCE_EXHAUSTED",
                        "message": "Do not log this provider message.",
                    }
                },
            )
            with self.assertLogs("apps.ai_tutor.services", level="ERROR") as captured:
                with self.assertRaises(AIQuotaExceededError):
                    generate_text(
                        private_prompt,
                        "private system instructions",
                        feature="interview_simulator.answer_evaluation",
                    )

        diagnostic = "\n".join(captured.output)
        self.assertIn("feature=interview_simulator.answer_evaluation", diagnostic)
        self.assertIn("exception_class=APIError", diagnostic)
        self.assertIn("http_status=429", diagnostic)
        self.assertIn("gemini_error_code=RESOURCE_EXHAUSTED", diagnostic)
        self.assertNotIn(private_prompt, diagnostic)
        self.assertNotIn("private system instructions", diagnostic)
        self.assertNotIn("test-key", diagnostic)
        self.assertNotIn("Do not log this provider message.", diagnostic)

    @override_settings(
        GEMINI_API_KEY="test-key",
        GEMINI_MODEL="gemini-3.5-flash-lite",
        DATAFORGE_AI_MAX_INPUT_CHARS=4000,
        DATAFORGE_AI_MAX_OUTPUT_TOKENS=800,
        DATAFORGE_AI_TIMEOUT_MS=12000,
    )
    def test_gemini_service_uses_one_attempt_and_configured_limits(self):
        with patch("google.genai.Client") as client_class:
            client_class.return_value.models.generate_content.return_value.text = "A safe answer."
            answer = generate_text(
                "A valid prompt",
                "Tutor instructions",
                response_mime_type="application/json",
            )
        self.assertEqual(answer, "A safe answer.")
        client_kwargs = client_class.call_args.kwargs
        self.assertEqual(client_kwargs["api_key"], "test-key")
        self.assertEqual(client_kwargs["http_options"].timeout, 12000)
        self.assertEqual(client_kwargs["http_options"].retry_options.attempts, 1)
        generation_call = client_class.return_value.models.generate_content.call_args
        self.assertEqual(
            generation_call.kwargs["model"],
            "gemini-3.5-flash-lite",
        )
        config = generation_call.kwargs["config"]
        self.assertEqual(config.max_output_tokens, 800)
        self.assertEqual(config.response_mime_type, "application/json")

    @override_settings(
        GEMINI_API_KEY="test-key",
        GEMINI_MODEL="test-model",
        DATAFORGE_AI_MAX_INPUT_CHARS=10,
    )
    def test_gemini_service_rejects_oversized_prompt_before_request(self):
        with patch("google.genai.Client") as client_class:
            with self.assertRaises(AIServiceError):
                generate_text("This prompt is too long", "Instructions")
        client_class.assert_not_called()

    @override_settings(
        GEMINI_API_KEY="test-key",
        GEMINI_MODEL="test-model",
        DATAFORGE_AI_MAX_INPUT_CHARS=4000,
    )
    def test_gemini_empty_response_is_reported_as_unavailable(self):
        with patch("google.genai.Client") as client_class:
            client_class.return_value.models.generate_content.return_value.text = None
            with self.assertRaises(AIUnavailableError):
                generate_text("A valid prompt", "Tutor instructions")
