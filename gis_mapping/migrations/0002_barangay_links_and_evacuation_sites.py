import django.contrib.gis.db.models.fields
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("gis_mapping", "0001_initial"),
        ("residents", "0012_official_notification_fks_and_resident_user_state"),
    ]

    operations = [
        migrations.AddField(
            model_name="infrastructure",
            name="barangay_ref",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="infrastructure",
                to="residents.barangay",
            ),
        ),
        migrations.AddField(
            model_name="disasterpronearea",
            name="barangay_ref",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="disaster_areas",
                to="residents.barangay",
            ),
        ),
        migrations.CreateModel(
            name="EvacuationSite",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150)),
                ("location", django.contrib.gis.db.models.fields.PointField(srid=4326)),
                ("capacity", models.PositiveIntegerField(blank=True, null=True)),
                (
                    "barangay",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="evacuation_sites",
                        to="residents.barangay",
                    ),
                ),
            ],
        ),
    ]

