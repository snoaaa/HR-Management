from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"accounts", views.AccountViewSet, basename="account")
router.register(r"journals", views.JournalViewSet, basename="journal")
router.register(r"mappings", views.MappingViewSet, basename="account-mapping")
router.register(r"fiscal-years", views.FiscalYearViewSet, basename="fiscal-year")
router.register(r"entries", views.EntryViewSet, basename="journal-entry")
router.register(r"budgets", views.BudgetViewSet, basename="budget")

urlpatterns = [
    path("books/<str:book>/", views.BooksView.as_view(), name="accounting-books"),
    path(
        "documents/<str:kind>/<int:pk>/",
        views.EntryDocumentView.as_view(),
        name="accounting-document",
    ),
    path("", include(router.urls)),
]
