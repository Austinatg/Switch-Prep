
import json
from pathlib import Path
from urllib.parse import quote_plus

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from apps.curriculum.models import (
    Specialization,
    Module,
    Section,
    Topic,
    TopicResource,
)


class Command(BaseCommand):
    help = "Import Data Engineering Fundamentals curriculum"

    @transaction.atomic
    def handle(self, *args, **options):

        # --------------------------------------------------
        # 1. Load curriculum JSON
        # --------------------------------------------------

        data_path = (
            Path(__file__).resolve().parents[2]
            / "fundamentals_content.json"
        )

        if not data_path.exists():
            raise CommandError(
                f"Curriculum JSON file not found: {data_path}"
            )

        try:
            lessons = json.loads(
                data_path.read_text(encoding="utf-8")
            )
        except json.JSONDecodeError as exc:
            raise CommandError(
                f"Invalid JSON file: {exc}"
            )

        if not isinstance(lessons, list) or not lessons:
            raise CommandError(
                "The JSON must contain a non-empty list of lessons."
            )

        required_fields = {
            "module_order",
            "module_title",
            "topic_order",
            "title",
            "content",
        }

        for index, item in enumerate(lessons, start=1):
            missing = required_fields - set(item.keys())

            if missing:
                raise CommandError(
                    f"Lesson {index} is missing fields: "
                    f"{', '.join(sorted(missing))}"
                )

        # --------------------------------------------------
        # 2. Get or create specialization
        # --------------------------------------------------

        spec = Specialization.objects.filter(
            name="Data Engineering Fundamentals"
        ).first()

        if spec is None:
            spec = Specialization.objects.create(
                name="Data Engineering Fundamentals",
                short_description=(
                    "A complete beginner-to-intermediate "
                    "foundation in data engineering."
                ),
                description=(
                    "13 modules covering the data engineering lifecycle."
                ),
                level="beginner",
                estimated_hours=90,
                icon="database",
                display_order=1,
                is_published=True,
            )

        else:
            spec.short_description = (
                "A complete beginner-to-intermediate "
                "foundation in data engineering."
            )
            spec.description = (
                "13 modules and 90 lessons covering "
                "the complete Data Engineering Fundamentals learning path."
            )
            spec.estimated_hours = 90
            spec.is_published = True
            spec.save()

        # --------------------------------------------------
        # 3. Group lessons by module
        # --------------------------------------------------

        grouped = {}

        for item in lessons:
            module_order = int(item["module_order"])

            grouped.setdefault(
                module_order, []
            ).append(item)

        # Validate module names before making changes.
        module_titles = {}

        for module_order, items in grouped.items():
            titles = {
                item["module_title"].strip()
                for item in items
            }

            if len(titles) != 1:
                raise CommandError(
                    f"Module order {module_order} has "
                    "inconsistent module titles."
                )

            module_titles[module_order] = titles.pop()

        active_module_titles = set(module_titles.values())

        # --------------------------------------------------
        # 4. Hide obsolete starter modules
        # --------------------------------------------------

        Module.objects.filter(
            specialization=spec
        ).exclude(
            title__in=active_module_titles
        ).update(
            is_published=False
        )

        # --------------------------------------------------
        # 5. Import modules, sections and topics
        # --------------------------------------------------

        imported_topics = 0
        imported_resources = 0

        for module_order in sorted(grouped):

            items = grouped[module_order]
            module_title = module_titles[module_order]

            self.stdout.write(
                f"\nProcessing Module {module_order}: {module_title}"
            )

            # ----------------------------------------------
            # 5A. Find existing module safely
            # ----------------------------------------------

            module_slug = slugify(module_title)

            module = Module.objects.filter(
                specialization=spec,
                slug=module_slug
            ).first()

            # Fallback: match by exact title.
            if module is None:
                module = Module.objects.filter(
                    specialization=spec,
                    title=module_title
                ).first()

            # Create only when no existing module matches.
            if module is None:

                module = Module(
                    specialization=spec,
                    title=module_title,
                    description="",
                    display_order=module_order,
                    is_published=True,
                )

            # Update existing or newly created module.
            module.title = module_title
            module.description = (
                f"Module {module_order}: {module_title}. "
                "Complete the lessons in sequence, use the linked "
                "resources and prepare for the interview questions."
            )
            module.display_order = module_order
            module.is_published = True
            module.save()

            # ----------------------------------------------
            # 5B. Get or create section
            # ----------------------------------------------

            section = Section.objects.filter(
                module=module,
                title="Lessons"
            ).first()

            if section is None:
                section = Section(
                    module=module,
                    title="Lessons",
                    description=f"All lessons in {module_title}",
                    display_order=1,
                    is_published=True,
                )

            section.description = (
                f"All lessons in {module_title}"
            )
            section.display_order = 1
            section.is_published = True
            section.save()

            # ----------------------------------------------
            # 5C. Import individual lessons
            # ----------------------------------------------

            for item in sorted(
                items,
                key=lambda x: int(x["topic_order"])
            ):

                title = item["title"].strip()
                content = item["content"]

                # Preserve structured content from JSON.
                detailed_explanation = item.get(
                    "detailed_explanation", ""
                )
                real_world_example = item.get(
                    "real_world_example", ""
                )
                practical_guidance = item.get(
                    "practical_guidance", ""
                )
                key_takeaways = item.get(
                    "key_takeaways", []
                )
                learning_objectives = item.get(
                    "learning_objectives", []
                )
                interview_questions = item.get(
                    "interview_questions", []
                )

                # Support both string and list formats.
                if isinstance(learning_objectives, list):
                    learning_objectives = "\n".join(
                        learning_objectives
                    )

                if isinstance(key_takeaways, list):
                    key_takeaways = "\n".join(
                        str(value) for value in key_takeaways
                    )

                # Find by title first.
                topic = Topic.objects.filter(
                    section=section,
                    title=title
                ).first()

                # Create if not found.
                if topic is None:
                    topic = Topic(
                        section=section,
                        title=title,
                    )

                # Update all lesson fields.
                topic.summary = item.get(
                    "summary",
                    content.replace("\n", " ")[:280]
                )

                # Keep the complete PDF lesson text.
                topic.theory = content

                topic.learning_objectives = (
                    learning_objectives
                    or "Understand the concept\n"
                       "Explain its role in a data platform\n"
                       "Apply it to a real-world scenario"
                )

                topic.key_takeaways = (
                    key_takeaways
                    or "Understand the definition and purpose\n"
                       "Connect the concept to a production pipeline"
                )

                topic.interview_questions = interview_questions

                topic.difficulty = item.get(
                    "difficulty", "beginner"
                )

                topic.estimated_minutes = item.get(
                    "estimated_minutes", 35
                )

                topic.display_order = int(
                    item["topic_order"]
                )

                topic.is_published = True

                topic.save()

                imported_topics += 1

                # ------------------------------------------
                # 5D. Import resources
                # ------------------------------------------

                resources = item.get("resources", {})

                documentation = resources.get(
                    "documentation", []
                )

                videos = resources.get(
                    "videos", []
                )

                resource_items = []

                for resource in documentation:
                    resource_items.append({
                        "title": resource.get(
                            "title", "Documentation"
                        ),
                        "resource_type": "documentation",
                        "url": resource.get("url", ""),
                        "description": resource.get(
                            "note",
                            resource.get("description", "")
                        ),
                        "is_free": resource.get(
                            "is_free", True
                        ),
                        "display_order": 1,
                    })

                for resource in videos:
                    resource_items.append({
                        "title": resource.get(
                            "title", "Video lesson"
                        ),
                        "resource_type": "video",
                        "url": resource.get("url", ""),
                        "description": resource.get(
                            "note",
                            resource.get("description", "")
                        ),
                        "is_free": True,
                        "display_order": 2,
                    })

                # Backward-compatible fallback if resources
                # are absent from the JSON.
                if not resource_items:
                    query = quote_plus(title)

                    resource_items = [
                        {
                            "title": "IBM — Data Engineering overview",
                            "resource_type": "documentation",
                            "url": (
                                "https://www.ibm.com/think/topics/"
                                "data-engineering"
                            ),
                            "description": (
                                "Background reading and concepts."
                            ),
                            "is_free": True,
                            "display_order": 1,
                        },
                        {
                            "title": f"Video lessons — {title}",
                            "resource_type": "video",
                            "url": (
                                "https://www.youtube.com/results?"
                                f"search_query={query}+data+engineering"
                            ),
                            "description": (
                                "Topic-specific video search."
                            ),
                            "is_free": True,
                            "display_order": 2,
                        },
                    ]

                for resource_data in resource_items:

                    url = resource_data["url"].strip()

                    if not url:
                        continue

                    resource = TopicResource.objects.filter(
                        topic=topic,
                        title=resource_data["title"]
                    ).first()

                    if resource is None:
                        resource = TopicResource(
                            topic=topic,
                            title=resource_data["title"],
                        )

                    resource.resource_type = (
                        resource_data["resource_type"]
                    )
                    resource.url = url
                    resource.description = (
                        resource_data["description"]
                    )
                    resource.is_free = (
                        resource_data["is_free"]
                    )
                    resource.display_order = (
                        resource_data["display_order"]
                    )

                    resource.save()

                    imported_resources += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f"Completed Module {module_order}"
                )
            )

        # --------------------------------------------------
        # 6. Final import summary
        # --------------------------------------------------

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Data Engineering Fundamentals import completed!"
            )
        )

        self.stdout.write(
            f"Modules processed: {len(grouped)}"
        )

        self.stdout.write(
            f"Lessons processed: {imported_topics}"
        )

        self.stdout.write(
            f"Resources processed: {imported_resources}"
        )
