from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"saved", views.SavedReportViewSet, basename="saved-report")
router.register(r"schedules", views.ReportScheduleViewSet, basename="report-schedule")

urlpatterns = [
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("indicators/<str:kind>/", views.IndicatorView.as_view(), name="indicator"),
    path("", include(router.urls)),
]
