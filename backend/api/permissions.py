"""
BN-170 / BN-171 / BN-172 - fine-grained, scope-aware DRF permissions.

Usage on a viewset:

    class SalaryRecordViewSet(ScopedQuerysetMixin, viewsets.ModelViewSet):
        module = Module.PAYROLL
        security_action_map = {"list": Action.CONSULT, "retrieve": Action.CONSULT,
                                "create": Action.CREATE, "update": Action.MODIFY,
                                "partial_update": Action.MODIFY, "destroy": Action.DELETE}
        owner_field = "employee"
        permission_classes = [HasModulePermission, SalaryConfidentiality]

NOTE: this is deliberately NOT called `action_map`. DRF's own
`ViewSetMixin` sets an *instance* attribute of that exact name at request
time (it maps HTTP methods like "get"/"post" to view methods like
"list"/"create"), which would silently shadow a class attribute of the
same name and make every lookup below fall through to the wrong value.
"""

from rest_framework.permissions import BasePermission

from .models import Action, Scope
from .services import record_audit

DEFAULT_ACTION_MAP = {
    "list": Action.CONSULT,
    "retrieve": Action.CONSULT,
    "create": Action.CREATE,
    "update": Action.MODIFY,
    "partial_update": Action.MODIFY,
    "destroy": Action.DELETE,
}


def _required_action(view):
    action_map = getattr(view, "security_action_map", DEFAULT_ACTION_MAP)
    return action_map.get(view.action, view.action)


class HasModulePermission(BasePermission):
    """
    Requires that the user has, through one of their roles, the permission
    to perform the view's action on the view's module (BN-170). Access
    denials are themselves recorded to the audit trail.
    """

    def has_permission(self, request, view):
        module = getattr(view, "module", None)
        if module is None or not request.user or not request.user.is_authenticated:
            return False

        action = _required_action(view)
        allowed = request.user.has_module_permission(module, action)
        if not allowed:
            record_audit(
                action="access_denied",
                module=module,
                notes=f"Denied action='{action}' on module='{module}'",
            )
        return allowed


class ScopedQuerysetMixin:
    """
    Filters `get_queryset()` according to the widest visibility scope
    (BN-171) the user's roles grant for the current module/action:

      OWN          -> rows owned by the requesting user (view.owner_field)
      TEAM         -> rows whose owner is in the requester's team
      DEPARTMENT   -> rows whose owner is in the requester's department
      SITE         -> rows whose owner is in the requester's site
      ORGANISATION -> unrestricted

    `owner_field` is the FK (dotted path allowed, e.g. "employee") on the
    model pointing to the User who "owns" the row for scoping purposes.
    """

    owner_field = "employee"
    module = None
    security_action_map = DEFAULT_ACTION_MAP

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return qs

        action = _required_action(self)
        scope = user.broadest_scope(self.module, action)
        if scope is None:
            return qs.none()

        field = self.owner_field
        if scope == Scope.OWN:
            return qs.filter(**{field: user})
        if scope == Scope.TEAM:
            if user.team_id:
                return qs.filter(**{f"{field}__team": user.team})
            return qs.filter(**{field: user})
        if scope == Scope.DEPARTMENT:
            return (
                qs.filter(**{f"{field}__department": user.department})
                if user.department_id
                else qs.filter(**{field: user})
            )
        if scope == Scope.SITE:
            if user.site_id:
                return qs.filter(**{f"{field}__site": user.site})
            return qs.filter(**{field: user})
        return qs  # ORGANISATION


class TwoFactorRequired(BasePermission):
    """
    BN-176 - accounts flagged `is_payroll_authorized`, or holding a role
    with `requires_two_factor`, must have completed a second-factor check
    for the *current session* (set by TwoFactorVerifyView) before they can
    use an endpoint guarded by this permission. Accounts that don't need
    2FA are let through unaffected.
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if not user.requires_two_factor():
            return True
        verified = bool(request.session.get("two_factor_verified"))
        if not verified:
            record_audit(
                action="access_denied",
                module=getattr(view, "module", ""),
                notes="Blocked: second authentication factor not verified this session",
            )
        return verified


class SalaryConfidentiality(BasePermission):
    """
    BN-172 - on top of the generic PAYROLL/CONSULT module permission,
    salary data additionally requires the explicit `is_payroll_authorized`
    flag on the account. This means granting the PAYROLL module to a role
    is not by itself enough to see salaries: each individual account must
    also be flagged, giving HR a second, deliberate gate on the most
    sensitive data.
    """

    def has_permission(self, request, view):
        user = request.user
        allowed = bool(
            user
            and user.is_authenticated
            and (user.is_superuser or user.is_payroll_authorized)
        )
        if not allowed:
            record_audit(
                action="access_denied",
                module="payroll",
                notes="Missing payroll authorisation flag",
            )
        return allowed
