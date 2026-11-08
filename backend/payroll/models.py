"""
M-11 – Payroll management.

Governing rules of the Product Owner:
- no rate, ceiling, scale or threshold in the source code: every value is a
  dated PayrollParameter, Scale or StatutoryDeduction version (BN-89);
- recalculating a past period gives the same result, because the versions
  in force at the end of the period are used and a snapshot of every input
  is kept on the payslip (BN-109);
- a validated period is never modified, only reversed (BN-108).
"""

from decimal import Decimal

from django.conf import settings
from django.db import models

from employees.models import Employee
from organisation.models import Classification, Department


class PayrollParameter(models.Model):
    """BN-89 / BN-92: dated value used by the formulas (rates, ceilings...)."""

    UNITS = (
        ("PERCENT", "Percentage"),
        ("AMOUNT", "Amount"),
        ("NUMBER", "Number"),
    )

    code = models.CharField(max_length=60)
    name = models.CharField(max_length=150)
    value = models.DecimalField(max_digits=16, decimal_places=4)
    unit = models.CharField(max_length=10, choices=UNITS, default="AMOUNT")
    effective_from = models.DateField()
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["code", "-effective_from"]
        unique_together = ("code", "effective_from")

    def __str__(self):
        return f"{self.code}={self.value} (from {self.effective_from})"


class Scale(models.Model):
    """
    BN-89: scales. PROGRESSIVE applies each rate to the slice of the base
    (income tax); FLAT returns the amount of the bracket containing the base
    (audiovisual fee, local development tax).
    brackets: [{"from": 0, "to": 2000000, "rate": 10}, ...] or
              [{"from": 0, "to": 50000, "amount": 0}, ...]; "to": null = no limit.
    """

    KINDS = (("PROGRESSIVE", "Progressive rates"), ("FLAT", "Flat amount per bracket"))

    code = models.CharField(max_length=60)
    name = models.CharField(max_length=150)
    kind = models.CharField(max_length=20, choices=KINDS)
    brackets = models.JSONField(default=list)
    effective_from = models.DateField()

    class Meta:
        ordering = ["code", "-effective_from"]
        unique_together = ("code", "effective_from")

    def __str__(self):
        return f"{self.name} (from {self.effective_from})"


class StatutoryDeduction(models.Model):
    """
    BN-89: social contribution or tax withheld at source, as dated versions.

    RATE    base x employee rate / employer rate, within floor and ceiling.
    SCALE   the scale applied to the base, divided by result_divisor.
    PERCENT_OF  rate x the employee amount of another deduction (e.g. the
            additional council tax is a percentage of the income tax).
    base_formula uses the payroll variables (GROSS, TAXABLE, CONTRIBUTORY,
    BASE, parameters, previous deductions...). condition_formula, when set,
    must be true for the deduction to apply.
    """

    METHODS = (
        ("RATE", "Rates"),
        ("SCALE", "Scale"),
        ("PERCENT_OF", "Percentage of another deduction"),
    )
    BODIES = (
        ("CNPS", "Social insurance (CNPS)"),
        ("TAX", "Tax administration"),
        ("CFC", "Crédit Foncier"),
        ("FNE", "National Employment Fund"),
        ("COMMUNE", "Council"),
        ("CRTV", "Audiovisual fee"),
        ("OTHER", "Other"),
    )

    code = models.CharField(max_length=60)
    name = models.CharField(max_length=150)
    body = models.CharField(max_length=20, choices=BODIES)
    method = models.CharField(max_length=20, choices=METHODS, default="RATE")
    base_formula = models.CharField(max_length=500, default="CONTRIBUTORY")
    employee_rate = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    employer_rate = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    ceiling = models.DecimalField(
        max_digits=16, decimal_places=2, null=True, blank=True
    )
    floor = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    scale_code = models.CharField(max_length=60, blank=True)
    result_divisor = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal("1")
    )
    percent_of_code = models.CharField(max_length=60, blank=True)
    condition_formula = models.CharField(max_length=500, blank=True)
    order = models.PositiveSmallIntegerField(default=10)
    on_payslip = models.BooleanField(default=True)
    effective_from = models.DateField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "code", "-effective_from"]
        unique_together = ("code", "effective_from")

    def __str__(self):
        return f"{self.name} (from {self.effective_from})"


