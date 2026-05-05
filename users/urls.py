from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'users'

urlpatterns = [
    path('register/', views.resident_registration, name='register'),
    # User management for admins
    path('list/', views.user_list, name='user_list'),
    path('add/', views.add_user, name='add_user'),
    path('edit/<int:pk>/', views.edit_user_role, name='edit_user_role'),
    path('toggle-status/<int:pk>/', views.toggle_user_status, name='toggle_user_status'),
    
    # Auth views
    path('login/', views.login_selection, name='login'),
    path('admin/login/', views.admin_login, name='admin_login'),
    path('barangay/login/', views.barangay_login, name='barangay_login'),
    path('resident/login/', views.resident_login, name='resident_login'),
    path('logout/', views.logout_user, name='logout'),
    
    # Registration
    path('barangay/register/', views.barangay_registration, name='barangay_register'),
    path('resident/register/', views.resident_registration, name='resident_register'),
    
    # Forgot password features
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(template_name='users/password_reset.html'), 
         name='password_reset'),
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(template_name='users/password_reset_done.html'), 
         name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(template_name='users/password_reset_confirm.html'), 
         name='password_reset_confirm'),
    path('password-reset-complete/', 
         auth_views.PasswordResetCompleteView.as_view(template_name='users/password_reset_complete.html'), 
         name='password_reset_complete'),
]
