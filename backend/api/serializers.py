from django.contrib.auth.password_validation import (
    validate_password as run_password_validators,
)
from rest_framework import serializers

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


class SiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Site
        fields = ["id", "name", "code"]


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "name", "code", "site"]


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ["id", "name", "department"]


class UserSummarySerializer(serializers.ModelSerializer):
    """Minimal, non-sensitive representation used to nest a user in other payloads."""

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "employee_id"]


class UserSerializer(serializers.ModelSerializer):
    """
    BN-169/171/172/174/176/177 - never exposes `password`, `two_factor_secret`
    or `password_history`: those stay internal to the auth/2FA flows.
    """

    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "employee_id",
            "is_active",
            "is_staff",
            "is_superuser",
            "site",
            "department",
            "team",
            "manager",
            "is_payroll_authorized",
            "two_factor_enabled",
            "must_change_password",
            "processing_purpose",
            "data_retention_until",
            "data_processing_consent",
            "roles",
        ]
        read_only_fields = [
            "is_staff",
            "is_superuser",
            "two_factor_enabled",
            "must_change_password",
        ]

    def get_roles(self, obj):
        return list(
            obj.role_assignments.filter(role__is_active=True).values_list(
                "role__name", flat=True
            )
        )


class RolePermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RolePermission
        fields = ["id", "role", "module", "action"]


class RoleSerializer(serializers.ModelSerializer):
    permissions = RolePermissionSerializer(many=True, read_only=True)

    class Meta:
        model = Role
        fields = [
            "id",
            "name",
            "description",
            "scope",
            "requires_two_factor",
            "is_active",
            "created_at",
            "updated_at",
            "permissions",
        ]
        read_only_fields = ["created_at", "updated_at"]


class UserRoleSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source="role.name", read_only=True)
    user_display = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = UserRole
        fields = [
            "id",
            "user",
            "user_display",
            "role",
            "role_name",
            "assigned_by",
            "assigned_at",
        ]
        read_only_fields = ["assigned_by", "assigned_at"]


class SalaryRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalaryRecord
        fields = [
            "id",
            "employee",
            "base_salary",
            "currency",
            "effective_date",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class AuditLogSerializer(serializers.ModelSerializer):
    """BN-173/175 - read-only by construction: this serializer is only ever
    wired to a ReadOnlyModelViewSet, but it also has no writable fields."""

    user_display = serializers.CharField(
        source="user.username", read_only=True, default=""
    )

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "user",
            "user_display",
            "username_snapshot",
            "action",
            "module",
            "object_type",
            "object_id",
            "object_repr",
            "previous_value",
            "new_value",
            "ip_address",
            "machine",
            "session_key",
            "notes",
            "timestamp",
        ]
        read_only_fields = fields


class DataSubjectRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataSubjectRequest
        fields = [
            "id",
            "employee",
            "request_type",
            "details",
            "status",
            "requested_at",
            "handled_at",
            "handled_by",
            "resolution_notes",
        ]
        read_only_fields = [
            "employee",
            "status",
            "requested_at",
            "handled_at",
            "handled_by",
        ]


# -- Auth / password / 2FA payloads (not tied to a model) --------------------


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(
        trim_whitespace=False, style={"input_type": "password"}
    )


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(
        trim_whitespace=False, style={"input_type": "password"}
    )
    new_password = serializers.CharField(
        trim_whitespace=False, style={"input_type": "password"}
    )

    def validate(self, attrs):
        user = self.context["request"].user
        if not user.check_password(attrs["current_password"]):
            raise serializers.ValidationError(
                {"current_password": "Incorrect current password."}
            )
        run_password_validators(attrs["new_password"], user=user)
        return attrs


class TwoFactorVerifySerializer(serializers.Serializer):
    code = serializers.CharField(max_length=8)
