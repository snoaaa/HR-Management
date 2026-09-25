from django.contrib.auth.models import Permission
from django.db.models import Q
from django.utils import timezone
from rest_framework.permissions import BasePermission

from .audit import audit
from .models import AuditLog


def role_permissions(user):
    """Ensemble de 'app_label.codename' que l'utilisateur possède AUJOURD'HUI
    via ses rôles datés (mis en cache sur l'objet user pour la requête)."""
    if hasattr(user, "_role_perms"):
        return user._role_perms
    today = timezone.localdate()
    rows = (
        Permission.objects.filter(
            Q(roles_assignmentsend_date_isnull=True)
            | Q(roles_assignmentsend_date_gte=today),
            roles_assignments_user=user,
            roles_assignmentsstart_date_lte=today,
        )
        .values_list("content_type__app_label", "codename")
        .distinct()
    )
    user._role_perms = {f"{app}.{code}" for app, code in rows}
    return user._role_perms


def require(perm):
    """Usage :
    permission_classes = [IsAuthenticated, require("api.view_salary")]
    """

    class _Has(BasePermission):
        def has_permission(self, request, view):
            ok = perm in role_permissions(request.user)
            if not ok:
                audit(AuditLog.Action.DENIED, request=request, changes={"needed": perm})
            return ok

    return _Has