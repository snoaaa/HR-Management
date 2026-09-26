from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT serializer to include user details in the token response.
    This saves the frontend from having to make a separate request immediately after login.
    """
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Add custom user data to the response payload
        data['user'] = {
            'id': self.user.id,
            'username': self.user.username,
            'email': self.user.email,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'role': self.user.role,
            'requires_password_change': self.user.requires_password_change,
        }
        
        return data

class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for representing a User instance.
    """
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'is_active', 'role', 'requires_password_change')
        read_only_fields = ('id', 'requires_password_change')

    def create(self, validated_data):
        # Generate a default password for new users
        # and ensure they change it on first login
        user = User.objects.create_user(**validated_data)
        user.set_password('Welcome123!')  # Hardcoded default for simplicity, user changes it later
        user.requires_password_change = True
        user.save()
        return user


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for password change endpoint.
    """
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

from users.models import AuditLog

class AuditLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = AuditLog
        fields = '__all__'
        read_only_fields = ('id', 'user', 'action', 'module', 'ip_address', 'details', 'timestamp')
