from django.shortcuts import render, redirect, get_object_or_404
from django.db import models
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import Barangay, Household, Official, Service, ServiceRequest, Resident, IncidentReport, Notification, Announcement, ResidentDocument
from .forms import ResidentForm, HouseholdForm, ProfileCompletionForm, DocumentUploadForm, OfficialForm, ServiceForm, ServiceRequestForm, ServiceRequestUpdateForm, IncidentReportForm, IncidentResponseForm, AnnouncementForm, StaffAccountForm, ResidentsExcelUploadForm
from django.contrib.auth import get_user_model
import json
import pandas as pd
from io import BytesIO
from openpyxl import Workbook

User = get_user_model()
from analytics.ml_models import VulnerabilityClassifier
import csv

def _barangay_boundaries_json(qs):
    payload = []
    for b in qs:
        if not b.boundary:
            continue
        geom = b.boundary
        if hasattr(geom, 'valid') and not geom.valid:
            try:
                geom = geom.buffer(0)
            except Exception:
                geom = b.boundary
        payload.append({
            'id': b.id,
            'name': b.name,
            'boundary': json.loads(geom.json),
        })
    return json.dumps(payload)

def _is_within_barangay_boundary(barangay, location_point):
    if not barangay or not getattr(barangay, 'boundary', None) or not location_point:
        return True
    try:
        boundary = barangay.boundary
        point = location_point

        boundary_srid = getattr(boundary, 'srid', None) or 0
        point_srid = getattr(point, 'srid', None) or 0

        if boundary_srid in (0, None):
            boundary = boundary.clone()
            boundary.srid = point_srid or 4326
            boundary_srid = boundary.srid

        if point_srid in (0, None) and boundary_srid not in (0, None):
            point = point.clone()
            point.srid = boundary_srid
            point_srid = point.srid

        if boundary_srid and point_srid and boundary_srid != point_srid:
            point = point.clone()
            point.transform(boundary_srid)

        b = boundary
        if hasattr(b, 'valid') and not b.valid:
            try:
                b = b.buffer(0)
            except Exception:
                b = boundary

        try:
            if hasattr(b, 'covers') and b.covers(point):
                return True
        except Exception:
            pass

        if b.contains(point) or b.touches(point):
            return True

        for tol in (0.0002, 0.001):
            try:
                buffered = b.buffer(tol)
                if hasattr(buffered, 'covers'):
                    if buffered.covers(point):
                        return True
                elif buffered.contains(point) or buffered.touches(point):
                    return True
            except Exception:
                continue
        return False
    except Exception:
        return False

def is_barangay_admin(user):
    return user.role == 'BARANGAY'

def is_any_barangay_official(user):
    return user.role in ['BARANGAY', 'BARANGAY_STAFF']

def is_staff_portal(user):
    return user.is_system_admin or user.is_any_barangay_official

def get_user_barangay(user):
    """
    Helper to get the barangay object associated with a user.
    """
    if user.is_barangay_admin:
        return user.managed_barangay
    elif user.is_barangay_staff:
        return Barangay.objects.filter(name=user.barangay_name).first()
    return None

def get_resident_barangay(resident):
    brgy = None
    if resident.household and resident.household.barangay:
        brgy = resident.household.barangay
    elif resident.barangay:
        brgy = resident.barangay

    if brgy and resident.barangay_id != brgy.id and resident.pk:
        Resident.objects.filter(pk=resident.pk).update(barangay=brgy)
        resident.barangay = brgy

    return brgy

def announcement_queryset_for_user(user):
    if user.is_system_admin:
        return Announcement.objects.all().order_by('-created_at')
    if user.is_any_barangay_official:
        brgy = get_user_barangay(user)
        if brgy:
            return Announcement.objects.filter(barangay=brgy).order_by('-created_at')
    return Announcement.objects.none()

@login_required
@user_passes_test(is_barangay_admin)
def official_list(request):
    brgy = get_user_barangay(request.user)
    if not brgy:
        messages.error(request, "You are not assigned to a barangay.")
        return redirect('home')
        
    term = request.GET.get('term')
    officials = Official.objects.filter(barangay=brgy)
    
    if term:
        # Simple term filtering (year based)
        officials = officials.filter(term_start__year=term)
        
    return render(request, 'residents/official_list.html', {
        'officials': officials,
        'barangay': brgy,
        'current_term': term
    })

@login_required
@user_passes_test(is_barangay_admin)
def official_add(request):
    brgy = get_user_barangay(request.user)
    if request.method == 'POST':
        form = OfficialForm(request.POST, barangay=brgy)
        if form.is_valid():
            official = form.save(commit=False)
            official.barangay = brgy
            official.save()
            messages.success(request, "Official added successfully.")
            return redirect('residents:official_list')
    else:
        form = OfficialForm(barangay=brgy)
    return render(request, 'residents/official_form.html', {'form': form, 'title': 'Add Official'})

@login_required
@user_passes_test(is_barangay_admin)
def official_edit(request, pk):
    brgy = get_user_barangay(request.user)
    official = get_object_or_404(Official, pk=pk, barangay=brgy)
    if request.method == 'POST':
        form = OfficialForm(request.POST, instance=official, barangay=brgy)
        if form.is_valid():
            form.save()
            messages.success(request, "Official updated successfully.")
            return redirect('residents:official_list')
    else:
        form = OfficialForm(instance=official, barangay=brgy)
    return render(request, 'residents/official_form.html', {'form': form, 'title': 'Edit Official'})

@login_required
@user_passes_test(is_barangay_admin)
def official_delete(request, pk):
    brgy = get_user_barangay(request.user)
    official = get_object_or_404(Official, pk=pk, barangay=brgy)
    official.delete()
    messages.success(request, "Official deleted successfully.")
    return redirect('residents:official_list')

@login_required
@user_passes_test(is_any_barangay_official)
def service_list(request):
    brgy = get_user_barangay(request.user)
    services = Service.objects.filter(barangay=brgy)
    return render(request, 'residents/service_list.html', {'services': services, 'barangay': brgy})

@login_required
@user_passes_test(is_barangay_admin)
def service_add(request):
    brgy = get_user_barangay(request.user)
    if request.method == 'POST':
        form = ServiceForm(request.POST)
        if form.is_valid():
            service = form.save(commit=False)
            service.barangay = brgy
            service.save()
            messages.success(request, "Service added successfully.")
            return redirect('residents:service_list')
    else:
        form = ServiceForm()
    return render(request, 'residents/service_form.html', {'form': form, 'title': 'Add Service'})

