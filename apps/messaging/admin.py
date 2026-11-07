from django.contrib import admin
from .models import Conversation,Message,UserPresence,Notification
admin.site.register([Conversation,Message,UserPresence,Notification])
