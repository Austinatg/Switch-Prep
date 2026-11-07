from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import CertificationTrack,CertificationExam,CertificationQuestion,CertificationChoice,CertificationAttempt
class CertificationTests(TestCase):
 def test_exam_attempt_is_user_scoped(self):
  u=get_user_model().objects.create_user(email="learner@example.com",password="StrongPass123!",first_name="Learner")
  t=CertificationTrack.objects.create(provider="aws",name="AWS Data Engineer",summary="Prepare",is_published=True)
  e=CertificationExam.objects.create(track=t,title="Mock",is_published=True)
  a=CertificationAttempt.objects.create(user=u,exam=e,percentage=80,passed=True)
  self.assertEqual(CertificationAttempt.objects.get(pk=a.pk,user=u).percentage,80)
