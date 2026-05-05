from django.db import migrations


def ensure_columns(apps, schema_editor):
    User = apps.get_model("users", "User")
    connection = schema_editor.connection
    table = User._meta.db_table

    with connection.cursor() as cursor:
        try:
            description = connection.introspection.get_table_description(cursor, table)
        except Exception:
            return

        existing = {col.name for col in description}

        for field_name in ("is_approved", "barangay_name"):
            field = User._meta.get_field(field_name)
            if field.column not in existing:
                schema_editor.add_field(User, field)


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0002_alter_user_role"),
    ]

    operations = [
        migrations.RunPython(ensure_columns, reverse_code=migrations.RunPython.noop),
    ]
