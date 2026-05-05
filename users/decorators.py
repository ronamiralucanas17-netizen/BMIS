from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from functools import wraps

def role_required(allowed_roles):
    """
    Decorator for views that checks if the user has the required role.
    allowed_roles: list of role strings (e.g. ['ADMIN', 'BARANGAY'])
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return user_passes_test(lambda u: u.is_authenticated)(view_func)(request, *args, **kwargs)
            
            if request.user.role in allowed_roles or request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            
            raise PermissionDenied
        return _wrapped_view
    return decorator

def system_admin_only(view_func):
    return role_required(['ADMIN'])(view_func)

def barangay_admin_only(view_func):
    return role_required(['BARANGAY'])(view_func)

def staff_only(view_func):
    """Admin or Barangay staff."""
    return role_required(['ADMIN', 'BARANGAY'])(view_func)
