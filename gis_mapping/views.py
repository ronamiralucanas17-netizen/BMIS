from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.gis.geos import Polygon, MultiPolygon, GEOSGeometry
from django.db.models import Count, Q
from residents.models import Barangay, Resident, Household
from .models import Infrastructure, DisasterProneArea, EvacuationSite
from .forms import InfrastructureForm, DisasterProneAreaForm, EvacuationSiteForm
import json

_SENIOR_AGE_RANGES = ['OLD_AGE', 'SENIOR_CITIZEN']
_MINOR_AGE_RANGES = ['INFANT', 'CHILDHOOD', 'ADOLESCENCE']

def _count_age_groups(residents):
    seniors = 0
    minors = 0
    infants = 0
    for r in residents:
        ar = getattr(r, 'computed_age_range', None)
        if ar == 'INFANT':
            infants += 1
            minors += 1
        elif ar in _MINOR_AGE_RANGES:
            minors += 1
        if ar in _SENIOR_AGE_RANGES:
            seniors += 1
    return seniors, minors, infants

def is_admin_or_dilg(user):
    return user.is_authenticated and (user.is_system_admin or user.is_barangay_admin)

def map_view(request):
    """
    Main GIS mapping view to visualize households, infrastructure, and disaster areas.
    Includes demographic aggregates per Purok or Barangay.
    """
    infrastructure = Infrastructure.objects.all()
    disaster_areas = DisasterProneArea.objects.all()
    evacuation_sites = EvacuationSite.objects.all()
    barangays = Barangay.objects.all()
    households = Household.objects.filter(location__isnull=False).select_related('barangay').annotate(members_count=Count('members'))
    
    demographics = []
    
    if request.user.is_authenticated:
        if request.user.is_any_barangay_official:
            try:
                if request.user.is_barangay_admin:
                    brgy = Barangay.objects.get(admin_user=request.user)
                else:
                    brgy = Barangay.objects.filter(name=request.user.barangay_name).first()
            except Barangay.DoesNotExist:
                brgy = Barangay.objects.filter(name=request.user.barangay_name).first()
            
            if brgy:
                infrastructure = infrastructure.filter(barangay_ref=brgy)
                disaster_areas = disaster_areas.filter(barangay_ref=brgy)
                evacuation_sites = evacuation_sites.filter(barangay=brgy)
                households = households.filter(barangay=brgy)
                
                residents_in_brgy = list(Resident.objects.filter(barangay=brgy))
                seniors_count, minors_count, infants_count = _count_age_groups(residents_in_brgy)

                center = None
                first_hh = Household.objects.filter(barangay=brgy, location__isnull=False).first()
                if first_hh:
                    center = [first_hh.location.y, first_hh.location.x]
                elif brgy.boundary:
                    c = brgy.boundary.centroid
                    center = [c.y, c.x]

                demographics.append({
                    'name': brgy.name,
                    'type': 'barangay',
                    'id': brgy.id,
                    'center': center,
                    'population': len(residents_in_brgy),
                    'seniors': seniors_count,
                    'students': sum(1 for r in residents_in_brgy if r.is_student),
                    'unemployed': sum(1 for r in residents_in_brgy if r.employment_status == 'UNEMPLOYED'),
                    'employed': sum(1 for r in residents_in_brgy if r.employment_status == 'EMPLOYED'),
                    'minors': minors_count,
                    'infants': infants_count,
                })
        
        elif request.user.is_system_admin:
            # Aggregate by Barangay for system admin
            barangays = Barangay.objects.all()
            for brgy in barangays:
                residents_in_brgy = list(Resident.objects.filter(barangay=brgy))
                seniors_count, minors_count, infants_count = _count_age_groups(residents_in_brgy)
                
                # Get center from barangay location or first household
                center = None
                first_hh = Household.objects.filter(barangay=brgy, location__isnull=False).first()
                if first_hh:
                    center = [first_hh.location.y, first_hh.location.x]
                elif brgy.boundary:
                    c = brgy.boundary.centroid
                    center = [c.y, c.x]
                
                demographics.append({
                    'name': brgy.name,
                    'type': 'barangay',
                    'id': brgy.id,
                    'center': center,
                    'population': len(residents_in_brgy),
                    'seniors': seniors_count,
                    'students': sum(1 for r in residents_in_brgy if r.is_student),
                    'unemployed': sum(1 for r in residents_in_brgy if r.employment_status == 'UNEMPLOYED'),
                    'employed': sum(1 for r in residents_in_brgy if r.employment_status == 'EMPLOYED'),
                    'minors': minors_count,
                    'infants': infants_count,
                })

    can_edit = request.user.is_authenticated and (request.user.is_system_admin or request.user.is_barangay_admin)
    households_json = json.dumps([
        {
            'id': h.id,
            'household_number': h.household_number,
            'address': h.address,
            'barangay': h.barangay.name if h.barangay else '',
            'lat': h.location.y if h.location else None,
            'lng': h.location.x if h.location else None,
            'members_count': getattr(h, 'members_count', None),
        }
        for h in households
    ])

    return render(request, 'gis_mapping/map_view.html', {
        'infrastructure': infrastructure,
        'disaster_areas': disaster_areas,
        'evacuation_sites': evacuation_sites,
        'barangays': barangays,
        'can_edit_gis': can_edit,
        'demographics_json': json.dumps(demographics),
        'households_json': households_json,
    })

