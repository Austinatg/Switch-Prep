from django.db import migrations, models
from django.utils import timezone


def ensure_verification_send_fields(apps, schema_editor):
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

    fields = (
        ("send_window_started_at", models.DateTimeField(default=timezone.now)),
        ("send_count", models.PositiveSmallIntegerField(default=1)),
    )
    for field_name, field in fields:
        if field_name not in existing:
            verification_model.add_to_class(field_name, field)
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
            if field_name == "send_count":
                default_value = 1
            else:
                default_value = connection.ops.adapt_datetimefield_value(
                    timezone.now()
                )
            with connection.cursor() as cursor:
                cursor.execute(
                    f"UPDATE {quoted_table} SET {quoted_column} = %s "
                    f"WHERE {quoted_column} IS NULL",
                    [default_value],
                )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    ensure_verification_send_fields,
                    migrations.RunPython.noop,
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="emailverification",
                    name="send_window_started_at",
                    field=models.DateTimeField(default=timezone.now),
                ),
                migrations.AddField(
                    model_name="emailverification",
                    name="send_count",
                    field=models.PositiveSmallIntegerField(default=1),
                ),
            ],
        ),
    ]