@login_required
@user_passes_test(is_barangay_admin)
def service_edit(request, pk):
    brgy = get_user_barangay(request.user)
    service = get_object_or_404(Service, pk=pk, barangay=brgy)
    if request.method == 'POST':
        form = ServiceForm(request.POST, instance=service)
        if form.is_valid():
            form.save()
            messages.success(request, "Service updated successfully.")
            return redirect('residents:service_list')
    else:
        form = ServiceForm(instance=service)
    return render(request, 'residents/service_form.html', {'form': form, 'title': 'Edit Service'})

@login_required
@user_passes_test(is_barangay_admin)
def service_delete(request, pk):
    brgy = get_user_barangay(request.user)
    service = get_object_or_404(Service, pk=pk, barangay=brgy)
    service.delete()
    messages.success(request, "Service deleted successfully.")
    return redirect('residents:service_list')

@login_required
def available_services(request):
    if request.user.is_system_admin:
        return redirect('analytics:dilg_dashboard')
    elif request.user.is_any_barangay_official:
        return redirect('analytics:barangay_dashboard')

    """
    View for residents to see services offered by their barangay.
    """
    try:
        resident = request.user.resident_profile
    except Resident.DoesNotExist:
        return redirect('residents:complete_profile')

    brgy = get_resident_barangay(resident)
    if not brgy:
        return redirect('residents:complete_profile')
        
    services = Service.objects.filter(barangay=brgy, is_active=True)
    return render(request, 'residents/available_services.html', {'services': services, 'barangay': brgy})

@login_required
def request_service(request, pk):
    if request.user.is_system_admin:
        return redirect('analytics:dilg_dashboard')
    elif request.user.is_any_barangay_official:
        return redirect('analytics:barangay_dashboard')

    try:
        resident = request.user.resident_profile
    except Resident.DoesNotExist:
        return redirect('residents:complete_profile')

    brgy = get_resident_barangay(resident)
    if not brgy:
        return redirect('residents:complete_profile')

    service = get_object_or_404(Service, pk=pk, barangay=brgy, is_active=True)
    existing = ServiceRequest.objects.filter(service=service, resident=resident).exclude(status='COMPLETED').first()
    if existing:
        messages.info(request, "You already have a pending request for this service.")
        return redirect('residents:my_service_requests')

    if request.method == 'POST':
        form = ServiceRequestForm(request.POST)
        if form.is_valid():
            req = form.save(commit=False)
            req.service = service
            req.resident = resident
            req.barangay = service.barangay
            req.save()
            if brgy.admin_user:
                Notification.objects.create(
                    user=brgy.admin_user,
                    title=f"New Service Request: {service.name}",
                    message=f"{resident.full_name} requested '{service.name}'.",
                )
            messages.success(request, "Service request submitted successfully.")
            return redirect('residents:my_service_requests')
    else:
        form = ServiceRequestForm()
    return render(request, 'residents/service_request_form.html', {'form': form, 'service': service, 'barangay': brgy})

@login_required
def my_service_requests(request):
    if request.user.is_system_admin:
        return redirect('analytics:dilg_dashboard')
    elif request.user.is_any_barangay_official:
        return redirect('analytics:barangay_dashboard')

    try:
        resident = request.user.resident_profile
    except Resident.DoesNotExist:
        return redirect('residents:complete_profile')

    brgy = get_resident_barangay(resident)
    if not brgy:
        return redirect('residents:complete_profile')

    requests_qs = ServiceRequest.objects.filter(resident=resident).select_related('service', 'barangay')
    return render(request, 'residents/my_service_requests.html', {'requests': requests_qs, 'barangay': brgy})

@login_required
@user_passes_test(is_any_barangay_official)
def service_request_list(request):
    brgy = get_user_barangay(request.user)
    if not brgy:
        return redirect('home')
        
    status_filter = request.GET.get('status')
    requests = ServiceRequest.objects.filter(barangay=brgy).select_related('service', 'resident').order_by('-created_at')
    
    if status_filter:
        requests = requests.filter(status=status_filter)
        
    return render(request, 'residents/service_request_list.html', {
        'requests': requests,
        'barangay': brgy,
        'current_status': status_filter
    })

@login_required
@user_passes_test(is_any_barangay_official)
def service_request_update(request, pk):
    brgy = get_user_barangay(request.user)
    if not brgy:
        return redirect('home')
        
    req = get_object_or_404(ServiceRequest, pk=pk, barangay=brgy)
    if request.method == 'POST':
        form = ServiceRequestUpdateForm(request.POST, instance=req)
        if form.is_valid():
            req = form.save()
            if req.resident and req.resident.user:
                Notification.objects.create(
                    user=req.resident.user,
                    title=f"Service Request Update: {req.service.name}",
                    message=f"Your request status is now '{req.get_status_display()}'.",
                )
            messages.success(request, "Service request updated.")
            return redirect('residents:service_request_list')
    else:
        form = ServiceRequestUpdateForm(instance=req)
    return render(request, 'residents/service_request_update.html', {'form': form, 'request_obj': req, 'barangay': brgy})

@login_required
def submit_report(request):
    if request.user.is_system_admin:
        return redirect('analytics:dilg_dashboard')
    elif request.user.is_any_barangay_official:
        return redirect('analytics:barangay_dashboard')

    try:
        resident = request.user.resident_profile
    except Resident.DoesNotExist:
        return redirect('residents:complete_profile')
        
    if not resident.barangay:
        messages.error(request, "Please complete your profile first.")
        return redirect('residents:complete_profile')
        
    if request.method == 'POST':
        form = IncidentReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.resident = resident
            report.barangay = resident.barangay
            report.save()
            
            # Create notification for barangay officials (future task)
            messages.success(request, "Report submitted successfully. We will review it shortly.")
            return redirect('residents:my_reports')
    else:
        form = IncidentReportForm()
    return render(request, 'residents/report_form.html', {'form': form, 'title': 'Submit Report'})

@login_required
def my_reports(request):
    try:
        resident = request.user.resident_profile
    except Resident.DoesNotExist:
        return redirect('residents:complete_profile')
        
    reports = IncidentReport.objects.filter(resident=resident).order_by('-created_at')
    return render(request, 'residents/my_reports.html', {'reports': reports})

@login_required
@user_passes_test(is_any_barangay_official)
def report_list(request):
    brgy = get_user_barangay(request.user)
    if not brgy:
        return redirect('home')
        
    status_filter = request.GET.get('status')
    reports = IncidentReport.objects.filter(barangay=brgy).order_by('-created_at')
    
    if status_filter:
        reports = reports.filter(status=status_filter)
        
    return render(request, 'residents/report_list.html', {
        'reports': reports,
        'barangay': brgy,
        'current_status': status_filter
    })

