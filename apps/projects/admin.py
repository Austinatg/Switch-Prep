from django.contrib import admin
from .models import Project,ProjectMilestone,ProjectEnrollment,MilestoneSubmission
class MilestoneInline(admin.TabularInline): model=ProjectMilestone; extra=1
@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin): list_display=("title","level","is_capstone","is_published"); list_filter=("level","is_capstone","is_published"); search_fields=("title","summary"); inlines=[MilestoneInline]
@admin.register(MilestoneSubmission)
class SubmissionAdmin(admin.ModelAdmin): list_display=("enrollment","milestone","status","submitted_at"); list_filter=("status",); search_fields=("enrollment__user__email","milestone__title")
admin.site.register(ProjectEnrollment)
