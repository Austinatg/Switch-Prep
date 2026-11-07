
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Specialization(TimeStampedModel):
    class Level(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"
        ALL = "all", "All levels"

    name = models.CharField(max_length=140, unique=True)
    slug = models.SlugField(max_length=160, unique=True, blank=True)
    short_description = models.CharField(max_length=280)
    description = models.TextField(blank=True)
    icon = models.CharField(
        max_length=40,
        default="database",
        help_text="Short icon name or emoji"
    )
    accent_color = models.CharField(max_length=20, default="#69a7ff")
    level = models.CharField(
        max_length=20,
        choices=Level.choices,
        default=Level.ALL
    )
    estimated_hours = models.PositiveIntegerField(default=0)
    display_order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ["display_order", "name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def topic_count(self):
        return Topic.objects.filter(
            section__module__specialization=self,
            is_published=True
        ).count()


class Module(TimeStampedModel):
    specialization = models.ForeignKey(
        Specialization,
        on_delete=models.CASCADE,
        related_name="modules"
    )
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    display_order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ["display_order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["specialization", "slug"],
                name="uniq_module_slug_per_specialization"
            )
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.specialization.name} — {self.title}"


class Section(TimeStampedModel):
    module = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        related_name="sections"
    )
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    display_order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ["display_order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["module", "slug"],
                name="uniq_section_slug_per_module"
            )
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.module.title} — {self.title}"


class Topic(TimeStampedModel):
    class Difficulty(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"

    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name="topics"
    )
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, blank=True)
    summary = models.CharField(max_length=320, blank=True)
    learning_objectives = models.TextField(
        blank=True,
        help_text="One objective per line."
    )
    theory = models.TextField(
        blank=True,
        help_text="Lesson content."
    )
    key_takeaways = models.TextField(
        blank=True,
        help_text="One takeaway per line."
    )
    interview_questions = models.JSONField(
        default=list,
        blank=True,
        help_text="List of interview questions and answers for this lesson."
    )
    difficulty = models.CharField(
        max_length=20,
        choices=Difficulty.choices,
        default=Difficulty.BEGINNER
    )
    estimated_minutes = models.PositiveIntegerField(default=15)
    prerequisites = models.ManyToManyField(
        "self",
        blank=True,
        symmetrical=False,
        related_name="unlocks"
    )
    display_order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ["display_order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["section", "slug"],
                name="uniq_topic_slug_per_section"
            )
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class TopicResource(TimeStampedModel):
    class ResourceType(models.TextChoices):
        DOCUMENTATION = "documentation", "Official documentation"
        VIDEO = "video", "Video"
        ARTICLE = "article", "Article"
        LAB = "lab", "Hands-on lab"
        DOWNLOAD = "download", "Download"
        TOOL = "tool", "Tool"

    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name="resources"
    )
    title = models.CharField(max_length=200)
    resource_type = models.CharField(
        max_length=24,
        choices=ResourceType.choices
    )
    url = models.URLField(max_length=1000)
    description = models.CharField(max_length=300, blank=True)
    is_free = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "id"]

    def __str__(self):
        return f"{self.topic.title} — {self.title}"


class TopicProgress(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="topic_progress"
    )
    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name="user_progress"
    )
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_opened_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "topic"],
                name="uniq_user_topic_progress"
            )
        ]
        indexes = [
            models.Index(fields=["user", "is_completed"])
        ]

    def save(self, *args, **kwargs):
        if self.is_completed and not self.completed_at:
            self.completed_at = timezone.now()

        if not self.is_completed:
            self.completed_at = None

        super().save(*args, **kwargs)

    def __str__(self):
        state = "done" if self.is_completed else "in progress"
        return f"{self.user} — {self.topic} — {state}"


class TopicBookmark(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="topic_bookmarks"
    )
    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name="bookmarks"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "topic"],
                name="uniq_user_topic_bookmark"
            )
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} bookmarked {self.topic}"


class TopicCodeExample(TimeStampedModel):
    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name="code_examples"
    )
    title = models.CharField(max_length=180)
    language = models.CharField(max_length=40, default="python")
    code = models.TextField()
    explanation = models.TextField(blank=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "id"]

    def __str__(self):
        return f"{self.topic.title} — {self.title}"


class Assessment(TimeStampedModel):
    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name="assessments"
    )
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    pass_percentage = models.PositiveSmallIntegerField(default=70)
    time_limit_minutes = models.PositiveSmallIntegerField(
        default=0,
        help_text="0 means no time limit."
    )
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.section.title} — {self.title}"


class AssessmentQuestion(TimeStampedModel):
    assessment = models.ForeignKey(
        Assessment,
        on_delete=models.CASCADE,
        related_name="questions"
    )
    prompt = models.TextField()
    explanation = models.TextField(blank=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "id"]

    def __str__(self):
        return self.prompt[:90]