@login_required
@user_passes_test(is_any_barangay_official)
def report_respond(request, pk):
    brgy = get_user_barangay(request.user)
    if not brgy:
        return redirect('home')
        
    report = get_object_or_404(IncidentReport, pk=pk, barangay=brgy)
    if request.method == 'POST':
        form = IncidentResponseForm(request.POST, instance=report)
        if form.is_valid():
            report = form.save()
            
            # Notify Complainant (nagreklamo)
            if report.resident and report.resident.user:
                Notification.objects.create(
                    user=report.resident.user,
                    title=f"Report Update: {report.title}",
                    message=f"Your report status is now '{report.get_status_display()}'. " + 
                            (f"Scheduled for {report.schedule_date} at {report.schedule_time} at {report.location}." if report.status == 'SCHEDULED' else "")
                )
            
            # Notify Respondent (gireklamo) if they are in the system
            if report.respondent_name and report.status == 'SCHEDULED':
                # Attempt to find the respondent in the resident database
                from django.db.models import Q
                potential_respondents = Resident.objects.filter(
                    Q(first_name__icontains=report.respondent_name) | 
                    Q(last_name__icontains=report.respondent_name)
                ).filter(barangay=report.barangay)
                
                for res in potential_respondents:
                    if res.user:
                        Notification.objects.create(
                            user=res.user,
                            title="Summon: Barangay Hearing",
                            message=f"You are requested to appear at {report.location} for a hearing regarding a report filed by {report.resident.full_name}. " +
                                    f"Schedule: {report.schedule_date} at {report.schedule_time}."
                        )
            
            messages.success(request, "Response saved and notifications sent.")
            return redirect('residents:report_list')
    else:
        form = IncidentResponseForm(instance=report)
    return render(request, 'residents/report_respond.html', {'form': form, 'report': report})

@login_required
def notification_list(request):
    notifications = request.user.notifications.all().order_by('-created_at')
    return render(request, 'residents/notification_list.html', {'notifications': notifications})

@login_required
def mark_notification_as_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save()
    return redirect('residents:notification_list')

@login_required
def download_resident_history(request):
    """
    Generate a CSV report of the resident's incident report history.
    """
    try:
        resident = request.user.resident_profile
    except (Resident.DoesNotExist, AttributeError):
        return render(request, 'error.html', {'message': 'Profile not found.'})

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{resident.last_name}_activity_report.csv"'

    writer = csv.writer(response)
    writer.writerow(['Date Reported', 'Title', 'Type', 'Respondent', 'Status', 'Last Updated'])

    reports = IncidentReport.objects.filter(resident=resident).order_by('-created_at')
    for report in reports:
        writer.writerow([
            report.created_at.strftime("%Y-%m-%d %H:%M"),
            report.title,
            report.get_report_type_display(),
            report.respondent_name or "N/A",
            report.get_status_display(),
            report.updated_at.strftime("%Y-%m-%d %H:%M")
        ])

    return response

@login_required
def complete_profile(request):
    if request.user.is_any_barangay_official:
        return redirect('analytics:barangay_dashboard')
    elif request.user.is_system_admin:
        return redirect('analytics:dilg_dashboard')

    resident, created = Resident.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = ProfileCompletionForm(request.POST, request.FILES, instance=resident)
        if form.is_valid():
            # Check for existing record to enforce 1:1 resident account constraint
            first_name = form.cleaned_data.get('first_name')
            last_name = form.cleaned_data.get('last_name')
            dob = form.cleaned_data.get('date_of_birth')
            
            # Check if another user already claimed this resident profile
            existing_resident_with_user = Resident.objects.filter(
                first_name__iexact=first_name,
                last_name__iexact=last_name,
                date_of_birth=dob,
                user__isnull=False
            ).exclude(pk=resident.pk).first()
            
            if existing_resident_with_user:
                messages.error(request, "A resident with this name and date of birth is already registered with an account. Please contact your barangay office if you believe this is an error.")
                return render(request, 'residents/complete_profile.html', {'form': form})

            existing_resident = Resident.objects.filter(
                first_name__iexact=first_name,
                last_name__iexact=last_name,
                date_of_birth=dob,
                user__isnull=True
            ).exclude(pk=resident.pk).first()
            
            if existing_resident:
                # Link existing record to this user and remove the temporary one
                temp_resident_pk = resident.pk
                resident = existing_resident
                resident.user = request.user
                # Re-bind form to the existing resident instance to save the new data
                form = ProfileCompletionForm(request.POST, request.FILES, instance=resident)
                if form.is_valid():
                    resident = form.save(commit=False)
                    # Delete temporary resident after we're sure we can save
                    Resident.objects.filter(pk=temp_resident_pk).delete()
                    messages.success(request, "We found an existing record for you and linked it to your account.")
                else:
                    # If for some reason it's invalid now, revert to the temporary resident
                    # and show errors. This shouldn't really happen.
                    resident = Resident.objects.get(pk=temp_resident_pk)
                    return render(request, 'residents/complete_profile.html', {'form': form})
            else:
                resident = form.save(commit=False)
            
            # Logic to handle new household creation if provided
            if not form.cleaned_data.get('household'):
                new_hh_num = form.cleaned_data.get('new_household_number')
                if form.cleaned_data.get('no_household_number'):
                    import uuid
                    # Generate a unique temporary number
                    new_hh_num = f"TEMP-{uuid.uuid4().hex[:8].upper()}"
                
                brgy = form.cleaned_data.get('new_barangay')
                
                new_hh = Household.objects.create(
                    household_number=new_hh_num,
                    address=form.cleaned_data.get('new_household_address'),
                    barangay=brgy
                )
                resident.household = new_hh
                resident.barangay = brgy
            else:
                resident.barangay = resident.household.barangay
            
            resident.save()
            return redirect('residents:resident_dashboard')
    else:
        # Check if profile is actually complete and update status if it's still INCOMPLETE
        if resident.profile_status == 'INCOMPLETE' and resident.has_completed_profile():
            resident.profile_status = 'PENDING_APPROVAL'
            resident.save()
            messages.info(request, "Your profile is now complete and pending approval.")
        
        form = ProfileCompletionForm(instance=resident)
        if resident.profile_status == 'INCOMPLETE' and not any('is-invalid-highlight' in f.widget.attrs.get('class', '') for f in form.fields.values()):
            messages.info(request, "Your profile is marked as incomplete, but all basic required fields seem to be filled. Please review all sections.")
    return render(request, 'residents/complete_profile.html', {'form': form})

@login_required
def my_profile(request):
    """
    Residents can view their own profile.
    """
    if request.user.is_any_barangay_official:
        messages.info(request, "Staff profiles are managed by the System Administrator.")
        return redirect('analytics:barangay_dashboard')
    elif request.user.is_system_admin:
        return redirect('analytics:dilg_dashboard')

    try:
        resident = request.user.resident_profile
    except (Resident.DoesNotExist, AttributeError):
        messages.error(request, "Your account is not linked to a resident record.")
        return redirect('home')
    
    return render(request, 'residents/my_profile.html', {'resident': resident})

