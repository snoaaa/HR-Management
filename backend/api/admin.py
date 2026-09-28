from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import (
    AuditLog,
    DataSubjectRequest,
    Department,
    Role,
    RolePermission,
    SalaryRecord,
    Site,
    Team,
    User,
    UserRole,
)


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ["name", "code"]
    search_fields = ["name", "code"]


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "site"]
    list_filter = ["site"]
    search_fields = ["name", "code"]


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ["name", "department"]
    list_filter = ["department"]
    search_fields = ["name"]


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """
    BN-169/171/172/174/176/177 - surfaces the security-relevant fields in
    the admin on top of Django's own UserAdmin, without ever exposing the
    raw two-factor secret or password history for editing.
    """

    list_display = [
        "username",
        "email",
        "site",
        "department",
        "team",
        "is_payroll_authorized",
        "two_factor_enabled",
        "must_change_password",
        "is_active",
        "is_staff",
    ]
    list_filter = [
        "is_active",
        "is_staff",
        "is_payroll_authorized",
        "two_factor_enabled",
        "site",
        "department",
    ]
    fieldsets = DjangoUserAdmin.fieldsets + (
        (
            "Organisation & perimeter (BN-171)",
            {"fields": ("employee_id", "site", "department", "team", "manager")},
        ),
        (
            "Security (BN-172 / BN-174 / BN-176)",
            {
                "fields": (
                    "is_payroll_authorized",
                    "two_factor_enabled",
                    "must_change_password",
                    "failed_login_attempts",
                    "locked_until",
                )
            },
        ),
        (
            "Personal data processing (BN-177)",
            {
                "fields": (
                    "processing_purpose",
                    "data_retention_until",
                    "data_processing_consent",
                )
            },
        ),
    )
    readonly_fields = ["failed_login_attempts", "locked_until"]


class RolePermissionInline(admin.TabularInline):
    model = RolePermission
    extra = 1


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ["name", "scope", "requires_two_factor", "is_active"]
    list_filter = ["scope", "requires_two_factor", "is_active"]
    search_fields = ["name"]
    inlines = [RolePermissionInline]


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ["user", "role", "assigned_by", "assigned_at"]
    list_filter = ["role"]
    autocomplete_fields = ["user", "role", "assigned_by"]


@admin.register(SalaryRecord)
class SalaryRecordAdmin(admin.ModelAdmin):
    """BN-172 - salary data is still confined to staff who can reach the
    Django admin at all; the API's own SalaryConfidentiality permission is
    the primary gate for day-to-day access."""

    list_display = ["employee", "base_salary", "currency", "effective_date"]
    list_filter = ["currency"]
    autocomplete_fields = ["employee"]


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """
    BN-175 - the audit trail can be consulted (and, from the API, exported)
    by an authorised user, but nobody -- including a superuser through this
    very admin site -- can add, change or delete an entry.
    """

    list_display = [
        "timestamp",
        "user",
        "action",
        "module",
        "object_repr",
        "ip_address",
    ]
    list_filter = ["action", "module"]
    search_fields = ["object_repr", "username_snapshot", "ip_address", "machine"]
    readonly_fields = [field.name for field in AuditLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(DataSubjectRequest)
class DataSubjectRequestAdmin(admin.ModelAdmin):
    list_display = ["employee", "request_type", "status", "requested_at", "handled_by"]
    list_filter = ["request_type", "status"]
    autocomplete_fields = ["employee", "handled_by"]
