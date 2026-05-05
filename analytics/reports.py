import csv
from django.http import HttpResponse
from residents.models import Resident, Household

def export_residents_csv(queryset, filename="residents_report.csv"):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    writer = csv.writer(response)
    writer.writerow(['First Name', 'Last Name', 'Date of Birth', 'Gender', 'Barangay', 'Household #', 'Contact', 'Voter'])
    
    for resident in queryset:
        writer.writerow([
            resident.first_name,
            resident.last_name,
            resident.date_of_birth,
            resident.get_gender_display() if resident.gender else 'N/A',
            resident.barangay.name if resident.barangay else (resident.household.barangay.name if resident.household and resident.household.barangay else 'N/A'),
            resident.household.household_number if resident.household else 'N/A',
            resident.contact_number,
            'Yes' if resident.is_voter else 'No'
        ])
    
    return response

def export_households_csv(queryset, filename="households_report.csv"):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    writer = csv.writer(response)
    writer.writerow(['HH Number', 'Address', 'Barangay', 'Members Count'])
    
    for hh in queryset:
        writer.writerow([
            hh.household_number,
            hh.address,
            hh.barangay.name if hh.barangay else 'N/A',
            hh.members.count()
        ])
    
    return response