@login_required
def edit_my_profile(request):
    """
    Residents can edit their own profile information.
    """
    if request.user.is_any_barangay_official:
        messages.info(request, "Staff profiles are managed by the System Administrator.")
        return redirect('analytics:barangay_dashboard')
    elif request.user.is_system_admin:
        return redirect('analytics:dilg_dashboard')

    try:
        resident = request.user.resident_profile
    except (Resident.DoesNotExist, AttributeError):
        messages.error(request, "Your account is not linked to a resident record.")
        return redirect('home')
    
    if request.method == 'POST':
        form = ProfileCompletionForm(request.POST, request.FILES, instance=resident)
        if form.is_valid():
            resident = form.save(commit=False)
            
            # Handle new household creation if provided
            if not form.cleaned_data.get('household') and form.cleaned_data.get('new_household_number'):
                new_hh_num = form.cleaned_data.get('new_household_number')
                new_hh_addr = form.cleaned_data.get('new_household_address')
                new_brgy = form.cleaned_data.get('new_barangay')
                
                if new_brgy:
                    new_hh = Household.objects.create(
                        household_number=new_hh_num,
                        address=new_hh_addr,
                        barangay=new_brgy
                    )
                    resident.household = new_hh
                    resident.barangay = new_brgy
            
            resident.save()
            messages.success(request, "Your profile has been updated successfully.")
            return redirect('residents:my_profile')
    else:
        # Check if profile is actually complete and update status if it's still INCOMPLETE
        if resident.profile_status == 'INCOMPLETE' and resident.has_completed_profile():
            resident.profile_status = 'PENDING_APPROVAL'
            resident.save()
            messages.info(request, "Your profile is now complete and pending approval.")
            
        form = ProfileCompletionForm(instance=resident)
        if resident.profile_status == 'INCOMPLETE' and not any('is-invalid-highlight' in f.widget.attrs.get('class', '') for f in form.fields.values()):
            messages.info(request, "Your profile is marked as incomplete, but all basic required fields seem to be filled. Please review all sections.")
        if resident.barangay:
            form.fields['new_barangay'].initial = resident.barangay
        if resident.household:
            form.fields['household'].queryset = Household.objects.filter(barangay=resident.barangay)
    
    return render(request, 'residents/complete_profile.html', {'form': form})

@login_required
def map_my_household(request):
    if request.user.is_system_admin:
        return redirect('analytics:dilg_dashboard')
    if request.user.is_any_barangay_official:
        return redirect('analytics:barangay_dashboard')
    if not request.user.is_resident:
        return redirect('home')

    try:
        resident = request.user.resident_profile
    except (Resident.DoesNotExist, AttributeError):
        messages.error(request, "Your account is not linked to a resident record.")
        return redirect('home')

    if not resident.household:
        messages.error(request, "No household is linked to your profile. Please set your household first.")
        return redirect('residents:edit_my_profile')

    household = resident.household
    brgy = household.barangay

    if request.method == 'POST':
        if request.POST.get('delete_location') == '1':
            household.location = None
            household.save(update_fields=['location'])
            messages.success(request, "Household location deleted.")
            return redirect('residents:map_my_household')

        form = HouseholdForm(request.POST, instance=household)
        for name in ('household_number', 'address', 'barangay'):
            if name in form.fields:
                form.fields[name].disabled = True
        if form.is_valid():
            updated = form.save(commit=False)
            updated.household_number = household.household_number
            updated.address = household.address
            updated.barangay = household.barangay

            if not _is_within_barangay_boundary(brgy, updated.location):
                messages.error(request, "Pinned location is outside your barangay boundary. Please pin inside the boundary.")
                barangay_boundaries_json = _barangay_boundaries_json(Barangay.objects.filter(pk=brgy.pk))
                return render(request, 'residents/household_form.html', {
                    'form': form,
                    'title': 'Map My Household',
                    'barangay_boundaries_json': barangay_boundaries_json,
                    'is_resident_mapping': True,
                    'cancel_url': 'residents:resident_dashboard',
                })

            updated.save()
            messages.success(request, "Household location updated successfully.")
            return redirect('residents:resident_dashboard')
        messages.error(request, "Please correct the errors below.")
    else:
        form = HouseholdForm(instance=household)
        for name in ('household_number', 'address', 'barangay'):
            if name in form.fields:
                form.fields[name].disabled = True

    barangay_boundaries_json = _barangay_boundaries_json(Barangay.objects.filter(pk=brgy.pk)) if brgy else _barangay_boundaries_json(Barangay.objects.all())
    return render(request, 'residents/household_form.html', {
        'form': form,
        'title': 'Map My Household',
        'barangay_boundaries_json': barangay_boundaries_json,
        'is_resident_mapping': True,
        'cancel_url': 'residents:resident_dashboard',
    })

@login_required
def verify_resident(request, resident_id):
    """
    Mark a resident as verified/approved.
    Only the barangay where the resident lives can verify them.
    """
    resident = get_object_or_404(Resident, pk=resident_id)

    if request.method != 'POST':
        return redirect('residents:resident_detail', pk=resident_id)
    
    # Check permissions: System Admin or Barangay Official of the same barangay
    is_authorized = False
    if request.user.is_system_admin:
        is_authorized = True
    elif request.user.is_any_barangay_official:
        # Check if the official belongs to the same barangay as the resident
        official_brgy = get_user_barangay(request.user)
        if resident.barangay == official_brgy:
            is_authorized = True

    if not is_authorized:
        messages.error(request, "You are not authorized to verify residents from this barangay.")
        return redirect('residents:resident_detail', pk=resident_id)

    resident.profile_status = 'APPROVED'
    resident.is_active = True
    resident.is_verified = True
    resident.save()
    
    # Also update the associated user if it exists
    if resident.user:
        resident.user.is_approved = True
        resident.user.is_active = True
        resident.user.save()
        
        # Notify the resident
        Notification.objects.create(
            user=resident.user,
            title="Profile Approved",
            message="Your resident profile has been verified and approved by your barangay officials.",
        )
    
    messages.success(request, f"Resident {resident.full_name} has been verified and approved.")
    return redirect('residents:resident_detail', pk=resident_id)

