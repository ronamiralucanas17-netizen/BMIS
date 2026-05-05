from django.db import migrations


def ensure_columns(apps, schema_editor):
    Barangay = apps.get_model("residents", "Barangay")
    Resident = apps.get_model("residents", "Resident")
    connection = schema_editor.connection
    table = Resident._meta.db_table

    with connection.cursor() as cursor:
        existing_tables = set(connection.introspection.table_names(cursor))
        if Barangay._meta.db_table not in existing_tables:
            schema_editor.create_model(Barangay)

        try:
            description = connection.introspection.get_table_description(cursor, table)
        except Exception:
            return

        existing = {col.name for col in description}

        field = Resident._meta.get_field("barangay")
        if field.column not in existing:
            schema_editor.add_field(Resident, field)


class Migration(migrations.Migration):
    dependencies = [
        ("residents", "0004_alter_resident_date_of_birth_and_more"),
    ]

    operations = [
        migrations.RunPython(ensure_columns, reverse_code=migrations.RunPython.noop),
    ]
