"""
M-13 – Accounting of the payroll according to the OHADA system (SYSCOHADA).

The HRMS does not replace the general accounting: it holds the payroll
accounts and delivers balanced, numbered and immutable entries (BN-128 →
BN-147).
"""

from decimal import Decimal

from django.conf import settings
from django.db import models

from employees.models import Employee
from organisation.models import CostCentre, Department


class Account(models.Model):
    """BN-128: chart of accounts organised in classes (configurable length)."""

    number = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["number"]

    def __str__(self):
        return f"{self.number} – {self.name}"

    @property
    def account_class(self):
        return self.number[:1]


class Journal(models.Model):
    """BN-139: payroll journal, miscellaneous operations, bank..."""

    KINDS = (
        ("PAYROLL", "Payroll"),
        ("MISC", "Miscellaneous operations"),
        ("BANK", "Bank / cash"),
    )

    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    kind = models.CharField(max_length=10, choices=KINDS)

    def __str__(self):
        return f"{self.code} – {self.name}"


class FiscalYear(models.Model):
    """BN-137: financial year."""

    year = models.PositiveSmallIntegerField(unique=True)
    status = models.CharField(
        max_length=10, choices=(("OPEN", "Open"), ("CLOSED", "Closed")), default="OPEN"
    )
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-year"]

    def __str__(self):
        return str(self.year)


class AccountingPeriod(models.Model):
    """BN-137: monthly accounting period; a closed period refuses entries."""

    fiscal_year = models.ForeignKey(
        FiscalYear, on_delete=models.CASCADE, related_name="periods"
    )
    month = models.PositiveSmallIntegerField()
    status = models.CharField(
        max_length=10, choices=(("OPEN", "Open"), ("CLOSED", "Closed")), default="OPEN"
    )

    class Meta:
        ordering = ["fiscal_year__year", "month"]
        unique_together = ("fiscal_year", "month")

    def __str__(self):
        return f"{self.month:02d}/{self.fiscal_year.year}"


class AccountMapping(models.Model):
    """
    BN-129 / BN-130: account of every payroll item, dated versions.

    source_type ELEMENT        a salary element (code = element code)
                DEDUCTION      a statutory deduction (code = deduction code)
                LOAN / THIRD_PARTY  deductions from net
                NET_PAY        remuneration due to the personnel
                BANK / CASH    treasury used for the payment
                PROVISION      provision for paid leave
    """

    SOURCES = (
        ("ELEMENT", "Salary element"),
        ("DEDUCTION", "Statutory deduction"),
        ("LOAN", "Loan / advance repayment"),
        ("THIRD_PARTY", "Third-party deduction"),
        ("NET_PAY", "Net remuneration due"),
        ("BANK", "Bank"),
        ("CASH", "Cash"),
        ("PROVISION", "Leave provision"),
    )

    source_type = models.CharField(max_length=20, choices=SOURCES)
    source_code = models.CharField(
        max_length=60, blank=True, help_text="Empty = default of the type."
    )
    debit_account = models.ForeignKey(
        Account, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    credit_account = models.ForeignKey(
        Account, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    employer_debit_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        help_text="Statutory deductions: expense account of the employer share.",
    )
    employer_credit_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        help_text="Statutory deductions: account of the body for the employer share.",
    )
    effective_from = models.DateField()

    class Meta:
        ordering = ["source_type", "source_code", "-effective_from"]


class JournalEntry(models.Model):
    """BN-131 → BN-140: an accounting entry, immutable once saved."""

    SOURCES = (
        ("PAYROLL", "Payroll of the period"),
        ("PAYMENT", "Payment of the salaries"),
        ("SETTLEMENT", "Settlement of contributions and taxes"),
        ("PROVISION", "Leave provision"),
        ("REVERSAL", "Reversal"),
        ("MANUAL", "Manual entry"),
    )

    journal = models.ForeignKey(
        Journal, on_delete=models.PROTECT, related_name="entries"
    )
    number = models.CharField(max_length=30)
    date = models.DateField()
    period = models.ForeignKey(
        AccountingPeriod, on_delete=models.PROTECT, related_name="entries"
    )
    label = models.CharField(max_length=255)
    source = models.CharField(max_length=20, choices=SOURCES)
    payroll_period = models.ForeignKey(
        "payroll.PayrollPeriod",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="entries",
    )
    reference = models.CharField(
        max_length=100, blank=True, help_text="Justifying documents."
    )
    reversal_of = models.OneToOneField(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reversed_by",
    )
    exported_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["journal", "number"]
        unique_together = ("journal", "number")
        verbose_name_plural = "journal entries"

    def __str__(self):
        return f"{self.journal.code} {self.number} – {self.label}"

    @property
    def total_debit(self):
        return sum((line.debit for line in self.lines.all()), Decimal("0"))

    @property
    def total_credit(self):
        return sum((line.credit for line in self.lines.all()), Decimal("0"))

    def save(self, *args, **kwargs):
        # BN-138: intangibility; only the export date may be recorded.
        if self.pk is not None:
            update_fields = kwargs.get("update_fields")
            if not update_fields or set(update_fields) - {"exported_at"}:
                raise PermissionError(
                    "A posted entry cannot be modified: post a reversal."
                )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError("A posted entry cannot be deleted: post a reversal.")


class JournalLine(models.Model):
    entry = models.ForeignKey(
        JournalEntry, on_delete=models.CASCADE, related_name="lines"
    )
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="lines")
    label = models.CharField(max_length=255)
    debit = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    # BN-133 / BN-140: analytical breakdown and traceability.
    department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    cost_centre = models.ForeignKey(
        CostCentre, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    employee = models.ForeignKey(
        Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    third_party = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ["id"]


class Budget(models.Model):
    """BN-144: personnel budget per department (and optionally account) and year."""

    year = models.PositiveSmallIntegerField()
    department = models.ForeignKey(
        Department, on_delete=models.CASCADE, null=True, blank=True, related_name="+"
    )
    account = models.ForeignKey(
        Account, on_delete=models.CASCADE, null=True, blank=True, related_name="+"
    )
    amount = models.DecimalField(max_digits=16, decimal_places=2)

    class Meta:
        ordering = ["-year"]