@login_required
def reject_resident(request, resident_id):
    """
    Reject a resident's profile.
    """
    resident = get_object_or_404(Resident, pk=resident_id)

    if request.method != 'POST':
        return redirect('residents:resident_detail', pk=resident_id)
    
    # Check permissions: System Admin or Barangay Official of the same barangay
    is_authorized = False
    if request.user.is_system_admin:
        is_authorized = True
    elif request.user.is_any_barangay_official:
        official_brgy = get_user_barangay(request.user)
        if resident.barangay == official_brgy:
            is_authorized = True

    if not is_authorized:
        messages.error(request, "You are not authorized to reject residents from this barangay.")
        return redirect('residents:resident_detail', pk=resident_id)

    resident.profile_status = 'INCOMPLETE'
    resident.is_verified = False
    resident.save()
    
    # Notify the resident if they have a user account
    if resident.user:
        resident.user.is_approved = False
        resident.user.save(update_fields=['is_approved'])
        Notification.objects.create(
            user=resident.user,
            title="Profile Rejected",
            message="Your resident profile was not approved. Please review your information and submit again.",
        )
    
    messages.warning(request, f"Resident {resident.full_name}'s profile has been rejected.")
    return redirect('residents:resident_detail', pk=resident_id)

@login_required
@user_passes_test(is_barangay_admin)
def staff_list(request):
    """
    List all staff accounts for the current barangay.
    """
    brgy = get_user_barangay(request.user)
    if not brgy:
        messages.error(request, "You are not assigned to a barangay.")
        return redirect('home')
    
    staff_accounts = User.objects.filter(role='BARANGAY_STAFF', barangay_name=brgy.name)
    return render(request, 'residents/staff_list.html', {
        'staff_accounts': staff_accounts,
        'barangay': brgy
    })

@login_required
@user_passes_test(is_barangay_admin)
def staff_add(request):
    """
    Add a new staff account for the current barangay.
    """
    brgy = get_user_barangay(request.user)
    if not brgy:
        messages.error(request, "You are not assigned to a barangay.")
        return redirect('home')
    
    if request.method == 'POST':
        form = StaffAccountForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.barangay_name = brgy.name
            user.save()
            messages.success(request, f"Staff account for {user.get_full_name()} created successfully.")
            return redirect('residents:staff_list')
    else:
        form = StaffAccountForm()
    
    return render(request, 'residents/staff_form.html', {
        'form': form,
        'title': 'Add Staff Account',
        'barangay': brgy
    })

@login_required
@user_passes_test(is_barangay_admin)
def staff_delete(request, pk):
    """
    Delete a staff account.
    """
    brgy = get_user_barangay(request.user)
    staff = get_object_or_404(User, pk=pk, role='BARANGAY_STAFF', barangay_name=brgy.name)
    
    if request.method == 'POST':
        staff.delete()
        messages.success(request, "Staff account deleted successfully.")
        return redirect('residents:staff_list')
    
    return render(request, 'residents/staff_confirm_delete.html', {'staff': staff})

@login_required
def chatbot_view(request):
    """
    A simple chatbot to help residents and admins.
    """
    faq_data = [
        {"keywords": ["clearance", "document", "issue"], "answer": "To issue or request a clearance, go to the 'Services' section and select the type of document you need."},
        {"keywords": ["voter", "register"], "answer": "You can update your voter status in your profile settings. Ensure you are a registered resident first."},
        {"keywords": ["report", "incident", "concern"], "answer": "Use the 'Report a Concern' button on your dashboard to submit an incident report."},
        {"keywords": ["profile", "complete", "update"], "answer": "You can update your profile information in the 'My Profile' section to keep it accurate and up-to-date."},
        {"keywords": ["backup", "data", "secure"], "answer": "Barangay data is automatically backed up. Admins can also trigger manual backups via the system management console."},
    ]

    response = "I'm sorry, I didn't understand that. Could you please rephrase or ask about clearances, reporting concerns, or profile updates?"
    user_message = request.GET.get('message', '').lower()

    if user_message:
        for item in faq_data:
            if any(keyword in user_message for keyword in item['keywords']):
                response = item['answer']
                break
        return JsonResponse({'response': response})

    return render(request, 'residents/chatbot.html')

@login_required
def resident_dashboard(request):
    """
    Dashboard for Residents to view announcements and track reports.
    """
    if request.user.is_system_admin:
        return redirect('analytics:dilg_dashboard')
    elif request.user.is_any_barangay_official:
        return redirect('analytics:barangay_dashboard')

    try:
        resident = request.user.resident_profile
    except (Resident.DoesNotExist, AttributeError):
        return render(request, 'error.html', {'message': 'User is not linked to a resident record.'})
        
    brgy = resident.barangay
    if not brgy:
        return redirect('residents:complete_profile')

    from django.utils import timezone
    today = timezone.now().date()
    
    announcements = Announcement.objects.filter(
        models.Q(barangay=brgy) | models.Q(is_global=True)
    ).filter(
        models.Q(start_date__lte=today) | models.Q(start_date__isnull=True),
        models.Q(end_date__gte=today) | models.Q(end_date__isnull=True)
    ).order_by('-created_at')
    
    reports = IncidentReport.objects.filter(resident=resident).order_by('-created_at')
    documents = ResidentDocument.objects.filter(resident=resident)

    ml_vulnerability = None
    if resident.household:
        from datetime import date
        current_year = date.today().year
        household_size = Resident.objects.filter(household=resident.household).count()
        num_elderly = Resident.objects.filter(household=resident.household, date_of_birth__year__lt=current_year - 60).count()
        num_children = Resident.objects.filter(household=resident.household, date_of_birth__year__gt=current_year - 12).count()
        address = resident.household.address or ''
        is_near_river = 1 if 'river' in address.lower() else 0
        is_near_slope = 1 if any(k in address.lower() for k in ('slope', 'mountain')) else 0
        classifier = VulnerabilityClassifier()
        ml_vulnerability = classifier.predict([household_size, num_elderly, num_children, is_near_river, is_near_slope])
    
    if request.method == 'POST':
        # Distinguish between incident report and document upload
        if 'submit_report' in request.POST:
            # We'll need a new IncidentReportForm
            pass
        elif 'submit_document' in request.POST:
            doc_form = DocumentUploadForm(request.POST, request.FILES)
            if doc_form.is_valid():
                doc = doc_form.save(commit=False)
                doc.resident = resident
                doc.save()
                return redirect('residents:resident_dashboard')
    
    # We'll refine the forms later
    doc_form = DocumentUploadForm()
        
    context = {
        'resident': resident,
        'barangay': brgy,
        'announcements': announcements,
        'reports': reports,
        'documents': documents,
        'doc_form': doc_form,
        'ml_vulnerability': ml_vulnerability,
    }
    return render(request, 'residents/resident_dashboard.html', context)

