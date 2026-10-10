from django.db.models import Q
from django.http import HttpResponse
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from core.pdf import render_pdf
from users.permissions import (
    ModulePermission,
    can_view_salary,
    has_module_permission,
    scope_employees,
)

from . import services
from .models import Campaign, Evaluation, Objective


class CampaignSerializer(serializers.ModelSerializer):
    evaluations_count = serializers.IntegerField(
        source="evaluations.count", read_only=True
    )
    department_names = serializers.SerializerMethodField()

    class Meta:
        model = Campaign
        fields = "__all__"
        read_only_fields = ("status", "created_by")

    def get_department_names(self, campaign):
        return [d.name for d in campaign.departments.all()]

    def validate_criteria(self, value):
        codes = set()
        for item in value:
            if (
                not isinstance(item, dict)
                or not item.get("code")
                or not item.get("label")
            ):
                raise serializers.ValidationError(
                    'Each criterion is {"code", "label", "weight"}.'
                )
            if item["code"] in codes:
                raise serializers.ValidationError(
                    f"Duplicate criterion {item['code']}."
                )
            codes.add(item["code"])
        return value


class ObjectiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Objective
        fields = "__all__"


class EvaluationSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    department_name = serializers.CharField(
        source="employee.department.name", read_only=True
    )
    evaluator_name = serializers.CharField(
        source="evaluator.get_full_name", read_only=True
    )
    campaign_name = serializers.CharField(source="campaign.name", read_only=True)
    criteria = serializers.JSONField(source="campaign.criteria", read_only=True)
    scale_max = serializers.IntegerField(source="campaign.scale_max", read_only=True)
    objectives = ObjectiveSerializer(many=True, read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Evaluation
        fields = "__all__"
        read_only_fields = (
            "campaign",
            "employee",
            "evaluator",
            "status",
            "final_score",
            "proposal_applied",
            "validated_at",
        )

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        if request is not None and not can_view_salary(request.user, instance.employee):
            data["bonus_amount"] = None
        return data


def _is_hr(user):
    return has_module_permission(user, "evaluation", "create")


class CampaignViewSet(viewsets.ModelViewSet):
    serializer_class = CampaignSerializer
    permission_classes = [ModulePermission]
    permission_module = "evaluation"
    action_permissions = {
        "open": "create",
        "close": "create",
        "summary": "consult",
        "print_summary": "print",
    }
    search_fields = ("name",)

    def get_queryset(self):
        return Campaign.objects.prefetch_related("departments")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def open(self, request, pk=None):
        campaign = self.get_object()
        try:
            created = services.open_campaign(campaign, request.user)
        except services.EvaluationError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(
            {"created": created, "campaign": self.get_serializer(campaign).data}
        )

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        campaign = self.get_object()
        campaign.status = "CLOSED"
        campaign.save(update_fields=["status"])
        return Response(self.get_serializer(campaign).data)

    @action(detail=True, methods=["get"])
    def summary(self, request, pk=None):
        return Response(services.campaign_summary(self.get_object()))

    @action(detail=True, methods=["get"])
    def print_summary(self, request, pk=None):
        """BN-86: summary of the campaign."""
        summary = services.campaign_summary(self.get_object())
        body = """
<h1>Evaluation campaign – {{ s.campaign }}</h1>
<table class="no-border"><tr><td>Population</td><td>{{ s.population }}</td></tr>
<tr><td>Completed</td><td>{{ s.completed }}</td></tr><tr><td>Validated</td><td>{{ s.validated }}</td></tr>
<tr><td>Average score</td><td>{{ s.average_score|default:"—" }} / 100</td></tr></table>
<h2>By department</h2><table><tr><th>Department</th><th class="num">Evaluated</th><th class="num">Average</th></tr>
{% for d in s.by_department %}<tr><td>{{ d.department }}</td><td class="num">{{ d.count }}</td>
<td class="num">{{ d.average|default:"—" }}</td></tr>{% endfor %}</table>
<h2>Proposals</h2><table>{% for k, v in s.proposals.items %}<tr><td>{{ k }}</td><td class="num">{{ v }}</td></tr>
{% endfor %}</table>"""
        pdf = render_pdf(body, {"s": summary}, footer_text="Campaign summary")
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = 'inline; filename="campaign-summary.pdf"'
        return response


EVALUATION_PRINT = """
<h1>Evaluation record – {{ e.campaign.name }}</h1>
<table class="no-border"><tr><td width="35%">Employee</td><td><b>{{ e.employee.full_name }}</b>
({{ e.employee.matriculation_number }})</td></tr>
<tr><td>Position</td><td>{{ e.employee.position.title|default:"" }}</td></tr>
<tr><td>Evaluator</td><td>{{ e.evaluator.get_full_name|default:"" }}</td></tr>
<tr><td>Final score</td><td><b>{{ e.final_score|default:"—" }} / 100</b></td></tr></table>
<h2>Criteria</h2><table><tr><th>Criterion</th><th class="num">Self-evaluation</th><th class="num">Manager</th></tr>
{% for c in criteria %}<tr><td>{{ c.label }}</td><td class="num">{{ c.self }}</td>
<td class="num">{{ c.manager }}</td></tr>
{% endfor %}</table>
<h2>Objectives</h2><table><tr><th>Objective</th><th>Target</th><th class="num">Achievement</th></tr>
{% for o in e.objectives.all %}<tr><td>{{ o.title }}</td><td>{{ o.target }}</td>
<td class="num">{{ o.achievement_percent|default:"—" }} %</td></tr>
{% empty %}<tr><td colspan="3">None</td></tr>{% endfor %}
</table>
<h2>Comments</h2><p><b>Employee:</b> {{ e.self_comment|linebreaksbr }}</p>
<p><b>Manager:</b> {{ e.manager_comment|linebreaksbr }}</p>
<p><b>Strengths:</b> {{ e.strengths|linebreaksbr }}</p><p><b>To improve:</b> {{ e.improvements|linebreaksbr }}</p>
<p><b>Actions decided:</b> {{ e.actions_decided|linebreaksbr }}</p>
<p><b>Proposal:</b> {{ e.get_proposal_display }}</p>
<br/><table class="signature"><tr><td width="50%"><b>The employee</b></td><td><b>The evaluator</b></td></tr></table>
"""


class EvaluationViewSet(viewsets.ModelViewSet):
    """BN-83 / BN-84 / BN-86: self-evaluation, manager evaluation, HR validation."""

    serializer_class = EvaluationSerializer
    permission_classes = [ModulePermission]
    permission_module = "evaluation"
    http_method_names = ["get", "post", "patch", "head", "options"]
    action_permissions = {
        "self_assessment": "consult",
        "manager_assessment": "modify",
        "validate": "create",
        "objectives": "modify",
        "print_record": "print",
    }
    filterset_fields = ("campaign", "status", "employee")
    search_fields = (
        "employee__surname",
        "employee__given_names",
        "employee__matriculation_number",
    )

    def get_queryset(self):
        user = self.request.user
        queryset = Evaluation.objects.select_related(
            "campaign",
            "employee",
            "employee__department",
            "evaluator",
            "employee__position",
        ).prefetch_related("objectives")
        if _is_hr(user):
            return queryset
        from employees.models import Employee

        perimeter = scope_employees(user, Employee.objects.all()).values("id")
        return queryset.filter(Q(employee__in=perimeter) | Q(evaluator=user))

    def _run(self, func, *args):
        try:
            evaluation = func(*args)
        except services.EvaluationError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(self.get_serializer(evaluation).data)

    @action(detail=True, methods=["post"])
    def self_assessment(self, request, pk=None):
        evaluation = self.get_object()
        if evaluation.employee.user_id != request.user.id:
            raise PermissionDenied("Only the employee completes the self-evaluation.")
        return self._run(
            services.submit_self,
            evaluation,
            request.data.get("scores"),
            request.data.get("comment", ""),
        )

    @action(detail=True, methods=["post"])
    def manager_assessment(self, request, pk=None):
        evaluation = self.get_object()
        if evaluation.evaluator_id != request.user.id and not _is_hr(request.user):
            raise PermissionDenied("Only the evaluator completes this evaluation.")
        return self._run(
            services.submit_manager, evaluation, request.user, request.data
        )

    @action(detail=True, methods=["post"])
    def validate(self, request, pk=None):
        return self._run(services.validate, self.get_object(), request.user)

    @action(detail=True, methods=["post"])
    def objectives(self, request, pk=None):
        """Set the objectives (manager) or their achievement."""
        evaluation = self.get_object()
        if evaluation.status in ("VALIDATED",):
            return Response({"detail": "The evaluation is validated."}, status=400)
        if evaluation.evaluator_id != request.user.id and not _is_hr(request.user):
            raise PermissionDenied("Only the evaluator sets the objectives.")
        evaluation.objectives.all().delete()
        serializer = ObjectiveSerializer(
            data=[
                {**o, "evaluation": evaluation.id}
                for o in request.data.get("objectives", [])
            ],
            many=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(self.get_serializer(evaluation).data)

    @action(detail=True, methods=["get"])
    def print_record(self, request, pk=None):
        evaluation = self.get_object()
        criteria = [
            {
                "label": c["label"],
                "self": evaluation.self_scores.get(c["code"], "—"),
                "manager": evaluation.manager_scores.get(c["code"], "—"),
            }
            for c in evaluation.campaign.criteria
        ]
        pdf = render_pdf(
            EVALUATION_PRINT,
            {"e": evaluation, "criteria": criteria},
            footer_text="Evaluation record",
        )
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'inline; filename="evaluation-{evaluation.id}.pdf"'
        )
        return response

    @action(detail=False, methods=["get"])
    def mine(self, request):
        evaluations = self.get_queryset().filter(
            Q(employee__user=request.user) | Q(evaluator=request.user)
        )
        return Response(self.get_serializer(evaluations, many=True).data)
