from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from users.permissions import ModulePermission
from users.utils import log_audit_action

from .models import (
    Classification,
    CompanyIdentity,
    CostCentre,
    Department,
    Position,
    Site,
)
from .serializers import (
    ClassificationSerializer,
    CompanyIdentitySerializer,
    CostCentreSerializer,
    DepartmentSerializer,
    PositionSerializer,
    SiteSerializer,
)


class BaseOrganisationViewSet(viewsets.ModelViewSet):
    """
    Base viewset to handle audit logging for organisation structure changes.
    """

    # BN-170: permissions per module and per action.
    permission_classes = [ModulePermission]
    permission_module = "organisation"

    def perform_create(self, serializer):
        instance = serializer.save()

        # Serialize the new state to dict for audit
        new_data = self.get_serializer(instance).data

        log_audit_action(
            user=self.request.user,
            action=f"Created {instance._meta.verbose_name}: {instance}",
            module="Organisation",
            request=self.request,
            details={"id": instance.id, "new_value": new_data},
        )

    def perform_update(self, serializer):
        # Fetch the old instance from DB before saving
        old_instance = self.get_object()
        old_data = self.get_serializer(old_instance).data

        instance = serializer.save()
        new_data = self.get_serializer(instance).data

        log_audit_action(
            user=self.request.user,
            action=f"Updated {instance._meta.verbose_name}: {instance}",
            module="Organisation",
            request=self.request,
            details={
                "id": instance.id,
                "previous_value": old_data,
                "new_value": new_data,
            },
        )

    def perform_destroy(self, instance):
        old_data = self.get_serializer(instance).data

        log_audit_action(
            user=self.request.user,
            action=f"Deleted {instance._meta.verbose_name}: {instance}",
            module="Organisation",
            request=self.request,
            details={"id": instance.id, "previous_value": old_data},
        )
        instance.delete()


class CompanyIdentityViewSet(BaseOrganisationViewSet):
    search_fields = ("corporate_name",)
    queryset = CompanyIdentity.objects.all()
    serializer_class = CompanyIdentitySerializer
    action_permissions = {"logo": "modify", "current": "consult"}

    ALLOWED_LOGO_TYPES = ("image/png", "image/jpeg", "image/gif")
    MAX_LOGO_SIZE = 2 * 1024 * 1024

    def get_permissions(self):
        if self.action == "current":
            return [AllowAny()]
        return super().get_permissions()

    @action(detail=False, methods=["get"])
    def current(self, request):
        """Name and logo of the organisation (sign-in page, menu)."""
        company = CompanyIdentity.objects.first()
        if company is None:
            return Response({"corporate_name": "", "logo": None})
        return Response(
            {
                "corporate_name": company.corporate_name,
                "logo": (
                    request.build_absolute_uri(company.logo.url)
                    if company.logo
                    else None
                ),
            }
        )

    @action(
        detail=True,
        methods=["post", "delete"],
        parser_classes=[MultiPartParser, FormParser],
    )
    def logo(self, request, pk=None):
        """BN-01: upload (or remove) the logo printed on every document."""
        company = self.get_object()
        if request.method == "DELETE":
            if company.logo:
                company.logo.delete(save=False)
            company.logo = None
            company.save(update_fields=["logo"])
            log_audit_action(
                request.user, "Removed the organisation logo", "Organisation", request
            )
            return Response(self.get_serializer(company).data)
        upload = request.FILES.get("logo")
        if upload is None:
            return Response({"detail": "Send the image in 'logo'."}, status=400)
        if upload.content_type not in self.ALLOWED_LOGO_TYPES:
            return Response(
                {"detail": "The logo must be a PNG, JPEG or GIF image."}, status=400
            )
        if upload.size > self.MAX_LOGO_SIZE:
            return Response({"detail": "The logo must not exceed 2 MB."}, status=400)
        try:
            from PIL import Image

            Image.open(upload).verify()
            upload.seek(0)
        except Exception:
            return Response({"detail": "The file is not a valid image."}, status=400)
        if company.logo:
            company.logo.delete(save=False)
        company.logo.save(upload.name, upload, save=True)
        log_audit_action(
            request.user, "Uploaded the organisation logo", "Organisation", request
        )
        return Response(self.get_serializer(company).data)


class SiteViewSet(BaseOrganisationViewSet):
    search_fields = ("name", "code")
    queryset = Site.objects.all()
    serializer_class = SiteSerializer


class CostCentreViewSet(BaseOrganisationViewSet):
    search_fields = ("name", "code")
    queryset = CostCentre.objects.all()
    serializer_class = CostCentreSerializer


class DepartmentViewSet(BaseOrganisationViewSet):
    search_fields = ("name", "code")
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer


class ClassificationViewSet(BaseOrganisationViewSet):
    search_fields = ("category", "grade", "echelon")
    queryset = Classification.objects.all()
    serializer_class = ClassificationSerializer


class PositionViewSet(BaseOrganisationViewSet):
    search_fields = ("title", "code")
    queryset = Position.objects.all()
    serializer_class = PositionSerializer
