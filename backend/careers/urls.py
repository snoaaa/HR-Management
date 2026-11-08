from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"acts", views.CareerActViewSet, basename="career-act")

urlpatterns = [
    path("org-chart/", views.OrgChartView.as_view(), name="org-chart"),
    path(
        "structure-history/<int:department_id>/",
        views.StructureHistoryView.as_view(),
        name="structure-history",
    ),
    path("", include(router.urls)),
]
