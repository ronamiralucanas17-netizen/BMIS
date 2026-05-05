from django.db import migrations


def ensure_tables(apps, schema_editor):
    connection = schema_editor.connection

    with connection.cursor() as cursor:
        existing_tables = set(connection.introspection.table_names(cursor))

        model_names_in_order = [
            "Official",
            "Service",
            "IncidentReport",
            "Notification",
        ]

        for model_name in model_names_in_order:
            Model = apps.get_model("residents", model_name)
            if Model._meta.db_table not in existing_tables:
                schema_editor.create_model(Model)
                existing_tables.add(Model._meta.db_table)


class Migration(migrations.Migration):
    dependencies = [
        ("residents", "0005_ensure_resident_barangay_column"),
    ]

    operations = [
        migrations.RunPython(ensure_tables, reverse_code=migrations.RunPython.noop),
    ]

