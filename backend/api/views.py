# flake8: noqa
from django.shortcuts import render

# Create your views here.
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .audit import audit
from .models import AuditLog, Role, User, UserRole
from .permissions import require
from .serializers import (
    AuditLogSerializer,
    RoleSerializer,
    UserCreateSerializer,
    UserRoleSerializer,
    UserSerializer,
)


class MeView(APIView):
    """GET /api/me/ - infos de l'utilisateur connecté"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class UserListCreateView(generics.ListCreateAPIView):
    """GET/POST /api/users/"""
    queryset = User.objects.filter(is_active=True)
    permission_classes = [permissions.IsAuthenticated, require("api.add_user")]

    def get_serializer_class(self):
        return UserCreateSerializer if self.request.method == "POST" else UserSerializer

    def perform_create(self, serializer):
        user = serializer.save()
        audit(AuditLog.Action.CREATE, request=self.request, target=("api.User", user.id))


class UserDetailView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/users/<id>/"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, require("api.change_user")]

    def perform_update(self, serializer):
        user = serializer.save()
        audit(AuditLog.Action.UPDATE, request=self.request, target=("api.User", user.id))


class RoleListCreateView(generics.ListCreateAPIView):
    """GET/POST /api/roles/"""
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [permissions.IsAuthenticated, require("api.add_role")]


class UserRoleListCreateView(generics.ListCreateAPIView):
    """GET/POST /api/user-roles/ - attribuer un rôle à un utilisateur"""
    queryset = UserRole.objects.all()
    serializer_class = UserRoleSerializer
    permission_classes = [permissions.IsAuthenticated, require("api.add_userrole")]

    def perform_create(self, serializer):
        ur = serializer.save(granted_by=self.request.user)
        audit(AuditLog.Action.ROLE_GRANT, request=self.request,
              target=("api.UserRole", ur.id), changes={"role": ur.role.code, "user": ur.user_id})


class AuditLogListView(generics.ListAPIView):
    """GET /api/audit-logs/ - lecture seule, réservé aux admins"""
    queryset = AuditLog.objects.all().order_by("-created_at")
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated, require("api.view_auditlog")]