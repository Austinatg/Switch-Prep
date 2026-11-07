from django.conf import settings
from django.db import models
from django.utils import timezone


class AIConversation(models.Model):
    class ExplanationLevel(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_conversations",
    )
    title = models.CharField(max_length=180, blank=True)
    explanation_level = models.CharField(
        max_length=20,
        choices=ExplanationLevel.choices,
        default=ExplanationLevel.BEGINNER,
    )
    lesson_title = models.CharField(max_length=200, blank=True)
    lesson_context = models.TextField(blank=True)
    lesson_reference = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [models.Index(fields=["user", "-updated_at"])]

    def __str__(self):
        return self.title or self.lesson_title or f"AI conversation {self.pk}"


class AIMessage(models.Model):
    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"

    conversation = models.ForeignKey(
        AIConversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=12, choices=Role.choices)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [models.Index(fields=["conversation", "created_at"])]

    def __str__(self):
        return f"{self.get_role_display()} message in {self.conversation_id}"


class AIUsage(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_usage",
    )
    date = models.DateField(default=timezone.localdate)
    request_count = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "date"], name="uniq_ai_usage_user_date")
        ]
        indexes = [models.Index(fields=["date", "request_count"])]

    def __str__(self):
        return f"{self.user_id} — {self.date}: {self.request_count}"


class AIGlobalUsage(models.Model):
    date = models.DateField(unique=True, default=timezone.localdate)
    request_count = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [models.Index(fields=["date", "request_count"])]

    def __str__(self):
        return f"{self.date}: {self.request_count} requests"


class InterviewSession(models.Model):
    class Category(models.TextChoices):
        SQL = "sql", "SQL"
        PYTHON = "python", "Python"
        PYSPARK = "pyspark", "PySpark"
        FUNDAMENTALS = "fundamentals", "Data Engineering fundamentals"
        ETL = "etl", "ETL and ELT"
        WAREHOUSING = "warehousing", "Data Warehousing"
        SPARK = "spark", "Spark"
        KAFKA = "kafka", "Kafka"
        AIRFLOW = "airflow", "Airflow"
        CLOUD = "cloud", "Cloud Data Engineering"
        MIXED = "mixed", "Mixed interview"

    class Difficulty(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"

    class Status(models.TextChoices):
        ACTIVE = "active", "In progress"
        COMPLETED = "completed", "Completed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_interviews",
    )
    category = models.CharField(max_length=40, choices=Category.choices)
    difficulty = models.CharField(max_length=20, choices=Difficulty.choices)
    total_questions = models.PositiveSmallIntegerField()
    current_question = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    total_score = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "status", "-created_at"])]

    def __str__(self):
        return f"{self.user_id} — {self.category} interview ({self.status})"


class InterviewQuestion(models.Model):
    session = models.ForeignKey(
        InterviewSession,
        on_delete=models.CASCADE,
        related_name="questions",
    )
    question_text = models.TextField()
    question_number = models.PositiveSmallIntegerField()
    user_answer = models.TextField(blank=True)
    is_evaluating = models.BooleanField(default=False)
    evaluation = models.JSONField(default=dict, blank=True)
    score = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["question_number", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "question_number"],
                name="uniq_interview_question_number",
            )
        ]
        indexes = [models.Index(fields=["session", "question_number"])]

    def __str__(self):
        return f"Interview {self.session_id}, question {self.question_number}"
