from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import SharedNotebook
User=get_user_model()
class CollaborationTests(TestCase):
 def setUp(self):
  self.owner=User.objects.create_user(email='owner@example.com',password='StrongPass123!',first_name='Owner')
  self.other=User.objects.create_user(email='other@example.com',password='StrongPass123!',first_name='Other')
  self.book=SharedNotebook.objects.create(owner=self.owner,title='Team SQL')
 def test_private_notebook_is_not_visible_to_non_member(self):
  self.client.force_login(self.other); response=self.client.get(reverse('collaboration:detail',args=[self.book.pk])); self.assertEqual(response.status_code,302)
 def test_member_can_add_note(self):
  self.book.members.add(self.other);self.client.force_login(self.other)
  self.client.post(reverse('collaboration:detail',args=[self.book.pk]),{'title':'Joins','content':'A join combines rows.'})
  self.assertEqual(self.book.notes.count(),1)
