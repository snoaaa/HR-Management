import datetime

from django.http import HttpResponse
from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from core.pdf import render_pdf
from employees.models import Employee
from notifications.services import start_approval
from users.permissions import (
    is_admin,
    ORGANISATION_SCOPE_ROLES,
    ModulePermission,
    managed_department_ids,
    scope_employees,
)
from users.utils import log_audit_action

from . import services
from .models import Shift, ShiftSwapRequest, Timetable, TimetableEntry


class ShiftSerializer(serializers.ModelSerializer):
    duration_minutes = serializers.IntegerField(read_only=True)

    class Meta:
        model = Shift
        fields = "__all__"


class TimetableSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)
    entries_count = serializers.IntegerField(source="entries.count", read_only=True)

    class Meta:
        model = Timetable
        fields = "__all__"
        read_only_fields = ("status", "published_at", "created_by")

    def validate(self, attrs):
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start and end and end < start:
            raise serializers.ValidationError("The end date is before the start date.")
        if start and end and (end - start).days > 62:
            raise serializers.ValidationError("A timetable covers at most two months.")
        return attrs


class TimetableEntrySerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    shift_name = serializers.CharField(source="shift.name", read_only=True)
    shift_color = serializers.CharField(source="shift.color", read_only=True)
    start_time = serializers.TimeField(source="shift.start_time", read_only=True)
    end_time = serializers.TimeField(source="shift.end_time", read_only=True)
    timetable_name = serializers.CharField(source="timetable.name", read_only=True)

    class Meta:
        model = TimetableEntry
        fields = "__all__"


class ShiftSwapSerializer(serializers.ModelSerializer):
    entry_detail = TimetableEntrySerializer(source="entry", read_only=True)
    replacement_name = serializers.CharField(
        source="replacement.full_name", read_only=True
    )

    class Meta:
        model = ShiftSwapRequest
        fields = "__all__"
        read_only_fields = ("status", "decision_comment", "created_by")


def _allowed_departments(user):
    if is_admin(user) or user.role in ORGANISATION_SCOPE_ROLES:
        return None
    return managed_department_ids(user)


class ShiftViewSet(viewsets.ModelViewSet):
    search_fields = ("name", "code")
    queryset = Shift.objects.all()
    serializer_class = ShiftSerializer
    permission_classes = [ModulePermission]
    permission_module = "planning"
    action_permissions = {"create": "modify"}


TIMETABLE_PRINT = """
<h1>{{ timetable.name }}</h1>
<p class="muted">{{ timetable.department.name }} – {{ timetable.start_date|date:"d/m/Y" }} to
{{ timetable.end_date|date:"d/m/Y" }}{% if timetable.status == "DRAFT" %} – DRAFT{% endif %}</p>
<table><thead><tr><th>Employee</th>{% for day in days %}<th>{{ day|date:"D d/m" }}</th>{% endfor %}</tr></thead>
<tbody>{% for row in rows %}<tr><td>{{ row.employee }}</td>
{% for cell in row.cells %}<td>{% for s in cell %}{{ s.code }}<br/>{% endfor %}</td>{% endfor %}</tr>
{% endfor %}</tbody></table>
<h2>Shifts</h2>
<table class="no-border">{% for shift in shifts %}<tr><td width="15%"><b>{{ shift.code }}</b></td>
<td>{{ shift.name }} {{ shift.start_time|time:"H:i" }}–{{ shift.end_time|time:"H:i" }}</td></tr>{% endfor %}</table>
"""


