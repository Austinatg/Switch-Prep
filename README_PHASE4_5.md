# DataForge — Phase 4 + Phase 5

This combined release adds a richer lesson experience, section assessments and personal daily notes.

## Apply to your Phase 3 project

1. Back up your Phase 3 folder and `db.sqlite3`.
2. Extract this complete project package to a new folder.
3. If you want to retain your Phase 3 accounts and curriculum, copy your existing `db.sqlite3` into the new project's root.
4. Activate the virtual environment and install requirements:

```powershell
pip install -r requirements.txt
```

5. Generate migrations for the new fields/models and the Notes app:

```powershell
python manage.py makemigrations curriculum notes
python manage.py migrate
```

6. Run tests:

```powershell
python manage.py test apps.curriculum apps.notes
```

7. Start the server:

```powershell
python manage.py runserver
```

## Phase 4 features
- Lesson reader with previous/next topic navigation.
- Topic bookmarks.
- Admin-managed code examples with copy-to-clipboard.
- Section-level multiple-choice assessments.
- Attempt history and scored result review.
- Passing threshold configurable per assessment.
- Existing user-specific topic progress and prerequisite checks retained.

## Phase 5 features
- Daily notes, one point per card.
- Importance labels: no highlight, red, yellow and highlight.
- Add, edit and delete points.
- Search notes for a selected date.
- Date picker and archive links.
- Monthly calendar with note-day indicators.
- User ownership enforced on edit/delete operations.

## Admin workflow for lessons and tests
- Open a Topic in Django Admin and add Topic Code Examples.
- Open its Section and create an Assessment.
- Add Assessment Questions, then add choices to each question.
- Mark exactly one correct choice per question.
- Publish the Assessment to show it in the lesson reader.

## Routes
- `/learning/` — specializations
- `/learning/<specialization>/` — roadmap
- `/learning/<specialization>/topics/<topic>/` — lesson
- `/learning/assessments/<id>/` — assessment
- `/notes/` — daily notes
- `/notes/calendar/` — notes calendar

## Important implementation notes
- Assessment attempts are stored per user. The backend calculates scores; browser-submitted scores are never trusted.
- Notes are private to their owner. Users cannot edit or delete another user's notes by changing an ID.
- Code examples are displayed as escaped text in a code block; they are not executed on the server.
- The calendar and daily note dates use the application date. For production, keep Django `TIME_ZONE` configured to your intended user base or evolve to per-user timezone handling.
