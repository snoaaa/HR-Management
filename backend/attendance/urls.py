from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AttendancePeriodViewSet,
    AttendanceSheetView,
    CalendarViewSet,
    ClockingViewSet,
    DailyAttendanceViewSet,
    MissionViewSet,
    PublicHolidayViewSet,
    RegularisationViewSet,
    ScheduleAssignmentViewSet,
    ScheduleExceptionViewSet,
    WorkScheduleViewSet,
)

router = DefaultRouter()
router.register(r"calendars", CalendarViewSet, basename="working-calendar")
router.register(r"holidays", PublicHolidayViewSet, basename="public-holiday")
router.register(r"schedules", WorkScheduleViewSet, basename="work-schedule")
router.register(
    r"assignments", ScheduleAssignmentViewSet, basename="schedule-assignment"
)
router.register(r"exceptions", ScheduleExceptionViewSet, basename="schedule-exception")
router.register(r"clockings", ClockingViewSet, basename="clocking")
router.register(r"regularisations", RegularisationViewSet, basename="regularisation")
router.register(r"missions", MissionViewSet, basename="mission")
router.register(r"days", DailyAttendanceViewSet, basename="daily-attendance")
router.register(r"periods", AttendancePeriodViewSet, basename="attendance-period")

urlpatterns = [
    path("sheet/", AttendanceSheetView.as_view(), name="attendance-sheet"),
    path("", include(router.urls)),
]
