from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    path('dilg/', views.dilg_dashboard, name='dilg_dashboard'),
    path('barangay/', views.barangay_dashboard, name='barangay_dashboard'),
    path('vulnerability/', views.vulnerability_dashboard, name='vulnerability_dashboard'),
    path('barangay/approve/<int:pk>/', views.approve_barangay, name='approve_barangay'),
    path('barangay/reject/<int:pk>/', views.reject_barangay, name='reject_barangay'),
    path('barangay/edit/<int:pk>/', views.edit_barangay, name='edit_barangay'),
    path('resident-report/', views.generate_resident_report, name='resident_report'),
]
