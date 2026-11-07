from django.contrib import admin
from .models import DailyNote, NotePoint
class NotePointInline(admin.TabularInline):
    model = NotePoint
    extra = 0
@admin.register(DailyNote)
class DailyNoteAdmin(admin.ModelAdmin):
    list_display = ("user","learning_date","title","updated_at")
    list_filter = ("learning_date",)
    search_fields = ("user__email","title","points__content")
    inlines = [NotePointInline]
@admin.register(NotePoint)
class NotePointAdmin(admin.ModelAdmin):
    list_display = ("daily_note","importance","display_order","created_at")
    list_filter = ("importance",)
    search_fields = ("content","daily_note__user__email")
