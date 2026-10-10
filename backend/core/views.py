from rest_framework import viewsets
from rest_framework.permissions import BasePermission, IsAuthenticated

from users.models import User
from users.utils import log_audit_action

from .models import Setting
from .serializers import SettingSerializer


class IsAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return request.user.role in (
            User.Roles.SYSTEM_ADMINISTRATOR,
            User.Roles.HR_MANAGER,
        )


class SettingViewSet(viewsets.ModelViewSet):
    """BN-178: configure the reference parameters of the system."""

    queryset = Setting.objects.all()
    serializer_class = SettingSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]

    def perform_update(self, serializer):
        previous = serializer.instance.value
        setting = serializer.save()
        log_audit_action(
            user=self.request.user,
            action=f"Changed setting {setting.key}",
            module="Settings",
            request=self.request,
            details={"previous_value": previous, "new_value": setting.value},
        )
