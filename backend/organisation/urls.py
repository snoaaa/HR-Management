from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CompanyIdentityViewSet, SiteViewSet, CostCentreViewSet,
    DepartmentViewSet, ClassificationViewSet, PositionViewSet
)

router = DefaultRouter()
router.register(r'company-identity', CompanyIdentityViewSet)
router.register(r'sites', SiteViewSet)
router.register(r'cost-centres', CostCentreViewSet)
router.register(r'departments', DepartmentViewSet)
router.register(r'classifications', ClassificationViewSet)
router.register(r'positions', PositionViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
