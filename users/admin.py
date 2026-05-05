from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ['username', 'email', 'role', 'is_active', 'barangay_name']
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('role', 'barangay_name')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('role', 'barangay_name')}),
    )

admin.site.register(User, CustomUserAdmin)
