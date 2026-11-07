from django.test import TestCase, override_settings
from django.urls import reverse
from django.core import mail
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from .models import EmailVerification
User=get_user_model()
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class RegistrationTests(TestCase):
 def test_email_verification_send_count_default_for_direct_creation(self):
  user=User.objects.create_user(email="default@example.com",password="TestPass!2026",first_name="Default")
  verification=EmailVerification.objects.create(
   user=user,
   code_hash=EmailVerification.hash_code("123456"),
   expires_at=timezone.now()+timedelta(minutes=10),
  )
  self.assertEqual(verification.send_count,1)
  self.assertIsNotNone(verification.send_window_started_at)

 def test_issue_for_creates_record_and_initializes_send_count(self):
  user=User.objects.create_user(email="issue@example.com",password="TestPass!2026",first_name="Issue",is_active=False)
  verification,code=EmailVerification.issue_for(user)
  self.assertEqual(len(code),6)
  self.assertEqual(verification.send_count,1)
  self.assertEqual(verification.code_hash,EmailVerification.hash_code(code))
  self.assertTrue(EmailVerification.objects.filter(pk=verification.pk).exists())

 def test_issue_for_preserves_hourly_send_count_on_resend(self):
  user=User.objects.create_user(email="resend@example.com",password="TestPass!2026",first_name="Resend",is_active=False)
  verification,_=EmailVerification.issue_for(user)
  verification.last_sent_at=timezone.now()-timedelta(seconds=61)
  verification.save(update_fields=["last_sent_at"])
  resent,_=EmailVerification.issue_for(user)
  self.assertEqual(resent.send_count,2)

 def test_registration_creates_inactive_user_and_sends_code(self):
  response=self.client.post(reverse("accounts:register"),{"first_name":"Ada","last_name":"Lovelace","email":"ada@example.com","password1":"VeryStrongPassword!2026","password2":"VeryStrongPassword!2026"})
  self.assertRedirects(response,reverse("accounts:verify_email"))
  user=User.objects.get(email="ada@example.com"); self.assertFalse(user.is_active)
  self.assertEqual(len(mail.outbox),1); self.assertTrue(EmailVerification.objects.filter(user=user).exists())
 def test_verification_activates_user(self):
  user=User.objects.create_user(email="grace@example.com",password="VeryStrongPassword!2026",first_name="Grace",is_active=False)
  verification,code=EmailVerification.issue_for(user)
  session=self.client.session; session["pending_verification_user_id"]=user.pk; session.save()
  response=self.client.post(reverse("accounts:verify_email"),{"code":code})
  self.assertRedirects(response,reverse("dashboard")); user.refresh_from_db()
  self.assertTrue(user.is_active); self.assertTrue(user.email_verified)
