from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Lab
from .services import evaluate_submission
class LabEvaluationTests(TestCase):
 def test_exact_output_evaluation(self):
  lab=Lab.objects.create(title="Count rows",category="sql",instructions="Count",evaluation_type="exact",expected_output="42")
  self.assertEqual(evaluate_submission(lab," 42 ")["score"],100)
 def test_manual_review_does_not_execute_code(self):
  lab=Lab.objects.create(title="Python pipeline",category="python",instructions="Build",evaluation_type="review")
  self.assertEqual(evaluate_submission(lab,"print('hello')")["status"],"needs_review")
