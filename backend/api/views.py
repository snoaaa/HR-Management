from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from drf_spectacular.utils import extend_schema


from users.utils import log_audit_action

from .serializers import CustomTokenObtainPairSerializer, UserSerializer


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Takes a set of user credentials and returns an access and refresh JSON web
    token to prove the authentication of those credentials, along with user details.
    """

    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        try:
            response = super().post(request, *args, **kwargs)
            # Login successful
            username = request.data.get("username")
            from django.contrib.auth import get_user_model

            User = get_user_model()
            user = User.objects.filter(username=username).first()
            log_audit_action(
                user=user,
                action="User logged in successfully",
                module="Authentication",
                request=request,
            )
            return response
        except Exception as e:
            # Login failed
            username = request.data.get("username")
            from django.contrib.auth import get_user_model

            User = get_user_model()
            user = User.objects.filter(username=username).first()
            log_audit_action(
                user=user,
                action=f"Failed login attempt: {str(e)}",
                module="Authentication",
                request=request,
                details={"username_attempted": username},
            )
            raise


class LogoutView(APIView):
    """
    Blacklists the given refresh token, effectively logging the user out.
    Requires the user to be authenticated.
    """

    permission_classes = (IsAuthenticated,)

    @extend_schema(request=None, responses={205: None})
    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return Response(
                    {"detail": "Refresh token is required to log out."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            token = RefreshToken(refresh_token)
            token.blacklist()

            log_audit_action(
                user=request.user,
                action="User logged out",
                module="Authentication",
                request=request,
            )

            return Response(
                {"detail": "Successfully logged out."},
                status=status.HTTP_205_RESET_CONTENT,
            )
        except TokenError as e:
            return Response(
                {"detail": "Token is invalid or expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"detail": "An error occurred during logout."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class UserMeView(APIView):
    """
    Returns the currently authenticated user's details.
    """

    permission_classes = (IsAuthenticated,)

    @extend_schema(responses={200: UserSerializer})
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .serializers import ChangePasswordSerializer


class ChangePasswordView(APIView):
    """
    An endpoint for changing password.
    """

    permission_classes = (IsAuthenticated,)

    @extend_schema(request=ChangePasswordSerializer, responses={200: None})
    def post(self, request, *args, **kwargs):
        serializer = ChangePasswordSerializer(data=request.data)

        if serializer.is_valid():
            user = request.user
            # Check old password
            if not user.check_password(serializer.data.get("old_password")):
                return Response(
                    {"old_password": ["Wrong password."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            new_password = serializer.data.get("new_password")

            # Validate new password against policies
            try:
                validate_password(new_password, user)
            except ValidationError as e:
                return Response(
                    {"new_password": list(e.messages)},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # set_password also hashes the password that the user will get
            user.set_password(new_password)
            user.requires_password_change = False
            user.save()

            log_audit_action(
                user=user,
                action="User changed password",
                module="Authentication",
                request=request,
            )

            # Return new tokens so the user doesn't get kicked out immediately
            refresh = RefreshToken.for_user(user)
            return Response(
                {
                    "detail": "Password updated successfully.",
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "role": user.role,
                        "requires_password_change": user.requires_password_change,
                    },
                },
                status=status.HTTP_200_OK,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


from django.contrib.auth import get_user_model
from rest_framework.permissions import BasePermission
from rest_framework.viewsets import ModelViewSet

User = get_user_model()


class IsSystemAdminOrHRManager(BasePermission):
    """
    Custom permission to only allow System Administrators or HR Managers to manage users.
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return request.user.role in [
            User.Roles.SYSTEM_ADMINISTRATOR,
            User.Roles.HR_MANAGER,
        ]


class UserViewSet(ModelViewSet):
    """
    ViewSet for listing, retrieving, creating, and updating users (BN-171, BN-177).
    """

    serializer_class = UserSerializer
    permission_classes = [IsSystemAdminOrHRManager]
    queryset = User.objects.all().order_by("-date_joined")

    def perform_create(self, serializer):
        user = serializer.save()
        new_data = self.get_serializer(user).data
        log_audit_action(
            user=self.request.user,
            action=f"Created user: {user.username}",
            module="User Management",
            request=self.request,
            details={
                "created_user_id": user.id,
                "role": user.role,
                "new_value": new_data,
            },
        )

    def perform_update(self, serializer):
        old_instance = self.get_object()
        old_data = self.get_serializer(old_instance).data

        user = serializer.save()
        new_data = self.get_serializer(user).data

        log_audit_action(
            user=self.request.user,
            action=f"Updated user: {user.username}",
            module="User Management",
            request=self.request,
            details={
                "updated_user_id": user.id,
                "is_active": user.is_active,
                "role": user.role,
                "previous_value": old_data,
                "new_value": new_data,
            },
        )

    def perform_destroy(self, instance):
        # We generally don't delete users, we deactivate them (is_active=False).
        # But if a DELETE request comes in, we can either soft delete or actually delete.
        # Let's enforce soft delete for audit purposes.
        username = instance.username
        old_data = self.get_serializer(instance).data

        instance.is_active = False
        instance.save()

        log_audit_action(
            user=self.request.user,
            action=f"Deactivated user: {username}",
            module="User Management",
            request=self.request,
            details={"deactivated_user_id": instance.id, "previous_value": old_data},
        )


