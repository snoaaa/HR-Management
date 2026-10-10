import logging

from .models import AuditLog

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """
    Utility function to get client IP from request.
    """
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


def log_audit_action(user, action, module, request=None, details=None):
    """
    Create an AuditLog entry.
    """
    ip_address = get_client_ip(request) if request else None
    details = dict(details or {})
    if request is not None:
        # BN-173: record the machine the operation came from.
        details.setdefault("user_agent", request.META.get("HTTP_USER_AGENT", ""))

    try:
        AuditLog.objects.create(
            user=user if user and user.is_authenticated else None,
            action=action,
            module=module,
            ip_address=ip_address,
            details=details,
        )
    except Exception as e:
        # We don't want audit logging failures to break the application flow,
        # but we should log it to standard error log.
        logger.error(f"Failed to create audit log: {e}")
