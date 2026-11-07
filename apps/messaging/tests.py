from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.community.models import Connection
from .models import Conversation
User=get_user_model()
class MessagingTests(TestCase):
 def setUp(self):
  self.a=User.objects.create_user(email='a@example.com',password='StrongPass123!',first_name='A')
  self.b=User.objects.create_user(email='b@example.com',password='StrongPass123!',first_name='B')
 def test_only_connected_users_can_start_conversation(self):
  self.client.force_login(self.a); self.client.post(reverse('messaging:inbox'),{'user_id':self.b.pk}); self.assertEqual(Conversation.objects.count(),0)
  Connection.objects.create(sender=self.a,receiver=self.b,status='accepted')
  self.client.post(reverse('messaging:inbox'),{'user_id':self.b.pk}); self.assertEqual(Conversation.objects.count(),1)
