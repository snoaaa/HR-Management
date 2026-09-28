"""
Thread-local storage carrying the current request so that model signals
(which have no access to the request) can still record who/from-where a
change was made, for the audit trail (BN-173).

Populated by api.middleware.AuditContextMiddleware on every request and
cleared afterwards, so nothing leaks between requests/threads.
"""

import threading

_local = threading.local()


def set_current_request(request):
    _local.request = request


def get_current_request():
    return getattr(_local, "request", None)


def clear_current_request():
    if hasattr(_local, "request"):
        del _local.request


def get_client_ip(request) -> str:
    if request is None:
        return ""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def get_client_machine(request) -> str:
    """Best-effort identification of the originating machine (BN-173)."""
    if request is None:
        return ""
    host = request.META.get("REMOTE_HOST") or get_client_ip(request)
    agent = request.META.get("HTTP_USER_AGENT", "")
    return f"{host} | {agent}"[:255]
