
from django.core.management.base import BaseCommand

from apps.curriculum.curriculum_importer import (
    import_curriculum,
)


class Command(BaseCommand):
    help = "Import the Azure Data Engineering curriculum."

    def handle(self, *args, **options):
        import_curriculum(
            json_filename="azure_data_engineering_content.json",
            specialization_name="Azure Data Engineering",
            short_description=(
                "Build secure, scalable data platforms with Azure "
                "storage, integration, processing and analytics services."
            ),
            description=(
                "13 modules and 93 lessons covering ADLS Gen2, "
                "Azure Data Factory, Databricks, Synapse, Azure SQL, "
                "Cosmos DB, Event Hubs, Stream Analytics, Purview, "
                "security, monitoring, DevOps and an enterprise capstone."
            ),
            level="intermediate",
            estimated_hours=55,
            icon="cloud",
            command=self,
        )
