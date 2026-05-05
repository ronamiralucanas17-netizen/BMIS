import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bmis.settings')
django.setup()

from residents.models import Resident, Barangay, Household
from users.models import User

try:
    u = User.objects.get(username='resident1')
    r = Resident.objects.get(user=u)
    print(f"Resident Name: {r.full_name}")
    print(f"Barangay: {r.barangay}")
    print(f"Present Address: {r.present_address}")
    print(f"Household: {r.household}")
    if r.household:
        print(f"Household Barangay: {r.household.barangay}")
        print(f"Household Address: {r.household.address}")
    
    print("\nBarangays in system:")
    for b in Barangay.objects.all():
        print(f"- {b.name}")

except User.DoesNotExist:
    print("User 'resident1' not found.")
except Resident.DoesNotExist:
    print("Resident profile for 'resident1' not found.")
except Exception as e:
    print(f"Error: {e}")
