
import json
from pathlib import Path

from django.core.management.base import CommandError
from django.db import transaction
from django.utils.text import slugify

from apps.curriculum.models import (
    Specialization,
    Module,
    Section,
    Topic,
    TopicResource,
)


@transaction.atomic
def import_curriculum(
    *,
    json_filename,
    specialization_name,
    short_description,
    description,
    level,
    estimated_hours,
    icon,
    command,
):
    data_path = Path(__file__).resolve().parent / json_filename

    if not data_path.exists():
        raise CommandError(
            f"Curriculum JSON not found: {data_path}"
        )

    try:
        lessons = json.loads(
            data_path.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as exc:
        raise CommandError(
            f"Invalid JSON in {data_path}: {exc}"
        )

    required = {
        "module_order",
        "module_title",
        "topic_order",
        "title",
        "content",
    }

    if not isinstance(lessons, list) or not lessons:
        raise CommandError(
            "Curriculum JSON must be a non-empty list."
        )

    for index, item in enumerate(lessons, 1):
        if not isinstance(item, dict):
            raise CommandError(
                f"Lesson record {index} is not an object."
            )

        missing = required - set(item)

        if missing:
            raise CommandError(
                f"Lesson record {index} is missing: "
                f"{', '.join(sorted(missing))}"
            )

    grouped = {}

    for item in lessons:
        module_order = int(item["module_order"])
        grouped.setdefault(module_order, []).append(item)

    module_titles = {}

    for order, items in grouped.items():
        titles = {
            str(x["module_title"]).strip()
            for x in items
        }

        if len(titles) != 1:
            raise CommandError(
                f"Module order {order} has inconsistent titles."
            )

        module_titles[order] = titles.pop()

    # Create or update specialization.
    spec, _ = Specialization.objects.get_or_create(
        name=specialization_name,
        defaults={
            "short_description": short_description,
            "description": description,
            "level": level,
            "estimated_hours": estimated_hours,
            "icon": icon,
            "is_published": True,
        },
    )

    spec.short_description = short_description
    spec.description = description
    spec.level = level
    spec.estimated_hours = estimated_hours
    spec.icon = icon
    spec.is_published = True
    spec.save()

    # Unpublish outdated modules rather than deleting them.
    active_titles = set(module_titles.values())

    Module.objects.filter(
        specialization=spec
    ).exclude(
        title__in=active_titles
    ).update(
        is_published=False
    )

    counts = {
        "modules": 0,
        "sections": 0,
        "topics": 0,
        "resources": 0,
    }

    for module_order in sorted(grouped):
        items = sorted(
            grouped[module_order],
            key=lambda x: int(x["topic_order"]),
        )

        module_title = module_titles[module_order]
        module_slug = slugify(module_title)

        # Match existing modules by slug first.
        # This prevents duplicate-slug integrity errors.
        module = Module.objects.filter(
            specialization=spec,
            slug=module_slug,
        ).first()

        if module is None:
            module = Module.objects.filter(
                specialization=spec,
                title=module_title,
            ).first()

        created_module = module is None

        if created_module:
            module = Module(specialization=spec)

        module.title = module_title
        module.description = (
            f"Module {module_order}: {module_title}. "
            "Follow the lessons in sequence and use the "
            "linked references, practical guidance and "
            "interview preparation."
        )
        module.display_order = module_order
        module.is_published = True
        module.save()

        counts["modules"] += int(created_module)

        # Create or update the Lessons section.
        section = Section.objects.filter(
            module=module,
            slug=slugify("Lessons"),
        ).first()

        if section is None:
            section = Section.objects.filter(
                module=module,
                title="Lessons",
            ).first()

        created_section = section is None

        if created_section:
            section = Section(module=module)

        section.title = "Lessons"
        section.description = (
            f"All lessons in {module_title}"
        )
        section.display_order = 1
        section.is_published = True
        section.save()

        counts["sections"] += int(created_section)

        for item in items:
            title = str(item["title"]).strip()
            topic_slug = slugify(title)

            # Reuse existing topics where possible.
            topic = Topic.objects.filter(
                section=section,
                slug=topic_slug,
            ).first()

            if topic is None:
                topic = Topic.objects.filter(
                    section=section,
                    title=title,
                ).first()

            created_topic = topic is None

            if created_topic:
                topic = Topic(section=section)

            # Learning objectives
            objectives = item.get(
                "learning_objectives", []
            )

            if isinstance(objectives, list):
                objectives = "\n".join(
                    str(x) for x in objectives
                )
            elif not isinstance(objectives, str):
                objectives = str(objectives)

            # Key takeaways
            takeaways = item.get(
                "key_takeaways", []
            )

            if isinstance(takeaways, list):
                takeaways = "\n".join(
                    str(x) for x in takeaways
                )
            elif not isinstance(takeaways, str):
                takeaways = str(takeaways)

            # Interview questions and answers
            interview = item.get(
                "interview_questions", []
            )

            normalized_questions = []

            for q in interview:
                if isinstance(q, dict):
                    normalized_questions.append({
                        "question": q.get(
                            "question", ""
                        ),
                        "answer": q.get(
                            "answer",
                            q.get("answer_guidance", ""),
                        ),
                    })

            # Update topic content.
            topic.section = section
            topic.title = title
            topic.summary = str(
                item.get(
                    "summary",
                    item["content"][:280],
                )
            )[:320]
            topic.theory = item["content"]
            topic.learning_objectives = objectives
            topic.key_takeaways = takeaways
            topic.interview_questions = (
                normalized_questions
            )
            topic.difficulty = item.get(
                "difficulty", "intermediate"
            )
            topic.estimated_minutes = int(
                item.get("estimated_minutes", 35)
            )
            topic.display_order = int(
                item["topic_order"]
            )
            topic.is_published = True
            topic.save()

            counts["topics"] += int(created_topic)

            # Import learning resources.
            resources = item.get("resources", {})
            resource_specs = []

            for key, kind in (
                ("documentation", "documentation"),
                ("videos", "video"),
                ("articles", "article"),
            ):
                for resource in resources.get(key, []):
                    resource_specs.append({
                        "title": resource.get(
                            "title", kind.title()
                        ),
                        "kind": kind,
                        "url": resource.get("url", ""),
                        "description": resource.get(
                            "description",
                            resource.get("note", ""),
                        ),
                        "is_free": resource.get(
                            "is_free", True
                        ),
                        "order": {
                            "documentation": 1,
                            "video": 2,
                            "article": 3,
                        }[kind],
                    })

            # Optional diagram/image search resource.
            image = item.get("image") or {}
            image_search_url = image.get(
                "search_url"
            )

            if image_search_url:
                resource_specs.append({
                    "title": (
                        f"Image / diagram search — {title}"
                    ),
                    "kind": "article",
                    "url": image_search_url,
                    "description": (
                        "Search for an appropriate lesson visual. "
                        "This is a search page, not an "
                        "embedded image."
                    ),
                    "is_free": True,
                    "order": 4,
                })

            for data in resource_specs:
                url = str(data["url"]).strip()

                if not url:
                    continue

                resource = TopicResource.objects.filter(
                    topic=topic,
                    title=data["title"],
                ).first()

                if resource is None:
                    resource = TopicResource(
                        topic=topic,
                        title=data["title"],
                    )

                resource.resource_type = data["kind"]
                resource.url = url
                resource.description = (
                    data["description"][:300]
                )
                resource.is_free = bool(
                    data["is_free"]
                )
                resource.display_order = data["order"]
                resource.save()

                counts["resources"] += 1

    command.stdout.write(
        command.style.SUCCESS(
            f"{specialization_name} import completed. "
            f"Lessons processed: {len(lessons)}; "
            f"modules created: {counts['modules']}; "
            f"sections created: {counts['sections']}; "
            f"topics created: {counts['topics']}; "
            f"resource records processed: "
            f"{counts['resources']}. "
            "Existing topic IDs and user progress "
            "are preserved."
        )
    )
