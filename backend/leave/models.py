"""
M-06 – Leave and absence management (BN-46 → BN-58).
"""

from decimal import Decimal

from django.conf import settings
from django.db import models

from employees.models import Employee


class LeaveType(models.Model):
    """BN-46 / BN-47: configurable catalogue of leave and absence types."""

    COUNTING = (
        ("WORKING_DAYS", "Working days (rest days and holidays excluded)"),
        ("CALENDAR_DAYS", "Calendar days"),
    )

    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=100)
    is_paid = models.BooleanField(default=True)
    consumes_entitlement = models.BooleanField(
        default=False, help_text="Deducted from the annual leave balance."
    )
    requires_document = models.BooleanField(default=False)
    generates_deduction = models.BooleanField(
        default=False, help_text="Unpaid days are deducted from the salary."
    )
    counts_for_seniority = models.BooleanField(default=True)
    pays_leave_allowance = models.BooleanField(
        default=False, help_text="The leave allowance is paid for these days."
    )
    counting_rule = models.CharField(
        max_length=20, choices=COUNTING, default="WORKING_DAYS"
    )
    max_days_per_request = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    color = models.CharField(max_length=7, default="#714B67")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class EntitlementRule(models.Model):
    """
    BN-48: rule of acquisition of the annual leave, dated so that a change
    applies only from its effective date. No value is written in the code.
    """

    name = models.CharField(max_length=100)
    effective_from = models.DateField()
    days_per_month = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("1.5")
    )
    seniority_brackets = models.JSONField(
        default=list,
        help_text='Extra days per year by seniority, e.g. [{"years": 5, "extra_days": 2}].',
    )
    max_carry_over_days = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Maximum balance carried to the next year (empty = no limit).",
    )
    # BN-56: leave allowance rule.
    allowance_reference_months = models.PositiveSmallIntegerField(
        default=12, help_text="Months of salary used to compute the leave allowance."
    )
    allowance_days_divisor = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("30"),
        help_text="Monthly average divided by this number gives the daily allowance.",
    )

    class Meta:
        ordering = ["-effective_from"]

    def __str__(self):
        return f"{self.name} (from {self.effective_from})"


class LeaveAdjustment(models.Model):
    """
    BN-48: additional entitlements, opening balances (BN-179) and manual
    corrections of a balance, always justified.
    """

    KINDS = (
        ("OPENING", "Opening balance"),
        ("EXTRA", "Additional entitlement"),
        ("CORRECTION", "Correction"),
    )

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="leave_adjustments"
    )
    year = models.PositiveSmallIntegerField()
    kind = models.CharField(max_length=20, choices=KINDS, default="EXTRA")
    days = models.DecimalField(max_digits=6, decimal_places=2)
    reason = models.CharField(max_length=255)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)


class LeaveRequest(models.Model):
    """BN-50 / BN-51 / BN-54: leave request and its life cycle."""

    STATUSES = (
        ("DRAFT", "Draft"),
        ("SUBMITTED", "Waiting for approval"),
        ("MODIFICATION", "Modification requested"),
        ("APPROVED", "Approved"),
        ("REFUSED", "Refused"),
        ("CANCELLED", "Cancelled"),
        ("INTERRUPTED", "Interrupted"),
    )

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="leave_requests"
    )
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT)
    start_date = models.DateField()
    end_date = models.DateField()
    days = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    replacement = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="replacing_requests",
    )
    reason = models.TextField(blank=True)
    document = models.FileField(upload_to="leave_documents/", null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUSES, default="DRAFT")
    decision_comment = models.TextField(blank=True)
    overlap_warning = models.CharField(max_length=255, blank=True)
    # BN-54: interruption and postponement keep the original dates.
    interruption_date = models.DateField(null=True, blank=True)
    original_start_date = models.DateField(null=True, blank=True)
    original_end_date = models.DateField(null=True, blank=True)
    # BN-56: allowance computed when the leave is approved.
    allowance_amount = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start_date", "-id"]

    def __str__(self):
        return f"{self.leave_type} {self.start_date}→{self.end_date} – {self.employee.full_name}"

    @property
    def effective_end_date(self):
        return self.interruption_date or self.end_date

    # Workflow protocol (notifications.services) -------------------------
    @property
    def approval_link(self):
        return f"/leave/requests/{self.id}"

    def approval_requester(self):
        return self.employee

    def approval_summary(self):
        warning = f" ⚠ {self.overlap_warning}" if self.overlap_warning else ""
        return (
            f"{self.leave_type.name}: {self.employee.full_name}, "
            f"{self.start_date:%d/%m} → {self.end_date:%d/%m/%Y} ({self.days} d){warning}"
        )

    def on_approval_completed(self, user):
        from .services import approve

        approve(self, user)

    def on_approval_refused(self, user, comment):
        from django.utils import timezone

        self.status = "REFUSED"
        self.decision_comment = comment
        self.decided_at = timezone.now()
        self.save(update_fields=["status", "decision_comment", "decided_at"])

    def on_modification_requested(self, user, comment):
        self.status = "MODIFICATION"
        self.decision_comment = comment
        self.save(update_fields=["status", "decision_comment"])
