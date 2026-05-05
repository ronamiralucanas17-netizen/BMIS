from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static

def root_redirect(request):
    if not request.user.is_authenticated:
        return redirect('users:login')
    if request.user.is_system_admin:
        return redirect('analytics:dilg_dashboard')
    elif request.user.is_any_barangay_official:
        return redirect('analytics:barangay_dashboard')
    elif request.user.is_resident:
        return redirect('residents:resident_dashboard')
    return TemplateView.as_view(template_name='home.html')(request)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', root_redirect, name='home'),
    path('about/', TemplateView.as_view(template_name='home.html'), name='about_system'),
    path('login/', lambda r: redirect('users:login')), # Redirect /login/ to /users/login/
    path('logout/', lambda r: redirect('users:logout')), # Redirect /logout/ to /users/logout/
    path('users/', include('users.urls')),
    path('residents/', include('residents.urls')),
    path('gis/', include('gis_mapping.urls')),
    path('analytics/', include('analytics.urls')),
    path('services/', include('barangay_services.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