class AssessmentChoice(TimeStampedModel):
    question = models.ForeignKey(
        AssessmentQuestion,
        on_delete=models.CASCADE,
        related_name="choices"
    )
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "id"]

    def __str__(self):
        return self.text[:90]


class AssessmentAttempt(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assessment_attempts"
    )
    assessment = models.ForeignKey(
        Assessment,
        on_delete=models.CASCADE,
        related_name="attempts"
    )
    score = models.PositiveSmallIntegerField(default=0)
    total_questions = models.PositiveSmallIntegerField(default=0)
    percentage = models.PositiveSmallIntegerField(default=0)
    passed = models.BooleanField(default=False)
    answers = models.JSONField(default=dict, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return (
            f"{self.user} — {self.assessment} — "
            f"{self.percentage}%"
        )


# ============================================================
# DATAFORGE MCQ EXAMINATION SYSTEM
# ============================================================

class Quiz(TimeStampedModel):
    class ExamType(models.TextChoices):
        LESSON = "lesson", "Lesson test"
        MODULE = "module", "Module test"
        COURSE_ONE = "course_one", "Course examination 1"
        COURSE_TWO = "course_two", "Course examination 2"

    specialization = models.ForeignKey(
        Specialization,
        on_delete=models.CASCADE,
        related_name="quizzes"
    )
    module = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="quizzes"
    )
    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="quizzes"
    )
    exam_type = models.CharField(
        max_length=20,
        choices=ExamType.choices
    )
    title = models.CharField(max_length=220)
    description = models.TextField(blank=True)
    question_count = models.PositiveSmallIntegerField(default=5)
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["topic", "exam_type"],
                condition=Q(exam_type="lesson"),
                name="uniq_lesson_quiz_type"
            ),
            models.UniqueConstraint(
                fields=["module", "exam_type"],
                condition=Q(exam_type="module"),
                name="uniq_module_quiz_type"
            ),
            models.UniqueConstraint(
                fields=["specialization", "exam_type"],
                condition=Q(
                    exam_type__in=["course_one", "course_two"]
                ),
                name="uniq_course_quiz_type"
            )
        ]

    def __str__(self):
        return self.title


class QuizQuestion(TimeStampedModel):
    class Difficulty(models.TextChoices):
        EASY = "easy", "Easy"
        MEDIUM = "medium", "Medium"
        HARD = "hard", "Hard"

    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name="questions"
    )
    prompt = models.TextField()
    explanation = models.TextField(blank=True)
    difficulty = models.CharField(
        max_length=10,
        choices=Difficulty.choices,
        default=Difficulty.MEDIUM
    )
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "id"]

    def __str__(self):
        return self.prompt[:100]


class QuizChoice(TimeStampedModel):
    question = models.ForeignKey(
        QuizQuestion,
        on_delete=models.CASCADE,
        related_name="choices"
    )
    text = models.CharField(max_length=700)
    is_correct = models.BooleanField(default=False)
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "id"]

    def __str__(self):
        return self.text[:100]


class QuizAttempt(TimeStampedModel):
    class ExamType(models.TextChoices):
        LESSON = "lesson", "Lesson test"
        MODULE = "module", "Module test"
        COURSE_ONE = "course_one", "Course examination 1"
        COURSE_TWO = "course_two", "Course examination 2"
        MISTAKES = "mistakes", "Mistake revision test"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="quiz_attempts"
    )
    specialization = models.ForeignKey(
        Specialization,
        on_delete=models.CASCADE,
        related_name="quiz_attempts"
    )
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attempts"
    )
    exam_type = models.CharField(
        max_length=20,
        choices=ExamType.choices
    )
    question_ids = models.JSONField(default=list)
    answers = models.JSONField(default=dict, blank=True)
    score = models.PositiveIntegerField(default=0)
    total_questions = models.PositiveIntegerField(default=0)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-submitted_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "quiz"],
                condition=Q(quiz__isnull=False),
                name="uniq_user_single_quiz_attempt"
            )
        ]

    @property
    def percentage(self):
        if not self.total_questions:
            return 0
        return round(
            self.score * 100 / self.total_questions
        )

    def __str__(self):
        return (
            f"{self.user} — {self.get_exam_type_display()} — "
            f"{self.score}/{self.total_questions}"
        )


class UserQuestionMistake(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="quiz_mistakes"
    )
    specialization = models.ForeignKey(
        Specialization,
        on_delete=models.CASCADE,
        related_name="user_mistakes"
    )
    question = models.ForeignKey(
        QuizQuestion,
        on_delete=models.CASCADE,
        related_name="user_mistakes"
    )
    wrong_count = models.PositiveIntegerField(default=1)
    is_resolved = models.BooleanField(default=False)
    last_wrong_at = models.DateTimeField(default=timezone.now)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-last_wrong_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "question"],
                name="uniq_user_quiz_question_mistake"
            )
        ]

    def __str__(self):
        state = (
            "resolved" if self.is_resolved
            else "unresolved"
        )
        return (
            f"{self.user} — {self.question_id} — {state}"
        )
