from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ShiftSwapViewSet,
    ShiftViewSet,
    TimetableEntryViewSet,
    TimetableViewSet,
)

router = DefaultRouter()
router.register(r"shifts", ShiftViewSet, basename="shift")
router.register(r"timetables", TimetableViewSet, basename="timetable")
router.register(r"entries", TimetableEntryViewSet, basename="timetable-entry")
router.register(r"swaps", ShiftSwapViewSet, basename="shift-swap")

urlpatterns = [path("", include(router.urls))]
