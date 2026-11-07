# SwitchFromTredence — Complete Combined Project (Phases 1–8)

This archive combines the existing SwitchFromTredence platform with the Phase 6–8 additions in one project tree:

- Accounts, registration, email verification and password reset
- Learning specializations, modules, sections, topic reader, progress, bookmarks and section assessments
- Daily notes, importance markers, search and calendar archive
- Practical labs with submissions and safe deterministic evaluation
- Guided projects, capstone milestones and instructor review
- Certification tracks, question banks, mock attempts and scoring
- Django Admin content management, responsive Django templates, static assets and Render configuration

## IMPORTANT: Install this as an update to your existing working project

The ZIP is designed to be extracted **over your existing `dataforge` folder**, not used to replace your database or migration history.

1. Stop the Django server.
2. Make a backup of the entire project folder and `db.sqlite3`.
3. Extract this ZIP. When prompted, choose the existing `D:\DataForge_Phase4_Phase5\dataforge` folder as the destination and allow files to merge/overwrite.
4. Do not delete the existing folder first. This preserves migration files created locally, including the already-resolved curriculum migration, and preserves `.env` and `db.sqlite3` (neither is included in this archive).
5. In PowerShell, from the project root, activate your existing `.venv` and run:

```powershell
pip install -r requirements.txt
python manage.py makemigrations labs projects certifications
python manage.py migrate
python manage.py test apps.curriculum apps.notes apps.labs apps.projects apps.certifications
python manage.py collectstatic --noinput
python manage.py runserver
```

If your project does not yet have migrations for the new apps, the `makemigrations` command above creates them. Do not regenerate or delete the existing `accounts`, `curriculum`, or `notes` migrations. The curriculum schema repair is assumed to have already been completed as confirmed in the conversation.

## Existing data

- Keep your current `db.sqlite3`; it is not included in this archive.
- Do not run `flush`, `migrate curriculum zero`, or delete migration files.
- No curriculum reseeding is needed.
- Existing accounts, learning progress, bookmarks, notes and assessments remain in the existing database.

## Main URLs

- `/` — Home / dashboard
- `/learning/` — Learning paths
- `/notes/` — Notes
- `/notes/calendar/` — Notes calendar
- `/labs/` — Practical labs
- `/projects/` — Projects and capstones
- `/certifications/` — Certification preparation
- `/admin/` — Django Admin
- `/health/` — Health check

## Phase 6 — Practical labs

Admin-published SQL, Python, PySpark, ETL and cloud labs, learner submissions, submission history and deterministic evaluation (exact output / required keywords). Submitted code is not executed on the Django web server; code-style tasks can be sent for manual review.

## Phase 7 — Projects and enterprise capstones

Admin-managed project catalog, outcomes, architecture notes, enrollments, milestones, acceptance criteria, artifact links and instructor feedback/review.

## Phase 8 — Certification preparation

Certification tracks for AWS, Azure, GCP, Databricks and Snowflake; exam guides, domains, question banks, mock attempts, server-side scoring, pass thresholds and answer explanations. Exam duration is currently informational rather than an enforced server-side timer.

## Deployment

For Render, configure a persistent managed PostgreSQL database through `DATABASE_URL`, set a strong `SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS`, and `CSRF_TRUSTED_ORIGINS`. Run migrations and `python manage.py collectstatic --noinput` during deployment. Do not rely on an ephemeral SQLite database for persistent production data.
