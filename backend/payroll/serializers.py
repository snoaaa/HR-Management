from rest_framework import serializers

from .formula import FormulaError, check
from .models import (
    ElementValue,
    Loan,
    ParameterChange,
    PayrollParameter,
    PayrollPeriod,
    Payslip,
    PayslipLine,
    PeriodTransition,
    SalaryElement,
    SalaryGrid,
    Scale,
    StatutoryDeduction,
    ThirdPartyDeduction,
    VariableInput,
)

# Variables provided by the engine itself (see engine.calculate).
ENGINE_VARIABLES = {
    "BASE_FULL",
    "BASE",
    "PRORATA",
    "PAID_DAYS",
    "DAYS_IN_MONTH",
    "MONTH",
    "WEEKLY_HOURS",
    "HOURLY_RATE",
    "SENIORITY_YEARS",
    "MONTHS_WORKED_YEAR",
    "CHILDREN",
    "VALUE",
    "QUANTITY",
    "CASH_GROSS",
    "CASH_TAXABLE",
    "CASH_CONTRIBUTORY",
    "GROSS",
    "CONTRIBUTORY",
    "TAXABLE",
    "BIK",
    "NET_BEFORE_DEDUCTIONS",
}


def known_names():
    names = set(ENGINE_VARIABLES)
    names |= set(PayrollParameter.objects.values_list("code", flat=True))
    names |= set(SalaryElement.objects.values_list("code", flat=True))
    for code in StatutoryDeduction.objects.values_list("code", flat=True):
        names |= {code, f"{code}_EMPLOYER"}
    return names


def validate_formula(value, extra=()):
    if not value:
        return value
    try:
        check(value, known_names() | set(extra))
    except FormulaError as exc:
        raise serializers.ValidationError(str(exc))
    return value


class PayrollParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayrollParameter
        fields = "__all__"

    def validate_code(self, value):
        if not value.replace("_", "").isalnum() or not value.isupper():
            raise serializers.ValidationError(
                "Use upper-case letters, digits and underscores."
            )
        return value


class ScaleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scale
        fields = "__all__"

    def validate(self, attrs):
        kind = attrs.get("kind", getattr(self.instance, "kind", None))
        key = "rate" if kind == "PROGRESSIVE" else "amount"
        for bracket in attrs.get("brackets", []):
            if "from" not in bracket or key not in bracket:
                raise serializers.ValidationError(
                    f'Each bracket needs "from", "to" and "{key}".'
                )
        return attrs


class StatutoryDeductionSerializer(serializers.ModelSerializer):
    body_label = serializers.CharField(source="get_body_display", read_only=True)

    class Meta:
        model = StatutoryDeduction
        fields = "__all__"

    def validate_base_formula(self, value):
        return validate_formula(value)

    def validate_condition_formula(self, value):
        return validate_formula(value)


class SalaryElementSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalaryElement
        fields = "__all__"

    def validate(self, attrs):
        code = attrs.get("code", getattr(self.instance, "code", ""))
        validate_formula(attrs.get("formula"), extra={code})
        validate_formula(attrs.get("rate_base"), extra={code})
        method = attrs.get("method", getattr(self.instance, "method", "FIXED"))
        if method == "FORMULA" and not attrs.get(
            "formula", getattr(self.instance, "formula", "")
        ):
            raise serializers.ValidationError("The formula method requires a formula.")
        if attrs.get("periodicity") == "ANNUAL" and not attrs.get("payment_month"):
            raise serializers.ValidationError(
                "An annual element requires its month of payment."
            )
        return attrs


class ElementValueSerializer(serializers.ModelSerializer):
    element_code = serializers.CharField(source="element.code", read_only=True)
    element_name = serializers.CharField(source="element.name", read_only=True)
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    classification_label = serializers.CharField(
        source="classification.__str__", read_only=True
    )
    level = serializers.CharField(read_only=True)

    class Meta:
        model = ElementValue
        fields = "__all__"

    def validate(self, attrs):
        targets = [attrs.get(k) for k in ("employee", "department", "classification")]
        if sum(t is not None for t in targets) != 1:
            raise serializers.ValidationError(
                "Choose exactly one level: employee, department or category."
            )
        return attrs