@login_required
@user_passes_test(lambda u: u.is_barangay_admin)
def edit_barangay_boundary(request):
    try:
        brgy = Barangay.objects.get(admin_user=request.user)
    except Barangay.DoesNotExist:
        messages.error(request, "No managed barangay found for your account.")
        return redirect('gis_mapping:map_view')

    if request.method == 'POST':
        boundary_json = request.POST.get('boundary_json')
        if boundary_json:
            try:
                # Convert GeoJSON to GEOS geometry
                geojson = json.loads(boundary_json)

                if isinstance(geojson, dict) and geojson.get('type') == 'FeatureCollection':
                    features = geojson.get('features') or []
                    geojson = features[0] if features else {}

                if isinstance(geojson, dict) and geojson.get('type') == 'Feature':
                    geojson = geojson.get('geometry') or {}

                if not isinstance(geojson, dict):
                    messages.error(request, "Invalid boundary data. Please redraw the polygon.")
                    return redirect('gis_mapping:edit_barangay_boundary')

                if geojson.get('type') not in ('Polygon', 'MultiPolygon'):
                    messages.error(request, "Invalid geometry type. Please draw a polygon.")
                    return redirect('gis_mapping:edit_barangay_boundary')

                if 'coordinates' not in geojson:
                    messages.error(request, "Invalid polygon coordinates. Please redraw the boundary.")
                    return redirect('gis_mapping:edit_barangay_boundary')

                geom = GEOSGeometry(json.dumps(geojson), srid=4326)

                if getattr(geom, 'srid', None) in (None, 0):
                    geom.srid = 4326

                if hasattr(geom, 'valid') and not geom.valid:
                    try:
                        geom = geom.buffer(0)
                    except Exception:
                        pass

                if isinstance(geom, MultiPolygon) or getattr(geom, 'geom_type', None) == 'MultiPolygon':
                    try:
                        geom = max(list(geom), key=lambda g: g.area)
                    except Exception:
                        pass
                
                # Check if it's a Polygon
                if geom.geom_type in ('Polygon', 'MultiPolygon'):
                    brgy.boundary = geom
                    brgy.save()
                    messages.success(request, f"Boundary for {brgy.name} has been updated.")
                    return redirect('gis_mapping:map_view')
                else:
                    messages.error(request, "Invalid geometry type. Please draw a polygon.")
            except Exception as e:
                messages.error(request, f"Error saving boundary: {str(e)}")
        else:
            messages.error(request, "No boundary data provided.")

    return render(request, 'gis_mapping/edit_barangay_boundary.html', {
        'barangay': brgy,
    })

