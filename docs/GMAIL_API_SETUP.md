# Gmail API email delivery

SwitchFromTredence sends application mail through the Gmail API and OAuth 2.0.
It does not use SMTP, Gmail passwords, App Passwords, or an external email
provider. The OAuth scope is limited to `https://www.googleapis.com/auth/gmail.send`.

## Google Cloud setup

1. In Google Cloud Console, create or select a project.
2. Enable **Gmail API** for that project.
3. Configure the OAuth consent screen. Add the Gmail sender as a test user while
   the consent screen is in testing.
4. Create an OAuth client ID with application type **Desktop app**.
5. Copy its client ID and client secret into your local `.env` as
   `GOOGLE_OAUTH_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET`. Do not commit them.
6. Confirm `GMAIL_SENDER_EMAIL=switchcompapp@gmail.com`.
7. Run `python manage.py setup_gmail_oauth` on your local computer and sign in
   as `switchcompapp@gmail.com` in the browser. The command uses the temporary
   local redirect `http://localhost:8080/`, verifies that Google returned a
   refresh token, and writes that token to the one matching variable in `.env`
   without displaying it. The Desktop OAuth client does not require adding a
   public web callback URL in Google Cloud.
8. Restart Django and send a test registration email. Do not run this
   authorization command on PythonAnywhere.

If the OAuth consent screen is in **Testing**, Google may expire refresh tokens
after seven days. For longer-lived use, configure the consent screen and
publishing status according to Google's current verification requirements for
the Gmail sending scope.

The command only requests `gmail.send`; account selection is prefilled to the
sender address as a convenience. Confirm the Google account shown in the
browser before approving. If Google does not issue a refresh token, revoke the
application's access for this sender in the Google Account security settings,
then run the command again.

## Local configuration

The relevant local `.env` keys are:

```dotenv
GOOGLE_OAUTH_CLIENT_ID=
GOOGLE_OAUTH_CLIENT_SECRET=
GOOGLE_OAUTH_REFRESH_TOKEN=
GOOGLE_OAUTH_TOKEN_URI=https://oauth2.googleapis.com/token
GMAIL_SENDER_EMAIL=switchcompapp@gmail.com
```

The setup command adds or updates only `GOOGLE_OAUTH_REFRESH_TOKEN`, preserving
the other `.env` entries. `.env`, OAuth JSON files, and token files are ignored
by Git.

## PythonAnywhere

In the PythonAnywhere web app's environment configuration, set all five
variables above, using the same OAuth client ID, client secret, and refresh
token. Store the refresh token directly in the host's environment settings;
do not upload `.env`, `credentials.json`, or `token.json`. Reload the WSGI app
after updating the environment. The Django WSGI process refreshes access
tokens as needed and sends using the Gmail API.

PythonAnywhere free accounts may restrict outbound access. Gmail API delivery
requires outbound HTTPS access to Google's OAuth token endpoint and Gmail API.
This project does not probe these endpoints automatically or switch to another
provider. If outbound access is blocked or OAuth is revoked, registration
remains unverified and the page shows a delivery error; use PythonAnywhere's
documented allowlist/support process before relying on delivery.

## Tests

Run account tests with:

```powershell
python manage.py check
python manage.py test apps.accounts
```

The tests mock token refresh and Gmail API calls; they do not send email or
perform OAuth authorization.
