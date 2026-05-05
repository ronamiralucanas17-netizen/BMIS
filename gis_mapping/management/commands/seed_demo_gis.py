from django.contrib.gis.geos import Point, Polygon
from django.core.management.base import BaseCommand
from django.db import IntegrityError, transaction

from gis_mapping.models import DisasterProneArea, EvacuationSite
from residents.models import Barangay


class Command(BaseCommand):
    def handle(self, *args, **options):
        targets = [
            ("Sabang Bao", (124.60, 11.00)),
            ("Labrador", (124.61, 11.01)),
            ("Bayog", (124.59, 10.99)),
        ]

        def make_poly(cx, cy, dx=0.01, dy=0.01):
            return Polygon(
                (
                    (cx - dx, cy - dy),
                    (cx + dx, cy - dy),
                    (cx + dx, cy + dy),
                    (cx - dx, cy + dy),
                    (cx - dx, cy - dy),
                )
            )

        created_hazards = 0
        created_sites = 0

        for name, (cx, cy) in targets:
            brgy = Barangay.objects.filter(name=name).first()
            if not brgy:
                continue

            try:
                with transaction.atomic():
                    _, h1_created = DisasterProneArea.objects.get_or_create(
                        name=f"{name} Flood Zone",
                        defaults={
                            "type": "FLOOD",
                            "boundary": make_poly(cx, cy),
                            "risk_level": 2,
                            "barangay_ref": brgy,
                        },
                    )
                    _, h2_created = DisasterProneArea.objects.get_or_create(
                        name=f"{name} Landslide Zone",
                        defaults={
                            "type": "LANDSLIDE",
                            "boundary": make_poly(cx + 0.008, cy + 0.008),
                            "risk_level": 3,
                            "barangay_ref": brgy,
                        },
                    )
                    _, s_created = EvacuationSite.objects.get_or_create(
                        name=f"{name} Evacuation Center",
                        defaults={
                            "location": Point(cx, cy),
                            "barangay": brgy,
                            "capacity": 250,
                        },
                    )
            except IntegrityError:
                continue

            created_hazards += int(h1_created) + int(h2_created)
            created_sites += int(s_created)

        print(f"created_hazards={created_hazards}")
        print(f"created_evacuation_sites={created_sites}")

