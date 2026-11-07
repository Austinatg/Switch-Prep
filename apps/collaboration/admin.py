from django.contrib import admin
from .models import SharedNotebook,SharedNote,NoteComment
admin.site.register([SharedNotebook,SharedNote,NoteComment])
