import datetime

from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from organisation.models import Department, Position
from users.permissions import ModulePermission
from users.utils import log_audit_action

from . import services
from .models import (
    Application,
    ApplicationEvent,
    JobOffer,
    OnboardingTask,
    RecruitmentNeed,
)

ALLOWED_UPLOADS = (".pdf", ".doc", ".docx", ".odt", ".jpg", ".jpeg", ".png")
MAX_UPLOAD = 5 * 1024 * 1024


class NeedSerializer(serializers.ModelSerializer):
    position_title = serializers.CharField(source="position.title", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    requested_by_name = serializers.CharField(
        source="requested_by.get_full_name", read_only=True
    )

    class Meta:
        model = RecruitmentNeed
        fields = "__all__"
        read_only_fields = ("status", "decision_comment", "requested_by")


class OfferSerializer(serializers.ModelSerializer):
    position_title = serializers.CharField(source="position.title", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    location_name = serializers.CharField(source="location.name", read_only=True)
    applications_count = serializers.IntegerField(
        source="applications.count", read_only=True
    )

    class Meta:
        model = JobOffer
        fields = "__all__"
        read_only_fields = ("status", "published_at")


class PublicOfferSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)
    location_name = serializers.CharField(source="location.name", read_only=True)
    contract_type_label = serializers.CharField(
        source="get_contract_type_display", read_only=True
    )

    class Meta:
        model = JobOffer
        fields = (
            "id",
            "title",
            "department_name",
            "location_name",
            "contract_type_label",
            "description",
            "requirements",
            "closing_date",
            "published_at",
        )


class EventSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = ApplicationEvent
        exclude = ("application",)


class ApplicationSerializer(serializers.ModelSerializer):
    offer_title = serializers.CharField(source="offer.title", read_only=True)
    full_name = serializers.CharField(read_only=True)
    stage_label = serializers.CharField(source="get_stage_display", read_only=True)
    events = EventSerializer(many=True, read_only=True)
    employee_matriculation = serializers.CharField(
        source="employee.matriculation_number", read_only=True
    )

    class Meta:
        model = Application
        fields = "__all__"
        read_only_fields = ("stage", "employee", "source")


class PublicApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = (
            "surname",
            "given_names",
            "email",
            "phone",
            "date_of_birth",
            "place_of_birth",
            "sex",
            "nationality",
            "marital_status",
            "address",
            "cv",
            "cover_letter",
            "motivation",
        )

    def _check_file(self, upload):
        if upload is None:
            return upload
        if (
            not upload.name.lower().endswith(ALLOWED_UPLOADS)
            or upload.size > MAX_UPLOAD
        ):
            raise serializers.ValidationError(
                "PDF, Word or image files of 5 MB at most."
            )
        return upload

    def validate_cv(self, value):
        return self._check_file(value)

    def validate_cover_letter(self, value):
        return self._check_file(value)


class OnboardingSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    responsible_name = serializers.CharField(
        source="responsible.get_full_name", read_only=True
    )

    class Meta:
        model = OnboardingTask
        fields = "__all__"
        read_only_fields = ("done_at",)


class RecruitmentView:
    permission_classes = [ModulePermission]
    permission_module = "recruitment"


class NeedViewSet(RecruitmentView, viewsets.ModelViewSet):
    """BN-22."""

    serializer_class = NeedSerializer
    action_permissions = {"submit": "create"}
    filterset_fields = ("status", "department", "position")
    search_fields = ("position__title", "department__name", "justification")

    def get_queryset(self):
        return RecruitmentNeed.objects.select_related(
            "position", "department", "requested_by"
        )

    def perform_create(self, serializer):
        need = serializer.save(requested_by=self.request.user)
        if self.request.data.get("submit") in (True, "true", "1"):
            services.submit_need(need, self.request.user)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        try:
            need = services.submit_need(self.get_object(), request.user)
        except services.RecruitmentError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(self.get_serializer(need).data)


class OfferViewSet(RecruitmentView, viewsets.ModelViewSet):
    """BN-23."""

    serializer_class = OfferSerializer
    action_permissions = {"publish": "modify", "close": "modify"}
    filterset_fields = ("status", "department", "need")
    search_fields = ("title", "department__name")

    def get_queryset(self):
        return JobOffer.objects.select_related(
            "position", "department", "location", "need"
        )

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        try:
            offer = services.publish_offer(self.get_object())
        except services.RecruitmentError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(self.get_serializer(offer).data)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        offer = self.get_object()
        offer.status = "CLOSED"
        offer.save(update_fields=["status"])
        return Response(self.get_serializer(offer).data)


class ApplicationViewSet(RecruitmentView, viewsets.ModelViewSet):
    """BN-24 / BN-25 / BN-27."""

    serializer_class = ApplicationSerializer
    action_permissions = {
        "move": "modify",
        "hire": "validate",
        "pool": "consult",
        "attach": "modify",
    }
    filterset_fields = ("offer", "stage", "in_pool")
    search_fields = ("surname", "given_names", "email", "phone", "offer__title")
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        return Application.objects.select_related("offer", "employee").prefetch_related(
            "events__user"
        )

    def perform_create(self, serializer):
        application = serializer.save(source="INTERNAL")
        services.receive(application)

    @action(detail=True, methods=["post"])
    def move(self, request, pk=None):
        application = self.get_object()
        if request.data.get("score") not in (None, ""):
            application.score = int(request.data["score"])
            application.save(update_fields=["score"])
        try:
            services.move(
                application,
                request.data.get("stage"),
                request.user,
                request.data.get("comment", ""),
            )
        except services.RecruitmentError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(self.get_serializer(application).data)

    @action(detail=True, methods=["post"])
    def hire(self, request, pk=None):
        application = self.get_object()
        try:
            start = datetime.date.fromisoformat(
                request.data.get("date_of_hire") or str(timezone.now().date())
            )
            employee = services.hire(
                application,
                request.user,
                start,
                Department.objects.filter(pk=request.data.get("department")).first(),
                Position.objects.filter(pk=request.data.get("position")).first(),
            )
        except (ValueError, services.RecruitmentError) as exc:
            return Response({"detail": str(exc)}, status=400)
        log_audit_action(
            request.user,
            f"Hired {employee.full_name} from application #{application.id}",
            "Recruitment",
            request,
        )
        return Response(
            {
                "employee_id": employee.id,
                "matriculation_number": employee.matriculation_number,
            }
        )

    @action(detail=True, methods=["post"])
    def attach(self, request, pk=None):
        """BN-27: a candidate of the pool is attached to another offer."""
        application = self.get_object()
        offer = JobOffer.objects.filter(pk=request.data.get("offer")).first()
        if offer is None:
            return Response({"detail": "Choose an offer."}, status=400)
        application.offer = offer
        application.stage = "RECEIVED"
        application.in_pool = False
        application.save(update_fields=["offer", "stage", "in_pool"])
        ApplicationEvent.objects.create(
            application=application,
            stage="RECEIVED",
            user=request.user,
            comment=f"Taken from the pool for {offer.title}",
        )
        return Response(self.get_serializer(application).data)


class OnboardingViewSet(RecruitmentView, viewsets.ModelViewSet):
    """BN-26."""

    serializer_class = OnboardingSerializer
    action_permissions = {"toggle": "consult"}
    filterset_fields = ("employee", "done", "responsible")
    search_fields = ("employee__surname", "title")

    def get_queryset(self):
        return OnboardingTask.objects.select_related("employee", "responsible")

    @action(detail=True, methods=["post"])
    def toggle(self, request, pk=None):
        task = self.get_object()
        task.done = not task.done
        task.done_at = timezone.now() if task.done else None
        task.save(update_fields=["done", "done_at"])
        return Response(self.get_serializer(task).data)


class PublicOffersView(APIView):
    """Public careers page: published offers (no login)."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        today = timezone.now().date()
        offers = (
            JobOffer.objects.filter(status="PUBLISHED")
            .exclude(closing_date__lt=today)
            .select_related("department", "location")
        )
        return Response(PublicOfferSerializer(offers, many=True).data)


class ApplyThrottle(AnonRateThrottle):
    rate = "20/hour"


class PublicApplyView(APIView):
    """Public application form (BN-23); applications are stored with their documents."""

    permission_classes = [AllowAny]
    authentication_classes = []
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    throttle_classes = [ApplyThrottle]

    def post(self, request, offer_id):
        today = timezone.now().date()
        offer = (
            JobOffer.objects.filter(pk=offer_id, status="PUBLISHED")
            .exclude(closing_date__lt=today)
            .first()
        )
        if offer is None:
            return Response({"detail": "This offer is closed."}, status=404)
        serializer = PublicApplicationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = serializer.save(offer=offer, source="PUBLIC")
        services.receive(application)
        return Response(
            {"detail": "Thank you, your application has been received."}, status=201
        )
