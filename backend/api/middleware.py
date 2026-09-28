"""
BN-174: password policy enforcement + automatic closing of inactive
sessions. BN-173: makes the current request available to model signals so
audit entries can carry author/IP/machine.
"""

from django.conf import settings
from django.contrib.auth import logout
from django.http import JsonResponse
from django.urls import resolve
from django.utils import timezone

from .request_context import clear_current_request, set_current_request

# Endpoints that must stay reachable even while a password change is
# mandatory or 2FA is not yet confirmed, otherwise the user could never
# satisfy the requirement.
EXEMPT_URL_NAMES = {
    "password-change",
    "two-factor-setup",
    "two-factor-verify",
    "login",
    "logout",
}


class AuditContextMiddleware:
    """Makes `request` available to signal handlers for the duration of the request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        set_current_request(request)
        try:
            return self.get_response(request)
        finally:
            clear_current_request()


class SessionTimeoutMiddleware:
    """
    BN-174 - automatically closes a session that has been inactive for
    longer than SESSION_INACTIVITY_TIMEOUT_MINUTES (default settings).
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.timeout_minutes = getattr(
            settings, "SESSION_INACTIVITY_TIMEOUT_MINUTES", 30
        )

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            now = timezone.now()
            idle_seconds = (
                (now - user.last_activity).total_seconds() if user.last_activity else 0
            )
            if user.last_activity and idle_seconds > self.timeout_minutes * 60:
                logout(request)
                return JsonResponse(
                    {
                        "detail": "Session expired due to inactivity. Please log in again."
                    },
                    status=401,
                )
            user.last_activity = now
            user.save(update_fields=["last_activity"])
        return self.get_response(request)


class ForcePasswordChangeMiddleware:
    """
    BN-174 - a user flagged `must_change_password` (new account, or admin
    reset) cannot use any other API endpoint until the password has been
    changed.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if (
            user is not None
            and user.is_authenticated
            and user.must_change_password
            and not request.path_info.startswith("/admin/")
        ):
            try:
                match = resolve(request.path_info)
                url_name = match.url_name
            except Exception:
                url_name = None
            if url_name not in EXEMPT_URL_NAMES:
                return JsonResponse(
                    {
                        "detail": "You must change your password before continuing.",
                        "code": "password_change_required",
                    },
                    status=403,
                )
        return self.get_response(request)
