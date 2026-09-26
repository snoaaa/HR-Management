from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, AuditLog

class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('HRMS Security', {'fields': ('role', 'requires_password_change')}),
    )

admin.site.register(User, CustomUserAdmin)

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action', 'module', 'ip_address')
    list_filter = ('module', 'timestamp')
    search_fields = ('user__username', 'action', 'details')
    readonly_fields = ('user', 'action', 'module', 'ip_address', 'details', 'timestamp')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
