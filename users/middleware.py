from django.shortcuts import redirect
from django.urls import reverse, resolve

class ProfileCompletionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and request.user.role == 'RESIDENT':
            allowed = {
                reverse('residents:complete_profile'),
                reverse('residents:my_profile'),
                reverse('residents:edit_my_profile'),
                reverse('residents:notification_list'),
                reverse('users:logout'),
                reverse('users:login'),
                reverse('users:resident_login'),
                reverse('users:admin_login'),
                reverse('users:barangay_login'),
                reverse('users:password_reset'),
                reverse('users:password_reset_done'),
                reverse('users:password_reset_complete'),
            }
            if request.path.startswith('/admin/') or request.path.startswith('/static/') or request.path.startswith('/media/') or request.path in allowed:
                return self.get_response(request)

            # Check if user has a resident profile and if it's incomplete
            try:
                profile = request.user.resident_profile
                if not profile.has_completed_profile():
                    # Allow access only to the profile completion page
                    if request.path != reverse('residents:complete_profile'):
                        return redirect('residents:complete_profile')
                if profile.profile_status == 'PENDING_APPROVAL':
                    if request.path not in allowed:
                        return redirect('residents:my_profile')
            except Exception:
                # This can happen if the resident profile was not created on registration
                # Redirect to complete profile to create it
                if request.path != reverse('residents:complete_profile'):
                    return redirect('residents:complete_profile')
        
        response = self.get_response(request)
        return response


class AuditTrailMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            from residents.models import set_audit_context
            if getattr(request, 'user', None) is not None and request.user.is_authenticated:
                set_audit_context(user=request.user, request=request)
        except Exception:
            pass

        response = None
        try:
            response = self.get_response(request)
            return response
        finally:
            try:
                self._log_request(request, response)
            finally:
                try:
                    from residents.models import clear_audit_context
                    clear_audit_context()
                except Exception:
                    pass

    def _log_request(self, request, response):
        if not getattr(request, 'user', None) or not request.user.is_authenticated:
            return
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return
        if response is None:
            return
        if getattr(response, 'status_code', 500) >= 500:
            return

        try:
            match = resolve(request.path_info)
            view_name = match.view_name or ''
        except Exception:
            view_name = ''

        try:
            from residents.models import AuditLog, _get_barangay_for_user
            actor = request.user
            barangay = _get_barangay_for_user(actor)
            details = {
                'view_name': view_name,
                'post_keys': sorted(list(getattr(request, 'POST', {}).keys())),
                'files': sorted(list(getattr(request, 'FILES', {}).keys())),
                'content_type': request.META.get('CONTENT_TYPE', ''),
            }
            AuditLog.objects.create(
                actor=actor,
                actor_role=getattr(actor, 'role', '') or '',
                barangay=barangay,
                action='REQUEST',
                path=request.path,
                method=request.method,
                status_code=getattr(response, 'status_code', None),
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=(request.META.get('HTTP_USER_AGENT', '')[:1000]),
                details=details,
            )
        except Exception:
            return
