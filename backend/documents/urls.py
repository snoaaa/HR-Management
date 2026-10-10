from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CertificateView,
    DecisionView,
    DocumentRequestViewSet,
    DocumentTemplateViewSet,
    IssuedDocumentViewSet,
)

router = DefaultRouter()
router.register(r"templates", DocumentTemplateViewSet, basename="document-template")
router.register(r"issued", IssuedDocumentViewSet, basename="issued-document")
router.register(r"requests", DocumentRequestViewSet, basename="document-request")

urlpatterns = [
    path("certificates/<str:code>/", CertificateView.as_view(), name="certificate"),
    path("decisions/", DecisionView.as_view(), name="decision"),
    path("", include(router.urls)),
]
