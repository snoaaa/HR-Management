from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"needs", views.NeedViewSet, basename="recruitment-need")
router.register(r"offers", views.OfferViewSet, basename="job-offer")
router.register(r"applications", views.ApplicationViewSet, basename="application")
router.register(r"onboarding", views.OnboardingViewSet, basename="onboarding-task")

urlpatterns = [
    path("public/offers/", views.PublicOffersView.as_view(), name="public-offers"),
    path(
        "public/offers/<int:offer_id>/apply/",
        views.PublicApplyView.as_view(),
        name="public-apply",
    ),
    path("", include(router.urls)),
]
