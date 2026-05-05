import django.db.models.deletion
from django.db import migrations, models


def backfill_household_barangay_fk(apps, schema_editor):
    connection = schema_editor.connection
    household_table = "residents_household"
    barangay_table = "residents_barangay"

    with connection.cursor() as cursor:
        cursor.execute(
            f"SELECT column_name FROM information_schema.columns WHERE table_name = %s",
            [household_table],
        )
        household_cols = {row[0] for row in cursor.fetchall()}

        if "barangay" not in household_cols or "barangay_id" not in household_cols:
            return

        cursor.execute(f"SELECT DISTINCT barangay FROM {household_table}")
        barangay_names = [row[0] for row in cursor.fetchall() if row[0]]

        for name in barangay_names:
            email_candidate = (
                "auto_" + "".join(ch.lower() for ch in name if ch.isalnum() or ch == "_")[:30] + "@example.com"
            )
            cursor.execute(
                f"""
                INSERT INTO {barangay_table} (name, municipality, email, captain_name, is_approved, created_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
                ON CONFLICT (name) DO NOTHING
                """,
                [name, "Ormoc City", email_candidate, "TBD", True],
            )

        cursor.execute(
            f"""
            UPDATE {household_table} h
            SET barangay_id = b.id
            FROM {barangay_table} b
            WHERE h.barangay_id IS NULL
              AND h.barangay = b.name
            """
        )


class Migration(migrations.Migration):
    dependencies = [
        ("residents", "0006_ensure_core_tables"),
    ]

    operations = [
        migrations.AddField(
            model_name="household",
            name="barangay",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="households",
                to="residents.barangay",
            ),
        ),
        migrations.RunPython(backfill_household_barangay_fk, reverse_code=migrations.RunPython.noop),
        migrations.AlterField(
            model_name="household",
            name="barangay",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="households",
                to="residents.barangay",
            ),
        ),
    ]
