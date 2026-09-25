# flake8: noqa
from django.contrib import admin

# Register your models here.
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import AuditLog, Role, User, UserRole


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ["username", "email", "is_active", "is_staff"]


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ["code", "name"]
    filter_horizontal = ["permissions"]


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ["user", "role", "start_date", "end_date"]
    list_filter = ["role"]


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["created_at", "actor", "action", "target_type", "target_id"]
    list_filter = ["action"]
    search_fields = ["target_type", "target_id"]

    def has_add_permission(self, request):
        return False  # le journal se remplit par le code, pas depuis l'admin

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False