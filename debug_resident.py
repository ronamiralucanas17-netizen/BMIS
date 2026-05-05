from residents.models import Resident
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BMIS.settings')
django.setup()

def debug_resident(name_part):
    residents = Resident.objects.filter(first_name__icontains=name_part)
    if not residents.exists():
        residents = Resident.objects.filter(last_name__icontains=name_part)
    
    if not residents.exists():
        print(f"No resident found matching {name_part}")
        return

    for r in residents:
        print(f"--- Debugging Resident: {r.full_name} (ID: {r.id}) ---")
        print(f"Status: {r.profile_status}")
        
        required_fields = [
            'first_name', 'last_name', 'date_of_birth', 'gender', 
            'civil_status', 'residency_status', 'present_address', 
            'residency_type', 'educational_attainment', 'occupation',
            'contact_number', 'household', 'birthplace', 'citizenship',
            'religion', 'years_in_barangay', 'income', 'employment_status',
            'permanent_address'
        ]
        
        empty_fields = []
        for field_name in required_fields:
            value = getattr(r, field_name, None)
            is_empty = False
            if value is None:
                is_empty = True
            elif isinstance(value, str) and not value.strip():
                is_empty = True
            elif hasattr(value, 'all') and not value.exists():
                is_empty = True
            elif field_name == 'household' and not value:
                is_empty = True
            
            if is_empty:
                empty_fields.append(field_name)
        
        if empty_fields:
            print(f"Empty required fields: {', '.join(empty_fields)}")
        else:
            print("All required fields are FILLED, but status is still INCOMPLETE.")
            
        print(f"has_completed_profile() returns: {r.has_completed_profile()}")

if __name__ == "__main__":
    debug_resident("resident1")
