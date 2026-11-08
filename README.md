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

## Data Engineering practical labs

The Practical Labs dashboard provides separate Python, SQL, and PySpark tracks,
progress summaries, recommendations, recent attempts, bookmarks, private drafts,
achievements, and ten end-to-end case studies. Seed the starter question bank after
applying migrations:

```powershell
python manage.py migrate
python manage.py seed_labs
```

The command is idempotent and only creates missing starter records; it leaves
existing admin-edited content untouched. It also runs during the included Render
build. Staff can add and publish more questions or case studies in Django Admin
without changing frontend code. User attempts, bookmarks,
drafts, and earned achievements are associated with the authenticated custom
user. A question is counted as solved only when the server-side evaluation or an
authorized review marks its attempt passed; browser-submitted scores are never
accepted. The current starter bank uses review-required submissions rather than
claiming browser test results are server-verified. Hidden grading is not
implemented because this deployment deliberately does not execute learner code
on the Django server.

### Execution capabilities and limitations

- **Python:** Monaco Editor with a textarea fallback; Pyodide runs Python in the
  learner's browser using WebAssembly. Some packages (including pandas) load on
  demand. A browser connection to the public runtime CDN may be required.
- **SQL:** SQL.js runs the exercise against a preloaded SQLite database entirely
  in the browser. The schema explorer and result table are local to that page.
  SQL dialects are not interchangeable: the labs explicitly identify SQLite
  syntax, date functions, type behavior, and query results as SQLite-specific.
- **PySpark:** the browser offers a clearly marked learning simulator for a
  limited subset of DataFrame operations. It is **not Apache Spark**, does not
  execute arbitrary Python, and cannot model executors, shuffles, streaming,
  cluster performance, or Spark SQL semantics. Unsupported operations are
  reported rather than represented as Spark results.
- **Real PySpark:** no external runtime is configured and no paid service is
  added. The labs app defines a future execution-adapter interface but does not
  submit code anywhere. To run an exercise locally, install a supported Java 17
  runtime and a compatible PySpark release in a separate environment, then run:

  ```powershell
  py -3.12 -m venv .venv-spark
  .venv-spark\Scripts\Activate.ps1
  python -m pip install pyspark
  python
  ```

  ```python
  from pyspark.sql import SparkSession

  spark = SparkSession.builder.master("local[*]").appName("DataEngineeringLab").getOrCreate()
  rows = [("o-1", "c-1", 42.5), ("o-2", "c-1", 12.0)]
  orders = spark.createDataFrame(rows, "order_id STRING, customer_id STRING, amount DOUBLE")
  orders.groupBy("customer_id").sum("amount").show()
  spark.stop()
  ```

  Paste the exercise's actual PySpark reference solution into that local
  environment and adapt the sample rows to its documented schema. Browser
  simulation results must not be interpreted as Spark execution.

Monaco, Pyodide, and SQL.js are loaded from public CDNs; a restrictive browser
network policy can leave the plain-text editor available while disabling a
runtime. AI assistance is optional and uses the existing server-side Gemini
configuration; credentials are not sent to the browser. PythonAnywhere free
hosting remains compatible because it does not run Spark or arbitrary submitted
code on the web server.

## Gemini AI learning tools

The AI Tutor, lesson assistant, Code Assistant, personalized learning planner,
interview simulator and shared-notebook study-guide compilation use Google's
`google-genai` SDK. The application does not use OpenAI, paid fallbacks, or
automatic billing upgrades. AI tools remain unavailable until `GEMINI_API_KEY`
is configured in the server environment; never put the key in templates,
JavaScript, source control or logs.

Configure these values in `.env` for local development or the host's environment
settings:

```env
GEMINI_API_KEY=your-google-ai-studio-key
GEMINI_MODEL=gemini-2.5-flash
DATAFORGE_AI_DAILY_LIMIT=10
DATAFORGE_AI_GLOBAL_DAILY_LIMIT=100
DATAFORGE_AI_MAX_INPUT_CHARS=4000
DATAFORGE_AI_MAX_OUTPUT_TOKENS=800
DATAFORGE_AI_TIMEOUT_MS=30000
```

The model name is configurable and its default may need changing as Google's
model availability evolves. Check the current Gemini API and free-tier
availability for your account before deployment. The application caps requests
but cannot guarantee Google's quota or free-tier availability; actual limits
vary by model and account. When a provider quota or application limit is reached,
the request stops with a friendly message. No paid fallback is attempted.
Code submissions are analyzed as text and are never executed by the server.

### PythonAnywhere connectivity

Do not assume local connectivity proves PythonAnywhere connectivity. Some
PythonAnywhere free accounts restrict outbound internet access, and Gemini API
requests may require Google API domains to be allowlisted. From a PythonAnywhere
Bash console, test basic access without sending an API key:

```bash
python -c "import socket; socket.create_connection(('generativelanguage.googleapis.com', 443), timeout=10); print('Gemini API host is reachable')"
```

Successful connection confirms DNS and TCP reachability; a DNS, timeout or
connection error indicates an egress/allowlist issue. Request
allowlisting from PythonAnywhere support if required, then test the AI feature
from the deployed web app. This project does not add a direct Supabase/PostgreSQL
dependency; verify database connectivity separately before choosing a hosted
database.

## Email verification and password recovery

For local development, `EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend` prints verification/reset emails in the terminal. For production, configure SMTP with `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS` and `DEFAULT_FROM_EMAIL`. Use an app password or provider credential, not your personal mailbox password.

## Render deployment

1. Create a managed PostgreSQL database and a Render web service.
2. Set `DATABASE_URL` to the database's **internal** connection URL where supported.
3. Set `SECRET_KEY` to a newly generated secret, `DEBUG=False`, `ALLOWED_HOSTS` to your Render hostname and `CSRF_TRUSTED_ORIGINS` to `https://your-service.onrender.com`.
4. Configure production SMTP and optional Gemini environment variables.
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