@login_required
def resident_list(request):
    if not is_staff_portal(request.user):
        return redirect('residents:resident_dashboard')

    residents = Resident.objects.all()
    
    # Quick Search Capability
    query = request.GET.get('q')
    if query:
        residents = residents.filter(
            models.Q(first_name__icontains=query) |
            models.Q(last_name__icontains=query) |
            models.Q(resident_code__icontains=query) |
            models.Q(gender__icontains=query) |
            models.Q(civil_status__icontains=query) |
            models.Q(citizenship__icontains=query) |
            models.Q(religion__icontains=query) |
            models.Q(zone_street_purok__icontains=query) |
            models.Q(profile_status__icontains=query) |
            models.Q(residency_status__icontains=query)
        )

    if request.user.is_any_barangay_official:
        brgy = get_user_barangay(request.user)
        if brgy:
            residents = residents.filter(barangay=brgy)
        else:
            # If official not assigned, they shouldn't see anything or at least only their own if they are also a resident
            residents = residents.none()

    profile_status = request.GET.get('status') or request.GET.get('profile_status')
    if profile_status in ['INCOMPLETE', 'PENDING_APPROVAL', 'APPROVED']:
        residents = residents.filter(profile_status=profile_status)

    # Active status filtering
    active_status = request.GET.get('active_status')
    if active_status == 'active':
        residents = residents.filter(is_active=True)
    elif active_status == 'inactive':
        residents = residents.filter(is_active=False)

    return render(request, 'residents/resident_list.html', {
        'residents': residents, 
        'query': query,
        'active_status': active_status,
        'profile_status': profile_status,
        'upload_form': ResidentsExcelUploadForm(),
    })

@login_required
def download_residents_excel_template(request):
    if not is_staff_portal(request.user):
        return redirect('residents:resident_dashboard')

    if not request.user.is_any_barangay_official:
        return redirect('residents:resident_list')

    wb = Workbook()
    ws = wb.active
    ws.title = 'Residents'

    headers = [
        'first_name',
        'last_name',
        'middle_name',
        'date_of_birth',
        'gender',
        'civil_status',
        'contact_number',
        'email',
        'zone_street_purok',
        'present_address',
        'residency_status',
        'residency_type',
        'years_in_barangay',
        'employment_status',
        'occupation',
        'income',
        'is_student',
        'is_voter',
        'current_location',
        'away_duration_years',
        'away_duration_months',
    ]

    ws.append(headers)
    ws.append([
        'Juan',
        'Dela Cruz',
        '',
        '2000-01-01',
        'MALE',
        'SINGLE',
        '09XXXXXXXXX',
        '',
        'Purok 1',
        'Sample Address',
        'PERMANENT',
        'HOUSE_OWNER',
        5,
        'EMPLOYED',
        'Driver',
        10000,
        False,
        True,
        'IN_BARANGAY',
        0,
        0,
    ])

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename="residents_upload_template.xlsx"'
    return response

@login_required
def import_residents_excel(request):
    if not is_staff_portal(request.user):
        return redirect('residents:resident_dashboard')

    if not request.user.is_any_barangay_official:
        return redirect('residents:resident_list')

    if request.method != 'POST':
        return redirect('residents:resident_list')

    form = ResidentsExcelUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        messages.error(request, "Please upload a valid Excel file.")
        return redirect('residents:resident_list')

    brgy = get_user_barangay(request.user)
    if not brgy:
        messages.error(request, "Your account is not assigned to a barangay.")
        return redirect('residents:resident_list')

    f = form.cleaned_data['file']

    try:
        df = pd.read_excel(f)
    except Exception:
        messages.error(request, "Unable to read the Excel file. Please upload a valid .xlsx file.")
        return redirect('residents:resident_list')

    def _norm_col(c):
        return str(c or '').strip().lower().replace(' ', '_')

    df.columns = [_norm_col(c) for c in df.columns]

    def _first(row, keys):
        for k in keys:
            if k in row and row[k] is not None and str(row[k]).strip() != '' and str(row[k]).strip().lower() != 'nan':
                return row[k]
        return None

    def _to_str(v):
        if v is None:
            return ''
        s = str(v).strip()
        return '' if s.lower() == 'nan' else s

    def _to_bool(v):
        s = _to_str(v).lower()
        if s in ('1', 'true', 'yes', 'y'):
            return True
        if s in ('0', 'false', 'no', 'n'):
            return False
        return None

    created = 0
    updated = 0
    skipped = 0
    errors = 0

    for row_dict in df.to_dict(orient='records'):
        try:
            first_name = _to_str(_first(row_dict, ['first_name', 'firstname', 'first']))
            last_name = _to_str(_first(row_dict, ['last_name', 'lastname', 'last', 'surname']))
            middle_name = _to_str(_first(row_dict, ['middle_name', 'middlename', 'middle']))

            dob_val = _first(row_dict, ['date_of_birth', 'dob', 'birth_date', 'birthday'])
            dob = None
            if dob_val is not None and str(dob_val).strip().lower() != 'nan':
                try:
                    ts = pd.to_datetime(dob_val, errors='coerce')
                    if ts is not pd.NaT:
                        dob = ts.date()
                except Exception:
                    dob = None

            if not first_name or not last_name or not dob:
                skipped += 1
                continue

            gender_val = _to_str(_first(row_dict, ['gender', 'sex'])).upper()
            if gender_val in ('M', 'MALE'):
                gender_val = 'MALE'
            elif gender_val in ('F', 'FEMALE'):
                gender_val = 'FEMALE'

            civil_status_val = _to_str(_first(row_dict, ['civil_status', 'civilstatus'])).upper()

            residency_status_val = _to_str(_first(row_dict, ['residency_status'])).upper()
            residency_type_val = _to_str(_first(row_dict, ['residency_type'])).upper()

            employment_status_val = _to_str(_first(row_dict, ['employment_status'])).upper()

            current_location_val = _to_str(_first(row_dict, ['current_location', 'current_residency', 'currently_in_barangay'])).upper()
            if current_location_val in ('YES', 'Y', 'TRUE', '1', 'IN_BARANGAY', 'IN'):
                current_location_val = 'IN_BARANGAY'
            elif current_location_val in ('NO', 'N', 'FALSE', '0', 'AWAY', 'OUT'):
                current_location_val = 'AWAY'
            elif not current_location_val:
                current_location_val = None

            defaults = {
                'middle_name': middle_name or None,
                'gender': gender_val,
                'civil_status': civil_status_val,
                'contact_number': _to_str(_first(row_dict, ['contact_number', 'contact', 'mobile', 'phone'])) or None,
                'email': _to_str(_first(row_dict, ['email', 'email_address'])) or None,
                'zone_street_purok': _to_str(_first(row_dict, ['zone_street_purok', 'purok', 'zone'])) or None,
                'present_address': _to_str(_first(row_dict, ['present_address', 'address'])) or None,
                'residency_status': residency_status_val,
                'residency_type': residency_type_val,
                'years_in_barangay': int(_to_str(_first(row_dict, ['years_in_barangay', 'years_in_brgy', 'years_in_barangay_residency'])) or 0),
                'employment_status': employment_status_val,
                'occupation': _to_str(_first(row_dict, ['occupation', 'job'])) or None,
                'income': None,
                'is_student': bool(_to_bool(_first(row_dict, ['is_student', 'student'])) or False),
                'is_voter': bool(_to_bool(_first(row_dict, ['is_voter', 'voter'])) or False),
                'current_location': current_location_val,
                'away_duration_years': int(_to_str(_first(row_dict, ['away_duration_years', 'away_years'])) or 0),
                'away_duration_months': int(_to_str(_first(row_dict, ['away_duration_months', 'away_months'])) or 0),
            }

            income_val = _first(row_dict, ['income', 'monthly_income'])
            if income_val is not None and str(income_val).strip().lower() != 'nan':
                try:
                    defaults['income'] = float(income_val)
                except Exception:
                    defaults['income'] = None

            resident = Resident.objects.filter(
                first_name__iexact=first_name,
                last_name__iexact=last_name,
                date_of_birth=dob,
                barangay=brgy,
            ).first()

            if not resident:
                resident = Resident(
                    first_name=first_name,
                    last_name=last_name,
                    date_of_birth=dob,
                    barangay=brgy,
                    profile_status='INCOMPLETE',
                    **defaults,
                )
                resident.save()
                created += 1
                continue

            if resident.user_id:
                skipped += 1
                continue

            changed = False
            for field, value in defaults.items():
                if field in ('barangay', 'profile_status'):
                    continue
                if value in (None, '', 0):
                    continue
                current = getattr(resident, field, None)
                if not current:
                    setattr(resident, field, value)
                    changed = True

            if changed:
                resident.profile_status = 'INCOMPLETE'
                resident.save()
                updated += 1
            else:
                skipped += 1
        except Exception:
            errors += 1

    if created or updated:
        messages.success(request, f"Imported residents: {created} created, {updated} updated. Skipped: {skipped}. Errors: {errors}.")
    else:
        messages.info(request, f"No residents imported. Skipped: {skipped}. Errors: {errors}.")

    return redirect('residents:resident_list')

