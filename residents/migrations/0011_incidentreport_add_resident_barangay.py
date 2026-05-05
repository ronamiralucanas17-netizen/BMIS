import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("residents", "0010_announcement_created_by_state"),
    ]

    operations = [
        migrations.AddField(
            model_name="incidentreport",
            name="barangay",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="reports",
                to="residents.barangay",
            ),
        ),
        migrations.AddField(
            model_name="incidentreport",
            name="resident",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="reports",
                to="residents.resident",
            ),
        ),
    ]

