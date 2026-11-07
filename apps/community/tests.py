from datetime import date
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import Connection,DailyBattle,BattleQuestion
User=get_user_model()
class CommunityTests(TestCase):
 def setUp(self):
  self.a=User.objects.create_user(email='a@example.com',password='StrongPass123!',first_name='A')
  self.b=User.objects.create_user(email='b@example.com',password='StrongPass123!',first_name='B')
 def test_connection_request_and_accept(self):
  self.client.force_login(self.a); self.client.post(reverse('community:connect',args=[self.b.pk])); item=Connection.objects.get(sender=self.a,receiver=self.b)
  self.client.force_login(self.b); self.client.post(reverse('community:respond',args=[item.pk,'accept']))
  item.refresh_from_db(); self.assertEqual(item.status,'accepted')
 def test_battle_requires_five_answers(self):
  battle=DailyBattle.objects.create(battle_date=date.today(),is_published=True)
  for i in range(5): BattleQuestion.objects.create(battle=battle,prompt=f'Question {i}',display_order=i+1)
  self.client.force_login(self.a); data={f'answer_{q.pk}':'Answer' for q in battle.questions.all()}
  self.client.post(reverse('community:battle'),data); self.assertEqual(battle.submissions.count(),1)
