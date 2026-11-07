
from django.contrib import admin

from .models import (
    Specialization,
    Module,
    Section,
    Topic,
    TopicResource,
    TopicProgress,
    TopicBookmark,
    TopicCodeExample,
    Assessment,
    AssessmentQuestion,
    AssessmentChoice,
    AssessmentAttempt,
    Quiz,
    QuizQuestion,
    QuizChoice,
    QuizAttempt,
    UserQuestionMistake,
)


# ============================================================
# EXISTING CURRICULUM ADMIN
# ============================================================

class ModuleInline(admin.TabularInline):
    model = Module
    extra = 0


class SectionInline(admin.TabularInline):
    model = Section
    extra = 0


class TopicInline(admin.TabularInline):
    model = Topic
    extra = 0


class TopicResourceInline(admin.TabularInline):
    model = TopicResource
    extra = 0


class TopicCodeExampleInline(admin.TabularInline):
    model = TopicCodeExample
    extra = 0


class AssessmentChoiceInline(admin.TabularInline):
    model = AssessmentChoice
    extra = 2


class AssessmentQuestionInline(admin.TabularInline):
    model = AssessmentQuestion
    extra = 0


@admin.register(Specialization)
class SpecializationAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "level",
        "estimated_hours",
        "display_order",
        "is_published",
    )
    list_filter = ("level", "is_published")
    search_fields = ("name", "short_description")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ModuleInline]
    list_editable = ("display_order", "is_published")


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "specialization",
        "display_order",
        "is_published",
    )
    list_filter = ("specialization", "is_published")
    search_fields = ("title", "description")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [SectionInline]


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "module",
        "display_order",
        "is_published",
    )
    list_filter = (
        "module__specialization",
        "is_published",
    )
    search_fields = ("title", "description")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [TopicInline]


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "section",
        "difficulty",
        "estimated_minutes",
        "display_order",
        "is_published",
    )
    list_filter = (
        "difficulty",
        "is_published",
        "section__module__specialization",
    )
    search_fields = ("title", "summary", "theory")
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("prerequisites",)
    inlines = [
        TopicResourceInline,
        TopicCodeExampleInline,
    ]


@admin.register(TopicResource)
class TopicResourceAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "topic",
        "resource_type",
        "is_free",
        "display_order",
    )
    list_filter = ("resource_type", "is_free")
    search_fields = ("title", "topic__title")


@admin.register(TopicProgress)
class TopicProgressAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "topic",
        "is_completed",
        "completed_at",
        "updated_at",
    )
    list_filter = (
        "is_completed",
        "topic__section__module__specialization",
    )
    search_fields = ("user__email", "topic__title")


@admin.register(TopicBookmark)
class TopicBookmarkAdmin(admin.ModelAdmin):
    list_display = ("user", "topic", "created_at")
    search_fields = ("user__email", "topic__title")


@admin.register(TopicCodeExample)
class TopicCodeExampleAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "topic",
        "language",
        "display_order",
    )
    list_filter = ("language",)
    search_fields = ("title", "topic__title")


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "section",
        "pass_percentage",
        "time_limit_minutes",
        "is_published",
    )
    list_filter = (
        "is_published",
        "section__module__specialization",
    )
    search_fields = ("title", "section__title")
    inlines = [AssessmentQuestionInline]


@admin.register(AssessmentQuestion)
class AssessmentQuestionAdmin(admin.ModelAdmin):
    list_display = (
        "prompt",
        "assessment",
        "display_order",
    )
    search_fields = ("prompt", "assessment__title")
    inlines = [AssessmentChoiceInline]


@admin.register(AssessmentChoice)
class AssessmentChoiceAdmin(admin.ModelAdmin):
    list_display = (
        "text",
        "question",
        "is_correct",
        "display_order",
    )
    list_filter = ("is_correct",)
    search_fields = ("text", "question__prompt")


@admin.register(AssessmentAttempt)
class AssessmentAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "assessment",
        "score",
        "total_questions",
        "percentage",
        "passed",
        "submitted_at",
    )
    list_filter = ("passed", "assessment")
    search_fields = ("user__email", "assessment__title")
    readonly_fields = (
        "user",
        "assessment",
        "score",
        "total_questions",
        "percentage",
        "passed",
        "answers",
        "submitted_at",
    )


# ============================================================
# NEW MCQ EXAMINATION ADMIN
# ============================================================

class QuizQuestionInline(admin.TabularInline):
    model = QuizQuestion
    extra = 0
    show_change_link = True


class QuizChoiceInline(admin.TabularInline):
    model = QuizChoice
    extra = 4
    min_num = 4


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "specialization",
        "exam_type",
        "module",
        "topic",
        "question_count",
        "is_published",
    )
    list_filter = (
        "exam_type",
        "specialization",
        "is_published",
    )
    search_fields = (
        "title",
        "specialization__name",
        "module__title",
        "topic__title",
    )
    inlines = [QuizQuestionInline]


@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    list_display = (
        "prompt",
        "quiz",
        "difficulty",
        "is_active",
    )
    list_filter = (
        "difficulty",
        "is_active",
        "quiz__exam_type",
        "quiz__specialization",
    )
    search_fields = (
        "prompt",
        "explanation",
        "quiz__title",
    )
    inlines = [QuizChoiceInline]


@admin.register(QuizChoice)
class QuizChoiceAdmin(admin.ModelAdmin):
    list_display = (
        "text",
        "question",
        "is_correct",
        "display_order",
    )
    list_filter = ("is_correct",)
    search_fields = ("text", "question__prompt")


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "specialization",
        "exam_type",
        "score",
        "total_questions",
        "submitted_at",
    )
    list_filter = (
        "exam_type",
        "specialization",
    )
    search_fields = (
        "user__email",
        "specialization__name",
    )
    readonly_fields = (
        "user",
        "specialization",
        "quiz",
        "exam_type",
        "question_ids",
        "answers",
        "score",
        "total_questions",
        "submitted_at",
    )


@admin.register(UserQuestionMistake)
class UserQuestionMistakeAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "specialization",
        "question",
        "wrong_count",
        "is_resolved",
        "last_wrong_at",
    )
    list_filter = (
        "specialization",
        "is_resolved",
    )
    search_fields = (
        "user__email",
        "question__prompt",
    )
    readonly_fields = (
        "user",
        "specialization",
        "question",
        "wrong_count",
        "last_wrong_at",
        "resolved_at",
    )
