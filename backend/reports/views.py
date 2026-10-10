import datetime

from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from core.exports import export_rows
from users.permissions import ModulePermission, has_module_permission

from . import services
from .models import ReportSchedule, SavedReport

FILTER_KEYS = ("department", "site", "category", "contract_type")


def _filters(request):
    return {
        k: request.query_params.get(k)
        for k in FILTER_KEYS
        if request.query_params.get(k)
    }


def _period(request):
    today = timezone.now().date()
    try:
        start = datetime.date.fromisoformat(
            request.query_params.get("start") or f"{today.year}-01-01"
        )
        end = datetime.date.fromisoformat(request.query_params.get("end") or str(today))
    except ValueError:
        start, end = datetime.date(today.year, 1, 1), today
    return start, end


def _export(request, title, rows, columns):
    fmt = request.query_params.get("file_format")
    if not fmt:
        return None
    if not has_module_permission(request.user, "reports", "export") and fmt != "pdf":
        raise PermissionDenied()
    return export_rows(
        [c[1] for c in columns],
        [[row.get(c[0]) for c in columns] for row in rows],
        title.lower().replace(" ", "-"),
        fmt,
        title=title,
    )


class DashboardView(APIView):
    """BN-155: dashboard adapted to the profile of the user."""

    permission_classes = [ModulePermission]
    permission_module = "reports"

    def get(self, request):
        return Response(services.dashboard(request.user))


class IndicatorView(APIView):
    """BN-156 → BN-160: indicators with filters, export and print."""

    permission_classes = [ModulePermission]
    permission_module = "reports"

    def get(self, request, kind):
        filters = _filters(request)
        start, end = _period(request)
        if kind == "headcount":
            data = services.headcount(request.user, filters, end)
            group = request.query_params.get("group", "department")
            export = _export(
                request,
                f"Headcount by {group}",
                data.get(f"by_{group}", []),
                [("label", group.capitalize()), ("value", "Employees")],
            )
        elif kind == "movements":
            data = services.movements(request.user, filters, start, end)
            export = _export(
                request,
                "HR movements",
                data["series"],
                [
                    ("month", "Month"),
                    ("hires", "Hires"),
                    ("departures", "Departures"),
                    ("promotions", "Promotions"),
                    ("transfers", "Transfers"),
                ],
            )
        elif kind == "time":
            data = services.time_indicators(request.user, filters, start, end)
            export = _export(
                request,
                "Time indicators",
                [{"k": k, "v": v} for k, v in data.items()],
                [("k", "Indicator"), ("v", "Value")],
            )
        elif kind == "payroll":
            if not services.can_see_payroll_indicators(request.user):
                raise PermissionDenied(
                    "Payroll indicators are reserved to HR, payroll and management."
                )
            data = services.payroll_indicators(request.user, filters, start, end)
            export = _export(
                request,
                "Payroll cost",
                data["by_month"],
                [("label", "Month"), ("value", "Cost")],
            )
        else:
            return Response({"detail": "Unknown indicator."}, status=404)
        return export or Response(data)


class SavedReportSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source="owner.username", read_only=True)

    class Meta:
        model = SavedReport
        fields = "__all__"
        read_only_fields = ("owner",)

    def validate(self, attrs):
        dataset = attrs.get("dataset", getattr(self.instance, "dataset", None))
        allowed = services.DATASET_FIELDS.get(dataset, {})
        unknown = [f for f in attrs.get("fields", []) if f not in allowed]
        if unknown:
            raise serializers.ValidationError(f"Unknown fields: {', '.join(unknown)}")
        return attrs


class ReportScheduleSerializer(serializers.ModelSerializer):
    report_name = serializers.CharField(source="report.name", read_only=True)

    class Meta:
        model = ReportSchedule
        fields = "__all__"
        read_only_fields = ("last_sent_at",)


class SavedReportViewSet(viewsets.ModelViewSet):
    """BN-161: personalised reports built by choosing fields, filters and grouping."""

    serializer_class = SavedReportSerializer
    permission_classes = [ModulePermission]
    permission_module = "reports"
    action_permissions = {"run": "consult", "datasets": "consult", "preview": "consult"}
    search_fields = ("name",)

    def get_queryset(self):
        from django.db.models import Q

        return SavedReport.objects.filter(Q(owner=self.request.user) | Q(shared=True))

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def _respond(self, request, name, dataset, fields, filters, group_by):
        try:
            headers, rows = services.run_report(
                request.user, dataset, fields, filters, group_by
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        fmt = request.query_params.get("file_format")
        if fmt:
            if (
                not has_module_permission(request.user, "reports", "export")
                and fmt != "pdf"
            ):
                raise PermissionDenied()
            return export_rows(headers, rows, name, fmt, title=name)
        return Response({"headers": headers, "rows": rows})

    @action(detail=True, methods=["get"])
    def run(self, request, pk=None):
        report = self.get_object()
        return self._respond(
            request,
            report.name,
            report.dataset,
            report.fields,
            report.filters,
            report.group_by,
        )

    @action(detail=False, methods=["post"])
    def preview(self, request):
        data = request.data
        return self._respond(
            request,
            data.get("name") or "report",
            data.get("dataset"),
            data.get("fields"),
            data.get("filters") or {},
            data.get("group_by") or "",
        )

    @action(detail=False, methods=["get"])
    def datasets(self, request):
        return Response(
            {
                key: [{"value": f, "label": label} for f, label in fields.items()]
                for key, fields in services.DATASET_FIELDS.items()
            }
        )


class ReportScheduleViewSet(viewsets.ModelViewSet):
    """BN-162: automatic sending of a periodic report."""

    serializer_class = ReportScheduleSerializer
    permission_classes = [ModulePermission]
    permission_module = "reports"

    def get_queryset(self):
        return ReportSchedule.objects.filter(
            report__owner=self.request.user
        ).select_related("report")
