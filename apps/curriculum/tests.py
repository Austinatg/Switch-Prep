from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import Specialization, Module, Section, Topic, TopicProgress
from apps.notes.models import DailyNote, NotePoint
from django.utils import timezone

class CurriculumTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(email="learner@example.com", password="StrongPassword!2026", first_name="Learner")
        self.spec = Specialization.objects.create(name="Data Engineering Fundamentals", short_description="Start with core concepts.", is_published=True)
        self.module = Module.objects.create(specialization=self.spec, title="SQL Foundations", is_published=True)
        self.section = Section.objects.create(module=self.module, title="Introduction", is_published=True)
        self.topic = Topic.objects.create(section=self.section, title="What is Data Engineering?", summary="Understand the role.", theory="Data Engineering is the practice of designing and operating data systems.", is_published=True)
    def test_specialization_list_requires_login(self):
        response = self.client.get(reverse("curriculum:specialization_list"))
        self.assertEqual(response.status_code, 302)
    def test_published_specialization_is_visible(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("curriculum:specialization_list"))
        self.assertContains(response, "Data Engineering Fundamentals")
    def test_topic_progress_is_user_specific(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("curriculum:toggle_topic_completion", args=[self.topic.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(TopicProgress.objects.get(user=self.user, topic=self.topic).is_completed)
    def test_lesson_shows_today_notes_instead_of_checklist(self):
        self.client.force_login(self.user)
        note = DailyNote.objects.create(user=self.user, learning_date=timezone.localdate())
        NotePoint.objects.create(daily_note=note, content="Review partition pruning.")
        response = self.client.get(reverse(
            "curriculum:topic_detail",
            args=[self.spec.slug, self.topic.slug],
        ))
        self.assertContains(response, "Review partition pruning.")
        self.assertContains(response, "ATTACHED NOTES")
        self.assertNotContains(response, "LESSON CHECKLIST")
