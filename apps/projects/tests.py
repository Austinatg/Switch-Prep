from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Project,ProjectMilestone,ProjectEnrollment
class ProjectTests(TestCase):
 def test_user_can_enroll_once(self):
  u=get_user_model().objects.create_user(email="learner@example.com",password="StrongPass123!",first_name="Learner")
  p=Project.objects.create(title="Warehouse",summary="Build a warehouse",description="Build it",is_published=True)
  ProjectEnrollment.objects.create(user=u,project=p)
  self.assertEqual(ProjectEnrollment.objects.filter(user=u,project=p).count(),1)
