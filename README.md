# DataForge — Complete Release (Phases 1–12)

DataForge is a free-to-use Django learning platform for Data Engineering. This package combines the existing Phases 1–8 with the integrated community, collaboration, messaging, AI tutor and production-readiness work in Phases 9–12.

## What's included

- **1–2 · Foundation:** custom email-based accounts, email verification, password reset, profile and responsive workspace.
- **3–4 · Learning engine:** specializations, modules, sections, topics, structured lesson reader, bookmarks, assessments and progress.
- **5 · Notes:** daily notes, importance labels, editing, search and calendar archive.
- **6–8 · Practice:** practical labs, guided projects, capstones, certification tracks and mock exams.
- **9 · DataForge Connect:** learner discovery, connection requests, daily five-question battles, submissions and connection-only peer reviews.
- **10 · Collaborative learning:** shared notebooks, invited members, comments, AI-assisted study-guide compilation and an optional AI Data Engineering tutor.
- **11 · Communication:** private messages between accepted connections, automatic refresh while chat is open, unread/read tracking and last-seen presence.
- **12 · Release readiness:** security defaults, environment configuration, migration files, tests, deployment notes and operational health endpoint.

## Windows setup

Use Python 3.12 or newer (Django 5.2). Open PowerShell in the `dataforge` folder.

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Put the generated key in `.env` as `SECRET_KEY=...`. For local development set `DEBUG=True` and keep the console email backend. Then run:

```powershell
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput
python manage.py runserver
```

Open `http://127.0.0.1:8000/`. The uploaded working SQLite database is included in this archive to retain the Phase 1–8 local learning data. Back it up before running upgrades or experimenting.

## Admin content setup

Visit `/admin/` and sign in as a staff user.

- **Daily battle:** create a `Daily battle`, set today's date, add exactly five `Battle question` records and publish it. Add reference answers for moderator guidance.
- **Shared notebooks:** users create notebooks in the app; owners can invite existing accounts by email.
- **Labs, projects, certifications and curriculum:** continue managing the content using their existing admin sections.

## Optional AI features

The platform runs without an AI provider. To enable tutor answers and AI compilation of shared notes, configure an OpenAI-compatible Chat Completions endpoint in `.env`:

```env
AI_API_KEY=your-provider-key
AI_API_BASE_URL=https://api.openai.com/v1
AI_MODEL=gpt-4o-mini
```

Use a provider/model available to your account. API usage may incur charges; the application itself does not charge learners. Never commit the key.

## Email verification and password recovery

For local development, `EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend` prints verification/reset emails in the terminal. For production, configure SMTP with `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS` and `DEFAULT_FROM_EMAIL`. Use an app password or provider credential, not your personal mailbox password.

## Render deployment

1. Create a managed PostgreSQL database and a Render web service.
2. Set `DATABASE_URL` to the database's **internal** connection URL where supported.
3. Set `SECRET_KEY` to a newly generated secret, `DEBUG=False`, `ALLOWED_HOSTS` to your Render hostname and `CSRF_TRUSTED_ORIGINS` to `https://your-service.onrender.com`.
4. Configure production SMTP and optional AI environment variables.
5. Use the included `render.yaml` build/start commands; ensure migrations run before serving traffic.
6. Run `python manage.py createsuperuser` once for admin access.

Render free web instances may sleep and their local filesystem is ephemeral. Use PostgreSQL for durable production data; do not rely on the included SQLite database or a free web instance filesystem for production persistence. Back up the database.

## Chat and presence behavior

Chat uses authenticated JSON endpoints with browser polling every three seconds while a conversation page is open. Presence is updated on authenticated requests and a user is treated as online for five minutes after the latest activity. This is near-real-time polling, not a WebSocket service; WebSocket scaling can be added later if concurrent chat volume requires it.

## Verification

The consolidated source was checked with Django system checks, migration drift checks and the full test suite for accounts, curriculum, notes, labs, projects, certifications, community, collaboration and messaging. The test suite passed in the build environment. Run these commands after extraction to verify your own environment:

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate
python manage.py test apps.accounts apps.curriculum apps.notes apps.labs apps.projects apps.certifications apps.community apps.collaboration apps.messaging
python manage.py collectstatic --noinput
```

## Important security notes

- `.env` is intentionally not included. Copy `.env.example` to `.env` and provide fresh secrets.
- Do not upload API keys, SMTP passwords or production database URLs to source control.
- The uploaded archive contained a local `.env`; it was excluded from this release. If it contained live credentials, rotate them.
- Keep Django, its dependencies and your host environment updated.
# Switch-Prep
