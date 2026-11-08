from datetime import date
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from unittest.mock import patch
from apps.notes.models import DailyNote, NotePoint
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

 def test_notes_calendar_shows_own_and_accepted_connection_notes_only(self):
  friend=DailyNote.objects.create(user=self.b,learning_date=date.today(),title='Friend notes')
  NotePoint.objects.create(daily_note=friend,content='Friend-only study point.')
  own=DailyNote.objects.create(user=self.a,learning_date=date.today(),title='My notes')
  NotePoint.objects.create(daily_note=own,content='My study point.')
  third=User.objects.create_user(email='third@example.com',password='StrongPass123!',first_name='Third')
  private=DailyNote.objects.create(user=third,learning_date=date.today())
  NotePoint.objects.create(daily_note=private,content='Must remain hidden.')
  Connection.objects.create(sender=self.b,receiver=self.a,status=Connection.ACCEPTED)

  self.client.force_login(self.a)
  response=self.client.get(reverse('community:notes_calendar'),{'date':date.today().isoformat()})

  self.assertEqual(response.status_code,200)
  self.assertContains(response,'My study point.')
  self.assertContains(response,self.b.first_name)
  self.assertNotContains(response,'Must remain hidden.')
  self.assertNotContains(response,'Friend-only study point.')
  self.assertEqual(response.content.count(b'class="community-note-card"'),1)
  self.assertEqual([user.pk for user in response.context['friends_with_notes']],[self.b.pk])
  friend_response=self.client.get(
   reverse('community:notes_calendar'),
   {'date':date.today().isoformat(),'friend':self.b.pk},
  )
  self.assertContains(friend_response,'Friend-only study point.')
  self.assertEqual(friend_response.content.count(b'class="community-note-card"'),2)

 def test_notes_calendar_does_not_expose_notes_of_unconnected_user(self):
  note=DailyNote.objects.create(user=self.b,learning_date=date.today())
  NotePoint.objects.create(daily_note=note,content='Private to a non-connection.')
  self.client.force_login(self.a)

  response=self.client.get(
   reverse('community:notes_calendar'),
   {'date':date.today().isoformat(),'friend':self.b.pk},
  )

  self.assertEqual(response.status_code,404)

 @patch('apps.community.views.generate_text',return_value='Combined notes\\n- Shared point')
 @patch('apps.community.views.reserve_ai_request')
 def test_compile_sends_only_selected_day_notes_after_explicit_consent(self,reserve,generate):
  Connection.objects.create(sender=self.a,receiver=self.b,status=Connection.ACCEPTED)
  own=DailyNote.objects.create(user=self.a,learning_date=date.today())
  NotePoint.objects.create(daily_note=own,content='My data-engineering point.')
  friend=DailyNote.objects.create(user=self.b,learning_date=date.today())
  NotePoint.objects.create(daily_note=friend,content='Friend data-engineering point.')
  self.client.force_login(self.a)

  response=self.client.post(reverse('community:notes_calendar'),{
   'date':date.today().isoformat(),
   'month':date.today().strftime('%Y-%m'),
   'friend':self.b.pk,
   'ai_consent':'yes',
  })

  self.assertEqual(response.status_code,200)
  self.assertContains(response,'Combined notes')
  reserve.assert_called_once_with(self.a)
  prompt=generate.call_args.args[0]
  self.assertIn('My data-engineering point.',prompt)
  self.assertIn('Friend data-engineering point.',prompt)
  self.assertEqual(generate.call_args.kwargs['feature'],'community_notes_compilation')

 @patch('apps.community.views.generate_text')
 @patch('apps.community.views.reserve_ai_request')
 def test_compile_requires_consent_before_sending_notes_to_ai(self,reserve,generate):
  Connection.objects.create(sender=self.a,receiver=self.b,status=Connection.ACCEPTED)
  own=DailyNote.objects.create(user=self.a,learning_date=date.today())
  NotePoint.objects.create(daily_note=own,content='My note.')
  friend=DailyNote.objects.create(user=self.b,learning_date=date.today())
  NotePoint.objects.create(daily_note=friend,content='Friend note.')
  self.client.force_login(self.a)

  response=self.client.post(reverse('community:notes_calendar'),{
   'date':date.today().isoformat(),
   'month':date.today().strftime('%Y-%m'),
   'friend':self.b.pk,
  })

  self.assertEqual(response.status_code,200)
  self.assertContains(response,'Confirm that both note sets may be sent to Gemini')
  reserve.assert_not_called()
  generate.assert_not_called()

 @patch('apps.community.views.generate_text')
 @patch('apps.community.views.reserve_ai_request')
 def test_invalid_compile_date_redirects_without_sending_notes(self,reserve,generate):
  self.client.force_login(self.a)

  response=self.client.post(reverse('community:notes_calendar'),{
   'date':'not-a-date',
   'friend':self.b.pk,
   'ai_consent':'yes',
  })

  self.assertRedirects(response,reverse('community:notes_calendar'))
  reserve.assert_not_called()
  generate.assert_not_called()
