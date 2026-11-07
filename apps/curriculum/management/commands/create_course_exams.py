
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.curriculum.models import (
    Specialization,
    Module,
    Topic,
    Quiz,
)


class Command(BaseCommand):
    help = (
        "Create lesson, module and final course "
        "examination records."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        created = 0
        updated = 0

        specializations = Specialization.objects.filter(
            is_published=True
        )

        for specialization in specializations:

            # ------------------------------------------------
            # LESSON TESTS: 5 QUESTIONS EACH
            # ------------------------------------------------

            topics = Topic.objects.filter(
                section__module__specialization=specialization,
                section__module__is_published=True,
                section__is_published=True,
                is_published=True,
            ).select_related(
                "section__module"
            )

            for topic in topics:
                quiz, was_created = Quiz.objects.update_or_create(
                    topic=topic,
                    exam_type=Quiz.ExamType.LESSON,
                    defaults={
                        "specialization": specialization,
                        "module": topic.section.module,
                        "title": f"{topic.title} — Lesson Test",
                        "description": (
                            "Five multiple-choice questions "
                            "testing the concepts taught in "
                            "this lesson. This examination "
                            "can only be submitted once."
                        ),
                        "question_count": 5,
                        "is_published": True,
                    },
                )

                if was_created:
                    created += 1
                else:
                    updated += 1

            # ------------------------------------------------
            # MODULE TESTS: 10 QUESTIONS EACH
            # ------------------------------------------------

            modules = Module.objects.filter(
                specialization=specialization,
                is_published=True,
            )

            for module in modules:
                quiz, was_created = Quiz.objects.update_or_create(
                    module=module,
                    exam_type=Quiz.ExamType.MODULE,
                    defaults={
                        "specialization": specialization,
                        "topic": None,
                        "title": (
                            f"{module.title} — "
                            "Module Examination"
                        ),
                        "description": (
                            "Ten challenging MCQs covering "
                            "the entire module. This examination "
                            "can only be submitted once."
                        ),
                        "question_count": 10,
                        "is_published": True,
                    },
                )

                if was_created:
                    created += 1
                else:
                    updated += 1

            # ------------------------------------------------
            # COURSE EXAMINATIONS: 50 QUESTIONS EACH
            # ------------------------------------------------

            course_examinations = [
                (
                    Quiz.ExamType.COURSE_ONE,
                    "Course Examination I",
                ),
                (
                    Quiz.ExamType.COURSE_TWO,
                    "Course Examination II",
                ),
            ]

            for exam_type, exam_title in course_examinations:
                quiz, was_created = Quiz.objects.update_or_create(
                    specialization=specialization,
                    exam_type=exam_type,
                    defaults={
                        "module": None,
                        "topic": None,
                        "title": (
                            f"{specialization.name} — "
                            f"{exam_title}"
                        ),
                        "description": (
                            "Fifty high-difficulty MCQs "
                            "covering the complete course. "
                            "This examination can only be "
                            "submitted once."
                        ),
                        "question_count": 50,
                        "is_published": True,
                    },
                )

                if was_created:
                    created += 1
                else:
                    updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                "Examination records created successfully.\n"
                f"Created: {created}\n"
                f"Updated: {updated}\n\n"
                "Next: add MCQ questions and four choices "
                "to each examination through Django Admin."
            )
        )
