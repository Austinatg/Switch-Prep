from django.test import TestCase, override_settings
from django.urls import reverse
from django.core import mail
from django.contrib.auth import get_user_model
from .models import EmailVerification
User=get_user_model()
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class RegistrationTests(TestCase):
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