class SalaryGridSerializer(serializers.ModelSerializer):
    classification_label = serializers.CharField(
        source="classification.__str__", read_only=True
    )

    class Meta:
        model = SalaryGrid
        fields = "__all__"


class ParameterChangeSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.username", read_only=True)

    class Meta:
        model = ParameterChange
        fields = "__all__"


class PeriodTransitionSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = PeriodTransition
        fields = "__all__"


class PayrollPeriodSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    is_locked = serializers.BooleanField(read_only=True)
    transitions = PeriodTransitionSerializer(many=True, read_only=True)
    totals = serializers.SerializerMethodField()

    class Meta:
        model = PayrollPeriod
        fields = "__all__"
        read_only_fields = ("status", "validated_at", "validated_by")

    def get_totals(self, period):
        from django.db.models import Count, Sum

        payslips = period.payslips.exclude(status="REVERSED")
        data = payslips.aggregate(
            count=Count("id"),
            gross=Sum("gross"),
            net_payable=Sum("net_payable"),
            employee_contributions=Sum("employee_contributions"),
            employer_contributions=Sum("employer_contributions"),
            taxes=Sum("taxes"),
        )
        data["anomalies"] = sum(
            1
            for p in payslips.only("anomalies")
            if any(a.get("blocking") for a in p.anomalies)
        )
        return data


class PayslipLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayslipLine
        exclude = ("payslip",)


class PayslipSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    matriculation = serializers.CharField(
        source="employee.matriculation_number", read_only=True
    )
    department_name = serializers.CharField(
        source="employee.department.name", read_only=True
    )
    period_label = serializers.CharField(source="period.__str__", read_only=True)
    has_blocking_anomaly = serializers.BooleanField(read_only=True)
    total_cost = serializers.DecimalField(
        max_digits=16, decimal_places=2, read_only=True
    )

    class Meta:
        model = Payslip
        exclude = ("snapshot",)


class PayslipDetailSerializer(PayslipSerializer):
    lines = PayslipLineSerializer(many=True, read_only=True)

    class Meta(PayslipSerializer.Meta):
        exclude = ()
        fields = "__all__"


class VariableInputSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    element_code = serializers.CharField(source="element.code", read_only=True)
    element_name = serializers.CharField(source="element.name", read_only=True)

    class Meta:
        model = VariableInput
        fields = "__all__"
        read_only_fields = ("source", "created_by")

    def validate(self, attrs):
        period = attrs.get("period", getattr(self.instance, "period", None))
        if period is not None and period.is_locked:
            raise serializers.ValidationError("The period is validated.")
        if attrs.get("quantity") is None and attrs.get("amount") is None:
            raise serializers.ValidationError("Enter a quantity or an amount.")
        return attrs


class LoanSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    repaid = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    remaining = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True
    )

    class Meta:
        model = Loan
        fields = "__all__"
        read_only_fields = ("created_by",)

    def validate(self, attrs):
        if attrs.get("installment", 1) <= 0 or attrs.get("amount", 1) <= 0:
            raise serializers.ValidationError("Amount and instalment must be positive.")
        if attrs.get("installment", 0) > attrs.get("amount", 0):
            raise serializers.ValidationError("The instalment exceeds the amount.")
        return attrs


class ThirdPartyDeductionSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    deducted = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = ThirdPartyDeduction
        fields = "__all__"

    def validate(self, attrs):
        if not attrs.get("monthly_amount") and not attrs.get("rate_of_net"):
            raise serializers.ValidationError(
                "Enter a monthly amount or a rate of the net salary."
            )
        return attrs