class SalaryElement(models.Model):
    """BN-87 / BN-88: configurable catalogue of salary elements."""

    KINDS = (
        ("GAIN", "Gain"),
        ("GROSS_DEDUCTION", "Deduction from gross (e.g. absence)"),
        ("NET_DEDUCTION", "Deduction from net (e.g. loan)"),
    )
    METHODS = (
        ("FIXED", "Fixed amount"),
        ("RATE", "Rate x base"),
        ("FORMULA", "Formula"),
        ("QUANTITY", "Quantity x unit value"),
    )
    PERIODICITIES = (("MONTHLY", "Every month"), ("ANNUAL", "Once a year"))

    code = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=150)
    kind = models.CharField(max_length=20, choices=KINDS, default="GAIN")
    method = models.CharField(max_length=20, choices=METHODS, default="FIXED")
    default_value = models.DecimalField(
        max_digits=16,
        decimal_places=4,
        default=0,
        help_text="Amount (fixed), rate in % (rate), unit value (quantity).",
    )
    rate_base = models.CharField(
        max_length=255,
        blank=True,
        help_text="Formula of the base for the 'rate' method.",
    )
    formula = models.CharField(
        max_length=500,
        blank=True,
        help_text="Formula of the amount, or of the unit value for 'quantity'.",
    )
    is_contributory = models.BooleanField(default=True)
    is_taxable = models.BooleanField(default=True)
    in_leave_allowance_base = models.BooleanField(default=True)
    is_benefit_in_kind = models.BooleanField(
        default=False, help_text="BN-102: taxed but not paid in cash."
    )
    prorated = models.BooleanField(
        default=True, help_text="Reduced pro rata of the days paid (BN-96)."
    )
    applies_to_all = models.BooleanField(
        default=False,
        help_text="Computed for every employee; otherwise only when a value is assigned.",
    )
    periodicity = models.CharField(
        max_length=10, choices=PERIODICITIES, default="MONTHLY"
    )
    payment_month = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text="Month of payment of an annual element."
    )
    on_payslip = models.BooleanField(default=True)
    payslip_order = models.PositiveSmallIntegerField(default=100)
    is_system = models.BooleanField(
        default=False, help_text="Fed automatically by attendance, leave or loans."
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["payslip_order", "code"]

    def __str__(self):
        return f"{self.code} – {self.name}"


class ElementValue(models.Model):
    """
    BN-91: value of an element at three levels; the most specific wins:
    employee > department > category (classification) > default value.
    """

    element = models.ForeignKey(
        SalaryElement, on_delete=models.CASCADE, related_name="values"
    )
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="element_values",
    )
    department = models.ForeignKey(
        Department, on_delete=models.CASCADE, null=True, blank=True, related_name="+"
    )
    classification = models.ForeignKey(
        Classification,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="+",
    )
    value = models.DecimalField(max_digits=16, decimal_places=4)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    comment = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["element", "-effective_from"]

    @property
    def level(self):
        if self.employee_id:
            return "EMPLOYEE"
        if self.department_id:
            return "DEPARTMENT"
        if self.classification_id:
            return "CATEGORY"
        return "DEFAULT"


class SalaryGrid(models.Model):
    """BN-90: base salary of each category / grade / echelon, dated."""

    classification = models.ForeignKey(
        Classification, on_delete=models.CASCADE, related_name="salary_grid"
    )
    base_salary = models.DecimalField(max_digits=14, decimal_places=2)
    effective_from = models.DateField()

    class Meta:
        ordering = ["classification", "-effective_from"]
        unique_together = ("classification", "effective_from")


class ParameterChange(models.Model):
    """BN-92: history of every change of a payroll setting."""

    object_type = models.CharField(max_length=60)
    object_code = models.CharField(max_length=60)
    effective_from = models.DateField(null=True, blank=True)
    previous_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-changed_at"]


