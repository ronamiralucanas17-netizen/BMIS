from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
import csv
from residents.models import Resident, Barangay, AuditLog
from django.db.utils import ProgrammingError, OperationalError
from residents.forms import ResidentForm, BarangayForm
from users.decorators import staff_only, system_admin_only

@login_required
@staff_only
def generate_resident_report(request):
    """
    Advanced report generation with filters.
    """
    # Use the decorator's logic instead of is_staff which might be False for some staff roles
    if not (request.user.role in ['ADMIN', 'BARANGAY'] or request.user.is_superuser):
        return redirect('residents:resident_dashboard')

    residents = Resident.objects.all()
    group = request.GET.get('group') or 'resident'
    if group not in ('resident', 'household'):
        group = 'resident'
    
    # Filters
    birthplace = request.GET.get('birthplace')
    gender = request.GET.get('gender')
    civil_status = request.GET.get('civil_status')
    religion = request.GET.get('religion')
    education = request.GET.get('educational_attainment')
    occupation = request.GET.get('occupation')
    purok = request.GET.get('purok')
    is_voter = request.GET.get('is_voter')
    residency_status = request.GET.get('residency_status')
    profile_status = request.GET.get('profile_status')
    age_range = request.GET.get('age_range')
    employment_status = request.GET.get('employment_status')
    category = request.GET.get('category')

    if birthplace: residents = residents.filter(birthplace__icontains=birthplace)
    if gender: residents = residents.filter(gender=gender)
    if civil_status: residents = residents.filter(civil_status=civil_status)
    if religion: residents = residents.filter(religion__icontains=religion)
    if education: residents = residents.filter(educational_attainment=education)
    if occupation: residents = residents.filter(occupation__icontains=occupation)
    if purok: residents = residents.filter(zone_street_purok__icontains=purok)
    if is_voter: residents = residents.filter(is_voter=(is_voter == 'true'))
    if residency_status: residents = residents.filter(residency_status=residency_status)
    if profile_status: residents = residents.filter(profile_status=profile_status)
    if employment_status: residents = residents.filter(employment_status=employment_status)

    if request.user.is_barangay_admin:
        residents = residents.filter(barangay=request.user.managed_barangay)

    residents_list = list(residents)

    if age_range:
        residents_list = [r for r in residents_list if r.computed_age_range == age_range]

    if category == 'MINOR':
        residents_list = [r for r in residents_list if r.computed_age_range in ['INFANT', 'CHILDHOOD', 'ADOLESCENCE']]
    elif category == 'SENIOR':
        residents_list = [r for r in residents_list if r.computed_age_range in ['OLD_AGE', 'SENIOR_CITIZEN']]
    elif category == 'UNEMPLOYED':
        residents_list = [r for r in residents_list if r.employment_status == 'UNEMPLOYED']
    elif category == 'PWD':
        pass

    if 'export' in request.GET:
        if group == 'household':
            from residents.models import Household
            household_ids = sorted({r.household_id for r in residents_list if r.household_id})
            households = Household.objects.filter(id__in=household_ids).select_related('barangay').prefetch_related('members')

            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="household_report.csv"'
            writer = csv.writer(response)
            writer.writerow(['Household #', 'Barangay', 'Address', 'Members Count', 'Members'])
            for hh in households.order_by('barangay__name', 'household_number', 'id'):
                members = list(hh.members.order_by('last_name', 'first_name', 'id').values_list('first_name', 'last_name'))
                member_names = '; '.join([f"{fn} {ln}".strip() for fn, ln in members if (fn or ln)])
                writer.writerow([
                    hh.household_number,
                    hh.barangay.name if hh.barangay else '',
                    hh.address,
                    len(members),
                    member_names,
                ])
            return response

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="resident_report.csv"'
        writer = csv.writer(response)
        writer.writerow(['Code', 'Name', 'Gender', 'Age Range', 'Purok', 'Employment', 'Status', 'Voter'])
        for r in residents_list:
            writer.writerow([r.resident_code, r.full_name, r.gender, r.computed_age_range, r.zone_street_purok, r.employment_status, r.profile_status, r.is_voter])
        return response

    households = []
    if group == 'household':
        from residents.models import Household
        from django.db.models import Prefetch

        household_ids = sorted({r.household_id for r in residents_list if r.household_id})
        households = Household.objects.filter(id__in=household_ids).select_related('barangay').prefetch_related(
            Prefetch('members', queryset=Resident.objects.order_by('last_name', 'first_name', 'id'))
        )

    return render(request, 'analytics/resident_report.html', {
        'residents': residents_list,
        'households': households,
        'group': group,
        'filters': request.GET,
    })
