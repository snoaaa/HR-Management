# flake8: noqa
from rest_framework import serializers

# Create your serializers here.
from rest_framework import serializers

from .models import AuditLog, Role, User, UserRole


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name",
                  "is_active", "must_change_password"]
        read_only_fields = ["id", "is_active"]


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "password"]

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)  # jamais de mot de passe en clair
        user.save()
        return user


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ["id", "code", "name", "permissions"]


class UserRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserRole
        fields = ["id", "user", "role", "start_date", "end_date", "granted_by", "created_at"]
        read_only_fields = ["id", "granted_by", "created_at"]


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = ["id", "actor", "action", "target_type", "target_id",
                  "changes", "ip_address", "created_at"]
        read_only_fields = fields  # lecture seule : le journal ne se modifie pas via l'API