"""
M-04 – Contract management.

The contract is a first-class object with its own history (BN-28 → BN-35).
The terms in force at any date are obtained by replaying the amendments
whose effective date is reached (BN-30), so that a past payroll can always
be recalculated with the terms that applied at the time.
"""

import datetime
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from employees.models import Employee
from organisation.models import Classification, Department, Position, Site

CONTRACT_TYPES = Employee.CONTRACT_TYPE_CHOICES

# Terms that an amendment can change (BN-30) and their labels.
AMENDABLE_TERMS = {
    "base_salary": "Base salary",
    "position_id": "Position",
    "classification_id": "Classification",
    "department_id": "Department",
    "workplace_id": "Workplace",
    "weekly_hours": "Weekly working time",
    "end_date": "End date",
}


class Contract(models.Model):
    STATUSES = (
        ("DRAFT", "Draft"),
        ("ACTIVE", "Active"),
        ("SUSPENDED", "Suspended"),
        ("TERMINATED", "Terminated"),
        ("EXPIRED", "Expired"),
    )

    employee = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name="contracts"
    )
    reference = models.CharField(max_length=60, unique=True, blank=True)
    contract_type = models.CharField(max_length=20, choices=CONTRACT_TYPES)
    status = models.CharField(max_length=20, choices=STATUSES, default="DRAFT")

    # BN-29: dates, trial, notice, working time, workplace, position, pay.
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    trial_period_end = models.DateField(null=True, blank=True)
    notice_period_days = models.PositiveIntegerField(default=30)
    weekly_hours = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("40")
    )
    workplace = models.ForeignKey(
        Site, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    position = models.ForeignKey(
        Position, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    classification = models.ForeignKey(
        Classification,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    base_salary = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    # BN-32: renewals of fixed-term contracts.
    renewal_count = models.PositiveSmallIntegerField(default=0)
    notes = models.TextField(blank=True)

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
        return f"{self.reference} – {self.employee.full_name}"

    def save(self, *args, **kwargs):
        if not self.reference:
            from core.models import Sequence

            year = self.start_date.year if self.start_date else timezone.now().year
            self.reference = f"CTR-{year}-{Sequence.next_value(f'contract-{year}'):04d}"
        super().save(*args, **kwargs)

    @property
    def is_fixed_term(self):
        return self.contract_type in ("FIXED_TERM", "TEMPORARY", "INTERNSHIP")

    def terms_at(self, day):
        """BN-30: the terms in force at a given date."""
        # The contract row holds the latest agreed terms. Amendments not yet in
        # force at `day` are undone, newest first (effective dates of the
        # successive amendments are increasing, see ContractAmendment).
        terms = {name: getattr(self, name) for name in AMENDABLE_TERMS}
        for amendment in self.amendments.order_by("-version"):
            if amendment.effective_date <= day:
                break
            terms.update(amendment.decoded_previous())
        return terms

    def is_in_force(self, day):
        if self.status == "DRAFT":
            return False
        if self.start_date > day:
            return False
        end = self.effective_end_date
        return end is None or end >= day

    @property
    def effective_end_date(self):
        termination = getattr(self, "termination", None)
        if termination is not None:
            return termination.termination_date
        return self.end_date


def _encode(value):
    if isinstance(value, (datetime.date, Decimal)):
        return str(value)
    return value


def _decode(name, value):
    if value is None:
        return None
    if name == "end_date":
        return datetime.date.fromisoformat(value)
    if name in ("base_salary", "weekly_hours"):
        return Decimal(value)
    return value


class ContractAmendment(models.Model):
    """BN-30: change of salary, position, working time or workplace."""

    contract = models.ForeignKey(
        Contract, on_delete=models.CASCADE, related_name="amendments"
    )
    version = models.PositiveSmallIntegerField()
    effective_date = models.DateField()
    reason = models.CharField(max_length=255)
    previous_values = models.JSONField(default=dict)
    new_values = models.JSONField(default=dict)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["contract", "version"]
        unique_together = ("contract", "version")

    def decoded_previous(self):
        return {k: _decode(k, v) for k, v in self.previous_values.items()}

    def decoded_new(self):
        return {k: _decode(k, v) for k, v in self.new_values.items()}


class ContractRenewal(models.Model):
    """BN-32: renewal of a fixed-term contract."""

    contract = models.ForeignKey(
        Contract, on_delete=models.CASCADE, related_name="renewals"
    )
    previous_end_date = models.DateField(null=True, blank=True)
    new_end_date = models.DateField()
    renewal_number = models.PositiveSmallIntegerField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)


class ContractSuspension(models.Model):
    """BN-33: suspension and its effect on payroll and seniority."""

    REASONS = (
        ("UNPAID_LEAVE", "Unpaid leave"),
        ("SECONDMENT", "Secondment"),
        ("SICK_LEAVE", "Sick leave"),
        ("DETENTION", "Detention"),
        ("DISCIPLINARY", "Disciplinary suspension"),
        ("OTHER", "Other"),
    )

    contract = models.ForeignKey(
        Contract, on_delete=models.CASCADE, related_name="suspensions"
    )
    reason = models.CharField(max_length=20, choices=REASONS)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_paid = models.BooleanField(
        default=False, help_text="Paid suspensions keep the salary (e.g. sick leave)."
    )
    counts_for_seniority = models.BooleanField(default=False)
    comment = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        ordering = ["-start_date"]

    def overlap_days(self, start, end):
        """Number of calendar days of [start, end] covered by the suspension."""
        s_end = self.end_date or end
        first = max(start, self.start_date)
        last = min(end, s_end)
        return max(0, (last - first).days + 1)


class ContractTermination(models.Model):
    """BN-34 / BN-73: end of contract and final settlement."""

    REASONS = (
        ("RESIGNATION", "Resignation"),
        ("DISMISSAL", "Dismissal"),
        ("END_OF_CONTRACT", "End of fixed-term contract"),
        ("TRIAL_END", "End during trial period"),
        ("MUTUAL", "Mutual agreement"),
        ("RETIREMENT", "Retirement"),
        ("DEATH", "Death"),
    )

    contract = models.OneToOneField(
        Contract, on_delete=models.CASCADE, related_name="termination"
    )
    reason = models.CharField(max_length=20, choices=REASONS)
    notification_date = models.DateField()
    termination_date = models.DateField(help_text="Last working day.")
    notice_days = models.PositiveIntegerField(default=0)
    notice_worked = models.BooleanField(default=True)
    leave_balance_days = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    comment = models.TextField(blank=True)
    # Filled by the payroll module (BN-103).
    final_settlement = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)