@login_required
def demographic_list(request):
    """
    View to show a list of residents for a specific demographic filter.
    Used when clicking on demographic markers on the map.
    """
    demo_type = request.GET.get('type') # e.g., 'seniors', 'students', 'unemployed', 'minors', 'infants'
    purok = request.GET.get('purok')
    barangay_id = request.GET.get('barangay_id')
    
    residents = Resident.objects.all()
    title = "Residents"
    
    if request.user.is_any_barangay_official:
        if request.user.is_barangay_admin:
            try:
                brgy = Barangay.objects.get(admin_user=request.user)
                residents = residents.filter(barangay=brgy)
            except Barangay.DoesNotExist:
                residents = residents.filter(barangay__name=request.user.barangay_name)
        else:
            residents = residents.filter(barangay__name=request.user.barangay_name)
    elif request.user.is_system_admin and barangay_id:
        residents = residents.filter(barangay_id=barangay_id)
        
    if purok:
        residents = residents.filter(zone_street_purok=purok)
        title += f" in Purok {purok}"
    elif barangay_id:
        brgy = get_object_or_404(Barangay, id=barangay_id)
        title += f" in {brgy.name}"

    if demo_type == 'seniors':
        title = "Senior Citizens " + title
    elif demo_type == 'students':
        title = "Students " + title
    elif demo_type == 'unemployed':
        title = "Unemployed Residents " + title
    elif demo_type == 'employed':
        title = "Employed Residents " + title
    elif demo_type == 'minors':
        title = "Minors " + title
    elif demo_type == 'infants':
        title = "Infants " + title

    residents_list = list(residents.order_by('last_name', 'first_name', 'id'))
    if demo_type == 'seniors':
        residents_list = [r for r in residents_list if r.computed_age_range in _SENIOR_AGE_RANGES]
    elif demo_type == 'students':
        residents_list = [r for r in residents_list if r.is_student]
    elif demo_type == 'unemployed':
        residents_list = [r for r in residents_list if r.employment_status == 'UNEMPLOYED']
    elif demo_type == 'employed':
        residents_list = [r for r in residents_list if r.employment_status == 'EMPLOYED']
    elif demo_type == 'minors':
        residents_list = [r for r in residents_list if r.computed_age_range in _MINOR_AGE_RANGES]
    elif demo_type == 'infants':
        residents_list = [r for r in residents_list if r.computed_age_range == 'INFANT']

    return render(request, 'gis_mapping/demographic_list.html', {
        'residents': residents_list,
        'title': title,
        'demo_type': demo_type
    })

@login_required
def demographic_data(request):
    demo_type = request.GET.get('type')
    purok = request.GET.get('purok')
    barangay_id = request.GET.get('barangay_id')

    residents = Resident.objects.select_related('barangay', 'household', 'user')
    title = "Residents"

    if request.user.is_any_barangay_official:
        if request.user.is_barangay_admin:
            try:
                brgy = Barangay.objects.get(admin_user=request.user)
                residents = residents.filter(barangay=brgy)
            except Barangay.DoesNotExist:
                residents = residents.filter(barangay__name=request.user.barangay_name)
        else:
            residents = residents.filter(barangay__name=request.user.barangay_name)
    elif request.user.is_system_admin and barangay_id:
        residents = residents.filter(barangay_id=barangay_id)

    if purok:
        residents = residents.filter(zone_street_purok=purok)
        title += f" in Purok {purok}"
    elif barangay_id:
        brgy = get_object_or_404(Barangay, id=barangay_id)
        title += f" in {brgy.name}"

    if demo_type == 'seniors':
        title = "Senior Citizens " + title
    elif demo_type == 'students':
        title = "Students " + title
    elif demo_type == 'unemployed':
        title = "Unemployed Residents " + title
    elif demo_type == 'employed':
        title = "Employed Residents " + title
    elif demo_type == 'minors':
        title = "Minors " + title
    elif demo_type == 'infants':
        title = "Infants " + title

    residents_list = list(residents.order_by('last_name', 'first_name', 'id'))
    if demo_type == 'seniors':
        residents_list = [r for r in residents_list if r.computed_age_range in _SENIOR_AGE_RANGES]
    elif demo_type == 'students':
        residents_list = [r for r in residents_list if r.is_student]
    elif demo_type == 'unemployed':
        residents_list = [r for r in residents_list if r.employment_status == 'UNEMPLOYED']
    elif demo_type == 'employed':
        residents_list = [r for r in residents_list if r.employment_status == 'EMPLOYED']
    elif demo_type == 'minors':
        residents_list = [r for r in residents_list if r.computed_age_range in _MINOR_AGE_RANGES]
    elif demo_type == 'infants':
        residents_list = [r for r in residents_list if r.computed_age_range == 'INFANT']

    data = []
    for r in residents_list:
        data.append({
            'id': r.id,
            'name': r.full_name,
            'barangay': r.barangay.name if r.barangay else None,
            'purok': r.zone_street_purok,
            'employment_status': r.employment_status,
            'is_student': bool(r.is_student),
            'age_range': r.computed_age_range,
            'age_range_display': r.computed_age_range_display,
            'contact_number': r.contact_number,
            'household_number': r.household.household_number if r.household else None,
        })

    return JsonResponse({'title': title, 'count': len(data), 'residents': data})

