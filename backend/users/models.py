from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

class User(AbstractUser):
    """
    Custom user model for the HRMS system.
    Extends AbstractUser to allow adding custom fields based on HRMS Expression of Needs.
    """
    class Roles(models.TextChoices):
        HR_MANAGER = 'HR_MANAGER', _('HR Manager')
        HR_OFFICER = 'HR_OFFICER', _('HR Officer')
        PAYROLL_OFFICER = 'PAYROLL_OFFICER', _('Payroll Officer')
        ACCOUNTANT = 'ACCOUNTANT', _('Accountant')
        HEAD_OF_DEPARTMENT = 'HEAD_OF_DEPARTMENT', _('Head of Department')
        EMPLOYEE = 'EMPLOYEE', _('Employee')
        GENERAL_MANAGEMENT = 'GENERAL_MANAGEMENT', _('General Management')
        SYSTEM_ADMINISTRATOR = 'SYSTEM_ADMINISTRATOR', _('System Administrator')

    role = models.CharField(
        max_length=50,
        choices=Roles.choices,
        default=Roles.EMPLOYEE,
        help_text=_("The user's role in the HRMS system, determining their permissions.")
    )
    
    requires_password_change = models.BooleanField(
        default=True,
        help_text=_("Designates whether the user needs to change their password at next login.")
    )

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class AuditLog(models.Model):
    """
    Model for recording user actions, logins, and system events (BN-176).
    """
    user = models.ForeignKey(
        User, 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL,
        help_text=_("The user who performed the action. Null if anonymous or failed login.")
    )
    action = models.CharField(max_length=255, help_text=_("A short description of the action performed."))
    module = models.CharField(max_length=100, help_text=_("The system module where the action occurred (e.g., 'Auth', 'HR', 'Payroll')."))
    ip_address = models.GenericIPAddressField(null=True, blank=True, help_text=_("The IP address of the user."))
    details = models.JSONField(null=True, blank=True, help_text=_("Additional context or data regarding the action."))
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = _('Audit Log')
        verbose_name_plural = _('Audit Logs')

    def __str__(self):
        user_str = self.user.username if self.user else "Anonymous/System"
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {user_str} - {self.action}"
