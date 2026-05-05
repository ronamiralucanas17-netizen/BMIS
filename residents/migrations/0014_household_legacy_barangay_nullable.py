from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("residents", "0013_seed_selected_barangays"),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE residents_household ALTER COLUMN barangay DROP NOT NULL;",
            reverse_sql="ALTER TABLE residents_household ALTER COLUMN barangay SET NOT NULL;",
        ),
    ]

