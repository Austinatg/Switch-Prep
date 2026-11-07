import base64
import logging
import re
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from email.utils import formataddr

logger = logging.getLogger(__name__)
GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"


@dataclass(frozen=True)
class EmailDeliveryResult:
    success: bool
    error_code: str | None = None


def _send_mime_message(message):
    required_settings = (
        settings.GOOGLE_OAUTH_CLIENT_ID,
        settings.GOOGLE_OAUTH_CLIENT_SECRET,
        settings.GOOGLE_OAUTH_REFRESH_TOKEN,
        settings.GOOGLE_OAUTH_TOKEN_URI,
        settings.GMAIL_SENDER_EMAIL,
    )
    if not all(required_settings):
        return EmailDeliveryResult(False, "oauth_not_configured")

    try:
        import httplib2
        from google.auth.exceptions import (
            GoogleAuthError,
            RefreshError,
            TransportError,
        )
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.errors import Error as GoogleApiError
    except ImportError as exc:
        return _failure("gmail_dependency_missing", exc)

    try:
        credentials = Credentials(
            token=None,
            refresh_token=settings.GOOGLE_OAUTH_REFRESH_TOKEN,
            token_uri=settings.GOOGLE_OAUTH_TOKEN_URI,
            client_id=settings.GOOGLE_OAUTH_CLIENT_ID,
            client_secret=settings.GOOGLE_OAUTH_CLIENT_SECRET,
            scopes=[GMAIL_SEND_SCOPE],
        )
        credentials.refresh(Request())
        gmail = build("gmail", "v1", credentials=credentials, cache_discovery=False)
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
        gmail.users().messages().send(
            userId="me",
            body={"raw": raw_message},
        ).execute()
        return EmailDeliveryResult(True)
    except RefreshError as exc:
        return _failure("oauth_refresh_failed", exc)
    except GoogleApiError as exc:
        return _failure("gmail_api_error", exc)
    except TransportError as exc:
        return _failure("network_error", exc)
    except GoogleAuthError as exc:
        return _failure("oauth_error", exc)
    except (httplib2.HttpLib2Error, OSError, TimeoutError) as exc:
        return _failure("network_error", exc)


def _failure(error_code, exc):
    status = getattr(getattr(exc, "resp", None), "status", None)
    if not isinstance(status, int):
        try:
            status = int(status)
        except (TypeError, ValueError):
            status = None

    reason = None
    details = getattr(exc, "error_details", None)
    if isinstance(details, dict):
        details = [details]
    if isinstance(details, (list, tuple)):
        for detail in details:
            if not isinstance(detail, dict):
                continue
            candidate = detail.get("reason")
            if (
                isinstance(candidate, str)
                and re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", candidate)
            ):
                reason = candidate
                break

    logger.error(
        "Gmail API delivery failed: error_code=%s exception_class=%s "
        "http_status=%s google_error_reason=%s",
        error_code,
        type(exc).__name__,
        status,
        reason,
    )
    return EmailDeliveryResult(False, error_code)


def send_email(to_email, subject, text_body, html_body=None):
    message = MIMEMultipart("alternative") if html_body else MIMEText(
        text_body,
        "plain",
        "utf-8",
    )
    if html_body:
        message.attach(MIMEText(text_body, "plain", "utf-8"))
        message.attach(MIMEText(html_body, "html", "utf-8"))
    message["From"] = formataddr(
        ("SwitchFromTredence", settings.GMAIL_SENDER_EMAIL)
    )
    message["To"] = to_email
    message["Subject"] = subject
    return _send_mime_message(message)


class GmailEmailBackend(BaseEmailBackend):
    """Deliver Django-generated mail through the Gmail API, never SMTP."""

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        sent = 0
        for email_message in email_messages:
            if not email_message.recipients():
                continue
            mime_message = email_message.message()
            if mime_message.get("From"):
                mime_message.replace_header(
                    "From",
                    formataddr(
                        ("SwitchFromTredence", settings.GMAIL_SENDER_EMAIL)
                    ),
                )
            result = _send_mime_message(mime_message)
            if result.success:
                sent += 1
            elif not self.fail_silently:
                raise RuntimeError(
                    "Gmail API email delivery failed "
                    f"({result.error_code or 'unknown_error'})."
                )
        return sent
