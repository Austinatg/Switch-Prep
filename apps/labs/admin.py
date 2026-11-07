from django.contrib import admin
from .models import Lab,LabAttempt
@admin.register(Lab)
class LabAdmin(admin.ModelAdmin): list_display=("title","category","difficulty","evaluation_type","is_published"); list_filter=("category","difficulty","is_published"); search_fields=("title","summary")
@admin.register(LabAttempt)
class LabAttemptAdmin(admin.ModelAdmin): list_display=("user","lab","status","score","submitted_at"); list_filter=("status","lab"); search_fields=("user__email","lab__title"); readonly_fields=("submitted_at",)
