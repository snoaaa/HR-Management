from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ApprovalCircuitViewSet,
    ApprovalTaskViewSet,
    NotificationViewSet,
    PreferenceView,
    RunAlertsView,
)

router = DefaultRouter()
router.register(r"approvals", ApprovalTaskViewSet, basename="approval-task")
router.register(r"circuits", ApprovalCircuitViewSet, basename="approval-circuit")
router.register(r"", NotificationViewSet, basename="notification")

urlpatterns = [
    path("preferences/", PreferenceView.as_view(), name="notification-preferences"),
    path("run-alerts/", RunAlertsView.as_view(), name="run-alerts"),
    path("", include(router.urls)),
]
