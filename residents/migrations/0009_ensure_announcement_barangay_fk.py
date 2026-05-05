import django.db.models.deletion
from django.db import migrations, models


def backfill_announcement_barangay_fk(apps, schema_editor):
    connection = schema_editor.connection
    announcement_table = "residents_announcement"
    barangay_table = "residents_barangay"

    Barangay = apps.get_model("residents", "Barangay")
    connection = schema_editor.connection

    with connection.cursor() as cursor:
        existing_tables = set(connection.introspection.table_names(cursor))
        if Barangay._meta.db_table not in existing_tables:
            schema_editor.create_model(Barangay)

        cursor.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = %s",
            [announcement_table],
        )
        cols = {row[0] for row in cursor.fetchall()}

        if "barangay" not in cols or "barangay_id" not in cols:
            return

        cursor.execute(
            f"SELECT DISTINCT barangay FROM {announcement_table} WHERE barangay_id IS NULL AND barangay IS NOT NULL AND barangay <> ''"
        )
        barangay_names = [row[0] for row in cursor.fetchall() if row and row[0]]

        for name in barangay_names:
            email_candidate = f"auto_ann_{abs(hash(name)) % 1000000000}@example.com"
            cursor.execute(
                f"""
                INSERT INTO {barangay_table} (name, municipality, email, captain_name, is_approved, created_at, admin_user_id)
                VALUES (%s, %s, %s, %s, %s, NOW(), NULL)
                ON CONFLICT (name) DO NOTHING
                """,
                [name, "Ormoc City", email_candidate, "TBD", True],
            )

        cursor.execute(
            f"""
            UPDATE {announcement_table} a
            SET barangay_id = b.id
            FROM {barangay_table} b
            WHERE a.barangay_id IS NULL
              AND a.barangay = b.name
            """
        )


class Migration(migrations.Migration):
    dependencies = [
        ("residents", "0008_barangay_admin_user"),
    ]

    operations = [
        migrations.AddField(
            model_name="announcement",
            name="barangay",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="announcements",
                to="residents.barangay",
            ),
        ),
        migrations.RunPython(backfill_announcement_barangay_fk, reverse_code=migrations.RunPython.noop),
    ]
