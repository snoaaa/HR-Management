from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import CompanyIdentity, Site, CostCentre, Department, Classification, Position
from .serializers import (
    CompanyIdentitySerializer, SiteSerializer, CostCentreSerializer,
    DepartmentSerializer, ClassificationSerializer, PositionSerializer
)
from users.utils import log_audit_action

class BaseOrganisationViewSet(viewsets.ModelViewSet):
    """
    Base viewset to handle audit logging for organisation structure changes.
    """
    permission_classes = [IsAuthenticated] # Fine grained permissions could be applied here

    def perform_create(self, serializer):
        instance = serializer.save()
        
        # Serialize the new state to dict for audit
        from rest_framework.renderers import JSONRenderer
        new_data = self.get_serializer(instance).data
        
        log_audit_action(
            user=self.request.user,
            action=f"Created {instance._meta.verbose_name}: {instance}",
            module="Organisation",
            request=self.request,
            details={"id": instance.id, "new_value": new_data}
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
            details={"id": instance.id, "previous_value": old_data, "new_value": new_data}
        )

    def perform_destroy(self, instance):
        old_data = self.get_serializer(instance).data
        
        log_audit_action(
            user=self.request.user,
            action=f"Deleted {instance._meta.verbose_name}: {instance}",
            module="Organisation",
            request=self.request,
            details={"id": instance.id, "previous_value": old_data}
        )
        instance.delete()


class CompanyIdentityViewSet(BaseOrganisationViewSet):
    queryset = CompanyIdentity.objects.all()
    serializer_class = CompanyIdentitySerializer

class SiteViewSet(BaseOrganisationViewSet):
    queryset = Site.objects.all()
    serializer_class = SiteSerializer

class CostCentreViewSet(BaseOrganisationViewSet):
    queryset = CostCentre.objects.all()
    serializer_class = CostCentreSerializer

class DepartmentViewSet(BaseOrganisationViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer

class ClassificationViewSet(BaseOrganisationViewSet):
    queryset = Classification.objects.all()
    serializer_class = ClassificationSerializer

class PositionViewSet(BaseOrganisationViewSet):
    queryset = Position.objects.all()
    serializer_class = PositionSerializer
