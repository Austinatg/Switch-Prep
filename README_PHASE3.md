# SwitchFromTredence — Phase 3: Curriculum Engine

This release adds an admin-managed curriculum engine on top of the Phase 2 project.

## New functionality
- Specializations, modules, sections, topics and external learning resources.
- Publish/unpublish controls and display ordering in Django Admin.
- Specialization catalogue with search.
- Specialization roadmap with module/section/topic hierarchy.
- Lesson pages with theory, objectives, takeaways, prerequisites and resources.
- User-specific topic completion tracking.
- Prerequisite checks before a topic can be marked complete.
- Repeatable starter content command.

## Apply Phase 3 to your existing project

This ZIP contains the complete updated project. Back up your current folder first, then extract this version into a new folder or replace the old project files.

In the project root, activate your existing virtual environment (or create one), then run:

```powershell
pip install -r requirements.txt
python manage.py makemigrations curriculum
python manage.py migrate
python manage.py seed_curriculum
python manage.py runserver
```

If you are reusing your existing Phase 2 database, do **not** delete `db.sqlite3`. The migration adds curriculum tables without removing your account data.

## Main URLs
- `/learning/` — specialization catalogue
- `/learning/<specialization-slug>/` — specialization roadmap
- `/learning/<specialization-slug>/topics/<topic-slug>/` — lesson reader
- `/admin/` — manage curriculum content

## Add content through Django Admin
1. Create a Specialization and set `is_published` only when ready.
2. Create Modules under that specialization.
3. Create Sections under each module.
4. Create Topics under each section and add theory, objectives, takeaways and prerequisites.
5. Add Topic Resources (official docs, videos, labs, articles or tools).
6. Publish each level of the hierarchy. A child is visible only when its parent is published.

The `seed_curriculum` command creates eight specialization shells and starter lessons for Data Engineering Fundamentals. It is safe to rerun and does not overwrite existing content.

## Scope note
Phase 3 implements the curriculum content and progress foundation. Quizzes, code execution labs, AI-generated content, notes and certification exam engines are separate later phases.
