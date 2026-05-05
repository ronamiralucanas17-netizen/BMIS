import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bmis.settings')
django.setup()

from residents.models import Resident, Barangay

print("Checking Sabang Bao residents...")
sabang_bao_residents = Resident.objects.filter(present_address__icontains='Sabang Bao')
print(f"Residents with Sabang Bao in address: {sabang_bao_residents.count()}")
for r in sabang_bao_residents:
    print(f" - {r.full_name}, Household: {r.household}, Barangay: {r.barangay}")

print("\nChecking all residents with None barangay...")
none_brgy = Resident.objects.filter(barangay__isnull=True)
for r in none_brgy:
    print(f" - {r.full_name}, Address: {r.present_address}, Household: {r.household}")