from django.db import models
from django.db.models import Count, Q
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.serializers import serialize
from django.urls import reverse
from residents.models import Barangay, Household, Resident, IncidentReport
from gis_mapping.models import DisasterProneArea, EvacuationSite
from .ml_models import VulnerabilityClassifier, HouseholdClusterer
from .reports import export_residents_csv, export_households_csv
import pandas as pd
import json
from sklearn.metrics import confusion_matrix, accuracy_score, precision_recall_fscore_support
from urllib.parse import urlencode

def is_system_admin(user):
    return user.role == 'ADMIN' or user.is_superuser

def require_system_admin(view_func):
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            login_url = reverse('users:admin_login')
            return redirect(f"{login_url}?{urlencode({'next': request.get_full_path()})}")
        if not is_system_admin(request.user):
            return redirect('users:admin_login')
        return view_func(request, *args, **kwargs)
    return _wrapped

@require_system_admin
def edit_barangay(request, pk):
    barangay = get_object_or_404(Barangay, pk=pk)
    if request.method == 'POST':
        form = BarangayForm(request.POST, instance=barangay)
        if form.is_valid():
            form.save()
            messages.success(request, f"Barangay {barangay.name} updated successfully.")
            return redirect('analytics:dilg_dashboard')
    else:
        form = BarangayForm(instance=barangay)
    return render(request, 'analytics/barangay_form.html', {'form': form, 'barangay': barangay})

