from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("sites", views.SiteViewSet, basename="site")
router.register("departments", views.DepartmentViewSet, basename="department")
router.register("teams", views.TeamViewSet, basename="team")
router.register("users", views.UserViewSet, basename="user")
router.register("roles", views.RoleViewSet, basename="role")
router.register(
    "role-permissions", views.RolePermissionViewSet, basename="role-permission"
)
router.register("user-roles", views.UserRoleViewSet, basename="user-role")
router.register("salary-records", views.SalaryRecordViewSet, basename="salary-record")
router.register("audit-log", views.AuditLogViewSet, basename="audit-log")
router.register(
    "data-subject-requests",
    views.DataSubjectRequestViewSet,
    basename="data-subject-request",
)

urlpatterns = [
    # BN-169 / BN-174 / BN-176 - authentication, password policy, 2FA.
    # The url_name of each of these must match middleware.EXEMPT_URL_NAMES
    # so a user can always reach them, even mid-forced-password-change.
    path("auth/login/", views.LoginView.as_view(), name="login"),
    path("auth/logout/", views.LogoutView.as_view(), name="logout"),
    path("auth/me/", views.CurrentUserView.as_view(), name="current-user"),
    path(
        "auth/password/change/",
        views.PasswordChangeView.as_view(),
        name="password-change",
    ),
    path(
        "auth/2fa/setup/", views.TwoFactorSetupView.as_view(), name="two-factor-setup"
    ),
    path(
        "auth/2fa/verify/",
        views.TwoFactorVerifyView.as_view(),
        name="two-factor-verify",
    ),
    path("", include(router.urls)),
]
