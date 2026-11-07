from django.db import migrations
from django.utils import timezone


def repair_verification_send_fields(apps, schema_editor):
    verification_model = apps.get_model("accounts", "EmailVerification")
    connection = schema_editor.connection
    table_name = verification_model._meta.db_table

    with connection.cursor() as cursor:
        existing = {
            column.name: column
            for column in connection.introspection.get_table_description(
                cursor,
                table_name,
            )
        }

    for field_name in ("send_window_started_at", "send_count"):
        field = verification_model._meta.get_field(field_name)
        if field_name not in existing:
            schema_editor.add_field(verification_model, field)
            with connection.cursor() as cursor:
                existing = {
                    column.name: column
                    for column in connection.introspection.get_table_description(
                        cursor,
                        table_name,
                    )
                }

        column = existing[field_name]
        if column.null_ok:
            quoted_table = schema_editor.quote_name(table_name)
            quoted_column = schema_editor.quote_name(field_name)
            default_value = (
                1
                if field_name == "send_count"
                else connection.ops.adapt_datetimefield_value(timezone.now())
            )
            with connection.cursor() as cursor:
                cursor.execute(
                    f"UPDATE {quoted_table} SET {quoted_column} = %s "
                    f"WHERE {quoted_column} IS NULL",
                    [default_value],
                )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_emailverification_send_count_and_more"),
    ]

    operations = [
        migrations.RunPython(
            repair_verification_send_fields,
            migrations.RunPython.noop,
        ),
    ]
