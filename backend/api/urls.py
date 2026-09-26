from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    AuditLogViewSet,
    ChangePasswordView,
    CustomTokenObtainPairView,
    LogoutView,
    UserMeView,
    UserViewSet,
)

router = DefaultRouter()
router.register(r"users/management", UserViewSet, basename="user-management")
router.register(r"audit-logs", AuditLogViewSet, basename="audit-log")

urlpatterns = [
    path("auth/login/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/logout/", LogoutView.as_view(), name="auth_logout"),
    path("auth/change-password/", ChangePasswordView.as_view(), name="change_password"),
    path("users/me/", UserMeView.as_view(), name="user_me"),
    path("", include(router.urls)),
]