from rest_framework.viewsets import ReadOnlyModelViewSet

from users.models import AuditLog

from .serializers import AuditLogSerializer


class AuditLogViewSet(ReadOnlyModelViewSet):
    """
    ViewSet for consulting the audit trail (BN-175). Read-only.
    """

    serializer_class = AuditLogSerializer
    permission_classes = [IsSystemAdminOrHRManager]
    queryset = AuditLog.objects.all()


from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework.decorators import action

from core.exports import export_rows
from users.models import RolePermission
from users.permissions import (
    ACTIONS,
    MODULES,
    can_view_salary,
    get_permissions_for_role,
    has_module_permission,
)


class AuditLogExportMixin:
    @action(detail=False, methods=["get"])
    def export(self, request):
        """BN-175: export the (filtered) audit trail."""
        if not has_module_permission(request.user, "audit", "export"):
            return Response(status=status.HTTP_403_FORBIDDEN)
        fmt = request.query_params.get("file_format", "csv")
        queryset = self.filter_queryset(self.get_queryset())[:10000]
        rows = [
            [
                log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                log.user.username if log.user else "",
                log.module,
                log.action,
                log.ip_address or "",
                (log.details or {}).get("user_agent", ""),
            ]
            for log in queryset
        ]
        log_audit_action(
            user=request.user,
            action=f"Exported audit trail ({len(rows)} rows)",
            module="Audit",
            request=request,
        )
        return export_rows(
            ["Date", "User", "Module", "Action", "IP address", "Machine"],
            rows,
            "audit-trail",
            fmt,
            title="Audit trail",
        )


class FilteredAuditLogViewSet(AuditLogExportMixin, AuditLogViewSet):
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = {
        "module": ["exact"],
        "user": ["exact"],
        "timestamp": ["gte", "lte"],
    }
    search_fields = ["action", "module", "user__username"]


class MyPermissionsView(APIView):
    """Permissions of the logged-in user, used by the frontend menus."""

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        from employees.models import Employee

        user = request.user
        if user.is_superuser:
            perms = {module: list(ACTIONS) for module in MODULES}
        else:
            perms = {
                module: sorted(actions)
                for module, actions in get_permissions_for_role(user.role).items()
            }
        employee = Employee.objects.filter(user=user).first()
        return Response(
            {
                "role": user.role,
                "permissions": perms,
                "can_view_salary": can_view_salary(user),
                "employee_id": employee.id if employee else None,
                "manages_departments": list(
                    user.managed_departments.values_list("id", flat=True)
                ),
            }
        )


class PermissionMatrixView(APIView):
    """
    BN-170: consult and change the permission matrix (role x module x action).
    GET returns {role: {module: [actions]}}; PUT replaces it.
    """

    permission_classes = (IsSystemAdminOrHRManager,)

    def get(self, request):
        matrix = {role: {} for role in User.Roles.values}
        for perm in RolePermission.objects.all():
            matrix.setdefault(perm.role, {}).setdefault(perm.module, []).append(
                perm.action
            )
        return Response(
            {
                "modules": MODULES,
                "actions": ACTIONS,
                "roles": [
                    {"value": value, "label": label}
                    for value, label in User.Roles.choices
                ],
                "matrix": matrix,
            }
        )

    def put(self, request):
        matrix = request.data.get("matrix", {})
        previous = {
            f"{p.role}:{p.module}:{p.action}" for p in RolePermission.objects.all()
        }
        rows = []
        for role, modules in matrix.items():
            if role not in User.Roles.values:
                continue
            for module, actions in modules.items():
                if module not in MODULES:
                    continue
                for perm_action in actions:
                    if perm_action in ACTIONS:
                        rows.append(
                            RolePermission(role=role, module=module, action=perm_action)
                        )
        with transaction.atomic():
            RolePermission.objects.all().delete()
            RolePermission.objects.bulk_create(rows)
        current = {f"{r.role}:{r.module}:{r.action}" for r in rows}
        log_audit_action(
            user=request.user,
            action="Changed the permission matrix",
            module="User Management",
            request=request,
            details={
                "granted": sorted(current - previous),
                "revoked": sorted(previous - current),
            },
        )
        return self.get(request)
