from django.urls import path
from . import views

app_name = 'residents'

urlpatterns = [
    path('dashboard/', views.resident_dashboard, name='resident_dashboard'),
    path('download-history/', views.download_resident_history, name='download_history'),
    path('download-excel-template/', views.download_residents_excel_template, name='download_residents_excel_template'),
    path('complete-profile/', views.complete_profile, name='complete_profile'),
    path('announcements/', views.announcement_list, name='announcement_list'),
    path('announcements/add/', views.announcement_add, name='announcement_add'),
    path('announcements/edit/<int:pk>/', views.announcement_edit, name='announcement_edit'),
    path('announcements/delete/<int:pk>/', views.announcement_delete, name='announcement_delete'),
    # Resident Profile (for own account)
    path('my-profile/', views.my_profile, name='my_profile'),
    path('my-profile/edit/', views.edit_my_profile, name='edit_my_profile'),
    path('my-household/map/', views.map_my_household, name='map_my_household'),
    # Resident URLs
    path('', views.resident_list, name='resident_list'),
    path('import-excel/', views.import_residents_excel, name='import_residents_excel'),
    path('add/', views.add_resident, name='add_resident'),
    path('detail/<int:pk>/', views.resident_detail, name='resident_detail'),
    path('update/<int:pk>/', views.update_resident, name='update_resident'),
    path('verify/<int:resident_id>/', views.verify_resident, name='verify_resident'),
    path('reject/<int:resident_id>/', views.reject_resident, name='reject_resident'),
    
    # Household URLs
    path('households/', views.household_list, name='household_list'),
    path('households/add/', views.add_household, name='add_household'),
    path('households/map/<int:pk>/', views.edit_household, name='map_household'),
    path('households/delete/<int:pk>/', views.delete_household, name='delete_household'),
    
    # Official URLs
    path('officials/', views.official_list, name='official_list'),
    path('officials/add/', views.official_add, name='official_add'),
    path('officials/edit/<int:pk>/', views.official_edit, name='official_edit'),
    path('officials/delete/<int:pk>/', views.official_delete, name='official_delete'),
    
    # Staff Account URLs
    path('staff/', views.staff_list, name='staff_list'),
    path('staff/add/', views.staff_add, name='staff_add'),
    path('staff/delete/<int:pk>/', views.staff_delete, name='staff_delete'),
    
    # Service URLs
    path('services/', views.service_list, name='service_list'),
    path('services/add/', views.service_add, name='service_add'),
    path('services/edit/<int:pk>/', views.service_edit, name='service_edit'),
    path('services/delete/<int:pk>/', views.service_delete, name='service_delete'),
    path('available-services/', views.available_services, name='available_services'),
    path('available-services/request/<int:pk>/', views.request_service, name='request_service'),
    path('my-service-requests/', views.my_service_requests, name='my_service_requests'),
    path('chatbot/', views.chatbot_view, name='chatbot'),
    path('service-requests/', views.service_request_list, name='service_request_list'),
    path('service-requests/update/<int:pk>/', views.service_request_update, name='service_request_update'),
    
    # Incident Report URLs
    path('reports/submit/', views.submit_report, name='submit_report'),
    path('reports/my/', views.my_reports, name='my_reports'),
    path('reports/list/', views.report_list, name='report_list'),
    path('reports/respond/<int:pk>/', views.report_respond, name='report_respond'),
    
    # Notification URLs
    path('notifications/', views.notification_list, name='notification_list'),
    path('notifications/read/<int:pk>/', views.mark_notification_as_read, name='mark_notification_as_read'),
]
