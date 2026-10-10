"""
BN-170: Fine-grained permissions per module and per action.
BN-171: Visibility of data restricted per perimeter (own, team, organisation).
BN-172: Salary information visible only to explicitly authorised profiles.

The permission matrix is stored in the RolePermission table so that it can be
changed without development. DEFAULT_MATRIX is only used to seed that table.
"""

from rest_framework.permissions import BasePermission

from .models import RolePermission, User

R = User.Roles

MODULES = (
    "organisation",
    "employees",
    "contracts",
    "attendance",
    "planning",
    "leave",
    "payroll",
    "documents",
    "users",
    "audit",
)
ACTIONS = ("consult", "create", "modify", "delete", "validate", "print", "export")

HR = {R.HR_MANAGER, R.HR_OFFICER}
EVERYONE = set(R.values)


def _full(roles):
    return {action: set(roles) for action in ACTIONS}


DEFAULT_MATRIX = {
    "organisation": {
        **_full({R.HR_MANAGER, R.SYSTEM_ADMINISTRATOR}),
        "consult": EVERYONE,
    },
    "employees": {
        **_full(HR),
        "consult": EVERYONE,
        "print": HR | {R.PAYROLL_OFFICER},
        "export": HR | {R.PAYROLL_OFFICER, R.GENERAL_MANAGEMENT},
        "delete": {R.HR_MANAGER},
    },
    "contracts": {
        **_full(HR),
        "consult": HR | {R.PAYROLL_OFFICER, R.GENERAL_MANAGEMENT, R.EMPLOYEE},
        "delete": {R.HR_MANAGER},
    },
    "attendance": {
        **_full(HR),
        # Employees self-record (BN-37); heads approve overtime (BN-40).
        "consult": HR
        | {R.HEAD_OF_DEPARTMENT, R.PAYROLL_OFFICER, R.EMPLOYEE, R.GENERAL_MANAGEMENT},
        "create": HR | {R.EMPLOYEE, R.HEAD_OF_DEPARTMENT},
        "validate": HR | {R.HEAD_OF_DEPARTMENT},
        "delete": {R.HR_MANAGER},
    },
    "planning": {
        **_full(HR | {R.HEAD_OF_DEPARTMENT}),
        "consult": EVERYONE,
        "create": HR | {R.HEAD_OF_DEPARTMENT, R.EMPLOYEE},
    },
    "leave": {
        **_full(HR),
        "consult": EVERYONE,
        "create": EVERYONE,
        "validate": HR | {R.HEAD_OF_DEPARTMENT},
        "print": EVERYONE,
        "delete": {R.HR_MANAGER},
    },
    "payroll": {
        **_full({R.PAYROLL_OFFICER, R.HR_MANAGER}),
        "consult": {R.PAYROLL_OFFICER, R.HR_MANAGER, R.ACCOUNTANT},
        "export": {R.PAYROLL_OFFICER, R.HR_MANAGER, R.ACCOUNTANT},
        "print": {R.PAYROLL_OFFICER, R.HR_MANAGER, R.EMPLOYEE},
    },
    "documents": {
        **_full(HR | {R.PAYROLL_OFFICER}),
        "consult": EVERYONE,
        "print": EVERYONE,
    },
    "users": _full({R.SYSTEM_ADMINISTRATOR, R.HR_MANAGER}),
    "audit": {
        "consult": {R.SYSTEM_ADMINISTRATOR, R.HR_MANAGER},
        "export": {R.SYSTEM_ADMINISTRATOR, R.HR_MANAGER},
    },
}

# Roles that see every employee record; the others are restricted (BN-171).
ORGANISATION_SCOPE_ROLES = {
    R.HR_MANAGER,
    R.HR_OFFICER,
    R.PAYROLL_OFFICER,
    R.GENERAL_MANAGEMENT,
    R.SYSTEM_ADMINISTRATOR,
}
# BN-172 / Table 8: HR officer sees salaries except executives; admin never.
SALARY_ROLES = {R.HR_MANAGER, R.PAYROLL_OFFICER, R.HR_OFFICER}


def get_permissions_for_role(role):
    """Return {module: set(actions)} for a role, read from the database."""
    result = {}
    for module, action in RolePermission.objects.filter(role=role).values_list(
        "module", "action"
    ):
        result.setdefault(module, set()).add(action)
    return result


def has_module_permission(user, module, action):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    cache = getattr(user, "_module_permissions", None)
    if cache is None:
        cache = get_permissions_for_role(user.role)
        user._module_permissions = cache
    return action in cache.get(module, set())


METHOD_ACTIONS = {
    "GET": "consult",
    "HEAD": "consult",
    "OPTIONS": "consult",
    "POST": "create",
    "PUT": "modify",
    "PATCH": "modify",
    "DELETE": "delete",
}


class ModulePermission(BasePermission):
    """
    DRF permission reading `permission_module` from the view.
    Custom @action methods map to a permission action through
    `action_permissions` on the view, e.g. {"archive": "modify"}.
    """

    def has_permission(self, request, view):
        module = getattr(view, "permission_module", None)
        if module is None:
            return request.user and request.user.is_authenticated
        action_name = getattr(view, "action", None)
        mapping = getattr(view, "action_permissions", {}) or {}
        perm_action = (
            mapping.get(action_name)
            or getattr(view, "required_action", None)
            or METHOD_ACTIONS.get(request.method, "consult")
        )
        return has_module_permission(request.user, module, perm_action)


def is_head_of_department(user):
    return user.role == R.HEAD_OF_DEPARTMENT or user.managed_departments.exists()


def managed_department_ids(user):
    """All departments managed by the user, including their sub-units."""
    from organisation.models import Department

    ids = set(user.managed_departments.values_list("id", flat=True))
    frontier = set(ids)
    while frontier:
        children = set(
            Department.objects.filter(parent_id__in=frontier).values_list(
                "id", flat=True
            )
        )
        frontier = children - ids
        ids |= children
    return ids


def scope_employees(user, queryset, field_prefix=""):
    """
    BN-171 / BN-154: restrict a queryset of Employee (or of objects having
    an employee FK when field_prefix="employee__") to the user's perimeter.
    """
    from django.db.models import Q

    if user.is_superuser or user.role in ORGANISATION_SCOPE_ROLES:
        return queryset
    own = Q(**{f"{field_prefix}user": user})
    if user.role == R.HEAD_OF_DEPARTMENT or user.managed_departments.exists():
        team = Q(**{f"{field_prefix}department_id__in": managed_department_ids(user)})
        return queryset.filter(own | team).distinct()
    return queryset.filter(own)


def can_view_salary(user, employee=None):
    """BN-172: only payroll / HR profiles explicitly authorised see salaries."""
    if not user or not user.is_authenticated:
        return False
    if user.role not in SALARY_ROLES and not user.is_superuser:
        # An employee may always see their own pay (payslips, BN-150).
        return bool(employee and employee.user_id == user.id)
    if user.role == R.HR_OFFICER and employee is not None:
        classification = employee.classification
        if classification is not None and classification.is_executive:
            return False
    return True
