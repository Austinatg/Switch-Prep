
from django.core.management.base import BaseCommand

from apps.curriculum.curriculum_importer import (
    import_curriculum,
)


class Command(BaseCommand):
    help = "Import the Advanced Data Engineering curriculum."

    def handle(self, *args, **options):
        import_curriculum(
            json_filename="advanced_data_engineering_content.json",
            specialization_name="Advanced Data Engineering",
            short_description=(
                "Advanced distributed data platforms, streaming, "
                "lakehouse engineering and production operations."
            ),
            description=(
                "13 modules and 88 lessons covering advanced SQL, "
                "distributed systems, Spark, lakehouse formats, CDC, "
                "streaming, DataOps, quality, performance, security, "
                "operations and an enterprise capstone."
            ),
            level="advanced",
            estimated_hours=70,
            icon="layers",
            command=self,
        )