@login_required
def resident_detail(request, pk):
    if not is_staff_portal(request.user):
        return redirect('residents:resident_dashboard')

    if request.user.is_any_barangay_official:
        brgy = get_user_barangay(request.user)
        resident = get_object_or_404(Resident, pk=pk, barangay=brgy)
    else:
        resident = get_object_or_404(Resident, pk=pk)
    return render(request, 'residents/resident_detail.html', {'resident': resident})

@login_required
def add_resident(request):
    if not is_staff_portal(request.user):
        return redirect('residents:resident_dashboard')

    if request.method == 'POST':
        form = ResidentForm(request.POST, request.FILES)
        if form.is_valid():
            resident = form.save(commit=False)
            
            # Logic to handle new household creation if provided manually
            if not form.cleaned_data.get('household') and form.cleaned_data.get('new_household_number'):
                new_hh_num = form.cleaned_data.get('new_household_number')
                new_hh_addr = form.cleaned_data.get('new_household_address')
                
                # Determine barangay for the new household
                if request.user.is_any_barangay_official:
                    brgy = get_user_barangay(request.user)
                else:
                    # Fallback for system admin - they should ideally use the dropdown or we need to handle this
                    # For now, let's use the first available barangay or error out if not found
                    brgy = form.cleaned_data.get('barangay') or Barangay.objects.first() 
                
                new_hh = Household.objects.create(
                    household_number=new_hh_num,
                    address=new_hh_addr,
                    barangay=brgy
                )
                resident.household = new_hh
                resident.barangay = brgy
            elif resident.household:
                resident.barangay = resident.household.barangay
                
            if request.user.is_any_barangay_official:
                brgy = get_user_barangay(request.user)
                if resident.household and resident.household.barangay_id != brgy.id:
                    messages.error(request, "Selected household is not in your barangay.")
                    return redirect('residents:add_resident')
            
            resident.save()
            return redirect('residents:resident_list')
    else:
        form = ResidentForm()
        if request.user.is_any_barangay_official:
            brgy = get_user_barangay(request.user)
            if brgy:
                form.fields['household'].queryset = Household.objects.filter(barangay=brgy)
                if 'barangay' in form.fields:
                    form.fields['barangay'].queryset = Barangay.objects.filter(pk=brgy.id)
                    form.fields['barangay'].initial = brgy
    return render(request, 'residents/resident_form.html', {'form': form, 'title': 'Add Resident'})

@login_required
def update_resident(request, pk):
    if not is_staff_portal(request.user):
        return redirect('residents:resident_dashboard')

    if request.user.is_any_barangay_official:
        brgy = get_user_barangay(request.user)
        resident = get_object_or_404(Resident, pk=pk, barangay=brgy)
    else:
        resident = get_object_or_404(Resident, pk=pk)

    if request.method == 'POST':
        form = ResidentForm(request.POST, request.FILES, instance=resident)
        if form.is_valid():
            resident = form.save(commit=False)
            
            # Logic to handle new household creation if provided manually
            if not form.cleaned_data.get('household') and form.cleaned_data.get('new_household_number'):
                new_hh_num = form.cleaned_data.get('new_household_number')
                new_hh_addr = form.cleaned_data.get('new_household_address')
                
                if request.user.is_any_barangay_official:
                    brgy = get_user_barangay(request.user)
                else:
                    brgy = resident.barangay or form.cleaned_data.get('barangay') or Barangay.objects.first()
                
                new_hh = Household.objects.create(
                    household_number=new_hh_num,
                    address=new_hh_addr,
                    barangay=brgy
                )
                resident.household = new_hh
                resident.barangay = brgy
            elif resident.household:
                resident.barangay = resident.household.barangay

            if request.user.is_any_barangay_official:
                brgy = get_user_barangay(request.user)
                if resident.household and resident.household.barangay_id != brgy.id:
                    messages.error(request, "Selected household is not in your barangay.")
                    return redirect('residents:update_resident', pk=pk)
            
            resident.save()
            messages.success(request, "Resident updated successfully.")
            return redirect('residents:resident_detail', pk=resident.pk)
    else:
        form = ResidentForm(instance=resident)
        if resident.profile_status == 'INCOMPLETE' and not any('is-invalid-highlight' in f.widget.attrs.get('class', '') for f in form.fields.values()):
            messages.info(request, "This resident's profile is marked as incomplete, but all basic required fields seem to be filled.")
        if request.user.is_any_barangay_official:
            brgy = get_user_barangay(request.user)
            if brgy:
                form.fields['household'].queryset = Household.objects.filter(barangay=brgy)
                if 'barangay' in form.fields:
                    form.fields['barangay'].queryset = Barangay.objects.filter(pk=brgy.id)
                    form.fields['barangay'].initial = brgy
    return render(request, 'residents/resident_form.html', {'form': form, 'title': 'Update Resident', 'resident': resident})

