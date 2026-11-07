
"""Populate DataForge lesson, module and course MCQs.

File:
apps/curriculum/management/commands/populate_question_bank.py

Required JSON files:
apps/curriculum/data/fundamentals_content.json
apps/curriculum/data/advanced_data_engineering_content.json
apps/curriculum/data/azure_data_engineering_content.json

Run:
python manage.py populate_question_bank --replace-generated
"""

from __future__ import annotations

import hashlib
import json
import random
import re

from collections import defaultdict
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.curriculum.models import (
    Specialization,
    Module,
    Topic,
    Quiz,
    QuizQuestion,
    QuizChoice,
)


DATA_DIR = Path(__file__).resolve().parents[2] / "data"

COURSES = [
    (
        "fundamentals_content.json",
        ("fundamental", "data engineering fundamentals"),
    ),
    (
        "advanced_data_engineering_content.json",
        ("advanced",),
    ),
    (
        "azure_data_engineering_content.json",
        ("azure",),
    ),
]


LESSON_PATTERNS = [
    (
        "A team is implementing {topic} for a production pipeline. "
        "Which approach best reflects the lesson's core engineering objective?",
        "Prefer an explicit, repeatable design with a defined contract, "
        "measurable correctness checks and observable execution.",
        [
            "Choose the tool with the most features and leave its defaults unchanged.",
            "Move the entire workload into one script with no checkpoints or validation.",
            "Optimize throughput first and defer correctness and recovery controls.",
        ],
    ),
    (
        "A pipeline built around {topic} succeeds on a small sample but "
        "fails intermittently at production scale. What should the engineer do first?",
        "Characterize the workload and inspect the relevant limits, data shape, "
        "execution metrics and failure evidence before changing the design.",
        [
            "Increase every resource limit without measuring the bottleneck.",
            "Suppress the errors so downstream jobs continue as if the run succeeded.",
            "Delete the failed records and report the run as complete.",
        ],
    ),
    (
        "Which test provides the strongest evidence that an implementation "
        "of {topic} is correct?",
        "A test that checks both technical invariants and the expected business "
        "meaning of representative outputs, including edge cases.",
        [
            "A test that only confirms the process exits with code zero.",
            "A test that checks only that the output file exists.",
            "A test that compares row counts without checking keys, values or business rules.",
        ],
    ),
    (
        "A source system changes its data contract while a pipeline uses "
        "{topic}. Which response is safest?",
        "Detect and validate the contract change, make compatibility decisions "
        "explicit, and deploy a tested transformation or versioned contract.",
        [
            "Silently coerce every new field into a string and continue.",
            "Drop unfamiliar fields without recording the change.",
            "Overwrite historical outputs before checking downstream dependencies.",
        ],
    ),
    (
        "A retry of a job involving {topic} can run after a partial failure. "
        "Which design property most reduces the risk of corrupt output?",
        "Idempotent processing with stable keys or checkpoints, "
        "plus validation before publishing the result.",
        [
            "Appending all rows again because retries are expected to be rare.",
            "Using the wall-clock time as the only record identifier.",
            "Disabling retries and relying on an operator to rebuild everything manually.",
        ],
    ),
]


MODULE_PATTERNS = [
    (
        "A platform team combines {a} and {b}. A late upstream change "
        "causes one downstream dataset to become inconsistent. "
        "Which response best addresses the system-level problem?",
        "Trace dependencies and data contracts, isolate the affected stage, "
        "replay from a safe checkpoint and validate downstream invariants "
        "before republishing.",
        [
            "Rerun every pipeline concurrently without checking dependencies.",
            "Patch the dashboard query to hide the inconsistent rows.",
            "Delete the raw data and restart ingestion without preserving lineage.",
        ],
    ),
    (
        "A workload spanning {a} and {b} must meet a freshness SLA "
        "while controlling cost. Which decision process is most defensible?",
        "Compare measured volume, latency, concurrency, retention, "
        "recovery objectives and cost against the SLA, then select "
        "the simplest design that meets them.",
        [
            "Select the most expensive architecture because it is likely to be fastest.",
            "Choose batch or streaming solely based on which technology is newer.",
            "Ignore workload measurements and optimize only for developer familiarity.",
        ],
    ),
    (
        "During a production review of {a}, which evidence most strongly "
        "demonstrates operational readiness?",
        "Run-level lineage, freshness and quality metrics, alert thresholds, "
        "documented recovery steps and tested replay behavior.",
        [
            "A screenshot showing that the pipeline ran once on a developer laptop.",
            "A successful deployment with no monitoring or ownership assigned.",
            "A large number of logs without correlation IDs or actionable alerts.",
        ],
    ),
    (
        "A design decision in {a} improves throughput but increases "
        "the chance of duplicate publication. What should be prioritized?",
        "Preserve correctness through deduplication or idempotent writes "
        "and validate the publication boundary before tuning throughput further.",
        [
            "Accept duplicates because consumers can remove them later.",
            "Disable all validation to preserve the throughput gain.",
            "Increase parallelism again so duplicate records arrive faster.",
        ],
    ),
    (
        "A team must evolve a platform covering {a} and {b} "
        "without breaking consumers. Which approach is best?",
        "Use versioned data contracts, compatibility checks, "
        "staged rollout and consumer-impact validation.",
        [
            "Change schemas in place and notify consumers after deployment.",
            "Maintain undocumented differences between development and production.",
            "Replace stable identifiers whenever a schema changes.",
        ],
    ),
]


