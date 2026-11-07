from django.contrib import admin

from .models import (
    AIGlobalUsage,
    AIConversation,
    AIMessage,
    AIUsage,
    InterviewQuestion,
    InterviewSession,
)


class AIMessageInline(admin.TabularInline):
    model = AIMessage
    extra = 0
    readonly_fields = ("role", "content", "created_at")
    can_delete = False


@admin.register(AIConversation)
class AIConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "title", "lesson_title", "updated_at")
    search_fields = ("user__email", "title", "lesson_title")
    list_filter = ("created_at", "updated_at")
    readonly_fields = ("created_at", "updated_at")
    inlines = [AIMessageInline]


@admin.register(AIUsage)
class AIUsageAdmin(admin.ModelAdmin):
    list_display = ("user", "date", "request_count")
    list_filter = ("date",)
    search_fields = ("user__email",)
    readonly_fields = ("user", "date", "request_count")


@admin.register(AIGlobalUsage)
class AIGlobalUsageAdmin(admin.ModelAdmin):
    list_display = ("date", "request_count")
    readonly_fields = ("date", "request_count")


class InterviewQuestionInline(admin.TabularInline):
    model = InterviewQuestion
    extra = 0
    readonly_fields = (
        "question_text",
        "question_number",
        "user_answer",
        "evaluation",
        "score",
        "created_at",
    )
    can_delete = False


@admin.register(InterviewSession)
class InterviewSessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "category",
        "difficulty",
        "status",
        "total_score",
        "created_at",
    )
    list_filter = ("category", "difficulty", "status")
    search_fields = ("user__email",)
    readonly_fields = ("created_at", "completed_at")
    inlines = [InterviewQuestionInline]