class PayrollPeriod(models.Model):
    """BN-93: the monthly payroll cycle and its explicit states."""

    STATUSES = (
        ("OPENED", "Opened"),
        ("IN_PREPARATION", "In preparation"),
        ("CALCULATED", "Calculated"),
        ("VERIFIED", "Verified"),
        ("VALIDATED", "Validated"),
        ("PAID", "Paid"),
        ("POSTED", "Posted"),
        ("CLOSED", "Closed"),
    )
    LOCKED_STATUSES = ("VALIDATED", "PAID", "POSTED", "CLOSED")

    year = models.PositiveSmallIntegerField()
    month = models.PositiveSmallIntegerField()
    status = models.CharField(max_length=20, choices=STATUSES, default="OPENED")
    payment_date = models.DateField(null=True, blank=True)
    validated_at = models.DateTimeField(null=True, blank=True)
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        ordering = ["-year", "-month"]
        unique_together = ("year", "month")

    def __str__(self):
        return f"{self.month:02d}/{self.year}"

    @property
    def is_locked(self):
        return self.status in self.LOCKED_STATUSES

    @property
    def start_date(self):
        import datetime

        return datetime.date(self.year, self.month, 1)

    @property
    def end_date(self):
        import calendar
        import datetime

        return datetime.date(
            self.year, self.month, calendar.monthrange(self.year, self.month)[1]
        )


class PeriodTransition(models.Model):
    """BN-93 / BN-108: every change of state of a period is traced."""

    period = models.ForeignKey(
        PayrollPeriod, on_delete=models.CASCADE, related_name="transitions"
    )
    from_status = models.CharField(max_length=20)
    to_status = models.CharField(max_length=20)
    comment = models.CharField(max_length=255, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["at"]


class VariableInput(models.Model):
    """BN-94: variable elements of the period."""

    SOURCES = (
        ("MANUAL", "Manual entry"),
        ("ATTENDANCE", "Attendance"),
        ("LEAVE", "Leave"),
        ("CAREER", "Career / back pay"),
        ("SETTLEMENT", "Final settlement"),
    )

    period = models.ForeignKey(
        PayrollPeriod, on_delete=models.CASCADE, related_name="inputs"
    )
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="payroll_inputs"
    )
    element = models.ForeignKey(SalaryElement, on_delete=models.PROTECT)
    quantity = models.DecimalField(
        max_digits=12, decimal_places=4, null=True, blank=True
    )
    amount = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Overrides the computed amount.",
    )
    source = models.CharField(max_length=20, choices=SOURCES, default="MANUAL")
    comment = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        ordering = ["employee", "element__payslip_order"]


class Loan(models.Model):
    """BN-98: salary advances and loans with their repayment schedule."""

    KINDS = (("ADVANCE", "Salary advance"), ("LOAN", "Loan"))
    STATUSES = (
        ("ACTIVE", "Being repaid"),
        ("REPAID", "Repaid"),
        ("CANCELLED", "Cancelled"),
    )

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="loans"
    )
    kind = models.CharField(max_length=10, choices=KINDS, default="LOAN")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    installment = models.DecimalField(max_digits=14, decimal_places=2)
    granted_on = models.DateField()
    first_year = models.PositiveSmallIntegerField()
    first_month = models.PositiveSmallIntegerField()
    status = models.CharField(max_length=10, choices=STATUSES, default="ACTIVE")
    comment = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        ordering = ["-granted_on"]

    @property
    def repaid(self):
        total = self.repayments.filter(payslip__status__in=("VALIDATED",)).aggregate(
            s=models.Sum("amount")
        )["s"]
        return total or Decimal("0")

    @property
    def remaining(self):
        return self.amount - self.repaid


class ThirdPartyDeduction(models.Model):
    """BN-99: garnishment, alimony, union dues, with ceiling and beneficiary."""

    KINDS = (
        ("GARNISHMENT", "Garnishment of salary"),
        ("ALIMONY", "Alimony"),
        ("UNION", "Union dues"),
        ("OTHER", "Other"),
    )

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="third_party_deductions"
    )
    kind = models.CharField(max_length=20, choices=KINDS)
    beneficiary = models.CharField(max_length=150)
    monthly_amount = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    rate_of_net = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="% of the net salary.",
    )
    total_ceiling = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Total to deduct (empty = no limit).",
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    @property
    def deducted(self):
        total = self.repayments.filter(payslip__status="VALIDATED").aggregate(
            s=models.Sum("amount")
        )["s"]
        return total or Decimal("0")


