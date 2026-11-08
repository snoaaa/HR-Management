from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    EntitlementRuleViewSet,
    LeaveAdjustmentViewSet,
    LeaveRequestViewSet,
    LeaveTypeViewSet,
)

router = DefaultRouter()
router.register(r"types", LeaveTypeViewSet, basename="leave-type")
router.register(r"rules", EntitlementRuleViewSet, basename="entitlement-rule")
router.register(r"adjustments", LeaveAdjustmentViewSet, basename="leave-adjustment")
router.register(r"requests", LeaveRequestViewSet, basename="leave-request")

urlpatterns = [path("", include(router.urls))]