@require_system_admin
def dilg_dashboard(request):
    """
    Super Admin dashboard for DILG officials with analytics and GIS.
    """
    pending_barangays = Barangay.objects.filter(is_approved=False)
    all_barangays = Barangay.objects.all().order_by('name')
    
    # Analytics for charts
    barangay_stats = Barangay.objects.filter(is_approved=True).annotate(
        resident_count=Count('residents'),
        report_count=Count('reports')
    )
    
    # Report status breakdown
    report_status_data = list(IncidentReport.objects.values('status').annotate(count=Count('id')))
    
    # Resident age distribution (approximate)
    from datetime import date
    current_year = date.today().year
    age_groups = {
        '0-12 (Children)': Resident.objects.filter(date_of_birth__year__gt=current_year-12).count(),
        '13-19 (Youth)': Resident.objects.filter(date_of_birth__year__range=(current_year-19, current_year-13)).count(),
        '20-59 (Adults)': Resident.objects.filter(date_of_birth__year__range=(current_year-59, current_year-20)).count(),
        '60+ (Seniors)': Resident.objects.filter(date_of_birth__year__lt=current_year-60).count(),
    }

    classifier = VulnerabilityClassifier(algorithm="logistic_regression")
    ml_risk_counts = {'Low': 0, 'Medium': 0, 'High': 0}
    for hh in Household.objects.all():
        household_size = Resident.objects.filter(household=hh).count()
        num_elderly = Resident.objects.filter(household=hh, date_of_birth__year__lt=current_year - 60).count()
        num_children = Resident.objects.filter(household=hh, date_of_birth__year__gt=current_year - 12).count()
        is_near_river = 1 if 'river' in (hh.address or '').lower() else 0
        is_near_slope = 1 if any(k in (hh.address or '').lower() for k in ('slope', 'mountain')) else 0
        level = classifier.predict([household_size, num_elderly, num_children, is_near_river, is_near_slope])
        ml_risk_counts[level] += 1

    # GIS Data
    households_geojson = serialize('geojson', Household.objects.all(), geometry_field='location', fields=('household_number', 'address', 'barangay'))
    incidents_geojson = serialize('geojson', IncidentReport.objects.filter(location_point__isnull=False), geometry_field='location_point', fields=('title', 'status', 'report_type'))
    hazards_geojson = serialize('geojson', DisasterProneArea.objects.all(), geometry_field='boundary', fields=('name', 'type', 'risk_level'))
    evacuation_geojson = serialize('geojson', EvacuationSite.objects.all(), geometry_field='location', fields=('name', 'capacity', 'barangay'))
    barangay_boundaries_json = json.dumps([
        {'id': b.id, 'name': b.name, 'boundary': json.loads(b.boundary.json)}
        for b in Barangay.objects.filter(boundary__isnull=False)
    ])

    # Active status filtering for barangays
    active_status = request.GET.get('active_status')
    if active_status == 'active':
        all_barangays = all_barangays.filter(is_active=True)
    elif active_status == 'inactive':
        all_barangays = all_barangays.filter(is_active=False)

    context = {
        'total_residents': Resident.objects.count(),
        'total_households': Household.objects.count(),
        'total_barangays': Barangay.objects.count(),
        'pending_barangays': pending_barangays,
        'all_barangays': all_barangays,
        'active_status': active_status,
        'barangay_stats': barangay_stats,
        'recent_residents': Resident.objects.order_by('-created_at')[:10],
        'households_geojson': households_geojson,
        'incidents_geojson': incidents_geojson,
        'hazards_geojson': hazards_geojson,
        'evacuation_geojson': evacuation_geojson,
        'barangay_boundaries_json': barangay_boundaries_json,
        'chart_data': {
            'barangay_labels': [b.name for b in barangay_stats],
            'barangay_residents': [b.resident_count for b in barangay_stats],
            'report_status_labels': [s['status'] for s in report_status_data],
            'report_status_counts': [s['count'] for s in report_status_data],
            'age_labels': list(age_groups.keys()),
            'age_counts': list(age_groups.values()),
            'ml_risk_labels': list(ml_risk_counts.keys()),
            'ml_risk_counts': list(ml_risk_counts.values()),
        }
    }
    
    if 'download' in request.GET:
        return export_residents_csv(Resident.objects.all(), "dilg_all_residents.csv")
        
    return render(request, 'analytics/dilg_dashboard.html', context)

@require_system_admin
def approve_barangay(request, pk):
    barangay = get_object_or_404(Barangay, pk=pk)
    barangay.is_approved = True
    barangay.save()
    
    # Also ensure the associated user is active and approved
    user = barangay.admin_user
    if user:
        user.role = 'BARANGAY'
        user.is_active = True
        user.is_approved = True
        user.save(update_fields=['role', 'is_active', 'is_approved'])
    
    return redirect('analytics:dilg_dashboard')

@require_system_admin
def reject_barangay(request, pk):
    barangay = get_object_or_404(Barangay, pk=pk)
    user = barangay.admin_user
    barangay.delete()
    if user:
        user.delete()
    messages.success(request, f"Barangay {barangay.name} and its associated admin account have been rejected and removed.")
    return redirect('analytics:dilg_dashboard')

