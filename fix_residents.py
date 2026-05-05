import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bmis.settings')
django.setup()

from residents.models import Resident, Barangay

print("Starting fix...")
updated = 0
for r in Resident.objects.filter(barangay__isnull=True, household__isnull=False):
    if r.household.barangay:
        r.barangay = r.household.barangay
        r.save()
        updated += 1

print(f"Fixed {updated} residents with households.")

# For those without households, let's see if we can assign them back to Sabang Bao if they were there
# Actually, let's just assign all residents without a barangay to Sabang Bao if that's the current context
# Or better, just report them.
remaining = Resident.objects.filter(barangay__isnull=True)
print(f"Remaining residents with no barangay: {remaining.count()}")
for r in remaining:
    print(f" - {r.full_name} (Address: {r.present_address})")
