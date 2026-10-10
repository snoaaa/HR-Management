from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from users.models import User


class Notification(models.Model):
    """BN-163 / BN-167: notification centre inside the application."""

    CATEGORIES = (
        ("REQUEST", "Request"),
        ("APPROVAL", "Approval"),
        ("ALERT", "Deadline alert"),
        ("PAYROLL", "Payroll"),
        ("PLANNING", "Planning"),
        ("INFO", "Information"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    title = models.CharField(max_length=255)
    message = models.TextField(blank=True)
    link = models.CharField(max_length=255, blank=True)
    category = models.CharField(max_length=20, choices=CATEGORIES, default="INFO")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    # Prevents the same deadline alert from being sent twice.
    dedupe_key = models.CharField(max_length=255, blank=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} - {self.title}"


class NotificationPreference(models.Model):
    """BN-167: every user chooses the channels."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preference",
    )
    in_app = models.BooleanField(default=True)
    email = models.BooleanField(default=True)


class ApprovalCircuit(models.Model):
    """
    BN-51 / BN-166: approval circuit per type of request, with several levels.
    """

    REQUEST_TYPES = (
        ("LEAVE", "Leave request"),
        ("OVERTIME", "Overtime"),
        ("CLOCKING_REGULARISATION", "Clocking regularisation"),
        ("SHIFT_SWAP", "Shift exchange"),
        ("CONTRACT_AMENDMENT", "Contract amendment"),
        ("CAREER_ACT", "Career act (promotion, transfer, sanction...)"),
        ("RECRUITMENT_NEED", "Recruitment need"),
        ("PROFILE_CORRECTION", "Correction of personal data"),
        ("TRAINING_REQUEST", "Training request"),
    )

    request_type = models.CharField(max_length=40, choices=REQUEST_TYPES, unique=True)
    name = models.CharField(max_length=150)

    def __str__(self):
        return self.name


class ApprovalLevel(models.Model):
    LINE_MANAGER = "LINE_MANAGER"
    APPROVER_CHOICES = [(LINE_MANAGER, "Line manager")] + list(User.Roles.choices)

    circuit = models.ForeignKey(
        ApprovalCircuit, on_delete=models.CASCADE, related_name="levels"
    )
    order = models.PositiveSmallIntegerField()
    approver = models.CharField(
        max_length=50,
        choices=APPROVER_CHOICES,
        help_text="Line manager of the requester, or any user having this role.",
    )
    substitute = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Approver used when the normal approver is absent.",
    )

    class Meta:
        ordering = ["circuit", "order"]
        unique_together = ("circuit", "order")


class ApprovalTask(models.Model):
    """One decision expected from one approver for one request."""

    STATUSES = (
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REFUSED", "Refused"),
        ("MODIFICATION", "Modification requested"),
        ("CANCELLED", "Cancelled"),
    )

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    target = GenericForeignKey("content_type", "object_id")
    request_type = models.CharField(max_length=40)
    level = models.PositiveSmallIntegerField(default=1)
    approver_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approval_tasks",
    )
    approver_role = models.CharField(max_length=50, blank=True)
    summary = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUSES, default="PENDING")
    comment = models.TextField(blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # BN-168: request escalated when unanswered beyond the configured delay.
    escalated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["content_type", "object_id"])]
