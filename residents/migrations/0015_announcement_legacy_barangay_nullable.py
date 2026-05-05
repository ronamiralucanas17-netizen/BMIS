from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("residents", "0014_household_legacy_barangay_nullable"),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE residents_announcement ALTER COLUMN barangay DROP NOT NULL;",
            reverse_sql="ALTER TABLE residents_announcement ALTER COLUMN barangay SET NOT NULL;",
        ),
    ]

