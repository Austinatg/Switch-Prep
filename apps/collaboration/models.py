from django.conf import settings
from django.db import models
class SharedNotebook(models.Model):
    title=models.CharField(max_length=180); description=models.TextField(blank=True)
    owner=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='owned_notebooks')
    members=models.ManyToManyField(settings.AUTH_USER_MODEL,blank=True,related_name='shared_notebooks')
    is_public=models.BooleanField(default=False); created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    class Meta: ordering=['-updated_at']
    def __str__(self): return self.title
class SharedNote(models.Model):
    notebook=models.ForeignKey(SharedNotebook,on_delete=models.CASCADE,related_name='notes')
    author=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='shared_note_edits')
    title=models.CharField(max_length=180); content=models.TextField()
    created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    class Meta: ordering=['-updated_at']
    def __str__(self): return self.title
class NoteComment(models.Model):
    note=models.ForeignKey(SharedNote,on_delete=models.CASCADE,related_name='comments')
    author=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    body=models.TextField(max_length=2000); created_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=['created_at']