@login_required
def barangay_dashboard(request):
    """
    Local dashboard for Barangay Officials with analytics and GIS.
    """
    if not request.user.is_any_barangay_official:
        return redirect('home')
        
    try:
        # If admin_user is set, use it. Otherwise find by name.
        if request.user.is_barangay_admin:
            brgy = request.user.managed_barangay
        else:
            brgy = Barangay.objects.get(name=request.user.barangay_name)
    except Barangay.DoesNotExist:
        return render(request, 'error.html', {'message': 'You are not assigned to manage any barangay.'})
        
    residents = Resident.objects.filter(barangay=brgy)
    households = Household.objects.filter(barangay=brgy)
    reports = IncidentReport.objects.filter(barangay=brgy)
    occupied_households = households.filter(members__isnull=False).distinct()
    
    # Analytics for charts
    status_breakdown = reports.values('status').annotate(count=Count('id'))
    type_breakdown = reports.values('report_type').annotate(count=Count('id'))
    
    # GIS Data
    households_geojson = serialize('geojson', households, geometry_field='location', fields=('household_number', 'address'))
    incidents_geojson = serialize('geojson', reports.filter(location_point__isnull=False), geometry_field='location_point', fields=('title', 'status', 'report_type'))
    hazards_geojson = serialize('geojson', DisasterProneArea.objects.filter(barangay_ref=brgy), geometry_field='boundary', fields=('name', 'type', 'risk_level'))
    evacuation_geojson = serialize('geojson', EvacuationSite.objects.filter(barangay=brgy), geometry_field='location', fields=('name', 'capacity'))
    barangay_boundaries_json = json.dumps(
        [{'id': brgy.id, 'name': brgy.name, 'boundary': json.loads(brgy.boundary.json)}]
        if brgy.boundary else []
    )

    from datetime import date
    current_year = date.today().year
    classifier = VulnerabilityClassifier(algorithm="logistic_regression")
    ml_risk_counts = {'Low': 0, 'Medium': 0, 'High': 0}
    for hh in households:
        household_size = Resident.objects.filter(household=hh).count()
        num_elderly = Resident.objects.filter(household=hh, date_of_birth__year__lt=current_year - 60).count()
        num_children = Resident.objects.filter(household=hh, date_of_birth__year__gt=current_year - 12).count()
        is_near_river = 1 if 'river' in (hh.address or '').lower() else 0
        is_near_slope = 1 if any(k in (hh.address or '').lower() for k in ('slope', 'mountain')) else 0
        level = classifier.predict([household_size, num_elderly, num_children, is_near_river, is_near_slope])
        ml_risk_counts[level] += 1

    try:
        audit_logs = list(
            AuditLog.objects.filter(barangay=brgy)
            .select_related('actor')
            .order_by('-created_at')[:20]
        )
    except (ProgrammingError, OperationalError):
        audit_logs = []

    context = {
        'barangay': brgy,
        'residents': residents,
        'households': households,
        'pending_reports': reports.filter(status='PENDING'),
        'pending_residents': residents.filter(profile_status='PENDING_APPROVAL'),
        'total_residents': residents.count(),
        'total_households': occupied_households.count(),
        'audit_logs': audit_logs,
        'households_geojson': households_geojson,
        'incidents_geojson': incidents_geojson,
        'hazards_geojson': hazards_geojson,
        'evacuation_geojson': evacuation_geojson,
        'barangay_boundaries_json': barangay_boundaries_json,
        'chart_data': {
            'status_labels': [s['status'] for s in status_breakdown],
            'status_counts': [s['count'] for s in status_breakdown],
            'type_labels': [t['report_type'] for t in type_breakdown],
            'type_counts': [t['count'] for t in type_breakdown],
            'ml_risk_labels': list(ml_risk_counts.keys()),
            'ml_risk_counts': list(ml_risk_counts.values()),
        }
    }
    
    if 'download' in request.GET:
        return export_residents_csv(residents, f"{brgy.name}_residents_report.csv")
        
    return render(request, 'analytics/barangay_dashboard.html', context)

