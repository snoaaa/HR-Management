from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from core.exports import export_rows
from users.permissions import ModulePermission, has_module_permission, scope_employees
from users.utils import log_audit_action

from .models import (
    EducationAndExperience,
    Employee,
    EmployeeDocument,
    EmployeeHistory,
    FamilyMember,
)
from .serializers import (
    EducationAndExperienceSerializer,
    EmployeeDocumentSerializer,
    EmployeeHistorySerializer,
    EmployeeSerializer,
    FamilyMemberSerializer,
)

# Fields never written to the history (files, reverse relations).
HISTORY_EXCLUDED_FIELDS = {"id", "photograph"}

EXPORT_COLUMNS = [
    ("Matriculation", "matriculation_number"),
    ("Surname", "surname"),
    ("Given names", "given_names"),
    ("Sex", "sex"),
    ("Date of birth", "date_of_birth"),
    ("Nationality", "nationality"),
    ("Department", "department"),
    ("Position", "position"),
    ("Contract type", "contract_type"),
    ("Date of hire", "date_of_hire"),
    ("Status", "status"),
    ("Phone", "phone_number"),
    ("Professional e-mail", "professional_email"),
]


class EmployeeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Employee. Includes search, filter and custom actions.
    """

    serializer_class = EmployeeSerializer
    permission_classes = [ModulePermission]
    permission_module = "employees"
    action_permissions = {"archive": "modify", "export": "export", "me": "consult"}
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    # BN-19: Search and filter employees on any criterion
    filterset_fields = [
        "department",
        "position",
        "contract_type",
        "status",
        "workplace",
        "sex",
    ]
    search_fields = [
        "surname",
        "given_names",
        "matriculation_number",
        "personal_email",
        "professional_email",
    ]
    ordering_fields = ["surname", "date_of_hire", "matriculation_number"]

    def get_queryset(self):
        # BN-171 / BN-154: each user only sees the records of their perimeter.
        queryset = Employee.objects.select_related(
            "department", "position", "classification", "workplace"
        ).order_by("-id")
        return scope_employees(self.request.user, queryset)

    def perform_create(self, serializer):
        employee = serializer.save()
        EmployeeHistory.objects.create(
            employee=employee,
            author=self.request.user,
            field_name="record",
            previous_value=None,
            new_value="CREATED",
        )
        log_audit_action(
            user=self.request.user,
            action=f"Created employee record {employee.matriculation_number}",
            module="Employees",
            request=self.request,
            details={"employee_id": employee.id},
        )

    def perform_update(self, serializer):
        # BN-21: keep every modification with author, date and previous value.
        instance = serializer.instance
        previous = {
            field.name: getattr(instance, field.attname)
            for field in Employee._meta.concrete_fields
            if field.name not in HISTORY_EXCLUDED_FIELDS
        }
        employee = serializer.save()
        changes = {}
        for name, old_value in previous.items():
            field = Employee._meta.get_field(name)
            new_value = getattr(employee, field.attname)
            if old_value != new_value:
                changes[name] = (old_value, new_value)
                EmployeeHistory.objects.create(
                    employee=employee,
                    author=self.request.user,
                    field_name=name,
                    previous_value="" if old_value is None else str(old_value),
                    new_value="" if new_value is None else str(new_value),
                )
        if changes:
            log_audit_action(
                user=self.request.user,
                action=f"Updated employee record {employee.matriculation_number}",
                module="Employees",
                request=self.request,
                details={
                    "employee_id": employee.id,
                    "previous_value": {k: str(v[0]) for k, v in changes.items()},
                    "new_value": {k: str(v[1]) for k, v in changes.items()},
                },
            )

    def perform_destroy(self, instance):
        # BN-09: a record is never physically deleted once used; we archive it.
        self._archive(instance)

    def _archive(self, employee):
        previous = employee.status
        employee.status = "ARCHIVED"
        employee.save(update_fields=["status"])

        # BN-21: Log the modification
        EmployeeHistory.objects.create(
            employee=employee,
            author=self.request.user,
            field_name="status",
            previous_value=previous,
            new_value="ARCHIVED",
        )
        log_audit_action(
            user=self.request.user,
            action=f"Archived employee record {employee.matriculation_number}",
            module="Employees",
            request=self.request,
            details={"employee_id": employee.id, "previous_value": previous},
        )

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        """
        BN-09: Archive an employee record without physically deleting it.
        """
        self._archive(self.get_object())
        return Response({"status": "employee archived"}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def export(self, request):
        """BN-19: export the filtered list as CSV, Excel or PDF (?file_format=)."""
        fmt = request.query_params.get("file_format", "csv")
        queryset = self.filter_queryset(self.get_queryset())
        rows = []
        for employee in queryset:
            row = []
            for _, attr in EXPORT_COLUMNS:
                value = getattr(employee, attr)
                if attr in ("sex", "contract_type", "status"):
                    value = getattr(employee, f"get_{attr}_display")()
                row.append("" if value is None else str(value))
            rows.append(row)
        log_audit_action(
            user=request.user,
            action=f"Exported employee list ({len(rows)} rows, {fmt})",
            module="Employees",
            request=request,
            details={"filters": dict(request.query_params)},
        )
        return export_rows(
            [title for title, _ in EXPORT_COLUMNS],
            rows,
            "employees",
            fmt,
            title="Employee list",
        )

    @action(detail=False, methods=["get"])
    def me(self, request):
        """The employee record linked to the logged-in user (self-service)."""
        employee = Employee.objects.filter(user=request.user).first()
        if employee is None:
            return Response(
                {"detail": "No employee record is linked to this account."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(self.get_serializer(employee).data)


class EmployeeChildViewSet(viewsets.ModelViewSet):
    """Base for the sub-resources of an employee record, scoped by perimeter."""

    permission_classes = [ModulePermission]
    permission_module = "employees"
    model = None

    def get_employee(self):
        queryset = scope_employees(self.request.user, Employee.objects.all())
        return get_object_or_404(queryset, pk=self.kwargs["employee_pk"])

    def get_queryset(self):
        return self.model.objects.filter(employee=self.get_employee())

    def perform_create(self, serializer):
        employee = self.get_employee()
        instance = serializer.save(employee=employee)
        EmployeeHistory.objects.create(
            employee=employee,
            author=self.request.user,
            field_name=self.model._meta.verbose_name,
            previous_value=None,
            new_value=f"Added: {instance}",
        )

    def perform_destroy(self, instance):
        EmployeeHistory.objects.create(
            employee=instance.employee,
            author=self.request.user,
            field_name=self.model._meta.verbose_name,
            previous_value=str(instance),
            new_value="Removed",
        )
        instance.delete()


class FamilyMemberViewSet(EmployeeChildViewSet):
    serializer_class = FamilyMemberSerializer
    model = FamilyMember


class EmployeeDocumentViewSet(EmployeeChildViewSet):
    serializer_class = EmployeeDocumentSerializer
    model = EmployeeDocument


class EducationAndExperienceViewSet(EmployeeChildViewSet):
    serializer_class = EducationAndExperienceSerializer
    model = EducationAndExperience


class EmployeeHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = EmployeeHistorySerializer
    permission_classes = [ModulePermission]
    permission_module = "employees"

    def get_queryset(self):
        if not has_module_permission(self.request.user, "employees", "modify"):
            # The history exposes previous values: reserved to HR profiles.
            raise PermissionDenied()
        return EmployeeHistory.objects.filter(
            employee_id=self.kwargs["employee_pk"]
        ).order_by("-modification_date")
