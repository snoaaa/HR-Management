import datetime

from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.exports import export_rows
from employees.models import Employee
from notifications.services import line_manager_of, start_approval
from users.permissions import ModulePermission, has_module_permission, scope_employees
from users.utils import log_audit_action

from . import services
from .models import (
    AttendancePeriod,
    Clocking,
    ClockingRegularisation,
    DailyAttendance,
    Mission,
    PublicHoliday,
    ScheduleAssignment,
    ScheduleException,
    WorkingCalendar,
    WorkSchedule,
)
from .serializers import (
    AttendancePeriodSerializer,
    ClockingRegularisationSerializer,
    ClockingSerializer,
    DailyAttendanceSerializer,
    MissionSerializer,
    PublicHolidaySerializer,
    ScheduleAssignmentSerializer,
    ScheduleExceptionSerializer,
    WorkingCalendarSerializer,
    WorkScheduleSerializer,
)


def _date_param(request, name, default=None):
    value = request.query_params.get(name)
    if not value:
        return default
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        raise ValidationError({name: "Use the format YYYY-MM-DD."})


def _own_employee(user):
    employee = Employee.objects.filter(user=user).first()
    if employee is None:
        raise ValidationError(
            {"detail": "No employee record is linked to this account."}
        )
    return employee


def _is_hr(user):
    return has_module_permission(user, "attendance", "modify")


def _scoped_employee(user, employee_id):
    employee = (
        scope_employees(user, Employee.objects.all()).filter(pk=employee_id).first()
    )
    if employee is None:
        raise PermissionDenied("This employee is outside your perimeter.")
    return employee


class CalendarViewSet(viewsets.ModelViewSet):
    """BN-61 / BN-08: working calendar per site."""

    queryset = WorkingCalendar.objects.select_related("site")
    serializer_class = WorkingCalendarSerializer
    permission_classes = [ModulePermission]
    permission_module = "organisation"


class PublicHolidayViewSet(viewsets.ModelViewSet):
    queryset = PublicHoliday.objects.select_related("site")
    serializer_class = PublicHolidaySerializer
    permission_classes = [ModulePermission]
    permission_module = "organisation"
    filterset_fields = ("site", "recurring")


class WorkScheduleViewSet(viewsets.ModelViewSet):
    """BN-59: work schedule models."""

    queryset = WorkSchedule.objects.prefetch_related("days")
    serializer_class = WorkScheduleSerializer
    permission_classes = [ModulePermission]
    permission_module = "planning"


class ScheduleAssignmentViewSet(viewsets.ModelViewSet):
    """BN-60: assignment of a schedule with an effective date."""

    queryset = ScheduleAssignment.objects.select_related(
        "schedule", "employee", "position", "department", "site"
    )
    serializer_class = ScheduleAssignmentSerializer
    permission_classes = [ModulePermission]
    permission_module = "planning"
    filterset_fields = ("schedule", "employee", "position", "department", "site")


class ScheduleExceptionViewSet(viewsets.ModelViewSet):
    serializer_class = ScheduleExceptionSerializer
    permission_classes = [ModulePermission]
    permission_module = "planning"
    filterset_fields = ("employee", "date")

    def get_queryset(self):
        return scope_employees(
            self.request.user,
            ScheduleException.objects.select_related("employee"),
            "employee__",
        )

    def perform_create(self, serializer):
        exception = serializer.save()
        services.compute_day(exception.employee, exception.date)