@login_required
@user_passes_test(is_admin_or_dilg)
def edit_disaster_area(request, area_id=None):
    barangay = None
    if request.user.is_barangay_admin:
        barangay = get_object_or_404(Barangay, admin_user=request.user)

    if area_id:
        area = get_object_or_404(DisasterProneArea, pk=area_id)
        if barangay and area.barangay_ref != barangay:
            messages.error(request, "You can only edit areas in your own barangay.")
            return redirect('gis_mapping:map_view')
    else:
        area = None

    if request.method == 'POST':
        form = DisasterProneAreaForm(request.POST, instance=area)
        if form.is_valid():
            disaster_area = form.save(commit=False)
            if barangay:
                disaster_area.barangay_ref = barangay

            boundary_json = request.POST.get('boundary', '')
            if boundary_json:
                try:
                    boundary_data = json.loads(boundary_json)
                    coords = boundary_data['coordinates'][0]
                    poly = Polygon(coords)
                    poly.srid = 4326
                    disaster_area.boundary = poly
                except (json.JSONDecodeError, KeyError, IndexError) as e:
                    messages.error(request, "Invalid boundary data. Please draw again.")
                    return render(request, 'gis_mapping/edit_disaster_area.html', {
                        'form': form,
                        'area': area,
                        'barangays': barangays,
                        'is_system_admin': request.user.is_system_admin,
                    })

            disaster_area.save()
            messages.success(request, f"Hazard area '{disaster_area.name}' saved successfully.")
            return redirect('gis_mapping:map_view')
    else:
        initial = {}
        if area and area.boundary:
            initial['boundary_json'] = area.boundary.json
        form = DisasterProneAreaForm(instance=area, initial=initial)

    barangays = Barangay.objects.all() if request.user.is_system_admin else Barangay.objects.filter(id=barangay.id) if barangay else []

    return render(request, 'gis_mapping/edit_disaster_area.html', {
        'form': form,
        'area': area,
        'barangays': barangays,
        'is_system_admin': request.user.is_system_admin,
    })

@login_required
@user_passes_test(is_admin_or_dilg)
def delete_disaster_area(request, area_id):
    area = get_object_or_404(DisasterProneArea, pk=area_id)

    if request.user.is_barangay_admin:
        try:
            brgy = request.user.managed_barangay
            if area.barangay_ref != brgy:
                messages.error(request, "You can only delete areas in your own barangay.")
                return redirect('gis_mapping:map_view')
        except Barangay.DoesNotExist:
            messages.error(request, "Your account is not linked to a barangay.")
            return redirect('home')

    if request.method == 'POST':
        area_name = area.name
        area.delete()
        messages.success(request, f"Hazard area '{area_name}' deleted.")
        return redirect('gis_mapping:map_view')

    return render(request, 'gis_mapping/confirm_delete.html', {'area': area})

@login_required
@user_passes_test(is_admin_or_dilg)
def add_infrastructure(request):
    barangay = None
    if request.user.is_barangay_admin:
        try:
            barangay = request.user.managed_barangay
        except Barangay.DoesNotExist:
            messages.error(request, "Barangay record not found for your account.")
            return redirect('home')

    if request.method == 'POST':
        form = InfrastructureForm(request.POST)
        lat = request.POST.get('latitude')
        lng = request.POST.get('longitude')
        
        if form.is_valid():
            if not lat or not lng:
                messages.error(request, "Please select a location on the map.")
            else:
                try:
                    from django.contrib.gis.geos import Point
                    location = Point(float(lng), float(lat), srid=4326)
                    infra = form.save(commit=False)
                    infra.location = location
                    
                    if barangay:
                        infra.barangay_ref = barangay
                        infra.barangay = barangay.name # Sync with redundant CharField
                    elif form.cleaned_data.get('barangay_ref'):
                        infra.barangay_ref = form.cleaned_data.get('barangay_ref')
                        infra.barangay = infra.barangay_ref.name
                    else:
                        messages.error(request, "Please select a barangay.")
                        return render(request, 'gis_mapping/add_infrastructure.html', {
                            'form': form,
                            'barangays': Barangay.objects.all(),
                            'is_system_admin': request.user.is_system_admin
                        })
                        
                    infra.save()
                    messages.success(request, f"Infrastructure '{infra.name}' added successfully.")
                    return redirect('gis_mapping:map_view')
                except (ValueError, TypeError) as e:
                    messages.error(request, f"Error saving location: {str(e)}")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = InfrastructureForm()
        if barangay:
            form.fields['barangay_ref'].initial = barangay
            form.fields['barangay_ref'].queryset = Barangay.objects.filter(id=barangay.id)

    barangays = Barangay.objects.all() if request.user.is_system_admin else Barangay.objects.filter(id=barangay.id) if barangay else []
    return render(request, 'gis_mapping/add_infrastructure.html', {
        'form': form,
        'barangays': barangays,
        'is_system_admin': request.user.is_system_admin
    })

