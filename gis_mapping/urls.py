from django.urls import path
from . import views

app_name = 'gis_mapping'

urlpatterns = [
    path('map/', views.map_view, name='map_view'),
    path('disaster-area/add/', views.edit_disaster_area, name='add_disaster_area'),
    path('disaster-area/edit/<int:area_id>/', views.edit_disaster_area, name='edit_disaster_area'),
    path('disaster-area/delete/<int:area_id>/', views.delete_disaster_area, name='delete_disaster_area'),
    # Infrastructure URLs
    path('infrastructure/add/', views.add_infrastructure, name='add_infrastructure'),
    path('infrastructure/delete/<int:infra_id>/', views.delete_infrastructure, name='delete_infrastructure'),
    path('infrastructure/delete-all/', views.delete_all_infrastructure, name='delete_all_infrastructure'),
    # Evacuation Site URLs
    path('evacuation/add/', views.add_evacuation_site, name='add_evacuation_site'),
    path('evacuation/delete/<int:evac_id>/', views.delete_evacuation_site, name='delete_evacuation_site'),
    path('demographics/list/', views.demographic_list, name='demographic_list'),
    path('demographics/data/', views.demographic_data, name='demographic_data'),
    path('barangay/boundary/', views.edit_barangay_boundary, name='edit_barangay_boundary'),
]
