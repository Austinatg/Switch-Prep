from django.contrib import admin
from .models import CertificationTrack,CertificationExam,CertificationQuestion,CertificationChoice,CertificationAttempt
class ChoiceInline(admin.TabularInline): model=CertificationChoice; extra=2
class QuestionInline(admin.StackedInline): model=CertificationQuestion; extra=1
@admin.register(CertificationTrack)
class TrackAdmin(admin.ModelAdmin): list_display=("name","provider","exam_code","is_published"); list_filter=("provider","is_published"); search_fields=("name","exam_code")
@admin.register(CertificationExam)
class ExamAdmin(admin.ModelAdmin): list_display=("title","track","time_limit_minutes","pass_percentage","is_published"); list_filter=("is_published","track"); inlines=[QuestionInline]
@admin.register(CertificationQuestion)
class QuestionAdmin(admin.ModelAdmin): list_display=("prompt","exam","display_order"); inlines=[ChoiceInline]
admin.site.register(CertificationAttempt)
