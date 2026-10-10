from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from core.views import SettingViewSet

from .views import (
    ChangePasswordView,
    CustomTokenObtainPairView,
    FilteredAuditLogViewSet,
    LogoutView,
    MyPermissionsView,
    PermissionMatrixView,
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
    path("auth/change-password/", ChangePasswordView.as_view(), name="change_password"),
    path("users/me/", UserMeView.as_view(), name="user_me"),
    path("users/me/permissions/", MyPermissionsView.as_view(), name="my_permissions"),
    path(
        "users/permission-matrix/",
        PermissionMatrixView.as_view(),
        name="permission_matrix",
    ),
    path("", include(router.urls)),
]