@login_required
def vulnerability_dashboard(request):
    """
    DILG and Admin Dashboard to view ML-based disaster vulnerability predictions for households.
    """
    households = Household.objects.all()
    buffer_degrees = 0.002
    hazards = list(DisasterProneArea.objects.all().only('type', 'boundary'))
    water_polys = []
    slope_polys = []
    for h in hazards:
        if not h.boundary:
            continue
        if h.type in ('FLOOD', 'STORM_SURGE'):
            water_polys.append(h.boundary)
        elif h.type == 'LANDSLIDE':
            slope_polys.append(h.boundary)

    def _buffered(polys):
        out = []
        for p in polys:
            try:
                out.append(p.buffer(buffer_degrees))
            except Exception:
                continue
        return out

    water_buffers = _buffered(water_polys)
    slope_buffers = _buffered(slope_polys)

    def _near_any(point, polys, buffers):
        for p in polys:
            try:
                if p.contains(point) or p.touches(point):
                    return 1
            except Exception:
                continue
        for b in buffers:
            try:
                if b.contains(point) or b.touches(point):
                    return 1
            except Exception:
                continue
        return 0

    predictions = []
    features_all = []
    hh_index = []
    classifier = VulnerabilityClassifier(algorithm="logistic_regression")
    clusterer = HouseholdClusterer(algorithm="kmeans", n_clusters=3)
    y_true = []
    y_pred = []

    from datetime import date
    current_year = date.today().year

    for household in households:
        # Prepare household data for ML prediction
        num_elderly = Resident.objects.filter(household=household, date_of_birth__year__lt=current_year - 60).count()
        num_children = Resident.objects.filter(household=household, date_of_birth__year__gt=current_year - 12).count()
        household_size = Resident.objects.filter(household=household).count()

        address = (household.address or '').lower()
        if household.location:
            is_near_water = _near_any(household.location, water_polys, water_buffers)
            is_near_slope = _near_any(household.location, slope_polys, slope_buffers)
        else:
            is_near_water = 1 if any(k in address for k in ('river', 'lake', 'sea', 'coast', 'shore', 'water')) else 0
            is_near_slope = 1 if any(k in address for k in ('slope', 'mountain', 'hill')) else 0

        is_near_river = is_near_water
        features = [household_size, num_elderly, num_children, is_near_river, is_near_slope]
        features_all.append(features)
        hh_index.append((household, household_size, num_elderly, num_children))

    if features_all:
        clusterer.fit(features_all)

    for (household, household_size, num_elderly, num_children), features in zip(hh_index, features_all):
        prediction = classifier.predict(features)
        cluster = clusterer.predict(features)
        risk_score = (
            (1 if household_size >= 7 else 0)
            + (1 if num_elderly >= 2 else 0)
            + (1 if num_children >= 3 else 0)
            + features[3]
            + features[4]
        )
        true_level_idx = max(0, min(2, risk_score // 2))
        true_map = {0: "Low", 1: "Medium", 2: "High"}
        true_level = true_map[true_level_idx]
        y_true.append(true_level)
        y_pred.append(prediction)
        predictions.append({
            'household': household,
            'prediction': prediction,
            'size': household_size,
            'elderly': num_elderly,
            'children': num_children,
            'cluster': cluster,
        })

    labels = ["Low", "Medium", "High"]
    cm = confusion_matrix(y_true, y_pred, labels=labels).tolist() if y_true else [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
    acc = float(accuracy_score(y_true, y_pred)) if y_true else 0.0
    pr, rc, f1, _ = precision_recall_fscore_support(y_true, y_pred, labels=labels, zero_division=0)

    context = {
        "predictions": predictions,
        "model_name": "Logistic Regression",
        "cluster_name": "K-Means",
        "confusion": {"labels": labels, "matrix": cm},
        "metrics": {
            "accuracy": acc,
            "precision": [float(x) for x in pr],
            "recall": [float(x) for x in rc],
            "f1": [float(x) for x in f1],
        },
    }
    return render(request, 'analytics/vulnerability_dashboard.html', context)