class ClockingViewSet(viewsets.ModelViewSet):
    """BN-36 / BN-37: entries and exits."""

    serializer_class = ClockingSerializer
    permission_classes = [ModulePermission]
    permission_module = "attendance"
    action_permissions = {
        "clock": "consult",
        "import_file": "modify",
        "mine": "consult",
    }
    filterset_fields = {
        "employee": ["exact"],
        "date": ["exact", "gte", "lte"],
        "is_active": ["exact"],
    }

    def get_queryset(self):
        return scope_employees(
            self.request.user,
            Clocking.objects.select_related("employee"),
            "employee__",
        )

    def perform_create(self, serializer):
        # Manual entry is reserved to HR; employees use /clock/ (BN-37).
        if not _is_hr(self.request.user):
            raise PermissionDenied(
                "Use the clock-in button or a regularisation request."
            )
        data = serializer.validated_data
        try:
            services.validate_clocking(
                data["employee"], data["date"], data["time_in"], data.get("time_out")
            )
        except services.AttendanceError as exc:
            raise ValidationError({"detail": str(exc)})
        clocking = serializer.save(source="MANUAL", created_by=self.request.user)
        services.compute_day(clocking.employee, clocking.date)

    def perform_update(self, serializer):
        if not _is_hr(self.request.user):
            raise PermissionDenied()
        instance = serializer.instance
        data = serializer.validated_data
        try:
            services.validate_clocking(
                instance.employee,
                data.get("date", instance.date),
                data.get("time_in", instance.time_in),
                data.get("time_out", instance.time_out),
                exclude_id=instance.id,
            )
        except services.AttendanceError as exc:
            raise ValidationError({"detail": str(exc)})
        previous = f"{instance.time_in}-{instance.time_out}"
        clocking = serializer.save()
        log_audit_action(
            user=self.request.user,
            action=f"Modified clocking of {clocking.employee.full_name} on {clocking.date}",
            module="Attendance",
            request=self.request,
            details={
                "previous_value": previous,
                "new_value": f"{clocking.time_in}-{clocking.time_out}",
            },
        )
        services.compute_day(clocking.employee, clocking.date)

    def perform_destroy(self, instance):
        # The original record stays visible (BN-44): it is deactivated.
        try:
            services.check_not_locked(instance.date)
        except services.AttendanceError as exc:
            raise ValidationError({"detail": str(exc)})
        instance.is_active = False
        instance.save(update_fields=["is_active"])
        services.compute_day(instance.employee, instance.date)

    @action(detail=False, methods=["post"])
    def clock(self, request):
        """BN-37: the employee clocks in or out."""
        employee = _own_employee(request.user)
        try:
            clocking = services.self_clock(employee, request.user)
        except services.AttendanceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ClockingSerializer(clocking).data)

    @action(detail=False, methods=["get"])
    def mine(self, request):
        employee = _own_employee(request.user)
        today = timezone.now().date()
        clockings = Clocking.objects.filter(
            employee=employee, date=today, is_active=True
        )
        return Response(
            {
                "clockings": ClockingSerializer(clockings, many=True).data,
                "is_in": clockings.filter(time_out__isnull=True).exists(),
            }
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="import",
        parser_classes=[MultiPartParser, FormParser],
    )
    def import_file(self, request):
        """BN-37 / BN-180: import of a badge or biometric file."""
        upload = request.FILES.get("file")
        if upload is None:
            return Response(
                {
                    "detail": "Send the file in the 'file' field.",
                    "format": services.IMPORT_FORMAT,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        report = services.import_clockings(upload.read(), request.user)
        log_audit_action(
            user=request.user,
            action=f"Imported clockings ({report['imported']} lines, {len(report['rejected'])} rejected)",
            module="Attendance",
            request=request,
        )
        return Response(report)


class RegularisationViewSet(viewsets.ModelViewSet):
    """BN-44: request to correct a clocking, approved by the line manager."""

    serializer_class = ClockingRegularisationSerializer
    permission_classes = [ModulePermission]
    permission_module = "attendance"
    action_permissions = {"create": "consult"}
    http_method_names = ["get", "post", "head", "options"]
    filterset_fields = ("employee", "status")

    def get_queryset(self):
        return scope_employees(
            self.request.user,
            ClockingRegularisation.objects.select_related("employee"),
            "employee__",
        )

    def perform_create(self, serializer):
        user = self.request.user
        employee = serializer.validated_data["employee"]
        if not _is_hr(user) and employee.user_id != user.id:
            raise PermissionDenied("You can only regularise your own clockings.")
        try:
            services.check_not_locked(serializer.validated_data["date"])
        except services.AttendanceError as exc:
            raise ValidationError({"detail": str(exc)})
        regularisation = serializer.save(created_by=user)
        start_approval(regularisation, "CLOCKING_REGULARISATION", user)


class MissionViewSet(viewsets.ModelViewSet):
    """BN-43: missions and field work."""

    serializer_class = MissionSerializer
    permission_classes = [ModulePermission]
    permission_module = "attendance"
    action_permissions = {"create": "modify"}
    filterset_fields = ("employee",)

    def get_queryset(self):
        return scope_employees(
            self.request.user, Mission.objects.select_related("employee"), "employee__"
        )

    def perform_create(self, serializer):
        mission = serializer.save(created_by=self.request.user)
        services.recompute(mission.employee, mission.start_date, mission.end_date)


class DailyAttendanceViewSet(viewsets.ReadOnlyModelViewSet):
    """BN-38 / BN-40 / BN-41: computed days, overtime approval, absences."""

    serializer_class = DailyAttendanceSerializer
    permission_classes = [ModulePermission]
    permission_module = "attendance"
    action_permissions = {
        "recompute": "modify",
        "decide_overtime": "validate",
        "justify": "modify",
    }
    filterset_fields = {
        "employee": ["exact"],
        "employee__department": ["exact"],
        "date": ["exact", "gte", "lte"],
        "status": ["exact"],
        "overtime_status": ["exact"],
        "absence_justified": ["exact"],
    }

    def get_queryset(self):
        return scope_employees(
            self.request.user,
            DailyAttendance.objects.select_related("employee"),
            "employee__",
        ).order_by("-date", "employee__surname")

    @action(detail=False, methods=["post"])
    def recompute(self, request):
        start = datetime.date.fromisoformat(request.data["start"])
        end = datetime.date.fromisoformat(
            request.data.get("end") or request.data["start"]
        )
        employee_ids = request.data.get("employees")
        employees = scope_employees(
            request.user, Employee.objects.exclude(status="ARCHIVED")
        )
        if employee_ids:
            employees = employees.filter(pk__in=employee_ids)
        count = 0
        for employee in employees:
            count += len(services.recompute(employee, start, end))
        return Response({"computed_days": count})

    @action(detail=False, methods=["post"])
    def decide_overtime(self, request):
        """BN-40: the line manager (or HR) approves or refuses overtime."""
        decision = request.data.get("decision")
        if decision not in ("APPROVED", "REFUSED"):
            return Response(
                {"detail": "decision must be APPROVED or REFUSED."}, status=400
            )
        records = self.get_queryset().filter(
            pk__in=request.data.get("ids", []), overtime_status="PENDING"
        )
        decided = 0
        for record in records:
            if (
                not _is_hr(request.user)
                and line_manager_of(record.employee) != request.user
            ):
                continue
            if services.period_locked(record.date):
                continue
            record.overtime_status = decision
            record.overtime_decided_by = request.user
            record.save(update_fields=["overtime_status", "overtime_decided_by"])
            decided += 1
        log_audit_action(
            user=request.user,
            action=f"{decision} overtime on {decided} day(s)",
            module="Attendance",
            request=request,
            details={"ids": request.data.get("ids", [])},
        )
        return Response({"decided": decided})

    @action(detail=True, methods=["post"])
    def justify(self, request, pk=None):
        """BN-41: qualify an absence as justified (no payroll deduction)."""
        record = self.get_object()
        if services.period_locked(record.date):
            return Response({"detail": "The period is locked."}, status=400)
        if record.status != "ABSENT":
            return Response({"detail": "Only an absence can be justified."}, status=400)
        record.absence_justified = bool(request.data.get("justified", True))
        record.absence_justification = request.data.get("justification", "")
        record.save(update_fields=["absence_justified", "absence_justification"])
        log_audit_action(
            user=request.user,
            action=f"Qualified absence of {record.employee.full_name} on {record.date}",
            module="Attendance",
            request=request,
            details={
                "justified": record.absence_justified,
                "reason": record.absence_justification,
            },
        )
        return Response(DailyAttendanceSerializer(record).data)


class AttendancePeriodViewSet(viewsets.ReadOnlyModelViewSet):
    """BN-45: consolidation and locking of a month."""

    queryset = AttendancePeriod.objects.all()
    serializer_class = AttendancePeriodSerializer
    permission_classes = [ModulePermission]
    permission_module = "attendance"
    action_permissions = {"consolidate": "validate"}

    @action(detail=False, methods=["post"])
    def consolidate(self, request):
        try:
            year, month = int(request.data["year"]), int(request.data["month"])
            period = services.consolidate_period(year, month, request.user)
        except (KeyError, ValueError):
            return Response({"detail": "year and month are required."}, status=400)
        except services.AttendanceError as exc:
            return Response({"detail": str(exc)}, status=400)
        log_audit_action(
            user=request.user,
            action=f"Consolidated attendance {month:02d}/{year}",
            module="Attendance",
            request=request,
        )
        return Response(AttendancePeriodSerializer(period).data)


class AttendanceSheetView(APIView):
    """BN-42: attendance sheet per employee, team or department."""

    permission_classes = [ModulePermission]
    permission_module = "attendance"

    COLUMNS = [
        ("Employee", "employee"),
        ("Matriculation", "matriculation"),
        ("Department", "department"),
        ("Period", "period"),
        ("Status", "status"),
        ("Expected (h)", "expected_hours"),
        ("Worked (h)", "worked_hours"),
        ("Late (min)", "late_minutes"),
        ("Early departure (min)", "early_departure_minutes"),
        ("Missing (h)", "missing_hours"),
        ("Overtime (h)", "overtime_hours"),
        ("Absent days", "absent_days"),
        ("Unjustified", "unjustified_absent_days"),
        ("Leave days", "leave_days"),
    ]

    def get(self, request):
        today = timezone.now().date()
        start = _date_param(request, "start", today.replace(day=1))
        end = _date_param(request, "end", today)
        granularity = request.query_params.get("granularity", "daily")
        employees = scope_employees(
            request.user, Employee.objects.exclude(status="ARCHIVED")
        )
        if request.query_params.get("department"):
            employees = employees.filter(
                department_id=request.query_params["department"]
            )
        if request.query_params.get("employee"):
            employees = employees.filter(pk=request.query_params["employee"])
        rows = services.attendance_sheet(employees, start, end, granularity)
        fmt = request.query_params.get("file_format")
        if fmt:
            if (
                not has_module_permission(request.user, "attendance", "export")
                and fmt != "pdf"
            ):
                raise PermissionDenied()
            return export_rows(
                [title for title, _ in self.COLUMNS],
                [[row[key] for _, key in self.COLUMNS] for row in rows],
                f"attendance-{start}-{end}",
                fmt,
                title=f"Attendance sheet {start:%d/%m/%Y} – {end:%d/%m/%Y}",
            )
        return Response(rows)
