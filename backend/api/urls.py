from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.routers import DefaultRouter
from .views import CustomTokenObtainPairView, LogoutView, UserMeView, ChangePasswordView, UserViewSet, AuditLogViewSet

router = DefaultRouter()
router.register(r'users/management', UserViewSet, basename='user-management')
router.register(r'audit-logs', AuditLogViewSet, basename='audit-log')

urlpatterns = [
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/logout/', LogoutView.as_view(), name='auth_logout'),
    path('auth/change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('users/me/', UserMeView.as_view(), name='user_me'),
    path('', include(router.urls)),
]
