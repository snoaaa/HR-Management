"""
M-17 - Security, Roles and Audit.

This module holds every model needed to satisfy section 7.17 of the
Expression of Need:

  BN-169  Individual authentication            -> User
  BN-170  Fine-grained roles/permissions        -> Module, Action, Role, RolePermission
  BN-171  Visibility perimeter                  -> Scope, Site, Department, Team
  BN-172  Salary confidentiality                -> SalaryRecord, User.is_payroll_authorized
  BN-173  Immutable audit trail                 -> AuditLog
  BN-174  Password policy / session timeout     -> User.* password/lockout fields
  BN-175  Read-only, exportable audit trail     -> AuditLog.save()/delete()
  BN-176  Second factor for payroll profiles    -> User.two_factor_*, Role.requires_two_factor
  BN-177  GDPR purpose/retention/consent        -> User.* GDPR fields, DataSubjectRequest
"""

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import PermissionDenied
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models


class Scope(models.TextChoices):
    """BN-171 - visibility perimeter granted by a role."""

    OWN = "own", "Own data only"
    TEAM = "team", "Team"
    DEPARTMENT = "department", "Department"
    SITE = "site", "Site"
    ORGANISATION = "organisation", "Whole organisation"


# Ordering from narrowest to widest, used to pick the broadest scope a user
# has been granted across all of their roles for a given module/action.
SCOPE_ORDER = [Scope.OWN, Scope.TEAM, Scope.DEPARTMENT, Scope.SITE, Scope.ORGANISATION]


class Module(models.TextChoices):
    """BN-170 - the functional areas permissions can be scoped to."""

    EMPLOYEES = "employees", "Employee records"
    PAYROLL = "payroll", "Payroll & compensation"
    LEAVE = "leave", "Leave & absence"
    TIME_ATTENDANCE = "time_attendance", "Time & attendance"
    RECRUITMENT = "recruitment", "Recruitment"
    TRAINING = "training", "Training & development"
    PERFORMANCE = "performance", "Performance management"
    DOCUMENTS = "documents", "Documents"
    ADMIN = "admin", "Roles & security administration"
    AUDIT = "audit", "Audit trail"


class Action(models.TextChoices):
    """BN-170 - the actions a permission can grant on a module."""

    CONSULT = "consult", "Consult"
    CREATE = "create", "Create"
    MODIFY = "modify", "Modify"
    VALIDATE = "validate", "Validate"
    PRINT = "print", "Print"
    EXPORT = "export", "Export"
    DELETE = "delete", "Delete"


class AuditAction(models.TextChoices):
    """BN-173 - every kind of event the audit trail can record."""

    CREATE = "create", "Creation"
    UPDATE = "update", "Modification"
    DELETE = "delete", "Deletion"
    VALIDATE = "validate", "Validation"
    PRINT = "print", "Printing"
    EXPORT = "export", "Export"
    LOGIN_SUCCESS = "login_success", "Successful login"
    LOGIN_FAILURE = "login_failure", "Failed login attempt"
    LOGOUT = "logout", "Logout"
    PASSWORD_CHANGE = "password_change", "Password change"
    ACCESS_DENIED = "access_denied", "Access denied"
    SESSION_EXPIRED = "session_expired", "Session expired (inactivity)"
    ACCOUNT_LOCKED = "account_locked", "Account locked"


class Site(models.Model):
    """BN-171 - broadest organisational perimeter (a physical/legal site)."""

    name = models.CharField(max_length=150, unique=True)
    code = models.CharField(max_length=20, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Department(models.Model):
    """BN-171 - intermediate perimeter, belongs to a Site."""

    name = models.CharField(max_length=150)
    code = models.CharField(max_length=20)
    site = models.ForeignKey(
        Site,
        on_delete=models.PROTECT,
        related_name="departments",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["name"]
        unique_together = [("site", "code")]

    def __str__(self):
        return self.name


class Team(models.Model):
    """BN-171 - narrowest group perimeter, belongs to a Department."""

    name = models.CharField(max_length=150)
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="teams",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class User(AbstractUser):
    """
    BN-169 - every person logs in with their own individual account; there
    is no notion of a shared/service account anywhere in this model.

    Also carries the fields needed by BN-172 (payroll authorisation),
    BN-174 (password policy/lockout/session), BN-176 (2FA) and BN-177
    (GDPR purpose/retention/consent).
    """

    employee_id = models.CharField(max_length=32, unique=True, null=True, blank=True)

    # Organisational perimeter (BN-171)
    site = models.ForeignKey(
        Site, on_delete=models.SET_NULL, null=True, blank=True, related_name="users"
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )
    team = models.ForeignKey(
        Team, on_delete=models.SET_NULL, null=True, blank=True, related_name="users"
    )
    manager = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="direct_reports",
    )

    # BN-172 - explicit, per-account authorisation to see salary data. A
    # role granting the PAYROLL module is deliberately not enough on its
    # own: this flag is a second, individually-set gate.
    is_payroll_authorized = models.BooleanField(default=False)

    # BN-176 - second authentication factor for payroll-authorised profiles
    two_factor_enabled = models.BooleanField(default=False)
    two_factor_secret = models.CharField(max_length=64, blank=True)

    # BN-174 - password policy / lockout / idle-session tracking
    must_change_password = models.BooleanField(default=True)
    password_changed_at = models.DateTimeField(null=True, blank=True)
    password_history = models.JSONField(default=list, blank=True)
    failed_login_attempts = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    last_activity = models.DateTimeField(null=True, blank=True)

    # BN-177 - GDPR purpose / minimisation / retention / consent
    processing_purpose = models.TextField(
        blank=True,
        default=(
            "Human resources management: payroll, leave, performance "
            "and legal/regulatory compliance."
        ),
    )
    data_retention_until = models.DateField(null=True, blank=True)
    data_processing_consent = models.BooleanField(default=False)
    consent_given_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["username"]

    # -- BN-170/171 helpers -------------------------------------------------

    def has_module_permission(self, module, action) -> bool:
        """Does any active role held by this user grant module+action?"""
        if self.is_superuser:
            return True
        return RolePermission.objects.filter(
            role__assignments__user=self,
            role__is_active=True,
            module=module,
            action=action,
        ).exists()

    def broadest_scope(self, module, action):
        """
        The widest Scope granted, across all active roles, for module+action.
        Returns None when the user has no role granting that permission at
        all (the caller should then deny/empty the queryset).
        """
        if self.is_superuser:
            return Scope.ORGANISATION

        granted = set(
            Role.objects.filter(
                assignments__user=self,
                is_active=True,
                permissions__module=module,
                permissions__action=action,
            ).values_list("scope", flat=True)
        )
        if not granted:
            return None
        return max(granted, key=lambda scope: SCOPE_ORDER.index(scope))

    # -- BN-176 helper --------------------------------------------------

    def requires_two_factor(self) -> bool:
        """
        Whether this account must complete a second factor before using
        endpoints guarded by TwoFactorRequired: either it is individually
        authorised for payroll (BN-172/176), or one of its active roles
        explicitly demands it.
        """
        if self.is_payroll_authorized:
            return True
        return Role.objects.filter(
            assignments__user=self, is_active=True, requires_two_factor=True
        ).exists()


class Role(models.Model):
    """
    BN-170/171 - a named bundle of (module, action) grants plus a single
    visibility scope that applies to every one of those grants.
    """

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    scope = models.CharField(max_length=20, choices=Scope.choices, default=Scope.OWN)
    requires_two_factor = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class RolePermission(models.Model):
    """BN-170 - one (module, action) grant belonging to a Role."""

    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="permissions")
    module = models.CharField(max_length=32, choices=Module.choices)
    action = models.CharField(max_length=32, choices=Action.choices)

    class Meta:
        ordering = ["module", "action"]
        unique_together = [("role", "module", "action")]

    def __str__(self):
        return f"{self.role.name}: {self.module}/{self.action}"


