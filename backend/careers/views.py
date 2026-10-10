import datetime

from django.http import HttpResponse
from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from core.pdf import render_pdf
from documents.services import issue_document
from employees.models import Employee
from users.permissions import (
    ModulePermission,
    can_view_salary,
    has_module_permission,
    scope_employees,
)
from users.utils import log_audit_action

from . import services
from .models import CareerAct

DECISION_TEMPLATES = {
    "PROMOTION": "PROMOTION_DECISION",
    "TRANSFER": "TRANSFER_DECISION",
    "SALARY_REVISION": "SALARY_REVISION_DECISION",
    "TEMPORARY_ASSIGNMENT": "ASSIGNMENT_DECISION",
    "ACTING": "ASSIGNMENT_DECISION",
    "SECONDMENT": "ASSIGNMENT_DECISION",
    "DISCIPLINARY": "DISCIPLINARY_LETTER",
    "DEPARTURE": "WORK_CERTIFICATE",
}


class CareerActSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    act_type_label = serializers.CharField(
        source="get_act_type_display", read_only=True
    )
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    new_position_title = serializers.CharField(
        source="new_position.title", read_only=True
    )
    new_department_name = serializers.CharField(
        source="new_department.name", read_only=True
    )
    new_workplace_name = serializers.CharField(
        source="new_workplace.name", read_only=True
    )
    new_classification_label = serializers.CharField(
        source="new_classification.__str__", read_only=True
    )
    affects_payroll = serializers.BooleanField(read_only=True)

    class Meta:
        model = CareerAct
        fields = "__all__"
        read_only_fields = (
            "status",
            "previous_situation",
            "applied_at",
            "batch",
            "decision_comment",
            "created_by",
        )

    def validate(self, attrs):
        if self.instance is not None and self.instance.status not in (
            "DRAFT",
            "MODIFICATION",
        ):
            raise serializers.ValidationError(
                "A submitted act cannot be modified; cancel it instead."
            )
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        if request is not None and not can_view_salary(request.user, instance.employee):
            for key in ("new_base_salary", "increase_percent", "bonus_value"):
                data[key] = None
            data["previous_situation"] = {
                k: v
                for k, v in (data["previous_situation"] or {}).items()
                if k != "base_salary"
            }
        return data


