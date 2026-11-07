from django.conf import settings
from django.db import models
from django.utils import timezone

class DailyNote(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="daily_notes")
    learning_date = models.DateField(default=timezone.localdate, db_index=True)
    title = models.CharField(max_length=180, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ["-learning_date", "-updated_at"]
        constraints = [models.UniqueConstraint(fields=["user", "learning_date", "title"], name="uniq_user_daily_note_title")]
    def __str__(self): return f"{self.user} — {self.learning_date} — {self.title or 'Daily notes'}"

class NotePoint(models.Model):
    class Importance(models.TextChoices):
        NORMAL = "normal", "No highlight"
        RED = "red", "Red — important"
        YELLOW = "yellow", "Yellow — review"
        HIGHLIGHT = "highlight", "Highlight"
    daily_note = models.ForeignKey(DailyNote, on_delete=models.CASCADE, related_name="points")
    content = models.TextField()
    importance = models.CharField(max_length=12, choices=Importance.choices, default=Importance.NORMAL)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ["display_order", "created_at", "id"]
    def __str__(self): return self.content[:90]
