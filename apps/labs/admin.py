from django.contrib import admin

from .models import CaseStudy, Lab, LabAchievement, LabAttempt, LabBookmark, LabDraft
from .services import award_eligible_achievements


@admin.register(Lab)
class LabAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "subcategory", "difficulty", "execution_mode", "is_published")
    list_filter = ("category", "difficulty", "execution_mode", "is_published")
    search_fields = ("title", "summary", "subcategory", "instructions")
    prepopulated_fields = {"slug": ("title",)}
    fieldsets = (
        ("Question", {"fields": ("title", "slug", "category", "subcategory", "difficulty", "summary", "instructions", "concepts")}),
        ("Data and execution", {"fields": ("dataset_definition", "sample_input", "constraints", "starter_content", "execution_mode")}),
        ("Evaluation and learning", {"fields": ("expected_output", "public_test_cases", "hidden_test_cases", "reference_solution", "required_keywords", "evaluation_type", "hints", "brute_force_explanation", "time_complexity", "space_complexity", "follow_up_questions", "related_questions")}),
        ("Publishing", {"fields": ("estimated_minutes", "display_order", "is_published")}),
    )


@admin.register(CaseStudy)
class CaseStudyAdmin(admin.ModelAdmin):
    list_display = ("title", "track", "difficulty", "display_order", "is_published")
    list_filter = ("track", "difficulty", "is_published")
    search_fields = ("title", "summary", "requirements")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(LabAttempt)
class LabAttemptAdmin(admin.ModelAdmin):
    list_display = ("user", "lab", "status", "score", "submitted_at")
    list_filter = ("status", "lab")
    search_fields = ("user__email", "lab__title")
    readonly_fields = ("submitted_at",)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        award_eligible_achievements(obj.user)


@admin.register(LabDraft)
class LabDraftAdmin(admin.ModelAdmin):
    list_display = ("user", "lab", "updated_at")
    search_fields = ("user__email", "lab__title")
    readonly_fields = ("updated_at",)


@admin.register(LabBookmark)
class LabBookmarkAdmin(admin.ModelAdmin):
    list_display = ("user", "lab", "created_at")
    search_fields = ("user__email", "lab__title")
    readonly_fields = ("created_at",)


@admin.register(LabAchievement)
class LabAchievementAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "earned_at")
    search_fields = ("user__email", "title", "key")
    readonly_fields = ("earned_at",)
