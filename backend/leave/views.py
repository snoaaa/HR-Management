import datetime

from django.http import HttpResponse
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from core.exports import export_rows
from documents.services import issue_document
from employees.models import Employee
from users.permissions import ModulePermission, has_module_permission, scope_employees
from users.utils import log_audit_action

from . import services
from .models import EntitlementRule, LeaveAdjustment, LeaveRequest, LeaveType
from .serializers import (
    EntitlementRuleSerializer,
    LeaveAdjustmentSerializer,
    LeaveRequestSerializer,
    LeaveTypeSerializer,
)


def _is_hr(user):
    return has_module_permission(user, "leave", "modify")


def _pdf(issued):
    response = HttpResponse(issued.file.read(), content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{issued.reference}.pdf"'
    return response


def _scoped_employee(user, employee_id):
    employee = (
        scope_employees(user, Employee.objects.all()).filter(pk=employee_id).first()
    )
    if employee is None:
        raise PermissionDenied("This employee is outside your perimeter.")
    return employee


class LeaveTypeViewSet(viewsets.ModelViewSet):
    """BN-46 / BN-47."""

    queryset = LeaveType.objects.all()
    serializer_class = LeaveTypeSerializer
    permission_classes = [ModulePermission]
    permission_module = "leave"
    action_permissions = {"create": "modify"}

    def perform_destroy(self, instance):
        if instance.leaverequest_set.exists():
            raise ValidationError(
                {"detail": "This type is used: deactivate it instead."}
            )
        instance.delete()


class EntitlementRuleViewSet(viewsets.ModelViewSet):
    """BN-48: dated acquisition rules."""

    queryset = EntitlementRule.objects.all()
    serializer_class = EntitlementRuleSerializer
    permission_classes = [ModulePermission]
    permission_module = "leave"
    action_permissions = {"create": "modify"}


class LeaveAdjustmentViewSet(viewsets.ModelViewSet):
    serializer_class = LeaveAdjustmentSerializer
    permission_classes = [ModulePermission]
    permission_module = "leave"
    action_permissions = {"create": "modify"}
    filterset_fields = ("employee", "year", "kind")

    def get_queryset(self):
        return scope_employees(
            self.request.user,
            LeaveAdjustment.objects.select_related("employee"),
            "employee__",
        )

    def perform_create(self, serializer):
        adjustment = serializer.save(created_by=self.request.user)
        log_audit_action(
            user=self.request.user,
            action=f"Leave adjustment {adjustment.days} d for {adjustment.employee.full_name}",
            module="Leave",
            request=self.request,
            details={"reason": adjustment.reason, "kind": adjustment.kind},
        )


class LeaveRequestViewSet(viewsets.ModelViewSet):
    """BN-50 → BN-57: requests, approval, cancellation, printing."""

    serializer_class = LeaveRequestSerializer
    permission_classes = [ModulePermission]
    permission_module = "leave"
    action_permissions = {
        "submit": "create",
        "cancel": "create",
        "interrupt": "modify",
        "postpone": "create",
        "print_decision": "print",
        "print_certificate": "print",
        "preview": "create",
        "balance": "consult",
        "balances": "consult",
        "plan": "consult",
        "print_balance": "print",
    }
    filterset_fields = {
        "employee": ["exact"],
        "employee__department": ["exact"],
        "leave_type": ["exact"],
        "status": ["exact", "in"],
        "start_date": ["gte", "lte"],
    }
    search_fields = ("employee__surname", "employee__given_names")

    def get_queryset(self):
        return scope_employees(
            self.request.user,
            LeaveRequest.objects.select_related(
                "employee", "employee__department", "leave_type", "replacement"
            ),
            "employee__",
        )

    def _owner(self, employee_id=None):
        user = self.request.user
        if employee_id:
            if (
                _is_hr(user)
                or Employee.objects.filter(pk=employee_id, user=user).exists()
            ):
                return _scoped_employee(user, employee_id)
            if self.action in ("balance", "print_balance", "preview"):
                # Managers consult the balances of their team (read only).
                return _scoped_employee(user, employee_id)
            raise PermissionDenied("You can only make requests for yourself.")
        employee = Employee.objects.filter(user=user).first()
        if employee is None:
            raise ValidationError(
                {"detail": "No employee record is linked to this account."}
            )
        return employee

    def _check_owner(self, leave_request):
        user = self.request.user
        if leave_request.employee.user_id != user.id and not _is_hr(user):
            raise PermissionDenied("Only the employee or HR can act on this request.")

    def perform_create(self, serializer):
        employee_field = serializer.validated_data.get("employee")
        employee = self._owner(employee_field.id if employee_field else None)
        leave_request = serializer.save(employee=employee, created_by=self.request.user)
        if self.request.data.get("submit") in (True, "true", "1"):
            self._submit(leave_request)

    def perform_update(self, serializer):
        self._check_owner(serializer.instance)
        serializer.save()

    def perform_destroy(self, instance):
        self._check_owner(instance)
        if instance.status != "DRAFT":
            raise ValidationError(
                {"detail": "Only a draft can be deleted; cancel the request."}
            )
        instance.delete()

    def _submit(self, leave_request):
        try:
            services.submit(leave_request, self.request.user)
        except services.LeaveError as exc:
            raise ValidationError({"detail": str(exc)})

    def _respond(self, leave_request):
        leave_request.refresh_from_db()
        return Response(self.get_serializer(leave_request).data)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        leave_request = self.get_object()
        self._check_owner(leave_request)
        self._submit(leave_request)
        return self._respond(leave_request)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        leave_request = self.get_object()
        self._check_owner(leave_request)
        try:
            services.cancel(leave_request, request.user)
        except services.LeaveError as exc:
            return Response({"detail": str(exc)}, status=400)
        return self._respond(leave_request)

    @action(detail=True, methods=["post"])
    def interrupt(self, request, pk=None):
        leave_request = self.get_object()
        try:
            last_day = datetime.date.fromisoformat(request.data["last_day"])
            services.interrupt(leave_request, last_day, request.user)
        except (KeyError, ValueError):
            return Response(
                {"detail": "last_day (YYYY-MM-DD) is required."}, status=400
            )
        except services.LeaveError as exc:
            return Response({"detail": str(exc)}, status=400)
        log_audit_action(
            user=request.user,
            action=f"Interrupted leave #{leave_request.id} on {last_day}",
            module="Leave",
            request=request,
        )
        return self._respond(leave_request)

    @action(detail=True, methods=["post"])
    def postpone(self, request, pk=None):
        leave_request = self.get_object()
        self._check_owner(leave_request)
        try:
            services.postpone(
                leave_request,
                datetime.date.fromisoformat(request.data["start_date"]),
                datetime.date.fromisoformat(request.data["end_date"]),
                request.user,
            )
        except (KeyError, ValueError):
            return Response(
                {"detail": "start_date and end_date are required."}, status=400
            )
        except services.LeaveError as exc:
            return Response({"detail": str(exc)}, status=400)
        return self._respond(leave_request)

    @action(detail=False, methods=["post"])
    def preview(self, request):
        """Number of days, balance and team warning before submitting."""
        employee = self._owner(request.data.get("employee"))
        try:
            leave_type = LeaveType.objects.get(pk=request.data["leave_type"])
            start = datetime.date.fromisoformat(request.data["start_date"])
            end = datetime.date.fromisoformat(request.data["end_date"])
            days = services.count_days(leave_type, employee, start, end)
        except (KeyError, ValueError, LeaveType.DoesNotExist):
            return Response(
                {"detail": "leave_type, start_date and end_date are required."},
                status=400,
            )
        except services.LeaveError as exc:
            return Response({"detail": str(exc)}, status=400)
        draft = LeaveRequest(
            employee=employee, leave_type=leave_type, start_date=start, end_date=end
        )
        current = services.balance(employee, start.year, start)
        return Response(
            {
                "days": days,
                "balance": current,
                "sufficient": (not leave_type.consumes_entitlement)
                or days <= current["available"],
                "overlap_warning": services.overlap_warning(draft),
            }
        )

    @action(detail=False, methods=["get"])
    def balance(self, request):
        """BN-49: balance of the logged-in employee, or of ?employee=."""
        employee = self._owner(request.query_params.get("employee"))
        year = int(request.query_params.get("year", timezone.now().year))
        today = timezone.now().date()
        until = today if year == today.year else None
        return Response(
            {
                "employee": employee.id,
                "employee_name": employee.full_name,
                **services.balance(employee, year, until),
            }
        )

    @action(detail=False, methods=["get"])
    def balances(self, request):
        """Summary of balances (team or organisation), exportable."""
        year = int(request.query_params.get("year", timezone.now().year))
        today = timezone.now().date()
        until = today if year == today.year else None
        employees = scope_employees(
            request.user, Employee.objects.filter(status="ACTIVE")
        )
        if request.query_params.get("department"):
            employees = employees.filter(
                department_id=request.query_params["department"]
            )
        rows = []
        for employee in employees.select_related("department"):
            b = services.balance(employee, year, until)
            rows.append(
                {
                    "employee": employee.id,
                    "employee_name": employee.full_name,
                    "matriculation": employee.matriculation_number,
                    "department": (
                        employee.department.name if employee.department else ""
                    ),
                    **b,
                }
            )
        fmt = request.query_params.get("file_format")
        if fmt:
            if not has_module_permission(request.user, "leave", "export"):
                raise PermissionDenied()
            keys = [
                "matriculation",
                "employee_name",
                "department",
                "carried_over",
                "acquired",
                "taken",
                "pending",
                "remaining",
            ]
            return export_rows(
                [
                    "Matriculation",
                    "Employee",
                    "Department",
                    "Carried over",
                    "Acquired",
                    "Taken",
                    "Pending",
                    "Remaining",
                ],
                [[r[k] for k in keys] for r in rows],
                f"leave-balances-{year}",
                fmt,
                title=f"Leave balances {year}",
            )
        return Response(rows)

    @action(detail=False, methods=["get"])
    def plan(self, request):
        """BN-55: annual leave plan as calendar per team and department."""
        year = int(request.query_params.get("year", timezone.now().year))
        employees = scope_employees(
            request.user, Employee.objects.exclude(status="ARCHIVED")
        )
        if request.query_params.get("department"):
            employees = employees.filter(
                department_id=request.query_params["department"]
            )
        requests = services.annual_plan(year, employees)
        return Response(self.get_serializer(requests, many=True).data)

    def _context(self, leave_request):
        employee = leave_request.employee
        return {
            "leave": leave_request,
            "employee": employee,
            "balance": services.balance(employee, leave_request.start_date.year),
        }

    @action(detail=True, methods=["get"])
    def print_decision(self, request, pk=None):
        """BN-57: individual leave decision."""
        leave_request = self.get_object()
        if leave_request.status not in services.CONSUMED_STATUSES:
            return Response({"detail": "The leave is not approved."}, status=400)
        issued = issue_document(
            "LEAVE_DECISION",
            self._context(leave_request),
            employee=leave_request.employee,
            user=request.user,
        )
        return _pdf(issued)

    @action(detail=True, methods=["get"])
    def print_certificate(self, request, pk=None):
        """BN-57: leave certificate."""
        leave_request = self.get_object()
        if leave_request.status not in services.CONSUMED_STATUSES:
            return Response({"detail": "The leave is not approved."}, status=400)
        issued = issue_document(
            "LEAVE_CERTIFICATE",
            self._context(leave_request),
            employee=leave_request.employee,
            user=request.user,
        )
        return _pdf(issued)

    @action(detail=False, methods=["get"])
    def print_balance(self, request):
        """BN-57: summary of the balance with the detail of the leaves taken."""
        employee = self._owner(request.query_params.get("employee"))
        year = int(request.query_params.get("year", timezone.now().year))
        leaves = LeaveRequest.objects.filter(
            employee=employee,
            start_date__year=year,
            status__in=services.CONSUMED_STATUSES,
        ).select_related("leave_type")
        issued = issue_document(
            "LEAVE_BALANCE",
            {
                "employee": employee,
                "year": year,
                "balance": services.balance(employee, year),
                "leaves": leaves,
            },
            employee=employee,
            user=request.user,
        )
        return _pdf(issued)