class Payslip(models.Model):
    STATUSES = (
        ("CALCULATED", "Calculated"),
        ("VALIDATED", "Validated"),
        ("REVERSED", "Reversed"),
    )
    PAYMENT_METHODS = Employee.PAYMENT_METHOD_CHOICES

    period = models.ForeignKey(
        PayrollPeriod, on_delete=models.CASCADE, related_name="payslips"
    )
    employee = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name="payslips"
    )
    contract = models.ForeignKey(
        "contracts.Contract",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    status = models.CharField(max_length=20, choices=STATUSES, default="CALCULATED")
    paid_days = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    prorata = models.DecimalField(max_digits=8, decimal_places=6, default=1)
    base_salary = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    gross = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    contributory_base = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    taxable_base = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    employee_contributions = models.DecimalField(
        max_digits=16, decimal_places=2, default=0
    )
    employer_contributions = models.DecimalField(
        max_digits=16, decimal_places=2, default=0
    )
    taxes = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    other_deductions = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    net_salary = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    benefits_in_kind = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    net_payable = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    payment_method = models.CharField(
        max_length=20, choices=PAYMENT_METHODS, default="TRANSFER"
    )
    bank_name = models.CharField(max_length=150, blank=True)
    bank_account = models.CharField(max_length=120, blank=True)
    anomalies = models.JSONField(default=list, blank=True)
    snapshot = models.JSONField(default=dict, blank=True)
    leave_balance = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    calculated_at = models.DateTimeField(auto_now=True)
    reversal_of = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        ordering = ["employee__surname", "employee__given_names"]

    @property
    def total_cost(self):
        return self.gross + self.employer_contributions

    @property
    def has_blocking_anomaly(self):
        return any(a.get("blocking") for a in self.anomalies)


class PayslipLine(models.Model):
    KINDS = (
        ("GAIN", "Gain"),
        ("GROSS_DEDUCTION", "Deduction from gross"),
        ("CONTRIBUTION", "Social contribution"),
        ("TAX", "Tax"),
        ("NET_DEDUCTION", "Deduction from net"),
        ("INFO", "Information"),
    )

    payslip = models.ForeignKey(Payslip, on_delete=models.CASCADE, related_name="lines")
    code = models.CharField(max_length=60)
    label = models.CharField(max_length=150)
    kind = models.CharField(max_length=20, choices=KINDS)
    body = models.CharField(max_length=20, blank=True)
    base = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    rate = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    employer_rate = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True
    )
    quantity = models.DecimalField(
        max_digits=12, decimal_places=4, null=True, blank=True
    )
    amount = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    employer_amount = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    is_contributory = models.BooleanField(default=False)
    is_taxable = models.BooleanField(default=False)
    on_payslip = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=100)

    class Meta:
        ordering = ["order", "id"]


class LoanRepayment(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name="repayments")
    payslip = models.ForeignKey(
        Payslip, on_delete=models.CASCADE, related_name="loan_repayments"
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)


class ThirdPartyRepayment(models.Model):
    deduction = models.ForeignKey(
        ThirdPartyDeduction, on_delete=models.CASCADE, related_name="repayments"
    )
    payslip = models.ForeignKey(
        Payslip, on_delete=models.CASCADE, related_name="third_party_repayments"
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)


class BackPayAdjustment(models.Model):
    """BN-100: back pay paid in a period for a past period."""

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="back_pay"
    )
    source_period = models.ForeignKey(
        PayrollPeriod, on_delete=models.CASCADE, related_name="+"
    )
    target_period = models.ForeignKey(
        PayrollPeriod, on_delete=models.CASCADE, related_name="+"
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)


class LeaveProvision(models.Model):
    """BN-112: provision for leave not yet taken at the end of the period."""

    period = models.ForeignKey(
        PayrollPeriod, on_delete=models.CASCADE, related_name="provisions"
    )
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="+")
    days = models.DecimalField(max_digits=8, decimal_places=2)
    daily_rate = models.DecimalField(max_digits=14, decimal_places=2)
    amount = models.DecimalField(max_digits=16, decimal_places=2)

    class Meta:
        unique_together = ("period", "employee")
