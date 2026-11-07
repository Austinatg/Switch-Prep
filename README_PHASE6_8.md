# SwitchFromTredence — Phases 6, 7 and 8

This is an upgrade to the working Phase 4–5 project. It preserves the existing Django architecture, user accounts, curriculum, notes, bookmarks and topic progress.

## Phase 6 — Practical labs and evaluation
- Published SQL, Python, PySpark, ETL and cloud labs, filterable by category.
- Starter content, instructions, hints and learner submissions.
- Safe deterministic checks: exact-output and required-keyword evaluation.
- Code and SQL are **not executed** on the Django server. Use manual review for executable code or production-style work; this avoids running untrusted submissions on the web process.
- Submission history and scores per learner.

## Phase 7 — Guided projects and enterprise capstones
- Project catalog with level, estimated duration, learning outcomes and architecture notes.
- Admin-managed milestones and acceptance criteria.
- Learner enrollment and milestone submissions with optional artifact links.
- Admin reviewers can approve submissions or request revisions.

## Phase 8 — Certification preparation
- Admin-managed AWS, Azure, GCP, Databricks and Snowflake certification tracks.
- Exam codes, official exam-guide links, experience guidance and exam domains.
- Timed mock-exam metadata, question banks, scoring, pass thresholds, attempt history and answer explanations.
- Time limit is displayed as guidance; server-side timed auto-submission is not included in this release.

## Upgrade (Windows PowerShell)
1. Back up your current project folder and `db.sqlite3`.
2. Extract this ZIP into a new folder. Copy your existing Phase 4–5 `db.sqlite3` into the extracted `dataforge` folder. Do not replace a production PostgreSQL database.
3. Install dependencies in your existing virtual environment: `pip install -r requirements.txt`.
4. Generate migrations for the three new apps only:
   `python manage.py makemigrations labs projects certifications`
5. Apply migrations: `python manage.py migrate`
6. Run tests: `python manage.py test apps.labs apps.projects apps.certifications apps.curriculum apps.notes`
7. Start locally: `python manage.py runserver`
8. Before deployment: `python manage.py collectstatic --noinput`.

**Do not delete or regenerate existing curriculum, accounts or notes migrations.** The update deliberately adds new apps without rewriting existing migration history. No curriculum reseeding is required.

## Admin content setup
- Add `Lab` entries and publish them. Select `exact` for output matching, `keywords` for required concepts, or `manual review` for code/project-style tasks.
- Add `Project` entries, then add milestones inline. Publish the project when ready.
- Add `CertificationTrack`, then its `CertificationExam` records, questions and choices. Mark the track and exam as published.
- Review `LabAttempt` and `MilestoneSubmission` in Django Admin. Update submission status, score and feedback as appropriate.

## Production notes
- Keep API keys and secrets out of source control.
- For persistent production data on Render, use managed PostgreSQL via `DATABASE_URL`; ephemeral local SQLite storage can be lost on free instances.
- The mock exam records attempts and calculates scores on the server. The displayed duration is informational in this release, not an enforced timer.
