import base64
import io
import json
import re
import tempfile
from datetime import timedelta
from email import message_from_bytes
from pathlib import Path
from unittest.mock import patch

import httplib2
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.mail import EmailMessage
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError

from .email_service import EmailDeliveryResult, GMAIL_SEND_SCOPE, send_email
from .management.commands.setup_gmail_oauth import (
    OAUTH_SCOPES,
    _store_refresh_token,
)
from .models import (
    EmailVerification,
    VerificationCooldownError,
    VerificationRateLimitError,
)

User = get_user_model()
OAUTH_SETTINGS = {
    "GOOGLE_OAUTH_CLIENT_ID": "client-id",
    "GOOGLE_OAUTH_CLIENT_SECRET": "client-secret",
    "GOOGLE_OAUTH_REFRESH_TOKEN": "refresh-token-secret",
    "GOOGLE_OAUTH_TOKEN_URI": "https://oauth2.googleapis.com/token",
    "GMAIL_SENDER_EMAIL": "switchcompapp@gmail.com",
}


class RegistrationTests(TestCase):
    def register(self, email="ada@example.com", *, follow=False):
        return self.client.post(
            reverse("accounts:register"),
            {
                "first_name": "Ada",
                "last_name": "Lovelace",
                "email": email,
                "password1": "VeryStrongPassword!2026",
                "password2": "VeryStrongPassword!2026",
            },
            follow=follow,
        )

    @patch(
        "apps.accounts.views.send_email",
        return_value=EmailDeliveryResult(True),
    )
    def test_registration_creates_inactive_user_and_uses_gmail_delivery(self, send):
        response = self.register()
        self.assertRedirects(response, reverse("accounts:verify_email"))
        user = User.objects.get(email="ada@example.com")
        self.assertFalse(user.is_active)
        verification = EmailVerification.objects.get(user=user)
        self.assertEqual(len(verification.code_hash), 64)
        self.assertEqual(send.call_args.args[0], user.email)
        self.assertEqual(
            send.call_args.args[1],
            "Verify your SwitchFromTredence account",
        )
        self.assertIn("Welcome to SwitchFromTredence", send.call_args.args[2])
        self.assertIn("10 minutes", send.call_args.args[2])
        self.assertIn("<html", send.call_args.args[3])

    @patch(
        "apps.accounts.views.send_email",
        return_value=EmailDeliveryResult(False, "gmail_api_error"),
    )
    def test_delivery_failure_keeps_account_inactive_and_shows_required_message(self, _send):
        response = self.register(follow=True)
        self.assertEqual(response.status_code, 200)
        user = User.objects.get(email="ada@example.com")
        self.assertFalse(user.is_active)
        self.assertIn(
            "We couldn't send your verification email. Please try again.",
            [str(message) for message in response.context["messages"]],
        )

    @patch(
        "apps.accounts.views.send_email",
        return_value=EmailDeliveryResult(True),
    )
    def test_otp_is_not_in_stdout_or_http_response(self, send):
        output = io.StringIO()
        with patch("sys.stdout", output):
            response = self.register()
        otp = re.search(r"\b\d{6}\b", send.call_args.args[2]).group()
        self.assertNotIn(otp, response.content.decode())
        self.assertNotIn(otp, output.getvalue())

    @patch(
        "apps.accounts.views.send_email",
        return_value=EmailDeliveryResult(True),
    )
    def test_verification_activates_user_and_code_is_single_use(self, _send):
        user = User.objects.create_user(
            email="grace@example.com",
            password="VeryStrongPassword!2026",
            first_name="Grace",
            is_active=False,
        )
        verification, code = EmailVerification.issue_for(user)
        session = self.client.session
        session["pending_verification_user_id"] = user.pk
        session.save()

        response = self.client.post(
            reverse("accounts:verify_email"),
            {"code": code},
        )
        self.assertRedirects(response, reverse("dashboard"))
        user.refresh_from_db()
        verification.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertTrue(user.email_verified)
        self.assertFalse(verification.check_code(code))

    def test_expired_and_invalid_codes_are_rejected(self):
        user = User.objects.create_user(
            email="expired@example.com",
            password="VeryStrongPassword!2026",
            first_name="Expired",
            is_active=False,
        )
        verification, code = EmailVerification.issue_for(user)
        verification.expires_at = timezone.now() - timedelta(seconds=1)
        verification.save(update_fields=["expires_at"])
        self.assertFalse(verification.check_code(code))
        verification.expires_at = timezone.now() + timedelta(minutes=10)
        verification.save(update_fields=["expires_at"])
        self.assertFalse(verification.check_code("000000" if code != "000000" else "000001"))

    def test_otp_cooldown_and_hourly_rate_limit(self):
        user = User.objects.create_user(
            email="throttle@example.com",
            password="VeryStrongPassword!2026",
            first_name="Throttle",
            is_active=False,
        )
        verification, _ = EmailVerification.issue_for(user)
        with self.assertRaises(VerificationCooldownError):
            EmailVerification.issue_for(user)
        verification.last_sent_at = timezone.now() - timedelta(seconds=61)
        verification.send_count = EmailVerification.MAX_SENDS_PER_HOUR
        verification.save(update_fields=["last_sent_at", "send_count"])
        with self.assertRaises(VerificationRateLimitError):
            EmailVerification.issue_for(user)

    @patch(
        "apps.accounts.views.send_email",
        return_value=EmailDeliveryResult(True),
    )
    def test_registration_does_not_confirm_existing_account(self, _send):
        user = User.objects.create_user(
            email="existing@example.com",
            password="VeryStrongPassword!2026",
            first_name="Existing",
            is_active=True,
            email_verified=True,
        )
        response = self.register("existing@example.com", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "If this address is eligible, a verification code will be sent.",
        )
        self.assertFalse(EmailVerification.objects.filter(user=user).exists())
        _send.assert_not_called()

    def test_login_still_works_for_active_custom_user(self):
        user = User.objects.create_user(
            email="login@example.com",
            password="VeryStrongPassword!2026",
            first_name="Login",
            is_active=True,
        )
        response = self.client.post(
            reverse("accounts:login"),
            {"username": user.email, "password": "VeryStrongPassword!2026"},
        )
        self.assertRedirects(response, reverse("dashboard"))

    @patch(
        "apps.accounts.email_service._send_mime_message",
        return_value=EmailDeliveryResult(True),
    )
    def test_django_password_reset_email_uses_gmail_backend(self, send_message):
        message = EmailMessage(
            "Password reset",
            "Reset your password.",
            to=["reset@example.com"],
        )
        from .email_service import GmailEmailBackend

        connection = GmailEmailBackend()
        self.assertEqual(connection.send_messages([message]), 1)
        send_message.assert_called_once()

    def test_oauth_setup_updates_only_refresh_token_in_local_env(self):
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env"
            env_path.write_text(
                "SECRET_KEY=keep-this-line\nGOOGLE_OAUTH_CLIENT_ID=client-id\n",
                encoding="utf-8",
            )
            _store_refresh_token(env_path, "new-refresh-token")
            contents = env_path.read_text(encoding="utf-8")
        self.assertIn("SECRET_KEY=keep-this-line", contents)
        self.assertIn("GOOGLE_OAUTH_CLIENT_ID=client-id", contents)
        self.assertIn("GOOGLE_OAUTH_REFRESH_TOKEN=new-refresh-token", contents)

    @override_settings(
        GOOGLE_OAUTH_CLIENT_ID="client-id",
        GOOGLE_OAUTH_CLIENT_SECRET="client-secret",
        GMAIL_SENDER_EMAIL="switchcompapp@gmail.com",
    )
    @patch(
        "apps.accounts.management.commands.setup_gmail_oauth._store_refresh_token",
    )
    @patch("google_auth_oauthlib.flow.InstalledAppFlow.from_client_config")
    def test_oauth_command_uses_offline_send_scope_and_never_prints_token(
        self,
        from_client_config,
        store_token,
    ):
        flow = from_client_config.return_value
        flow.run_local_server.return_value.refresh_token = "refresh-token-secret"
        output = io.StringIO()

        call_command("setup_gmail_oauth", stdout=output)

        self.assertEqual(OAUTH_SCOPES, [GMAIL_SEND_SCOPE])
        self.assertEqual(
            from_client_config.call_args.kwargs["scopes"],
            [GMAIL_SEND_SCOPE],
        )
        flow.run_local_server.assert_called_once()
        flow_options = flow.run_local_server.call_args.kwargs
        self.assertEqual(flow_options["port"], 8080)
        self.assertEqual(flow_options["access_type"], "offline")
        self.assertEqual(flow_options["prompt"], "consent")
        self.assertEqual(flow_options["login_hint"], "switchcompapp@gmail.com")
        store_token.assert_called_once()
        self.assertNotIn("refresh-token-secret", output.getvalue())


