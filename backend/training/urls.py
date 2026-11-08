from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"skills", views.SkillViewSet, basename="skill")
router.register(
    r"position-skills", views.PositionSkillViewSet, basename="position-skill"
)
router.register(
    r"employee-skills", views.EmployeeSkillViewSet, basename="employee-skill"
)
router.register(r"plans", views.PlanViewSet, basename="training-plan")
router.register(r"needs", views.NeedViewSet, basename="training-need")
router.register(r"sessions", views.SessionViewSet, basename="training-session")

urlpatterns = [
    path("gaps/<int:employee_id>/", views.SkillGapView.as_view(), name="skill-gaps"),
    path("", include(router.urls)),
]
