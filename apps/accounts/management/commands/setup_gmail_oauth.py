import os
import re
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

OAUTH_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
REQUIRED_SENDER = "switchcompapp@gmail.com"


def _store_refresh_token(env_path, refresh_token):
    if env_path.is_symlink():
        raise CommandError("Refusing to update a symbolic-link .env file.")

    temporary_path = None
    try:
        original = env_path.read_bytes() if env_path.exists() else b""
        lines = original.splitlines(keepends=True)
        replacement = b"GOOGLE_OAUTH_REFRESH_TOKEN=" + refresh_token.encode("ascii")
        updated_lines = []
        found = False
        for line in lines:
            if re.match(
                rb"^\s*(?:export\s+)?GOOGLE_OAUTH_REFRESH_TOKEN\s*=",
                line,
            ):
                ending = b"\r\n" if line.endswith(b"\r\n") else b"\n" if line.endswith(b"\n") else b""
                updated_lines.append(replacement + ending)
                found = True
            else:
                updated_lines.append(line)
        if not found:
            if updated_lines and not updated_lines[-1].endswith((b"\n", b"\r")):
                updated_lines[-1] += b"\n"
            updated_lines.append(replacement + b"\n")
        updated = b"".join(updated_lines)

        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=env_path.parent,
            prefix=".env.",
            delete=False,
        ) as temporary:
            temporary.write(updated)
            temporary_path = Path(temporary.name)
        if os.name != "nt":
            os.chmod(temporary_path, 0o600)
        os.replace(temporary_path, env_path)
    except OSError as exc:
        if temporary_path and temporary_path.exists():
            try:
                temporary_path.unlink()
            except OSError as cleanup_error:
                raise CommandError(
                    "Could not remove a temporary OAuth credential file. "
                    f"Remove {temporary_path} securely."
                ) from cleanup_error
        raise CommandError(
            "Could not securely update the local .env file. No token was displayed."
        ) from None


class Command(BaseCommand):
    help = "Authorize switchcompapp@gmail.com for Gmail API email delivery."

    def handle(self, *args, **options):
        if not settings.GOOGLE_OAUTH_CLIENT_ID or not settings.GOOGLE_OAUTH_CLIENT_SECRET:
            raise CommandError(
                "Set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET before "
                "running this command."
            )
        if settings.GMAIL_SENDER_EMAIL.lower() != REQUIRED_SENDER:
            raise CommandError(
                "Set GMAIL_SENDER_EMAIL=switchcompapp@gmail.com before authorizing."
            )

        self.stdout.write(
            "When the browser opens, sign in as switchcompapp@gmail.com and "
            "confirm that account before granting access."
        )
        try:
            from google.auth.exceptions import GoogleAuthError
            from oauthlib.oauth2.rfc6749.errors import OAuth2Error
            from requests.exceptions import RequestException
            from google_auth_oauthlib.flow import InstalledAppFlow

            flow = InstalledAppFlow.from_client_config(
                {
                    "installed": {
                        "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
                        "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": settings.GOOGLE_OAUTH_TOKEN_URI,
                        "redirect_uris": ["http://localhost:8080/"],
                    }
                },
                scopes=OAUTH_SCOPES,
            )
            credentials = flow.run_local_server(
                host="localhost",
                port=8080,
                open_browser=True,
                access_type="offline",
                prompt="consent",
                login_hint=REQUIRED_SENDER,
                authorization_prompt_message=(
                    "Authorize the Gmail sender account in the browser window."
                ),
                success_message=(
                    "Authorization completed. You may close this browser window."
                ),
            )
            if not credentials.refresh_token:
                raise CommandError(
                    "Google did not return a refresh token. Revoke this app's access "
                    "for the sender account and run the command again."
                )

            _store_refresh_token(
                Path(settings.BASE_DIR) / ".env",
                credentials.refresh_token,
            )
        except CommandError:
            raise
        except ImportError:
            raise CommandError(
                "The Gmail OAuth packages are missing. Install requirements.txt first."
            ) from None
        except (GoogleAuthError, OAuth2Error, RequestException, OSError, TimeoutError):
            raise CommandError(
                "Gmail OAuth authorization failed. Check local network access and "
                "Google Cloud OAuth configuration, then try again."
            ) from None

        self.stdout.write(
            self.style.SUCCESS(
                "Gmail sender authorized. The refresh token was stored in .env "
                "without displaying it."
            )
        )
