from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils.http import url_has_allowed_host_and_scheme
from .models import User
from residents.models import Resident, Barangay
from .forms import UserRoleForm, CustomUserCreationForm, ResidentRegistrationForm, BarangayRegistrationForm

def role_based_redirect(user):
    if user.is_system_admin:
        return redirect('analytics:dilg_dashboard')
    elif user.is_any_barangay_official:
        try:
            if user.is_barangay_admin:
                brgy = user.managed_barangay
            else:
                brgy = Barangay.objects.filter(name=user.barangay_name).first()
            if not brgy or not brgy.is_approved:
                return redirect('users:barangay_login')
        except Exception:
            return redirect('users:barangay_login')
        return redirect('analytics:barangay_dashboard')
    elif user.is_resident:
        return redirect('residents:resident_dashboard')
    return redirect('home')

def login_selection(request):
    if request.user.is_authenticated:
        return role_based_redirect(request.user)
    return render(request, 'users/login_selection.html', {'title': 'BMIS Login Selection'})

def logout_user(request):
    redirect_to_admin_login = request.user.is_authenticated and (request.user.is_system_admin or request.user.is_superuser)
    logout(request)
    if redirect_to_admin_login:
        return redirect('users:admin_login')
    return redirect('users:login')

def admin_login(request):
    if request.user.is_authenticated:
        return role_based_redirect(request.user)
    next_url = request.GET.get('next') or ''
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.role == 'ADMIN' or user.is_superuser:
                login(request, user)
                posted_next = request.POST.get('next') or next_url
                if posted_next and url_has_allowed_host_and_scheme(
                    url=posted_next,
                    allowed_hosts={request.get_host()},
                    require_https=request.is_secure(),
                ):
                    return redirect(posted_next)
                return redirect('analytics:dilg_dashboard')
            else:
                messages.error(request, "This login is for Admins only.")
    else:
        form = AuthenticationForm()
    return render(request, 'users/login_admin.html', {'form': form, 'title': 'Admin Login', 'role': 'Admin', 'next': next_url})

def barangay_login(request):
    if request.user.is_authenticated:
        return role_based_redirect(request.user)
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.role in ('BARANGAY', 'BARANGAY_STAFF'):
                try:
                    if user.role == 'BARANGAY':
                        brgy = user.managed_barangay
                    else:
                        brgy = Barangay.objects.filter(name=user.barangay_name).first()
                    if not brgy or not brgy.is_approved:
                        messages.warning(request, "Your barangay registration is still pending approval.")
                        return redirect('users:barangay_login')
                except Exception:
                    messages.warning(request, "Your barangay account is not yet linked to a barangay record.")
                    return redirect('users:barangay_login')
                login(request, user)
                return redirect('analytics:barangay_dashboard')
            else:
                messages.error(request, "This login is for Barangay Officials only.")
    else:
        form = AuthenticationForm()
    return render(request, 'users/login_barangay.html', {'form': form, 'title': 'Barangay Login', 'role': 'Barangay'})

def resident_login(request):
    if request.user.is_authenticated:
        return role_based_redirect(request.user)
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.role == 'RESIDENT':
                login(request, user)
                return redirect('residents:resident_dashboard')
            else:
                messages.error(request, "This login is for Residents only.")
    else:
        form = AuthenticationForm()
    return render(request, 'users/login_resident.html', {'form': form, 'title': 'Resident Login', 'role': 'Resident'})

def barangay_registration(request):
    if request.method == 'POST':
        form = BarangayRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = 'BARANGAY'
            user.is_active = False
            user.save()
            name = form.cleaned_data.get('barangay_name')
            municipality = form.cleaned_data.get('municipality')
            captain = form.cleaned_data.get('captain_name')
            existing = Barangay.objects.filter(name=name).first()
            if existing:
                messages.error(request, "This barangay is already registered. Please log in or contact the admin.")
                return redirect('users:barangay_login')
            Barangay.objects.create(
                name=name,
                municipality=municipality,
                email=user.email,
                captain_name=captain,
                admin_user=user,
                is_approved=False
            )
            messages.success(request, "Registration submitted! Please wait for Admin approval.")
            return redirect('users:barangay_login')
    else:
        form = BarangayRegistrationForm()
    return render(request, 'users/registration.html', {'form': form, 'title': 'Barangay Registration'})

def resident_registration(request):
    if request.method == 'POST':
        form = ResidentRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = 'RESIDENT'
            user.save()
            # Create an empty resident profile if it doesn't exist
            Resident.objects.get_or_create(user=user)
            login(request, user)
            return redirect('residents:complete_profile')
    else:
        form = ResidentRegistrationForm()
    return render(request, 'users/registration.html', {'form': form, 'title': 'Resident Registration'})

def is_admin(user):
    return user.role == 'ADMIN' or user.is_superuser

@login_required
@user_passes_test(is_admin)
def user_list(request):
    users = User.objects.all().order_by('username')
    return render(request, 'users/user_list.html', {'users': users})

@login_required
@user_passes_test(is_admin)
def add_user(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('users:user_list')
    else:
        form = CustomUserCreationForm()
    return render(request, 'users/add_user.html', {'form': form})

@login_required
@user_passes_test(is_admin)
def edit_user_role(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = UserRoleForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return redirect('users:user_list')
    else:
        form = UserRoleForm(instance=user)
    return render(request, 'users/edit_user_role.html', {'form': form, 'user_to_edit': user})

@login_required
@user_passes_test(is_admin)
def toggle_user_status(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user != request.user: # Prevent self-deactivation
        user.is_active = not user.is_active
        user.save()
    return redirect('users:user_list')
