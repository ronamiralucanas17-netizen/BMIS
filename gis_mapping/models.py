from django.db import models
from django.contrib.gis.db import models as gis_models

class Infrastructure(models.Model):
    INFRA_TYPES = (
        ('HEALTH_CENTER', 'Health Center'),
        ('SCHOOL', 'School'),
        ('ROAD', 'Road'),
        ('BARANGAY_HALL', 'Barangay Hall'),
        ('OTHER', 'Other'),
    )
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=50, choices=INFRA_TYPES)
    location = gis_models.PointField(srid=4326)
    barangay = models.CharField(max_length=100, blank=True, null=True)
    barangay_ref = models.ForeignKey('residents.Barangay', on_delete=models.CASCADE, null=True, blank=True, related_name='infrastructure')

    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"

class DisasterProneArea(models.Model):
    DISASTER_TYPES = (
        ('FLOOD', 'Flood Prone'),
        ('LANDSLIDE', 'Landslide Prone'),
        ('STORM_SURGE', 'Storm Surge'),
    )
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=50, choices=DISASTER_TYPES)
    boundary = gis_models.PolygonField(srid=4326)
    risk_level = models.IntegerField(choices=[(1, 'Low'), (2, 'Medium'), (3, 'High')])
    barangay_ref = models.ForeignKey('residents.Barangay', on_delete=models.CASCADE, null=True, blank=True, related_name='disaster_areas')

    def __str__(self):
        return f"{self.name} - {self.get_type_display()}"

class EvacuationSite(models.Model):
    name = models.CharField(max_length=150)
    location = gis_models.PointField(srid=4326)
    barangay = models.ForeignKey('residents.Barangay', on_delete=models.CASCADE, related_name='evacuation_sites')
    capacity = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.barangay.name})"
