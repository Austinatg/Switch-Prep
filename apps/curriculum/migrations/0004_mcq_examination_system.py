
from django.conf import settings
from django.db import migrations, models
from django.db.models import Q
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("curriculum", "0003_topic_interview_questions"),
        migrations.swappable_dependency(
            settings.AUTH_USER_MODEL
        ),
    ]

    operations = [

        migrations.CreateModel(
            name="Quiz",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True),
                ),
                (
                    "exam_type",
                    models.CharField(
                        max_length=20,
                        choices=[
                            ("lesson", "Lesson test"),
                            ("module", "Module test"),
                            ("course_one", "Course examination 1"),
                            ("course_two", "Course examination 2"),
                        ],
                    ),
                ),
                (
                    "title",
                    models.CharField(max_length=220),
                ),
                (
                    "description",
                    models.TextField(blank=True),
                ),
                (
                    "question_count",
                    models.PositiveSmallIntegerField(default=5),
                ),
                (
                    "is_published",
                    models.BooleanField(default=False),
                ),
                (
                    "module",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="quizzes",
                        to="curriculum.module",
                    ),
                ),
                (
                    "specialization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="quizzes",
                        to="curriculum.specialization",
                    ),
                ),
                (
                    "topic",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="quizzes",
                        to="curriculum.topic",
                    ),
                ),
            ],
            options={
                "ordering": ["id"],
            },
        ),

        migrations.CreateModel(
            name="QuizQuestion",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True),
                ),
                (
                    "prompt",
                    models.TextField(),
                ),
                (
                    "explanation",
                    models.TextField(blank=True),
                ),
                (
                    "difficulty",
                    models.CharField(
                        max_length=10,
                        default="medium",
                        choices=[
                            ("easy", "Easy"),
                            ("medium", "Medium"),
                            ("hard", "Hard"),
                        ],
                    ),
                ),
                (
                    "display_order",
                    models.PositiveIntegerField(default=0),
                ),
                (
                    "is_active",
                    models.BooleanField(default=True),
                ),
                (
                    "quiz",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="questions",
                        to="curriculum.quiz",
                    ),
                ),
            ],
            options={
                "ordering": ["display_order", "id"],
            },
        ),

        migrations.CreateModel(
            name="QuizChoice",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True),
                ),
                (
                    "text",
                    models.CharField(max_length=700),
                ),
                (
                    "is_correct",
                    models.BooleanField(default=False),
                ),
                (
                    "display_order",
                    models.PositiveSmallIntegerField(default=0),
                ),
                (
                    "question",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="choices",
                        to="curriculum.quizquestion",
                    ),
                ),
            ],
            options={
                "ordering": ["display_order", "id"],
            },
        ),

        migrations.CreateModel(
            name="QuizAttempt",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True),
                ),
                (
                    "exam_type",
                    models.CharField(
                        max_length=20,
                        choices=[
                            ("lesson", "Lesson test"),
                            ("module", "Module test"),
                            ("course_one", "Course examination 1"),
                            ("course_two", "Course examination 2"),
                            ("mistakes", "Mistake revision test"),
                        ],
                    ),
                ),
                (
                    "question_ids",
                    models.JSONField(default=list),
                ),
                (
                    "answers",
                    models.JSONField(default=dict, blank=True),
                ),
                (
                    "score",
                    models.PositiveIntegerField(default=0),
                ),
                (
                    "total_questions",
                    models.PositiveIntegerField(default=0),
                ),
                (
                    "submitted_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "quiz",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="attempts",
                        to="curriculum.quiz",
                    ),
                ),
                (
                    "specialization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="quiz_attempts",
                        to="curriculum.specialization",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="quiz_attempts",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-submitted_at"],
            },
        ),

        migrations.CreateModel(
            name="UserQuestionMistake",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True),
                ),
                (
                    "wrong_count",
                    models.PositiveIntegerField(default=1),
                ),
                (
                    "is_resolved",
                    models.BooleanField(default=False),
                ),
                (
                    "last_wrong_at",
                    models.DateTimeField(
                        default=django.utils.timezone.now
                    ),
                ),
                (
                    "resolved_at",
                    models.DateTimeField(
                        blank=True,
                        null=True
                    ),
                ),
                (
                    "question",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="user_mistakes",
                        to="curriculum.quizquestion",
                    ),
                ),
                (
                    "specialization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="user_mistakes",
                        to="curriculum.specialization",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="quiz_mistakes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-last_wrong_at"],
            },
        ),

        migrations.AddConstraint(
            model_name="quiz",
            constraint=models.UniqueConstraint(
                fields=("topic", "exam_type"),
                condition=Q(exam_type="lesson"),
                name="uniq_lesson_quiz_type",
            ),
        ),

        migrations.AddConstraint(
            model_name="quiz",
            constraint=models.UniqueConstraint(
                fields=("module", "exam_type"),
                condition=Q(exam_type="module"),
                name="uniq_module_quiz_type",
            ),
        ),

        migrations.AddConstraint(
            model_name="quiz",
            constraint=models.UniqueConstraint(
                fields=("specialization", "exam_type"),
                condition=Q(
                    exam_type__in=["course_one", "course_two"]
                ),
                name="uniq_course_quiz_type",
            ),
        ),

        migrations.AddConstraint(
            model_name="quizattempt",
            constraint=models.UniqueConstraint(
                fields=("user", "quiz"),
                condition=Q(quiz__isnull=False),
                name="uniq_user_single_quiz_attempt",
            ),
        ),

        migrations.AddConstraint(
            model_name="userquestionmistake",
            constraint=models.UniqueConstraint(
                fields=("user", "question"),
                name="uniq_user_quiz_question_mistake",
            ),
        ),
    ]
