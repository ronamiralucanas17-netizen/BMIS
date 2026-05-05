import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bmis.settings')
django.setup()

from residents.models import Resident, Barangay

print("Cogon residents addresses:")
cogon_residents = Resident.objects.filter(barangay__name='Cogon')
for r in cogon_residents[:10]:
    print(f" - {r.full_name}: {r.present_address}")

print("\nDistrict 1 residents addresses:")
d1_residents = Resident.objects.filter(barangay__name='District 1')
for r in d1_residents[:10]:
    print(f" - {r.full_name}: {r.present_address}")