class UserRole(models.Model):
    """BN-170 - assignment of a Role to a User. A user may hold several."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="role_assignments",
    )
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="assignments")
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="role_assignments_made",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-assigned_at"]
        unique_together = [("user", "role")]

    def __str__(self):
        return f"{self.user}: {self.role}"


class SalaryRecord(models.Model):
    """BN-172 - the most sensitive kind of data in the system."""

    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="salary_records",
    )
    base_salary = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="EUR")
    effective_date = models.DateField()
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-effective_date"]

    def __str__(self):
        return f"{self.employee}: {self.base_salary} {self.currency} ({self.effective_date})"


class AuditLog(models.Model):
    """
    BN-173/BN-175 - an append-only trail. `save()` refuses any update to an
    existing row and `delete()` is disabled outright, so once written an
    entry can only ever be consulted or exported, never altered or removed
    -- including by staff/superusers, and including via the admin site
    (see api.admin.AuditLogAdmin).
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_entries",
    )
    # Kept even if the account is later deleted, so the trail stays legible.
    username_snapshot = models.CharField(max_length=150, blank=True)

    action = models.CharField(max_length=32, choices=AuditAction.choices)
    module = models.CharField(max_length=32, choices=Module.choices, blank=True)

    object_type = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=64, blank=True)
    object_repr = models.CharField(max_length=255, blank=True)

    # `encoder=DjangoJSONEncoder` lets these snapshot dicts safely hold the
    # Decimal/date/datetime values that come straight out of model fields
    # (e.g. SalaryRecord.base_salary, .effective_date) without a manual
    # pre-serialisation pass in api.signals._to_dict.
    previous_value = models.JSONField(null=True, blank=True, encoder=DjangoJSONEncoder)
    new_value = models.JSONField(null=True, blank=True, encoder=DjangoJSONEncoder)

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    machine = models.CharField(max_length=255, blank=True)
    session_key = models.CharField(max_length=40, blank=True)

    notes = models.CharField(max_length=500, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["-timestamp"], name="audit_timestamp_idx"),
            models.Index(fields=["user", "action"], name="audit_user_action_idx"),
            models.Index(fields=["module"], name="audit_module_idx"),
        ]

    def __str__(self):
        return f"[{self.timestamp}] {self.action} ({self.module}) by {self.user or self.username_snapshot}"

    def save(self, *args, **kwargs):
        if self.pk:
            raise PermissionDenied(
                "Audit log entries cannot be modified once written (BN-175)."
            )
        if not self.username_snapshot and self.user_id:
            self.username_snapshot = str(self.user)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionDenied("Audit log entries cannot be deleted (BN-175).")


class DataSubjectRequest(models.Model):
    """
    BN-177 - tracks an employee's exercise of their right to consult
    (access) or rectify the personal data held about them.
    """

    class RequestType(models.TextChoices):
        ACCESS = "access", "Right of access"
        RECTIFICATION = "rectification", "Right of rectification"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"
        REJECTED = "rejected", "Rejected"

    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="data_subject_requests",
    )
    request_type = models.CharField(max_length=20, choices=RequestType.choices)
    details = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    handled_at = models.DateTimeField(null=True, blank=True)
    handled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="handled_data_requests",
    )
    resolution_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-requested_at"]

    def __str__(self):
        return f"{self.get_request_type_display()} - {self.employee} ({self.status})"
