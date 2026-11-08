from pathlib import PurePath
from uuid import uuid4

from django.conf import settings
from django.db import models


def message_upload_path(instance, filename):
    extension = PurePath(filename).suffix.lower()
    return f"messaging/{instance.conversation_id}/{uuid4().hex}{extension}"


class Conversation(models.Model):
    participants=models.ManyToManyField(settings.AUTH_USER_MODEL,related_name='conversations')
    created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    def __str__(self): return f'Conversation {self.pk}'
class Message(models.Model):
    conversation=models.ForeignKey(Conversation,on_delete=models.CASCADE,related_name='messages')
    sender=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='sent_messages')
    body=models.TextField(max_length=5000,blank=True)
    attachment=models.FileField(upload_to=message_upload_path,blank=True,default="")
    attachment_name=models.CharField(max_length=255,blank=True,default="")
    created_at=models.DateTimeField(auto_now_add=True)
    read_by=models.ManyToManyField(settings.AUTH_USER_MODEL,blank=True,related_name='read_messages')
    class Meta: ordering=['created_at']


class UserPresence(models.Model):
    user=models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='presence')
    last_seen=models.DateTimeField(auto_now=True)
    @property
    def is_online(self):
        from django.utils import timezone
        from datetime import timedelta
        return self.last_seen >= timezone.now()-timedelta(minutes=5)


class Notification(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='notifications')
    actor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='sent_notifications',null=True,blank=True)
    message=models.CharField(max_length=240)
    target_url=models.CharField(max_length=500,blank=True)
    is_read=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=['-created_at']
