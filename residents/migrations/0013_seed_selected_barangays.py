from django.db import migrations


def seed_selected_barangays(apps, schema_editor):
    Barangay = apps.get_model("residents", "Barangay")

    defaults = [
        ("Sabang Bao", "sabangbao@bmis.local"),
        ("Labrador", "labrador@bmis.local"),
        ("Bayog", "bayog@bmis.local"),
    ]

    for name, email in defaults:
        Barangay.objects.get_or_create(
            name=name,
            defaults={
                "municipality": "Ormoc City",
                "email": email,
                "captain_name": "TBD",
                "is_approved": True,
                "admin_user": None,
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ("residents", "0012_official_notification_fks_and_resident_user_state"),
    ]

    operations = [
        migrations.RunPython(seed_selected_barangays, reverse_code=migrations.RunPython.noop),
    ]

