from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from core.data_views import BackupActionView, BackupListView, ImportView
from core.views import SettingViewSet, TableExportView

from .views import (
    ChangePasswordView,
    CustomTokenObtainPairView,
    FilteredAuditLogViewSet,
    LogoutView,
    MyPermissionsView,
    PermissionMatrixView,
    TwoFactorSetupView,
    TwoFactorVerifyView,
    UserMeView,
    UserViewSet,
)

router = DefaultRouter()
router.register(r"users/management", UserViewSet, basename="user-management")
router.register(r"audit-logs", FilteredAuditLogViewSet, basename="audit-log")
router.register(r"settings", SettingViewSet, basename="setting")

urlpatterns = [
    path("auth/login/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/logout/", LogoutView.as_view(), name="auth_logout"),
    path("auth/2fa/verify/", TwoFactorVerifyView.as_view(), name="two_factor_verify"),
    path("auth/2fa/setup/", TwoFactorSetupView.as_view(), name="two_factor_setup"),
    path("auth/change-password/", ChangePasswordView.as_view(), name="change_password"),
    path("users/me/", UserMeView.as_view(), name="user_me"),
    path("users/me/permissions/", MyPermissionsView.as_view(), name="my_permissions"),
    path(
        "users/permission-matrix/",
        PermissionMatrixView.as_view(),
        name="permission_matrix",
    ),
    path("exports/table/", TableExportView.as_view(), name="table-export"),
    path("imports/<str:kind>/", ImportView.as_view(), name="import"),
    path("backups/", BackupListView.as_view(), name="backups"),
    path(
        "backups/<str:name>/<str:operation>/",
        BackupActionView.as_view(),
        name="backup-action",
    ),
    path("", include(router.urls)),
]
