from django.core.management.base import BaseCommand
from apps.curriculum.models import Specialization, Module, Section, Topic, TopicResource

TRACKS = [
    ("Data Engineering Fundamentals", "Build a strong foundation in databases, SQL, Python, Linux and core data concepts.", "beginner", 45, "database"),
    ("Advanced Data Engineering", "Master distributed processing, orchestration, streaming, modelling and reliability.", "advanced", 70, "layers"),
    ("Azure Data Engineering", "Build cloud data platforms with Azure storage, integration and analytics services.", "intermediate", 55, "cloud"),
    ("Azure Databricks", "Develop lakehouse solutions using Spark, Delta Lake, Unity Catalog and workflows.", "intermediate", 50, "spark"),
    ("AWS Data Engineering", "Build scalable pipelines using AWS storage, integration, processing and analytics services.", "intermediate", 60, "aws"),
    ("Google Cloud Data Engineering", "Work with BigQuery, Dataflow, Pub/Sub, Dataproc and the GCP data ecosystem.", "intermediate", 50, "gcp"),
    ("Snowflake", "Learn cloud warehousing, SQL, data sharing, Snowpark, streams and tasks.", "intermediate", 40, "snowflake"),
    ("Enterprise Data Architecture", "Design secure, governed, observable and cost-efficient enterprise data platforms.", "advanced", 45, "architecture"),
]

# Each module contains a description and a list of starter topics.
FOUNDATION = [
    (
        "Data Engineering landscape",
        "Understand what data engineering is, where it fits and how modern data platforms work.",
        [
            ("What is Data Engineering?",
             "Data Engineering is the discipline of designing, building and operating systems that collect, transform, store and deliver reliable data. Data engineers make data usable for analytics, applications and machine learning.",
             ["Explain the role of a data engineer", "Distinguish data engineering from analytics and data science"],
             ["Data pipelines move data from sources to destinations.", "Reliability, quality, security and scalability are core responsibilities."]),
            ("Data lifecycle and data pipeline",
             "A typical data lifecycle includes data generation, ingestion, storage, transformation, serving, governance and eventual retention or deletion. A pipeline automates movement and transformation between stages.",
             ["Describe the major stages of a data lifecycle", "Identify batch and streaming pipeline patterns"],
             ["A pipeline is a repeatable sequence of data operations.", "Design for observability and recovery from the start."]),
        ],
    ),
    (
        "Databases and SQL foundations",
        "Learn relational data, query structure and practical SQL fundamentals.",
        [
            ("Relational database concepts",
             "A relational database organizes information into tables made of rows and columns. Keys and constraints represent relationships and protect data integrity.",
             ["Explain tables, rows, columns and keys", "Understand primary and foreign keys"],
             ["Primary keys uniquely identify rows.", "Foreign keys represent relationships between tables."]),
            ("SQL SELECT and filtering",
             "SELECT retrieves columns from a table. WHERE filters rows, ORDER BY sorts results, and GROUP BY aggregates records into groups.",
             ["Write SELECT queries with filters", "Use sorting and basic aggregation"],
             ["Filter rows with WHERE before grouping.", "Use explicit column lists instead of SELECT * in production queries."]),
        ],
    ),
    (
        "Python for data engineering",
        "Use Python to automate data handling and build reliable pipeline components.",
        [
            ("Python data structures",
             "Lists, tuples, dictionaries and sets are core structures for representing and processing data in Python.",
             ["Choose suitable Python data structures", "Iterate and transform collections"],
             ["Dictionaries map keys to values.", "Sets contain unique elements."]),
            ("Files, JSON and error handling",
             "Data pipelines frequently read and write files and exchange JSON payloads. Robust code validates inputs and handles expected failures explicitly.",
             ["Read and write common file formats", "Handle exceptions and validate data"],
             ["Use context managers for file operations.", "Log failures with enough context to debug them."]),
        ],
    ),
    (
        "Data modelling essentials",
        "Understand how data is structured for operational and analytical workloads.",
        [
            ("OLTP versus OLAP",
             "OLTP systems support transactional workloads with frequent small writes. OLAP systems support analytical queries over larger volumes of historical data.",
             ["Compare transactional and analytical workloads", "Choose appropriate storage patterns"],
             ["OLTP optimizes transactions and consistency.", "OLAP optimizes analytical access patterns."]),
            ("Fact and dimension tables",
             "Dimensional models organize measurable business events in fact tables and descriptive context in dimension tables.",
             ["Identify facts, dimensions and grain", "Understand star schema structure"],
             ["Define fact table grain before adding measures.", "Dimensions provide descriptive context for facts."]),
        ],
    ),
]


class Command(BaseCommand):
    help = "Create a starter SwitchFromTredence curriculum. Safe to run repeatedly."

    def handle(self, *args, **options):
        created_specializations = 0
        created_modules = 0
        created_sections = 0
        created_topics = 0

        for order, (name, desc, level, hours, icon) in enumerate(TRACKS, 1):
            _, created = Specialization.objects.get_or_create(
                name=name,
                defaults={
                    "short_description": desc,
                    "description": desc,
                    "level": level,
                    "estimated_hours": hours,
                    "icon": icon,
                    "display_order": order,
                    "is_published": True,
                },
            )
            created_specializations += int(created)

        fundamentals = Specialization.objects.get(name="Data Engineering Fundamentals")

        for module_order, (module_title, module_desc, topics) in enumerate(FOUNDATION, 1):
            module, module_created = Module.objects.get_or_create(
                specialization=fundamentals,
                title=module_title,
                defaults={
                    "description": module_desc,
                    "display_order": module_order,
                    "is_published": True,
                },
            )
            created_modules += int(module_created)

            # The starter data is organised as one section per module.
            section, section_created = Section.objects.get_or_create(
                module=module,
                title="Core concepts",
                defaults={
                    "description": module_desc,
                    "display_order": 1,
                    "is_published": True,
                },
            )
            created_sections += int(section_created)

            for topic_order, (topic_title, theory, objectives, takeaways) in enumerate(topics, 1):
                topic, topic_created = Topic.objects.get_or_create(
                    section=section,
                    title=topic_title,
                    defaults={
                        "summary": theory[:280],
                        "theory": theory,
                        "learning_objectives": "\\n".join(objectives),
                        "key_takeaways": "\\n".join(takeaways),
                        "difficulty": "beginner",
                        "estimated_minutes": 20,
                        "display_order": topic_order,
                        "is_published": True,
                    },
                )
                created_topics += int(topic_created)

                if topic_created:
                    TopicResource.objects.get_or_create(
                        topic=topic,
                        title="Official Python documentation",
                        defaults={
                            "resource_type": "documentation",
                            "url": "https://docs.python.org/3/",
                            "description": "Official Python documentation. Add topic-specific resources in Django Admin.",
                            "is_free": True,
                        },
                    )

        self.stdout.write(
            self.style.SUCCESS(
                "Starter curriculum ready. "
                f"Created: {created_specializations} specializations, "
                f"{created_modules} modules, {created_sections} sections, "
                f"{created_topics} topics. Existing records were preserved."
            )
        )
