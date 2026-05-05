from django.contrib import admin
from django.contrib.gis import admin as gis_admin
from .models import Barangay, Household, Official, Service, ServiceRequest, Resident, IncidentReport, Notification, Announcement, AuditLog

@admin.register(Barangay)
class BarangayAdmin(gis_admin.GISModelAdmin):
    list_display = ['name', 'municipality', 'captain_name', 'created_at']
    search_fields = ['name', 'captain_name']

@admin.register(Household)
class HouseholdAdmin(gis_admin.GISModelAdmin):
    list_display = ['household_number', 'barangay', 'address']
    list_filter = ['barangay']
    search_fields = ['household_number']

@admin.register(Official)
class OfficialAdmin(admin.ModelAdmin):
    list_display = ['name', 'position', 'barangay', 'term_start', 'term_end', 'is_active']
    list_filter = ['barangay', 'position', 'is_active']
    search_fields = ['name']

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'barangay', 'processing_time', 'is_active']
    list_filter = ['barangay', 'is_active']
    search_fields = ['name']

@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = ['service', 'resident', 'barangay', 'status', 'created_at']
    list_filter = ['barangay', 'status']
    search_fields = ['service__name', 'resident__first_name', 'resident__last_name']

@admin.register(Resident)
class ResidentAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'barangay', 'gender', 'is_voter']
    list_filter = ['barangay', 'gender', 'is_voter']
    search_fields = ['first_name', 'last_name']

@admin.register(IncidentReport)
class IncidentReportAdmin(gis_admin.GISModelAdmin):
    list_display = ['title', 'resident', 'barangay', 'report_type', 'status', 'created_at']
    list_filter = ['barangay', 'report_type', 'status']
    search_fields = ['title', 'description']

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'is_read', 'created_at']
    list_filter = ['is_read']

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ['title', 'barangay', 'is_global', 'created_at']
    list_filter = ['is_global', 'barangay']

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'actor', 'actor_role', 'barangay', 'action', 'object_type', 'object_id', 'method', 'status_code']
    list_filter = ['action', 'actor_role', 'barangay', 'method']
    search_fields = ['actor__username', 'object_type', 'object_id', 'path', 'object_repr']