@login_required
def household_list(request):
    if not is_staff_portal(request.user):
        return redirect('residents:resident_dashboard')

    if request.user.is_any_barangay_official:
        brgy = get_user_barangay(request.user)
        households = Household.objects.filter(barangay=brgy)
        barangay_boundaries_json = _barangay_boundaries_json(Barangay.objects.filter(pk=brgy.pk))
    else:
        households = Household.objects.all()
        barangay_boundaries_json = _barangay_boundaries_json(Barangay.objects.all())
    return render(request, 'residents/household_list.html', {
        'households': households,
        'barangay_boundaries_json': barangay_boundaries_json,
    })

@login_required
def add_household(request):
    if not is_staff_portal(request.user):
        return redirect('residents:resident_dashboard')

    if request.method == 'POST':
        form = HouseholdForm(request.POST)
        if form.is_valid():
            household = form.save(commit=False)
            if request.user.is_any_barangay_official:
                household.barangay = get_user_barangay(request.user)
            if not _is_within_barangay_boundary(household.barangay, household.location):
                messages.error(request, "Pinned location is outside the barangay boundary. Please pin inside the boundary.")
            else:
                household.save()
                return redirect('residents:household_list')
    else:
        form = HouseholdForm()
        if request.user.is_any_barangay_official:
            brgy = get_user_barangay(request.user)
            if brgy:
                form.fields['barangay'].queryset = Barangay.objects.filter(pk=brgy.id)
                form.fields['barangay'].initial = brgy
    barangay_boundaries_json = _barangay_boundaries_json(form.fields['barangay'].queryset)
    return render(request, 'residents/household_form.html', {
        'form': form,
        'title': 'Add Household',
        'barangay_boundaries_json': barangay_boundaries_json,
    })

@login_required
def edit_household(request, pk):
    if not is_staff_portal(request.user):
        return redirect('residents:resident_dashboard')

    if request.user.is_any_barangay_official:
        brgy = get_user_barangay(request.user)
        household = get_object_or_404(Household, pk=pk, barangay=brgy)
    else:
        household = get_object_or_404(Household, pk=pk)

    if request.method == 'POST':
        if request.POST.get('delete_location') == '1':
            household.location = None
            household.save(update_fields=['location'])
            messages.success(request, "Household location deleted.")
            return redirect('residents:map_household', pk=household.pk)

        form = HouseholdForm(request.POST, instance=household)
        if request.user.is_any_barangay_official:
            brgy = get_user_barangay(request.user)
            if brgy:
                form.fields['barangay'].queryset = Barangay.objects.filter(pk=brgy.id)
                form.fields['barangay'].initial = brgy
        if form.is_valid():
            updated = form.save(commit=False)
            if request.user.is_any_barangay_official:
                updated.barangay = get_user_barangay(request.user)
            if not _is_within_barangay_boundary(updated.barangay, updated.location):
                messages.error(request, "Pinned location is outside the barangay boundary. Please pin inside the boundary.")
            else:
                updated.save()
                messages.success(request, "Household updated successfully.")
                return redirect('residents:household_list')
    else:
        form = HouseholdForm(instance=household)
        if request.user.is_any_barangay_official:
            brgy = get_user_barangay(request.user)
            if brgy:
                form.fields['barangay'].queryset = Barangay.objects.filter(pk=brgy.id)
                form.fields['barangay'].initial = brgy
    barangay_boundaries_json = _barangay_boundaries_json(form.fields['barangay'].queryset)
    return render(request, 'residents/household_form.html', {
        'form': form,
        'title': 'Edit Household',
        'barangay_boundaries_json': barangay_boundaries_json,
        'household': household,
    })

@login_required
def delete_household(request, pk):
    if not is_staff_portal(request.user):
        return redirect('residents:resident_dashboard')

    if request.user.is_any_barangay_official:
        brgy = get_user_barangay(request.user)
        household = get_object_or_404(Household, pk=pk, barangay=brgy)
    else:
        household = get_object_or_404(Household, pk=pk)

    if request.method != 'POST':
        return redirect('residents:map_household', pk=household.pk)

    if household.members.exists():
        messages.error(request, "Cannot delete this household because residents are already linked to it.")
        return redirect('residents:map_household', pk=household.pk)

    household_number = household.household_number
    household.delete()
    messages.success(request, f"Household '{household_number}' deleted.")
    return redirect('residents:household_list')

@login_required
def announcement_list(request):
    if not is_staff_portal(request.user):
        return redirect('residents:resident_dashboard')

    announcements = announcement_queryset_for_user(request.user)
    from django.utils import timezone
    return render(request, 'residents/announcement_list.html', {
        'announcements': announcements,
        'today': timezone.now().date()
    })

@login_required
def announcement_add(request):
    if not request.user.is_system_admin and not request.user.is_barangay_admin:
        messages.error(request, "Only administrators can add announcements.")
        return redirect('residents:announcement_list')

    if request.method == 'POST':
        form = AnnouncementForm(request.POST)
        if form.is_valid():
            ann = form.save(commit=False)
            ann.created_by = request.user
            if request.user.is_system_admin:
                ann.is_global = True
                ann.barangay = None
            else:
                ann.is_global = False
                ann.barangay = get_user_barangay(request.user)
            ann.save()
            return redirect('residents:announcement_list')
    else:
        form = AnnouncementForm()
    return render(request, 'residents/announcement_form.html', {'form': form, 'title': 'Add Announcement'})

@login_required
def announcement_edit(request, pk):
    if not request.user.is_system_admin and not request.user.is_barangay_admin:
        messages.error(request, "Only administrators can edit announcements.")
        return redirect('residents:announcement_list')

    qs = announcement_queryset_for_user(request.user)
    ann = get_object_or_404(qs, pk=pk)
    if request.method == 'POST':
        form = AnnouncementForm(request.POST, instance=ann)
        if form.is_valid():
            ann = form.save(commit=False)
            # Maintain original creator or update? Usually maintain or update to current editor.
            # Let's keep original creator for now or update if needed.
            ann.save()
            return redirect('residents:announcement_list')
    else:
        form = AnnouncementForm(instance=ann)
    return render(request, 'residents/announcement_form.html', {'form': form, 'title': 'Edit Announcement'})

@login_required
def announcement_delete(request, pk):
    if not request.user.is_system_admin and not request.user.is_barangay_admin:
        messages.error(request, "Only administrators can delete announcements.")
        return redirect('residents:announcement_list')

    qs = announcement_queryset_for_user(request.user)
    ann = get_object_or_404(qs, pk=pk)
    ann.delete()
    messages.success(request, "Announcement deleted successfully.")
    return redirect('residents:announcement_list')
