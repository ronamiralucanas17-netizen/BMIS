from django.apps import AppConfig

class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'

    def ready(self):
        try:
            from django.contrib.auth.signals import user_logged_in, user_logged_out
        except Exception:
            return

        def _log_auth(action, request, user):
            try:
                from residents.models import AuditLog, _get_barangay_for_user
                AuditLog.objects.create(
                    actor=user,
                    actor_role=getattr(user, 'role', '') or '',
                    barangay=_get_barangay_for_user(user),
                    action=action,
                    path=getattr(request, 'path', '') if request else '',
                    method=getattr(request, 'method', '') if request else '',
                    status_code=200,
                    ip_address=(request.META.get('REMOTE_ADDR') if request else None),
                    user_agent=(request.META.get('HTTP_USER_AGENT', '')[:1000] if request else ''),
                    details={'view_name': 'auth', 'event': action},
                )
            except Exception:
                return

        def _on_login(sender, request, user, **kwargs):
            _log_auth('LOGIN', request, user)

        def _on_logout(sender, request, user, **kwargs):
            _log_auth('LOGOUT', request, user)

        try:
            user_logged_in.connect(_on_login, dispatch_uid='auditlog_user_logged_in')
            user_logged_out.connect(_on_logout, dispatch_uid='auditlog_user_logged_out')
        except Exception:
            return