COURSE_PATTERNS = [
    (
        "A global retailer processes high-volume order events using "
        "{a} and {b}. Events can arrive late, be duplicated and contain "
        "evolving fields. Which end-to-end design is strongest?",
        "Use durable raw retention, stable event identifiers, "
        "schema/contract validation, event-time handling, "
        "idempotent transformations, quality checks and observable "
        "publication with replay support.",
        [
            "Process only the latest event received, overwrite previous state "
            "and discard raw inputs.",
            "Assume delivery is exactly once, skip deduplication "
            "and publish without validation.",
            "Reject all late events and silently drop fields "
            "not present in the first schema.",
        ],
    ),
    (
        "A data platform meets its throughput target but repeatedly "
        "publishes incomplete datasets. Which engineering response "
        "should come first?",
        "Define completeness and correctness invariants, gate publication "
        "on validation, expose freshness/quality metrics "
        "and make recovery reproducible.",
        [
            "Increase compute until incomplete runs become less frequent.",
            "Change the dashboard refresh interval so users notice the issue less often.",
            "Treat successful task completion as proof that the data is complete.",
        ],
    ),
    (
        "A regulated organization is redesigning a pipeline that spans "
        "{a} and {b}. Which architecture best balances governance "
        "and operability?",
        "Apply least privilege, classified data handling, auditable lineage, "
        "controlled secrets, explicit retention and tested recovery "
        "at each processing boundary.",
        [
            "Give every pipeline identity administrator access to simplify operations.",
            "Copy sensitive datasets into unmanaged locations for faster debugging.",
            "Store credentials in source code and rely on repository access controls alone.",
        ],
    ),
    (
        "A pipeline migration changes storage and compute technologies "
        "but must preserve analytical results. What is the most reliable "
        "migration strategy?",
        "Define output contracts and representative reconciliation tests, "
        "run old and new paths in parallel, compare results "
        "and cut over with rollback criteria.",
        [
            "Switch all consumers immediately and investigate differences later.",
            "Compare only total storage size and assume semantic equivalence.",
            "Migrate the newest partition only and delete the previous implementation.",
        ],
    ),
    (
        "A team is choosing between a simpler architecture and "
        "a distributed design for {a}. Which principle should guide "
        "the decision?",
        "Use measured workload and service-level requirements; "
        "introduce distributed complexity only when scale, latency, "
        "availability or isolation requirements justify it.",
        [
            "Always choose distributed processing because it is more scalable in theory.",
            "Always choose a single process even when it cannot meet the required SLA.",
            "Choose the design with the largest number of managed services.",
        ],
    ),
]


DISTRACTOR_EXPLANATIONS = (
    "The other options omit important validation or recovery controls, "
    "hide failures, or introduce complexity without sufficient evidence."
)


def clean(value):
    """Normalize whitespace and handle null values."""
    return re.sub(r"\s+", " ", str(value or "")).strip()


def stable_seed(value):
    """Generate a reproducible seed from a string."""
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def make_item(pattern, context, difficulty, index):
    """Build one MCQ with four shuffled choices."""
    stem, correct, incorrect = pattern

    a = context[0] if context else "data ingestion"
    b = context[1] if len(context) > 1 else "data quality"

    prompt = stem.format(topic=a, a=a, b=b)
    prompt += f" (Assessment scenario {index:02d})"

    choices = [correct] + list(incorrect)

    rng = random.Random(stable_seed(prompt))
    rng.shuffle(choices)

    return {
        "prompt": prompt,
        "answer": correct,
        "explanation": correct + " " + DISTRACTOR_EXPLANATIONS,
        "difficulty": difficulty,
        "choices": choices,
    }


