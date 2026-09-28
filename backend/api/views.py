import csv

from django.contrib.auth import authenticate
from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Action,
    AuditLog,
    DataSubjectRequest,
    Department,
    Module,
    Role,
    RolePermission,
    SalaryRecord,
    Site,
    Team,
    User,
    UserRole,
)
from .permissions import (
    HasModulePermission,
    SalaryConfidentiality,
    ScopedQuerysetMixin,
    TwoFactorRequired,
)
from .serializers import (
    AuditLogSerializer,
    DataSubjectRequestSerializer,
    DepartmentSerializer,
    LoginSerializer,
    PasswordChangeSerializer,
    RolePermissionSerializer,
    RoleSerializer,
    SalaryRecordSerializer,
    SiteSerializer,
    TeamSerializer,
    TwoFactorVerifySerializer,
    UserRoleSerializer,
    UserSerializer,
)
from .services import (
    generate_two_factor_secret,
    get_two_factor_provisioning_uri,
    record_audit,
    set_user_password,
    verify_two_factor_code,
)

# ---------------------------------------------------------------------------
# BN-169 / BN-174 / BN-176 - authentication, password policy, second factor
# ---------------------------------------------------------------------------


class LoginView(APIView):
    """
    BN-169 - every person authenticates individually with their own
    username/password; BN-174 locks the account out after repeated
    failures; BN-176 makes login a two-step process for accounts that
    require a second factor (the client must then call
    TwoFactorVerifyView before anything else will work).
    """

    permission_classes = [AllowAny]
    authentication_classes = []


    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]

        try:
            existing = User.objects.get(username=username)
        except User.DoesNotExist:
            existing = None

        if (
            existing is not None
            and existing.locked_until
            and existing.locked_until > timezone.now()
        ):
            record_audit(
                action="account_locked",
                module=Module.ADMIN,
                obj=existing,
                notes="Login attempted while account is locked.",
            )
            return Response(
                {
                    "detail": "Account temporarily locked after repeated failed attempts."
                },
                status=status.HTTP_423_LOCKED,
            )

        # `authenticate()` dispatches Django's `user_login_failed` signal on
        # its own when credentials don't match, which api.signals already
        # turns into an audit entry + failed-attempt counter (BN-173/174).
        user = authenticate(request, username=username, password=password)
        if user is None:
            return Response(
                {"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED
            )
        if not user.is_active:
            return Response(
                {"detail": "This account is disabled."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # `django_login` dispatches `user_logged_in`, which api.signals
        # records to the audit trail and uses to reset lockout counters.
        django_login(request, user)
        request.session["two_factor_verified"] = False

        return Response(
            {
                "user": UserSerializer(user).data,
                "must_change_password": user.must_change_password,
                "requires_two_factor": user.requires_two_factor(),
                "two_factor_enabled": user.two_factor_enabled,
            }
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        django_logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        grants = list(
            RolePermission.objects.filter(
                role__assignments__user=user, role__is_active=True
            ).values_list("module", "action", "role__scope")
        )
        return Response(
            {
                "user": UserSerializer(user).data,
                "permissions": [
                    {"module": module, "action": act, "scope": scope}
                    for module, act, scope in grants
                ],
            }
        )


class PasswordChangeView(APIView):
    """BN-174 - used both for a voluntary change and for the mandatory
    first-login change enforced by ForcePasswordChangeMiddleware."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        set_user_password(request.user, serializer.validated_data["new_password"])
        return Response({"detail": "Password updated."})


class TwoFactorSetupView(APIView):
    """BN-176 - issues a new TOTP secret; the account is only actually
    switched to `two_factor_enabled=True` once a code is verified."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        secret = generate_two_factor_secret()
        user.two_factor_secret = secret
        user.save(update_fields=["two_factor_secret"])
        return Response(
            {
                "secret": secret,
                "provisioning_uri": get_two_factor_provisioning_uri(user, secret),
            }
        )


class TwoFactorVerifyView(APIView):
    """BN-176 - confirms a TOTP code; enables 2FA on first success and marks
    the current session as having passed the second factor."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = TwoFactorVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user

        if not verify_two_factor_code(
            user.two_factor_secret, serializer.validated_data["code"]
        ):
            record_audit(
                action="access_denied",
                module=Module.ADMIN,
                obj=user,
                notes="Invalid second-factor code.",
            )
            return Response(
                {"detail": "Invalid or expired code."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not user.two_factor_enabled:
            user.two_factor_enabled = True
            user.save(update_fields=["two_factor_enabled"])

        request.session["two_factor_verified"] = True
        return Response({"detail": "Second factor verified."})


# ---------------------------------------------------------------------------
# BN-170 / BN-171 - organisational structure & roles administration
# ---------------------------------------------------------------------------


class SiteViewSet(viewsets.ModelViewSet):
    queryset = Site.objects.all()
    serializer_class = SiteSerializer
    module = Module.ADMIN
    permission_classes = [HasModulePermission]


class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.select_related("site").all()
    serializer_class = DepartmentSerializer
    module = Module.ADMIN
    permission_classes = [HasModulePermission]


class TeamViewSet(viewsets.ModelViewSet):
    queryset = Team.objects.select_related("department").all()
    serializer_class = TeamSerializer
    module = Module.ADMIN
    permission_classes = [HasModulePermission]


class UserViewSet(viewsets.ModelViewSet):
    """BN-169/170 - user-account administration (creation, deactivation,
    perimeter/role assignment happens through UserRoleViewSet)."""

    queryset = User.objects.select_related("site", "department", "team").all()
    serializer_class = UserSerializer
    module = Module.ADMIN
    permission_classes = [HasModulePermission]

    def perform_create(self, serializer):
        # New accounts always start with a forced password change (BN-174)
        # and never inherit 2FA/payroll flags from the request payload.
        user = serializer.save(must_change_password=True)
        raw_password = self.request.data.get("password")
        if raw_password:
            set_user_password(user, raw_password, forced=True)
        record_audit(action="create", module=Module.ADMIN, obj=user)


class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.prefetch_related("permissions").all()
    serializer_class = RoleSerializer
    module = Module.ADMIN
    permission_classes = [HasModulePermission]


class RolePermissionViewSet(viewsets.ModelViewSet):
    queryset = RolePermission.objects.select_related("role").all()
    serializer_class = RolePermissionSerializer
    module = Module.ADMIN
    permission_classes = [HasModulePermission]


class UserRoleViewSet(viewsets.ModelViewSet):
    """Assigning/revoking a role is itself audited automatically, since
    UserRole is one of api.signals.AUDITED_MODELS."""

    queryset = UserRole.objects.select_related("user", "role").all()
    serializer_class = UserRoleSerializer
    module = Module.ADMIN
    permission_classes = [HasModulePermission]

    def perform_create(self, serializer):
        serializer.save(assigned_by=self.request.user)


# ---------------------------------------------------------------------------
# BN-172 - salary confidentiality
# ---------------------------------------------------------------------------


class SalaryRecordViewSet(ScopedQuerysetMixin, viewsets.ModelViewSet):
    """
    Reachable only by accounts that both (a) hold a role granting the
    PAYROLL module for the action in question, AND (b) are individually
    flagged `is_payroll_authorized` (BN-172), AND (c) have passed a second
    factor if their profile requires one (BN-176). The visible rows are
    additionally cut down to the caller's granted perimeter (BN-171).
    """

    queryset = SalaryRecord.objects.select_related("employee").all()
    serializer_class = SalaryRecordSerializer
    module = Module.PAYROLL
    owner_field = "employee"
    security_action_map = {
        "list": Action.CONSULT,
        "retrieve": Action.CONSULT,
        "create": Action.CREATE,
        "update": Action.MODIFY,
        "partial_update": Action.MODIFY,
        "destroy": Action.DELETE,
        "print_record": Action.PRINT,
        "export": Action.EXPORT,
    }
    permission_classes = [HasModulePermission, SalaryConfidentiality, TwoFactorRequired]

    @action(detail=True, methods=["get"], url_path="print")
    def print_record(self, request, pk=None):
        record = self.get_object()
        record_audit(action="print", module=Module.PAYROLL, obj=record)
        return Response(self.get_serializer(record).data)

    @action(detail=False, methods=["get"])
    def export(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="salary_records.csv"'
        writer = csv.writer(response)
        writer.writerow(
            ["employee", "base_salary", "currency", "effective_date", "notes"]
        )
        for record in queryset:
            writer.writerow(
                [
                    record.employee,
                    record.base_salary,
                    record.currency,
                    record.effective_date,
                    record.notes,
                ]
            )
        record_audit(
            action="export",
            module=Module.PAYROLL,
            notes=f"Exported {queryset.count()} salary record(s).",
        )
        return response


# ---------------------------------------------------------------------------
# BN-173 / BN-175 - audit trail: consult and export, never modify
# ---------------------------------------------------------------------------


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    BN-175 - `ReadOnlyModelViewSet` exposes only `list`/`retrieve`; there is
    no route at all for update or delete, and AuditLog.save()/delete()
    would refuse them regardless (BN-173's immutability is enforced at the
    model layer, not just by omitting routes here).
    """

    queryset = AuditLog.objects.select_related("user").all()
    serializer_class = AuditLogSerializer
    module = Module.AUDIT
    permission_classes = [HasModulePermission]
    security_action_map = {
        "list": Action.CONSULT,
        "retrieve": Action.CONSULT,
        "export": Action.EXPORT,
    }

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        if params.get("action"):
            qs = qs.filter(action=params["action"])
        if params.get("module"):
            qs = qs.filter(module=params["module"])
        if params.get("user"):
            qs = qs.filter(user_id=params["user"])
        if params.get("date_from"):
            qs = qs.filter(timestamp__date__gte=params["date_from"])
        if params.get("date_to"):
            qs = qs.filter(timestamp__date__lte=params["date_to"])
        return qs

    @action(detail=False, methods=["get"])
    def export(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="audit_log.csv"'
        writer = csv.writer(response)
        writer.writerow(
            [
                "timestamp",
                "user",
                "action",
                "module",
                "object_type",
                "object_id",
                "object_repr",
                "ip_address",
                "machine",
            ]
        )
        for entry in queryset:
            writer.writerow(
                [
                    entry.timestamp,
                    entry.user or entry.username_snapshot,
                    entry.action,
                    entry.module,
                    entry.object_type,
                    entry.object_id,
                    entry.object_repr,
                    entry.ip_address,
                    entry.machine,
                ]
            )
        record_audit(
            action="export",
            module=Module.AUDIT,
            notes=f"Exported {queryset.count()} audit log row(s).",
        )
        return response


# ---------------------------------------------------------------------------
# BN-177 - GDPR: purpose, minimisation, retention, right of access/rectify
# ---------------------------------------------------------------------------


class DataSubjectRequestViewSet(ScopedQuerysetMixin, viewsets.ModelViewSet):
    """
    An employee raises a request about their own data (visible to them
    under the OWN scope); HR/management roles with a wider EMPLOYEES scope
    can see, and `resolve`, requests across their perimeter.
    """

    queryset = DataSubjectRequest.objects.select_related("employee", "handled_by").all()
    serializer_class = DataSubjectRequestSerializer
    module = Module.EMPLOYEES
    owner_field = "employee"
    security_action_map = {
        "list": Action.CONSULT,
        "retrieve": Action.CONSULT,
        "create": Action.CREATE,
        "update": Action.MODIFY,
        "partial_update": Action.MODIFY,
        "destroy": Action.DELETE,
        "resolve": Action.VALIDATE,
    }
    permission_classes = [HasModulePermission]

    def perform_create(self, serializer):
        # Self-service: an employee always raises a request about their own
        # data (BN-177's "right of the employee to consult and rectify").
        serializer.save(employee=self.request.user)

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        instance = self.get_object()
        new_status = request.data.get("status", DataSubjectRequest.Status.COMPLETED)
        instance.status = new_status
        instance.resolution_notes = request.data.get("resolution_notes", "")
        instance.handled_by = request.user
        instance.handled_at = timezone.now()
        instance.save(
            update_fields=["status", "resolution_notes", "handled_by", "handled_at"]
        )
        record_audit(
            action="validate",
            module=Module.EMPLOYEES,
            obj=instance,
            notes=f"Resolved as {new_status}.",
        )
        return Response(self.get_serializer(instance).data)
