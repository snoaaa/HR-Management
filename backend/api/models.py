# flake8: noqa
from django.db import models

# Create your models here.
# ============================================================
# Ajoute ce bloc à LA FIN de api/models.py (ne remplace pas
# ce qui existe déjà dans le fichier).
# ============================================================
from django.conf import settings
from django.contrib.auth.models import AbstractUser, Permission
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    email = models.EmailField(unique=True)
    must_change_password = models.BooleanField(default=True)
    # Sprint 2: lier le login au dossier employé
    # employee = models.OneToOneField("api.Employee", null=True, blank=True,
    #                                 on_delete=models.PROTECT)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]
    # Ne jamais supprimer un utilisateur : mettre is_active=False (garder l'historique)


class Role(models.Model):
    code = models.SlugField(unique=True)  # hr_admin, payroll_officer, manager, employee
    name = models.CharField(max_length=100)
    permissions = models.ManyToManyField(Permission, blank=True, related_name="roles")

    def _str_(self):
        return self.name


class UserRole(models.Model):
    """Un rôle donné à un utilisateur pour une période.
    Ne jamais modifier en place : terminer l'ancien et en créer un nouveau."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="role_assignments"
    )
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="assignments")
    start_date = models.DateField(default=timezone.localdate)
    end_date = models.DateField(null=True, blank=True)
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+", null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)


class AppendOnlyQuerySet(models.QuerySet):
    def update(self, *a, **k):
        raise PermissionError("Le journal d'audit ne peut pas être modifié")

    def delete(self):
        raise PermissionError("Le journal d'audit ne peut pas être supprimé")


class AuditLog(models.Model):
    class Action(models.TextChoices):
        LOGIN = "LOGIN"
        LOGIN_FAILED = "LOGIN_FAILED"
        LOGOUT = "LOGOUT"
        CREATE = "CREATE"
        UPDATE = "UPDATE"
        ARCHIVE = "ARCHIVE"
        VIEW_SENSITIVE = "VIEW_SENSITIVE"  # ex : lecture d'un salaire
        DENIED = "DENIED"
        ROLE_GRANT = "ROLE_GRANT"
        ROLE_REVOKE = "ROLE_REVOKE"

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    action = models.CharField(max_length=20, choices=Action.choices)
    target_type = models.CharField(max_length=100, blank=True)  # "api.Employee"
    target_id = models.CharField(max_length=64, blank=True)
    changes = models.JSONField(default=dict, blank=True)  # {"champ": [ancien, nouveau]}
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    objects = AppendOnlyQuerySet.as_manager()

    def save(self, *a, **k):
        if self.pk:
            raise PermissionError("Le journal d'audit ne peut pas être modifié")
        super().save(*a, **k)

    def delete(self, *a, **k):
        raise PermissionError("Le journal d'audit ne peut pas être supprimé")