class CareerActViewSet(viewsets.ModelViewSet):
    """BN-68 → BN-76."""

    serializer_class = CareerActSerializer
    permission_classes = [ModulePermission]
    permission_module = "careers"
    action_permissions = {
        "submit": "create",
        "cancel": "create",
        "print_decision": "print",
        "general_increase": "validate",
        "timeline": "consult",
    }
    filterset_fields = {
        "employee": ["exact"],
        "act_type": ["exact"],
        "status": ["exact"],
        "effective_date": ["gte", "lte"],
    }
    search_fields = (
        "employee__surname",
        "employee__given_names",
        "employee__matriculation_number",
        "reason",
    )

    def get_queryset(self):
        return scope_employees(
            self.request.user,
            CareerAct.objects.select_related(
                "employee",
                "new_position",
                "new_department",
                "new_workplace",
                "new_classification",
            ),
            "employee__",
        )

    def perform_create(self, serializer):
        employee = serializer.validated_data["employee"]
        if not scope_employees(
            self.request.user, Employee.objects.filter(pk=employee.pk)
        ).exists():
            raise PermissionDenied("This employee is outside your perimeter.")
        act = serializer.save(created_by=self.request.user)
        try:
            services.validate_act(act)
        except services.CareerError as exc:
            act.delete()
            raise serializers.ValidationError({"detail": str(exc)})
        if self.request.data.get("submit") in (True, "true", "1"):
            self._submit(act)

    def perform_destroy(self, instance):
        if instance.status not in ("DRAFT",):
            raise serializers.ValidationError(
                {"detail": "Only a draft can be deleted; cancel it instead."}
            )
        instance.delete()

    def _submit(self, act):
        try:
            services.submit(act, self.request.user)
        except (services.CareerError, Exception) as exc:
            if isinstance(exc, (PermissionDenied,)):
                raise
            raise serializers.ValidationError({"detail": str(exc)})
        log_audit_action(self.request.user, f"Submitted {act}", "Careers", self.request)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        act = self.get_object()
        self._submit(act)
        act.refresh_from_db()
        return Response(self.get_serializer(act).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        from notifications.services import pending_tasks

        act = self.get_object()
        if act.status in ("APPLIED", "ENDED"):
            return Response(
                {"detail": "An applied act is corrected by a new act."}, status=400
            )
        pending_tasks(act).update(status="CANCELLED")
        act.status = "CANCELLED"
        act.save(update_fields=["status"])
        return Response(self.get_serializer(act).data)

    @action(detail=True, methods=["get"])
    def print_decision(self, request, pk=None):
        """BN-75: decision document from the configurable template."""
        act = self.get_object()
        code = DECISION_TEMPLATES[act.act_type]
        context = {
            "employee": act.employee,
            "act": act,
            "subject": f"{act.get_act_type_display()}: {act.reason}",
            "details": _details(act, can_view_salary(request.user, act.employee)),
            "effective_date": act.effective_date,
        }
        if code == "WORK_CERTIFICATE":
            contracts = list(
                act.employee.contracts.exclude(status="DRAFT").order_by("start_date")
            )
            context.update(
                {
                    "start_date": (
                        contracts[0].start_date
                        if contracts
                        else act.employee.date_of_hire
                    ),
                    "end_date": act.effective_date,
                    "position": (
                        act.employee.position.title if act.employee.position else ""
                    ),
                }
            )
        issued = issue_document(
            code,
            context,
            employee=act.employee,
            user=request.user,
            title=f"{act.get_act_type_display()} decision",
        )
        response = HttpResponse(issued.file.read(), content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{issued.reference}.pdf"'
        return response

    @action(detail=False, methods=["get"], url_path=r"timeline/(?P<employee_id>\d+)")
    def timeline(self, request, employee_id=None):
        employee = (
            scope_employees(request.user, Employee.objects.all())
            .filter(pk=employee_id)
            .first()
        )
        if employee is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(services.timeline(employee))

    @action(detail=False, methods=["post"])
    def general_increase(self, request):
        """BN-71: general increase of a population."""
        try:
            percent = serializers.DecimalField(
                max_digits=6, decimal_places=2
            ).to_internal_value(request.data.get("increase_percent"))
            effective = datetime.date.fromisoformat(request.data["effective_date"])
            reason = request.data.get("reason") or "General increase"
        except (KeyError, ValueError, serializers.ValidationError):
            return Response(
                {"detail": "increase_percent and effective_date are required."},
                status=400,
            )
        batch, acts = services.general_increase(
            request.user,
            percent,
            effective,
            reason,
            request.data.get("department"),
            request.data.get("classification"),
        )
        log_audit_action(
            request.user,
            f"General increase {percent}% ({len(acts)} employees)",
            "Careers",
            request,
        )
        return Response({"batch": batch, "count": len(acts)}, status=201)


def _details(act, show_salary):
    parts = []
    if act.new_position_id:
        parts.append(f"New position: {act.new_position.title}.")
    if act.new_classification_id:
        parts.append(f"New category / grade: {act.new_classification}.")
    if act.new_department_id:
        parts.append(f"Assigned to: {act.new_department.name}.")
    if act.new_workplace_id:
        parts.append(f"Workplace: {act.new_workplace.name}.")
    if show_salary and act.new_base_salary is not None:
        parts.append(f"New monthly base salary: {act.new_base_salary}.")
    if show_salary and act.increase_percent is not None:
        parts.append(f"Salary increase: {act.increase_percent} %.")
    if act.end_date:
        parts.append(
            f"Until {act.end_date:%d/%m/%Y}, with return to the original situation."
        )
    if act.disciplinary_measure:
        parts.append(
            f"Measure: {act.get_disciplinary_measure_display()}"
            + (f" of {act.suspension_days} day(s)." if act.suspension_days else ".")
        )
    if act.decision_reference:
        parts.append(f"Decision reference: {act.decision_reference}.")
    return "\n".join(parts)


def _render_nodes(nodes, depth=0):
    html = ""
    for node in nodes:
        indent = depth * 18
        html += (
            f'<p style="margin:2pt 0 2pt {indent}pt"><b>{node["name"]}</b> ({node["code"]}) – '
            f'{node.get("manager_name") or "no manager"} – {node.get("headcount", 0)} employee(s)</p>'
        )
        html += _render_nodes(node["children"], depth + 1)
    return html


class OrgChartView(APIView):
    """BN-07: organisation chart, now or at a past date (BN-06), JSON or PDF."""

    permission_classes = [ModulePermission]
    permission_module = "organisation"

    def get(self, request):
        day = request.query_params.get("date")
        day = datetime.date.fromisoformat(day) if day else None
        if request.query_params.get("unit"):
            nodes = _find(services.org_chart(day), int(request.query_params["unit"]))
        else:
            nodes = services.org_chart(day)
        if request.query_params.get("file_format") == "pdf":
            from django.utils.html import escape

            label = (
                f"Structure at {day:%d/%m/%Y}"
                if day
                else f"Structure on {timezone.now().date():%d/%m/%Y}"
            )
            body = (
                f"<h1>Organisation chart</h1><p class='muted'>{escape(label)}</p>"
                + _render_nodes(nodes)
            )
            pdf = render_pdf(body, {}, footer_text="Organisation chart")
            response = HttpResponse(pdf, content_type="application/pdf")
            response["Content-Disposition"] = 'inline; filename="org-chart.pdf"'
            return response
        return Response(nodes)


def _find(nodes, unit_id):
    for node in nodes:
        if node["id"] == unit_id:
            return [node]
        found = _find(node["children"], unit_id)
        if found:
            return found
    return []


class StructureHistoryView(APIView):
    """BN-06: history of the modifications of a unit."""

    permission_classes = [ModulePermission]
    permission_module = "organisation"

    def get(self, request, department_id):
        from .models import DepartmentVersion

        if not has_module_permission(request.user, "organisation", "consult"):
            raise PermissionDenied()
        versions = DepartmentVersion.objects.filter(
            department_ref=department_id
        ).select_related("parent", "site", "manager", "cost_centre", "recorded_by")
        return Response(
            [
                {
                    "effective_from": v.effective_from,
                    "name": v.name,
                    "code": v.code,
                    "unit_type": v.unit_type,
                    "parent": v.parent.name if v.parent else "",
                    "site": v.site.name if v.site else "",
                    "manager": v.manager.get_full_name() if v.manager else "",
                    "cost_centre": v.cost_centre.name if v.cost_centre else "",
                    "deleted": v.is_deleted,
                    "recorded_by": v.recorded_by.username if v.recorded_by else "",
                    "recorded_at": v.recorded_at,
                }
                for v in versions
            ]
        )