@login_required
@user_passes_test(is_admin_or_dilg)
def delete_infrastructure(request, infra_id):
    infra = get_object_or_404(Infrastructure, pk=infra_id)
    
    if request.user.is_barangay_admin:
        if infra.barangay_ref != request.user.managed_barangay:
            messages.error(request, "You can only delete infrastructure in your barangay.")
            return redirect('gis_mapping:map_view')
    
    if request.method == 'POST':
        infra_name = infra.name
        infra.delete()
        messages.success(request, f"Infrastructure '{infra_name}' deleted.")
        return redirect('gis_mapping:map_view')
    
    return render(request, 'gis_mapping/confirm_delete_infra.html', {'infra': infra})

@login_required
@user_passes_test(is_admin_or_dilg)
def delete_all_infrastructure(request):
    if request.method != 'POST':
        return redirect('gis_mapping:map_view')

    qs = Infrastructure.objects.all()

    if request.user.is_barangay_admin:
        try:
            qs = qs.filter(barangay_ref=request.user.managed_barangay)
        except Barangay.DoesNotExist:
            messages.error(request, "Your account is not linked to a barangay.")
            return redirect('home')

    deleted_count, _ = qs.delete()
    messages.success(request, f"Deleted {deleted_count} infrastructure record(s).")
    return redirect('gis_mapping:map_view')

@login_required
@user_passes_test(is_admin_or_dilg)
def add_evacuation_site(request):
    barangay = None
    if request.user.is_barangay_admin:
        try:
            barangay = request.user.managed_barangay
        except Barangay.DoesNotExist:
            messages.error(request, "Barangay record not found for your account.")
            return redirect('home')

    if request.method == 'POST':
        form = EvacuationSiteForm(request.POST)
        lat = request.POST.get('latitude')
        lng = request.POST.get('longitude')
        
        if form.is_valid():
            if not lat or not lng:
                messages.error(request, "Please select a location on the map.")
            else:
                try:
                    from django.contrib.gis.geos import Point
                    location = Point(float(lng), float(lat), srid=4326)
                    evac = form.save(commit=False)
                    evac.location = location
                    
                    if barangay:
                        evac.barangay = barangay
                    elif form.cleaned_data.get('barangay'):
                        evac.barangay = form.cleaned_data.get('barangay')
                    else:
                        messages.error(request, "Please select a barangay.")
                        return render(request, 'gis_mapping/add_evacuation_site.html', {
                            'form': form,
                            'barangays': Barangay.objects.all(),
                            'is_system_admin': request.user.is_system_admin
                        })
                        
                    evac.save()
                    messages.success(request, f"Evacuation Site '{evac.name}' added successfully.")
                    return redirect('gis_mapping:map_view')
                except (ValueError, TypeError) as e:
                    messages.error(request, f"Error saving location: {str(e)}")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = EvacuationSiteForm()
        if barangay:
            form.fields['barangay'].initial = barangay
            form.fields['barangay'].queryset = Barangay.objects.filter(id=barangay.id)

    barangays = Barangay.objects.all() if request.user.is_system_admin else Barangay.objects.filter(id=barangay.id) if barangay else []
    return render(request, 'gis_mapping/add_evacuation_site.html', {
        'form': form,
        'barangays': barangays,
        'is_system_admin': request.user.is_system_admin
    })

@login_required
@user_passes_test(is_admin_or_dilg)
def delete_evacuation_site(request, evac_id):
    evac = get_object_or_404(EvacuationSite, pk=evac_id)
    
    if request.user.is_barangay_admin:
        if evac.barangay != request.user.managed_barangay:
            messages.error(request, "You can only delete evacuation sites in your barangay.")
            return redirect('gis_mapping:map_view')
    
    if request.method == 'POST':
        evac_name = evac.name
        evac.delete()
        messages.success(request, f"Evacuation Site '{evac_name}' deleted.")
        return redirect('gis_mapping:map_view')
    
    return render(request, 'gis_mapping/confirm_delete_evac.html', {'evac': evac})