class TimetableViewSet(viewsets.ModelViewSet):
    """BN-62 → BN-67."""

    search_fields = ("name", "department__name")
    serializer_class = TimetableSerializer
    permission_classes = [ModulePermission]
    permission_module = "planning"
    action_permissions = {
        "create": "modify",
        "grid": "consult",
        "entries": "modify",
        "conflicts": "consult",
        "publish": "validate",
        "duplicate": "modify",
        "print_timetable": "print",
        "comparison": "consult",
    }
    filterset_fields = ("department", "status")

    def get_queryset(self):
        queryset = Timetable.objects.select_related("department")
        allowed = _allowed_departments(self.request.user)
        if allowed is None:
            return queryset
        employee = Employee.objects.filter(user=self.request.user).first()
        own = {employee.department_id} if employee and employee.department_id else set()
        return queryset.filter(department_id__in=allowed | own)

    def _check_department(self, department_id):
        allowed = _allowed_departments(self.request.user)
        if allowed is not None and department_id not in allowed:
            raise PermissionDenied("You can only plan the teams you manage.")

    def perform_create(self, serializer):
        self._check_department(serializer.validated_data["department"].id)
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        self._check_department(serializer.instance.department_id)
        serializer.save()

    @action(detail=True, methods=["get"])
    def grid(self, request, pk=None):
        timetable = self.get_object()
        return Response(
            {
                **services.grid(timetable),
                "conflicts": services.timetable_conflicts(timetable),
            }
        )

    @action(detail=True, methods=["post", "delete"])
    def entries(self, request, pk=None):
        """Add (POST) or remove (DELETE ?entry=) an assignment."""
        timetable = self.get_object()
        self._check_department(timetable.department_id)
        if request.method == "DELETE":
            entry = timetable.entries.filter(
                pk=request.query_params.get("entry")
            ).first()
            if entry is None:
                return Response(status=status.HTTP_404_NOT_FOUND)
            employee, day = entry.employee, entry.date
            entry.delete()
            if timetable.status == "PUBLISHED" and day <= timezone.now().date():
                from attendance.services import compute_day

                compute_day(employee, day)
            return Response(status=status.HTTP_204_NO_CONTENT)
        try:
            employee = Employee.objects.get(pk=request.data["employee"])
            shift = Shift.objects.get(pk=request.data["shift"])
            day = datetime.date.fromisoformat(request.data["date"])
            entry, warnings = services.add_entry(
                timetable, employee, day, shift, force=bool(request.data.get("force"))
            )
        except (KeyError, ValueError, Employee.DoesNotExist, Shift.DoesNotExist):
            return Response(
                {"detail": "employee, shift and date are required."}, status=400
            )
        except services.PlanningError as exc:
            return Response({"detail": str(exc), "conflict": True}, status=400)
        return Response(
            {"entry": TimetableEntrySerializer(entry).data, "warnings": warnings},
            status=201,
        )

    @action(detail=True, methods=["get"])
    def conflicts(self, request, pk=None):
        return Response(services.timetable_conflicts(self.get_object()))

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        timetable = self.get_object()
        self._check_department(timetable.department_id)
        try:
            services.publish(timetable, request.user)
        except services.PlanningError as exc:
            return Response({"detail": str(exc)}, status=400)
        log_audit_action(
            user=request.user,
            action=f"Published timetable {timetable.name}",
            module="Planning",
            request=request,
        )
        return Response(self.get_serializer(timetable).data)

    @action(detail=True, methods=["post"])
    def duplicate(self, request, pk=None):
        timetable = self.get_object()
        self._check_department(timetable.department_id)
        try:
            new_start = datetime.date.fromisoformat(request.data["start_date"])
        except (KeyError, ValueError):
            return Response({"detail": "start_date is required."}, status=400)
        copy = services.duplicate(
            timetable, new_start, request.user, request.data.get("name")
        )
        return Response(self.get_serializer(copy).data, status=201)

    @action(detail=True, methods=["get"])
    def print_timetable(self, request, pk=None):
        """BN-64: print per team, or per employee with ?employee=."""
        timetable = self.get_object()
        data = services.grid(timetable)
        if request.query_params.get("employee"):
            data["rows"] = [
                r
                for r in data["rows"]
                if str(r["employee_id"]) == request.query_params["employee"]
            ]
        days = [datetime.date.fromisoformat(d) for d in data["days"]]
        rows = [
            {
                "employee": r["employee"],
                "cells": [r["cells"].get(d.isoformat(), []) for d in days],
            }
            for r in data["rows"]
        ]
        shifts = Shift.objects.filter(timetableentry__timetable=timetable).distinct()
        pdf = render_pdf(
            TIMETABLE_PRINT,
            {"timetable": timetable, "days": days, "rows": rows, "shifts": shifts},
            footer_text=timetable.name,
            landscape=True,
        )
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'inline; filename="timetable-{timetable.id}.pdf"'
        )
        return response

    @action(detail=True, methods=["get"])
    def comparison(self, request, pk=None):
        """BN-67: planned vs actual."""
        return Response(services.planned_vs_actual(self.get_object()))


class TimetableEntryViewSet(viewsets.ReadOnlyModelViewSet):
    """Published shifts visible to the employees (BN-151)."""

    serializer_class = TimetableEntrySerializer
    permission_classes = [ModulePermission]
    permission_module = "planning"
    filterset_fields = {
        "employee": ["exact"],
        "date": ["gte", "lte"],
        "timetable": ["exact"],
    }

    def get_queryset(self):
        return scope_employees(
            self.request.user,
            TimetableEntry.objects.filter(timetable__status="PUBLISHED").select_related(
                "employee", "shift", "timetable"
            ),
            "employee__",
        )


class ShiftSwapViewSet(viewsets.ModelViewSet):
    serializer_class = ShiftSwapSerializer
    permission_classes = [ModulePermission]
    permission_module = "planning"
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return scope_employees(
            self.request.user,
            ShiftSwapRequest.objects.select_related(
                "entry__employee", "entry__shift", "replacement"
            ),
            "entry__employee__",
        )

    def perform_create(self, serializer):
        entry = serializer.validated_data["entry"]
        user = self.request.user
        if entry.employee.user_id != user.id and _allowed_departments(user) is not None:
            if entry.timetable.department_id not in managed_department_ids(user):
                raise PermissionDenied("You can only exchange your own shifts.")
        if entry.date < timezone.now().date():
            raise ValidationError({"detail": "A past shift cannot be exchanged."})
        swap = serializer.save(created_by=user)
        start_approval(swap, "SHIFT_SWAP", user)
