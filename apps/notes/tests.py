from datetime import date, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from .models import DailyNote, NotePoint

class NotesTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(email="notes@example.com", password="StrongPassword!2026", first_name="Notes")
        self.other = get_user_model().objects.create_user(email="other@example.com", password="StrongPassword!2026", first_name="Other")
    def test_user_can_add_point(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("notes:add"), {"content":"A data pipeline moves data between systems.", "importance":"yellow"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(NotePoint.objects.filter(daily_note__user=self.user).count(), 1)
    def test_quick_add_point_is_saved_to_daily_notes(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("notes:quick_add"), {
            "content": "A lesson insight saved inline.",
            "importance": "yellow",
        }, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["content"], "A lesson insight saved inline.")
        daily_notes_response = self.client.get(reverse("notes:home"))
        self.assertContains(daily_notes_response, "A lesson insight saved inline.")
    def test_quick_add_falls_back_to_the_lesson_without_javascript(self):
        self.client.force_login(self.user)
        lesson_url = "/learning-paths/data-engineering/topics/lesson/"
        response = self.client.post(reverse("notes:quick_add"), {
            "content": "Saved from the lesson.",
            "importance": "normal",
            "return_to": lesson_url,
        })
        self.assertRedirects(response, lesson_url, fetch_redirect_response=False)
        self.assertTrue(NotePoint.objects.filter(
            daily_note__user=self.user,
            content="Saved from the lesson.",
        ).exists())
    def test_user_cannot_edit_another_users_point(self):
        note = DailyNote.objects.create(user=self.other, learning_date=date.today())
        point = NotePoint.objects.create(daily_note=note, content="Private note")
        self.client.force_login(self.user)
        response = self.client.get(reverse("notes:edit", args=[point.pk]))
        self.assertEqual(response.status_code, 404)
    def test_search_is_scoped_to_selected_day_and_user(self):
        self.client.force_login(self.user)
        note = DailyNote.objects.create(user=self.user, learning_date=date.today())
        NotePoint.objects.create(daily_note=note, content="Kafka consumer groups")
        response = self.client.get(reverse("notes:home"), {"q":"Kafka"})
        self.assertContains(response, "Kafka consumer groups")
    def test_notes_are_newest_first_by_default_and_can_be_sorted_oldest_first(self):
        self.client.force_login(self.user)
        note = DailyNote.objects.create(user=self.user, learning_date=timezone.localdate())
        older = NotePoint.objects.create(daily_note=note, content="Older point")
        newer = NotePoint.objects.create(daily_note=note, content="Newer point")
        NotePoint.objects.filter(pk=older.pk).update(
            created_at=timezone.now() - timedelta(hours=1),
        )
        NotePoint.objects.filter(pk=newer.pk).update(
            created_at=timezone.now(),
        )

        newest_response = self.client.get(reverse("notes:home"))
        self.assertLess(
            newest_response.content.index(b"Newer point"),
            newest_response.content.index(b"Older point"),
        )
        oldest_response = self.client.get(reverse("notes:home"), {"sort": "oldest"})
        self.assertLess(
            oldest_response.content.index(b"Older point"),
            oldest_response.content.index(b"Newer point"),
        )
    def test_importance_sort_places_red_yellow_then_no_highlight(self):
        self.client.force_login(self.user)
        note = DailyNote.objects.create(user=self.user, learning_date=timezone.localdate())
        NotePoint.objects.create(daily_note=note, content="No highlight", importance="normal")
        NotePoint.objects.create(daily_note=note, content="Yellow point", importance="yellow")
        NotePoint.objects.create(daily_note=note, content="Red point", importance="red")

        response = self.client.get(reverse("notes:home"), {"sort": "importance"})
        ordered_contents = list(
            response.context["points"].values_list("content", flat=True)
        )
        self.assertEqual(
            ordered_contents,
            ["Red point", "Yellow point", "No highlight"],
        )