def generate_lesson(topic_title, module_title):
    """Generate five lesson-level MCQs."""
    context = [
        clean(topic_title),
        clean(module_title),
    ]

    return [
        make_item(pattern, context, "medium", index + 1)
        for index, pattern in enumerate(LESSON_PATTERNS)
    ]


def generate_higher(topics, patterns, count, difficulty, label):
    """Generate module-level or course-level questions."""
    titles = [
        clean(topic)
        for topic in topics
        if clean(topic)
    ]

    if not titles:
        titles = [label]

    output = []

    for index in range(count):
        a = titles[(index * 2) % len(titles)]
        b = titles[(index * 2 + 1) % len(titles)]

        pattern = patterns[index % len(patterns)]

        item = make_item(
            pattern,
            [a, b],
            difficulty,
            index + 1,
        )

        item["prompt"] = item["prompt"].replace(
            f"(Assessment scenario {index + 1:02d})",
            f"(Scenario {index + 1:02d}: {label})",
        )

        output.append(item)

    return output


class Command(BaseCommand):
    help = (
        "Generate lesson, module and two course-level MCQ exams "
        "for all three DataForge courses."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--replace-generated",
            action="store_true",
            help="Replace previously generated questions.",
        )

        parser.add_argument(
            "--data-dir",
            default=str(DATA_DIR),
            help="Directory containing the three course JSON files.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        data_dir = Path(options["data_dir"])
        replace_generated = options["replace_generated"]

        summary = []

        for filename, name_hints in COURSES:
            path = data_dir / filename

            if not path.exists():
                raise CommandError(
                    f"Missing JSON file: {path}\n"
                    "Copy the course JSON files into the data directory."
                )

            try:
                records = json.loads(
                    path.read_text(encoding="utf-8")
                )
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise CommandError(
                    f"Could not read {path}: {exc}"
                ) from exc

            if not isinstance(records, list):
                raise CommandError(
                    f"{filename} must contain a JSON array of lessons."
                )

            course = self.find_course(name_hints)

            if course is None:
                available = list(
                    Specialization.objects.values_list(
                        "name",
                        flat=True,
                    )
                )

                raise CommandError(
                    f"Could not identify Specialization for {filename}. "
                    f"Available courses: {available}"
                )

            self.stdout.write(
                f"\nProcessing course: {course.name}"
            )

            topic_map = {}

            for module in Module.objects.filter(
                specialization=course
            ):
                module_key = clean(module.title).casefold()

                for topic in Topic.objects.filter(
                    section__module=module
                ):
                    topic_key = clean(topic.title).casefold()

                    topic_map[
                        (module_key, topic_key)
                    ] = topic

            grouped = defaultdict(list)

            lesson_count = 0
            unmatched_count = 0
            matched_topic_ids = set()

            for record in records:
                if not isinstance(record, dict):
                    raise CommandError(
                        f"Invalid lesson record in {filename}: "
                        "expected a JSON object."
                    )

                module_title = clean(
                    record.get("module_title")
                )

                topic_title = clean(
                    record.get("title")
                )

                lookup_key = (
                    module_title.casefold(),
                    topic_title.casefold(),
                )

                topic = topic_map.get(lookup_key)

                if topic is None:
                    candidates = [
                        candidate
                        for (module_key, topic_key), candidate
                        in topic_map.items()
                        if topic_key == topic_title.casefold()
                    ]

                    if len(candidates) == 1:
                        topic = candidates[0]

                if topic is None:
                    unmatched_count += 1

                    self.stdout.write(
                        self.style.WARNING(
                            f"UNMATCHED: {course.name} / "
                            f"{module_title} / {topic_title}"
                        )
                    )

                    continue

                if topic.pk in matched_topic_ids:
                    self.stdout.write(
                        self.style.WARNING(
                            f"DUPLICATE SOURCE LESSON: "
                            f"{course.name} / {topic.title}"
                        )
                    )
                    continue

                matched_topic_ids.add(topic.pk)

                module = topic.section.module

                grouped[module].append(
                    (topic, record)
                )

                quiz, created = Quiz.objects.get_or_create(
                    specialization=course,
                    topic=topic,
                    exam_type="lesson",
                    defaults={
                        "title": f"Lesson Test: {topic.title}",
                        "question_count": 5,
                        "is_published": True,
                    },
                )

                quiz.question_count = 5
                quiz.is_published = True

                quiz.save(
                    update_fields=[
                        "question_count",
                        "is_published",
                    ]
                )

                questions = generate_lesson(
                    topic.title,
                    module.title,
                )

                self.populate(
                    quiz,
                    questions,
                    replace_generated,
                )

                lesson_count += 1

            module_count = 0
            all_titles = []

            for module, items in grouped.items():
                titles = [
                    topic.title
                    for topic, record in items
                ]

                all_titles.extend(titles)

                quiz, created = Quiz.objects.get_or_create(
                    specialization=course,
                    module=module,
                    exam_type="module",
                    defaults={
                        "title": f"Module Test: {module.title}",
                        "question_count": 10,
                        "is_published": True,
                    },
                )

                quiz.question_count = 10
                quiz.is_published = True

                quiz.save(
                    update_fields=[
                        "question_count",
                        "is_published",
                    ]
                )

                questions = generate_higher(
                    topics=titles,
                    patterns=MODULE_PATTERNS,
                    count=10,
                    difficulty="hard",
                    label=module.title,
                )

                self.populate(
                    quiz,
                    questions,
                    replace_generated,
                )

                module_count += 1

            course_tests = [
                (
                    "course_one",
                    "Course Comprehensive Test 1",
                ),
                (
                    "course_two",
                    "Course Comprehensive Test 2",
                ),
            ]

            for exam_type, title in course_tests:
                quiz, created = Quiz.objects.get_or_create(
                    specialization=course,
                    exam_type=exam_type,
                    defaults={
                        "title": title,
                        "question_count": 50,
                        "is_published": True,
                    },
                )

                quiz.title = title
                quiz.question_count = 50
                quiz.is_published = True

                quiz.save(
                    update_fields=[
                        "title",
                        "question_count",
                        "is_published",
                    ]
                )

                if exam_type == "course_one":
                    course_topics = list(all_titles)
                else:
                    course_topics = list(
                        reversed(all_titles)
                    )

                questions = generate_higher(
                    topics=course_topics,
                    patterns=COURSE_PATTERNS,
                    count=50,
                    difficulty="hard",
                    label=title,
                )

                if exam_type == "course_two":
                    for question in questions:
                        question["prompt"] = (
                            question["prompt"].replace(
                                "Scenario",
                                "Integrated scenario",
                            )
                        )

                self.populate(
                    quiz,
                    questions,
                    replace_generated,
                )

            summary.append(
                {
                    "course": course.name,
                    "source_lessons": len(records),
                    "matched_lessons": lesson_count,
                    "unmatched_lessons": unmatched_count,
                    "modules": module_count,
                }
            )

        self.stdout.write(
            self.style.SUCCESS(
                "\nQuestion bank generation completed."
            )
        )

        for item in summary:
            self.stdout.write(
                f"\nCourse: {item['course']}\n"
                f"Source lessons: {item['source_lessons']}\n"
                f"Matched lesson exams: {item['matched_lessons']}\n"
                f"Unmatched source lessons: {item['unmatched_lessons']}\n"
                f"Module exams: {item['modules']}\n"
                f"Course exams: 2 (50 questions each)"
            )

        self.stdout.write(
            self.style.WARNING(
                "\nIMPORTANT: These are template-generated draft MCQs. "
                "Review question relevance, answer keys, and difficulty "
                "in Django Admin before using them for real assessments."
            )
        )

    
    def find_course(self, hints):
        """Find a Specialization using its name field."""

        courses = Specialization.objects.all()

        for course in courses:
            course_name = clean(course.name).casefold()

            if any(
                hint.casefold() in course_name
                for hint in hints
            ):
                return course

        return None

    def populate(self, quiz, bank, replace):
        """Insert generated questions and their four choices."""

        marker = "[AUTO-GENERATED DATAFORGE]"

        existing = QuizQuestion.objects.filter(
            quiz=quiz,
            prompt__startswith=marker,
        )

        if replace:
            # Preserve questions referenced by mistake records.
            has_mistakes = existing.filter(
                user_mistakes__isnull=False
            ).exists()

            if has_mistakes:
                self.stdout.write(
                    self.style.WARNING(
                        f"Skipping replacement for '{quiz.title}' "
                        "because generated questions have mistake records."
                    )
                )
                return

            existing.delete()

        elif existing.exists():
            return

        current_count = QuizQuestion.objects.filter(
            quiz=quiz
        ).count()

        remaining = max(
            0,
            quiz.question_count - current_count,
        )

        for index, item in enumerate(
            bank[:remaining],
            start=current_count + 1,
        ):
            question = QuizQuestion.objects.create(
                quiz=quiz,
                prompt=f"{marker} {item['prompt']}",
                explanation=item["explanation"],
                difficulty=item["difficulty"],
                display_order=index,
                is_active=True,
            )

            for order, choice_text in enumerate(
                item["choices"],
                start=1,
            ):
                QuizChoice.objects.create(
                    question=question,
                    text=choice_text,
                    is_correct=(
                        choice_text == item["answer"]
                    ),
                    display_order=order,
                )