@override_settings(**OAUTH_SETTINGS)
class GmailServiceTests(TestCase):
    @patch("google.oauth2.credentials.Credentials.refresh")
    @patch("googleapiclient.discovery.build")
    def test_message_uses_sender_recipient_subject_and_both_alternatives(
        self,
        build,
        refresh,
    ):
        build.return_value.users.return_value.messages.return_value.send.return_value.execute.return_value = {
            "id": "message-id",
        }
        result = send_email(
            "learner@example.com",
            "Verify your SwitchFromTredence account",
            "Plain OTP 123456",
            "<html><body>HTML OTP 123456</body></html>",
        )
        self.assertTrue(result.success)
        refresh.assert_called_once()
        build.assert_called_once()
        self.assertEqual(build.call_args.args, ("gmail", "v1"))
        self.assertFalse(build.call_args.kwargs["cache_discovery"])
        request = build.return_value.users.return_value.messages.return_value.send
        self.assertEqual(request.call_args.kwargs["userId"], "me")
        raw = request.call_args.kwargs["body"]["raw"]
        decoded = base64.urlsafe_b64decode(raw.encode("ascii"))
        parsed = message_from_bytes(decoded)
        self.assertEqual(parsed["From"], "SwitchFromTredence <switchcompapp@gmail.com>")
        self.assertEqual(parsed["To"], "learner@example.com")
        self.assertEqual(parsed["Subject"], "Verify your SwitchFromTredence account")
        parts = {
            part.get_content_type(): part.get_payload(decode=True).decode("utf-8")
            for part in parsed.walk()
            if part.get_content_type() in {"text/plain", "text/html"}
        }
        self.assertIn("Plain OTP 123456", parts["text/plain"])
        self.assertIn("HTML OTP 123456", parts["text/html"])
        self.assertEqual(
            build.call_args.kwargs["credentials"].scopes,
            [GMAIL_SEND_SCOPE],
        )

    @patch("google.oauth2.credentials.Credentials.refresh")
    @patch("googleapiclient.discovery.build")
    def test_revoked_refresh_token_is_safe_and_does_not_log_credentials(
        self,
        _build,
        refresh,
    ):
        refresh.side_effect = RefreshError("refresh-token-secret OTP 123456")
        with self.assertLogs("apps.accounts.email_service", level="ERROR") as logged:
            result = send_email(
                "learner@example.com",
                "Subject",
                "OTP 123456",
                "<p>OTP 123456</p>",
            )
        self.assertFalse(result.success)
        self.assertEqual(result.error_code, "oauth_refresh_failed")
        output = "\n".join(logged.output)
        self.assertNotIn("refresh-token-secret", output)
        self.assertNotIn("123456", output)
        self.assertNotIn("client-secret", output)

    @patch("google.oauth2.credentials.Credentials.refresh")
    @patch("googleapiclient.discovery.build")
    def test_gmail_api_failure_returns_failure_without_response_body_in_logs(
        self,
        build,
        _refresh,
    ):
        response = httplib2.Response({"status": "403"})
        response_body = {
            "error": {
                "code": 403,
                "message": "Do not log private response details or OTP 123456.",
                "errors": [{
                    "reason": "accessNotConfigured",
                    "message": "Private provider detail",
                }],
            }
        }
        build.return_value.users.return_value.messages.return_value.send.return_value.execute.side_effect = (
            HttpError(response, json.dumps(response_body).encode("utf-8"))
        )
        with self.assertLogs("apps.accounts.email_service", level="ERROR") as logged:
            result = send_email("learner@example.com", "Subject", "Body")
        self.assertFalse(result.success)
        self.assertEqual(result.error_code, "gmail_api_error")
        log_output = "\n".join(logged.output)
        self.assertIn("http_status=403", log_output)
        self.assertIn("google_error_reason=accessNotConfigured", log_output)
        self.assertNotIn("Do not log private response details", log_output)
        self.assertNotIn("123456", log_output)
        self.assertNotIn("Private provider detail", log_output)

    @override_settings(
        GOOGLE_OAUTH_CLIENT_ID="",
        GOOGLE_OAUTH_CLIENT_SECRET="",
        GOOGLE_OAUTH_REFRESH_TOKEN="",
    )
    def test_missing_oauth_configuration_fails_without_sending(self):
        result = send_email("learner@example.com", "Subject", "Body")
        self.assertFalse(result.success)
        self.assertEqual(result.error_code, "oauth_not_configured")
