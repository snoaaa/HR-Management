"""hrms_backend URL Configuration"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import FileResponse
from django.urls import include, path, re_path
from django.views.static import serve

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
    path("api/organisation/", include("organisation.urls")),
    path("api/employees/", include("employees.urls")),
    path("api/notifications/", include("notifications.urls")),
    path("api/documents/", include("documents.urls")),
    path("api/contracts/", include("contracts.urls")),
    path("api/attendance/", include("attendance.urls")),
    path("api/leave/", include("leave.urls")),
    path("api/planning/", include("planning.urls")),
    path("api/payroll/", include("payroll.urls")),
    path("api/accounting/", include("accounting.urls")),
    path("api/careers/", include("careers.urls")),
    path("api/reports/", include("reports.urls")),
    path("api/evaluation/", include("evaluation.urls")),
    path("api/training/", include("training.urls")),
    path("api/recruitment/", include("recruitment.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
elif settings.SERVE_MEDIA:
    urlpatterns += [
        re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT})
    ]


def frontend(request, *args, **kwargs):
    """Entry page of the React application (it handles its own routes)."""
    response = FileResponse(open(settings.FRONTEND_DIST / "index.html", "rb"))
    response["Cache-Control"] = "no-cache"
    return response


if settings.SERVE_FRONTEND:
    # Everything that is not the API, the admin or a file goes to the SPA.
    urlpatterns += [
        re_path(r"^(?!api/|admin/|media/|static/|assets/).*$", frontend),
    ]
