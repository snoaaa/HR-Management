from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from employees.models import Employee
from users.permissions import ModulePermission, has_module_permission, scope_employees

from . import services
from .models import (
    EmployeeSkill,
    Participation,
    PositionSkill,
    Skill,
    TrainingNeed,
    TrainingPlan,
    TrainingSession,
)


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = "__all__"


class PositionSkillSerializer(serializers.ModelSerializer):
    skill_name = serializers.CharField(source="skill.name", read_only=True)
    position_title = serializers.CharField(source="position.title", read_only=True)

    class Meta:
        model = PositionSkill
        fields = "__all__"


class EmployeeSkillSerializer(serializers.ModelSerializer):
    skill_name = serializers.CharField(source="skill.name", read_only=True)
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)

    class Meta:
        model = EmployeeSkill
        fields = "__all__"


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingPlan
        fields = "__all__"


class NeedSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    skill_name = serializers.CharField(source="skill.name", read_only=True)
    session_title = serializers.CharField(source="session.title", read_only=True)

    class Meta:
        model = TrainingNeed
        fields = "__all__"
        read_only_fields = ("created_by",)


class ParticipationSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    session_title = serializers.CharField(source="session.title", read_only=True)
    session_start = serializers.DateField(source="session.start_date", read_only=True)

    class Meta:
        model = Participation
        fields = "__all__"
        read_only_fields = ("session", "employee")


class SessionSerializer(serializers.ModelSerializer):
    participations = ParticipationSerializer(many=True, read_only=True)
    skill_names = serializers.SerializerMethodField()
    cost_per_participant = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True
    )

    class Meta:
        model = TrainingSession
        fields = "__all__"

    def get_skill_names(self, session):
        return [s.name for s in session.skills.all()]

    def validate(self, attrs):
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start and end and end < start:
            raise serializers.ValidationError("The end date is before the start date.")
        return attrs


class TrainingView:
    permission_classes = [ModulePermission]
    permission_module = "training"


class SkillViewSet(TrainingView, viewsets.ModelViewSet):
    queryset = Skill.objects.all()
    serializer_class = SkillSerializer
    action_permissions = {"create": "modify"}
    search_fields = ("name", "category")


class PositionSkillViewSet(TrainingView, viewsets.ModelViewSet):
    queryset = PositionSkill.objects.select_related("skill", "position")
    serializer_class = PositionSkillSerializer
    action_permissions = {"create": "modify"}
    filterset_fields = ("position", "skill")


class EmployeeSkillViewSet(TrainingView, viewsets.ModelViewSet):
    serializer_class = EmployeeSkillSerializer
    action_permissions = {"create": "modify"}
    filterset_fields = ("employee", "skill")
    search_fields = ("employee__surname", "skill__name")

    def get_queryset(self):
        return scope_employees(
            self.request.user,
            EmployeeSkill.objects.select_related("employee", "skill"),
            "employee__",
        )


class PlanViewSet(TrainingView, viewsets.ModelViewSet):
    queryset = TrainingPlan.objects.all()
    serializer_class = PlanSerializer
    action_permissions = {"create": "modify", "costs": "consult"}

    @action(detail=False, methods=["get"])
    def costs(self, request):
        """BN-81: costs per employee and department versus the budget."""
        return Response(
            services.costs(int(request.query_params.get("year", timezone.now().year)))
        )


class NeedViewSet(TrainingView, viewsets.ModelViewSet):
    """BN-78: needs collected from managers, employees and evaluations."""

    serializer_class = NeedSerializer
    action_permissions = {"create": "consult"}
    filterset_fields = ("year", "status", "priority", "department", "employee")
    search_fields = ("subject", "employee__surname", "department__name")

    def get_queryset(self):
        queryset = TrainingNeed.objects.select_related(
            "employee", "department", "skill", "session"
        )
        if has_module_permission(self.request.user, "training", "modify"):
            return queryset
        return scope_employees(
            self.request.user, queryset.filter(employee__isnull=False), "employee__"
        )

    def perform_create(self, serializer):
        user = self.request.user
        employee = serializer.validated_data.get("employee")
        if not has_module_permission(user, "training", "create"):
            own = Employee.objects.filter(user=user).first()
            if own is None or (employee and employee != own):
                raise PermissionDenied("You can only request a training for yourself.")
            serializer.save(
                employee=own,
                department=own.department,
                origin="EMPLOYEE",
                created_by=user,
            )
        else:
            serializer.save(created_by=user)


class SessionViewSet(TrainingView, viewsets.ModelViewSet):
    """BN-79 → BN-81."""

    serializer_class = SessionSerializer
    action_permissions = {
        "create": "modify",
        "register": "modify",
        "result": "modify",
        "close": "modify",
        "mine": "consult",
    }
    filterset_fields = ("plan", "status")
    search_fields = ("title", "organiser", "place")

    def get_queryset(self):
        return TrainingSession.objects.prefetch_related(
            "participations__employee", "skills"
        )

    @action(detail=True, methods=["post"])
    def register(self, request, pk=None):
        session = self.get_object()
        employees = scope_employees(
            request.user,
            Employee.objects.filter(pk__in=request.data.get("employees", [])),
        )
        try:
            added = services.register(session, list(employees), request.user)
        except services.TrainingError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(
            {"added": len(added), "session": self.get_serializer(session).data}
        )

    @action(
        detail=True,
        methods=["post"],
        url_path=r"result/(?P<participation_id>\d+)",
        parser_classes=[MultiPartParser, FormParser, JSONParser],
    )
    def result(self, request, pk=None, participation_id=None):
        session = self.get_object()
        participation = session.participations.filter(pk=participation_id).first()
        if participation is None:
            return Response(status=404)
        data = {k: v for k, v in request.data.items()}
        if request.FILES.get("certificate"):
            data["certificate"] = request.FILES["certificate"]
        services.record_result(participation, data, request.user)
        return Response(ParticipationSerializer(participation).data)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        session = services.close_session(self.get_object())
        return Response(self.get_serializer(session).data)

    @action(detail=False, methods=["get"])
    def mine(self, request):
        participations = Participation.objects.filter(
            employee__user=request.user
        ).select_related("session")
        return Response(ParticipationSerializer(participations, many=True).data)


class SkillGapView(APIView):
    """BN-77: gaps between the position profile and the employee."""

    permission_classes = [ModulePermission]
    permission_module = "training"

    def get(self, request, employee_id):
        employee = (
            scope_employees(request.user, Employee.objects.all())
            .filter(pk=employee_id)
            .first()
        )
        if employee is None:
            return Response(status=404)
        return Response(services.skill_gaps(employee))
