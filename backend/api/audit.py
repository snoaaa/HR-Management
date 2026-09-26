from .models import AuditLog


def audit(action, *, request=None, actor=None, target=None, changes=None):
    """target = ("api.Employee", id).
    À appeler depuis les vues/services pour chaque action importante."""
    if actor is None and request is not None and request.user.is_authenticated:
        actor = request.user
    AuditLog.objects.create(
        actor=actor,
        action=action,
        target_type=target[0] if target else "",
        target_id=str(target[1]) if target else "",
        changes=changes or {},
        ip_address=request.META.get("REMOTE_ADDR") if request else None,
    )