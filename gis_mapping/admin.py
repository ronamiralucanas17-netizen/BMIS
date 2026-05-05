from django.contrib import admin
from leaflet.admin import LeafletGeoAdmin
from .models import Infrastructure, DisasterProneArea, EvacuationSite

@admin.register(Infrastructure)
class InfrastructureAdmin(LeafletGeoAdmin):
    list_display = ['name', 'type', 'barangay_ref', 'barangay']
    list_filter = ['type', 'barangay_ref', 'barangay']

@admin.register(DisasterProneArea)
class DisasterProneAreaAdmin(LeafletGeoAdmin):
    list_display = ['name', 'type', 'risk_level', 'barangay_ref']
    list_filter = ['type', 'risk_level', 'barangay_ref']

@admin.register(EvacuationSite)
class EvacuationSiteAdmin(LeafletGeoAdmin):
    list_display = ['name', 'barangay', 'capacity']
    list_filter = ['barangay']
