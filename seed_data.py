import os
import django
import random
from datetime import date, timedelta

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bmis.settings')
django.setup()

from users.models import User
from residents.models import Household, Resident
from analytics.ml_models import VulnerabilityClassifier

def generate_dummy_data():
    print("Creating dummy users...")
    # Admin
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@example.com', 'admin123', role='ADMIN')
    
    # DILG
    if not User.objects.filter(username='dilg_user').exists():
        User.objects.create_user('dilg_user', 'dilg@example.com', 'dilg123', role='DILG')
    
    # Barangay Official
    if not User.objects.filter(username='official_user').exists():
        User.objects.create_user('official_user', 'official@example.com', 'official123', role='BARANGAY_OFFICIAL', barangay='District 1')

    # Resident User
    if not User.objects.filter(username='resident_user').exists():
        User.objects.create_user('resident_user', 'resident@example.com', 'resident123', role='RESIDENT')

    print("Creating dummy households and residents...")
    barangays = ['District 1', 'District 2', 'Cogon', 'Can-adieng']
    addresses = ['Near River St.', 'Mountain Slope Rd.', 'Main Avenue', 'Poblacion', 'Coastal Road']
    
    for i in range(1, 11):
        hh_num = f"HH-{1000 + i}"
        brgy = random.choice(barangays)
        addr = f"{random.choice(addresses)}, {brgy}"
        
        # Random location in Ormoc City area
        lat = 11.00 + random.uniform(-0.02, 0.02)
        lng = 124.60 + random.uniform(-0.02, 0.02)
        
        hh, created = Household.objects.get_or_create(
            household_number=hh_num,
            defaults={
                'address': addr,
                'barangay': brgy,
                'location': f"POINT({lng} {lat})"
            }
        )
        
        if created:
            # Create 3-6 residents per household
            num_res = random.randint(3, 6)
            for j in range(num_res):
                res = Resident.objects.create(
                    first_name=f"Resident{i}_{j}",
                    last_name=f"LastName{i}",
                    date_of_birth=date.today() - timedelta(days=random.randint(0, 30000)),
                    gender=random.choice(['MALE', 'FEMALE']),
                    household=hh,
                    is_voter=random.choice([True, False])
                )
                # Link the first resident of the first household to the resident_user
                if i == 1 and j == 0:
                    resident_user = User.objects.get(username='resident_user')
                    res.user = resident_user
                    res.save()
    
    print("Training ML model with dummy data...")
    # Generate some training data for the Random Forest model
    training_data = []
    for i in range(100):
        hh_size = random.randint(1, 10)
        elderly = random.randint(0, 3)
        children = random.randint(0, 4)
        is_river = random.choice([0, 1])
        is_slope = random.choice([0, 1])
        
        # Heuristic for vulnerability level (0: Low, 1: Medium, 2: High)
        score = hh_size * 0.1 + elderly * 0.3 + children * 0.2 + is_river * 0.5 + is_slope * 0.5
        if score > 1.5: level = 2
        elif score > 0.8: level = 1
        else: level = 0
        
        training_data.append({
            'household_size': hh_size,
            'num_elderly': elderly,
            'num_children': children,
            'is_near_river': is_river,
            'is_near_slope': is_slope,
            'vulnerability_level': level
        })
    
    classifier = VulnerabilityClassifier()
    accuracy = classifier.train(training_data)
    print(f"ML Model trained successfully! Accuracy: {accuracy:.2f}")

if __name__ == "__main__":
    generate_dummy_data()
