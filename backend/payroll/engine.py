"""
Payroll calculation engine (BN-94 → BN-106).

The engine never contains a legal value: rates, ceilings, scales and
thresholds are read from the versions in force at the end of the period.
"""

import calendar
import datetime
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Q

from core.models import get_setting

from .formula import FormulaError, evaluate
from .models import (
    ElementValue,
    Loan,
    PayrollParameter,
    SalaryElement,
    SalaryGrid,
    Scale,
    StatutoryDeduction,
    ThirdPartyDeduction,
    VariableInput,
)

ZERO = Decimal("0")
TAX_BODIES = ("TAX", "CRTV", "COMMUNE")


def rounding_unit():
    try:
        return Decimal(get_setting("ROUNDING_UNIT", "1"))
    except Exception:
        return Decimal("1")


def money(value, unit=None):
    """BN-146: one single rounding rule for every amount."""
    unit = unit or rounding_unit()
    return (Decimal(value) / unit).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * unit


# --------------------------------------------------------------------------
# Versioned settings
# --------------------------------------------------------------------------


def parameters_at(day):
    """{code: value} of the parameter versions in force at `day`."""
    values = {}
    for param in PayrollParameter.objects.filter(effective_from__lte=day).order_by(
        "code", "-effective_from"
    ):
        values.setdefault(param.code, param.value)
    return values


def deductions_at(day):
    latest = {}
    for deduction in StatutoryDeduction.objects.filter(
        effective_from__lte=day
    ).order_by("code", "-effective_from"):
        latest.setdefault(deduction.code, deduction)
    return sorted(
        (d for d in latest.values() if d.is_active), key=lambda d: (d.order, d.code)
    )


def scale_at(code, day):
    return (
        Scale.objects.filter(code=code, effective_from__lte=day)
        .order_by("-effective_from")
        .first()
    )


def apply_scale(scale, base):
    base = Decimal(base)
    if scale is None or base <= 0:
        return ZERO
    if scale.kind == "PROGRESSIVE":
        total = ZERO
        for bracket in scale.brackets:
            low = Decimal(str(bracket.get("from", 0)))
            high = bracket.get("to")
            high = Decimal(str(high)) if high is not None else None
            if base <= low:
                continue
            top = base if high is None else min(base, high)
            total += (top - low) * Decimal(str(bracket.get("rate", 0))) / 100
        return total
    for bracket in scale.brackets:
        low = Decimal(str(bracket.get("from", 0)))
        high = bracket.get("to")
        if base >= low and (high is None or base <= Decimal(str(high))):
            return Decimal(str(bracket.get("amount", 0)))
    return ZERO


def resolve_value(element, employee, classification_id, day):
    """BN-91: employee > department > category > default."""
    values = ElementValue.objects.filter(
        element=element, effective_from__lte=day
    ).filter(Q(effective_to__isnull=True) | Q(effective_to__gte=day))
    lookups = [
        {"employee": employee},
        {"department_id": employee.department_id, "employee__isnull": True},
        {
            "classification_id": classification_id,
            "employee__isnull": True,
            "department__isnull": True,
        },
    ]
    if employee.pk is None:
        lookups = lookups[1:]
    for lookup in lookups:
        if any(v is None for k, v in lookup.items() if k.endswith("_id")):
            continue
        value = values.filter(**lookup).order_by("-effective_from").first()
        if value is not None:
            return value.value, True
    return element.default_value, False


# --------------------------------------------------------------------------
# Result
# --------------------------------------------------------------------------


@dataclass
class Line:
    code: str
    label: str
    kind: str
    amount: Decimal = ZERO
    employer_amount: Decimal = ZERO
    base: Decimal = None
    rate: Decimal = None
    employer_rate: Decimal = None
    quantity: Decimal = None
    body: str = ""
    is_contributory: bool = False
    is_taxable: bool = False
    on_payslip: bool = True
    order: int = 100


@dataclass
class Result:
    employee: object
    contract: object = None
    paid_days: Decimal = ZERO
    prorata: Decimal = Decimal("1")
    base_salary: Decimal = ZERO
    lines: list = field(default_factory=list)
    gross: Decimal = ZERO
    contributory_base: Decimal = ZERO
    taxable_base: Decimal = ZERO
    employee_contributions: Decimal = ZERO
    employer_contributions: Decimal = ZERO
    taxes: Decimal = ZERO
    other_deductions: Decimal = ZERO
    net_salary: Decimal = ZERO
    benefits_in_kind: Decimal = ZERO
    net_payable: Decimal = ZERO
    anomalies: list = field(default_factory=list)
    snapshot: dict = field(default_factory=dict)
    loan_repayments: list = field(default_factory=list)
    third_party_repayments: list = field(default_factory=list)

    def anomaly(self, code, message, blocking=True):
        self.anomalies.append({"code": code, "message": message, "blocking": blocking})

    @property
    def has_blocking_anomaly(self):
        return any(a["blocking"] for a in self.anomalies)


# --------------------------------------------------------------------------
# Context of the employee for the period
# --------------------------------------------------------------------------


def _contract_for_period(employee, start, end):
    if employee.pk is None:  # hiring simulation
        return None
    contracts = (
        employee.contracts.exclude(status="DRAFT")
        .select_related("termination")
        .prefetch_related("suspensions")
        .order_by("-start_date")
    )
    for contract in contracts:
        if contract.start_date <= end and (
            contract.effective_end_date is None or contract.effective_end_date >= start
        ):
            return contract
    return None


def _paid_days(employee, start, end):
    """Calendar days under contract in the period, minus unpaid suspensions."""
    contracts = list(
        employee.contracts.exclude(status="DRAFT")
        .select_related("termination")
        .prefetch_related("suspensions")
    )
    days = 0
    day = start
    while day <= end:
        in_force = [c for c in contracts if c.is_in_force(day)]
        if in_force:
            suspended = any(
                not s.is_paid
                and s.start_date <= day
                and (s.end_date is None or s.end_date >= day)
                for c in in_force
                for s in c.suspensions.all()
            )
            if not suspended:
                days += 1
        day += datetime.timedelta(days=1)
    return days


def _seniority_years(employee, day):
    if employee.pk is None:
        return ZERO
    try:
        from contracts.services import seniority_days

        days = seniority_days(employee, day)
        if days:
            return Decimal(days) / Decimal("365.25")
    except ImportError:
        pass
    if employee.date_of_hire and employee.date_of_hire <= day:
        return Decimal((day - employee.date_of_hire).days) / Decimal("365.25")
    return ZERO


def _months_worked_in_year(employee, year, month):
    if employee.pk is None:
        return month
    count = 0
    for m in range(1, month + 1):
        start = datetime.date(year, m, 1)
        end = datetime.date(year, m, calendar.monthrange(year, m)[1])
        if _contract_for_period(employee, start, end) is not None:
            count += 1
    return count


def _children(employee, day):
    if employee.pk is None:
        return 0
    return employee.family_members.filter(
        relationship="CHILD", date_of_birth__lte=day
    ).count()


def _str(value):
    return str(value) if isinstance(value, Decimal) else value


# --------------------------------------------------------------------------
# Calculation
# --------------------------------------------------------------------------


def calculate(employee, period, overrides=None, inputs=None):
    """
    Compute the payslip of an employee for a period without saving it.
    overrides: simulation values (base_salary, classification_id,
    weekly_hours, elements={code: value}).
    inputs: list of VariableInput-like objects (default: those of the period).
    """
    overrides = overrides or {}
    start, end = period.start_date, period.end_date
    result = Result(employee=employee)
    params = parameters_at(end)
    unit = rounding_unit()

    contract = _contract_for_period(employee, start, end)
    result.contract = contract
    terms = contract.terms_at(end) if contract else {}
    if (
        contract is not None
        and contract.effective_end_date
        and contract.effective_end_date < end
    ):
        terms = contract.terms_at(contract.effective_end_date)
    classification_id = overrides.get(
        "classification_id",
        terms.get("classification_id") or employee.classification_id,
    )
    base_full = Decimal(overrides.get("base_salary", terms.get("base_salary") or 0))
    weekly_hours = Decimal(
        overrides.get("weekly_hours", terms.get("weekly_hours") or 40)
    )
    if "base_salary" in overrides and contract is None:
        paid_days = calendar.monthrange(period.year, period.month)[1]
    else:
        paid_days = _paid_days(employee, start, end)
    if contract is None and "base_salary" not in overrides:
        result.anomaly(
            "NO_CONTRACT", "Employee without a contract in force during the period."
        )

    days_in_month = Decimal(calendar.monthrange(period.year, period.month)[1])
    prorata = (Decimal(paid_days) / days_in_month).quantize(Decimal("0.000001"))
    result.paid_days = Decimal(paid_days)
    result.prorata = prorata
    base = money(base_full * prorata, unit)
    result.base_salary = base

    hours_per_month = params.get("HOURS_PER_MONTH", Decimal("173.33"))
    variables = {
        **params,
        "BASE_FULL": base_full,
        "BASE": base,
        "PRORATA": prorata,
        "PAID_DAYS": Decimal(paid_days),
        "DAYS_IN_MONTH": days_in_month,
        "MONTH": Decimal(period.month),
        "WEEKLY_HOURS": weekly_hours,
        "HOURLY_RATE": (base_full / hours_per_month) if hours_per_month else ZERO,
        "SENIORITY_YEARS": _seniority_years(employee, end).quantize(Decimal("0.01")),
        "MONTHS_WORKED_YEAR": Decimal(
            _months_worked_in_year(employee, period.year, period.month)
        ),
        "CHILDREN": Decimal(_children(employee, end)),
    }

    if inputs is None and employee.pk is None:
        inputs = []
    if inputs is None:
        inputs = list(
            VariableInput.objects.filter(
                period=period, employee=employee
            ).select_related("element")
        )
    inputs_by_element = {}
    for item in inputs:
        inputs_by_element.setdefault(item.element.code, []).append(item)

    elements = list(SalaryElement.objects.filter(is_active=True))
    # Variables of the engine are never overwritten by an element of the
    # same name (e.g. the BASE element shows the BASE variable).
    reserved = set(variables)
    element_overrides = overrides.get("elements", {})

    def applicable(element):
        if element.periodicity == "ANNUAL" and element.payment_month != period.month:
            return element.code in inputs_by_element
        if element.code in inputs_by_element or element.code in element_overrides:
            return True
        if element.is_system:
            return element.applies_to_all
        if element.applies_to_all:
            return True
        return resolve_value(element, employee, classification_id, end)[1]

    def compute_element(element):
        if element.code in element_overrides:
            value = Decimal(str(element_overrides[element.code]))
        else:
            value = resolve_value(element, employee, classification_id, end)[0]
        variables["VALUE"] = value
        amounts = []
        items = inputs_by_element.get(element.code, [])
        if items:
            for item in items:
                quantity = item.quantity if item.quantity is not None else Decimal("1")
                variables["QUANTITY"] = quantity
                if item.amount is not None:
                    amounts.append((Decimal(item.amount), item.quantity, None))
                elif element.method == "QUANTITY":
                    unit_value = (
                        evaluate(element.formula, variables)
                        if element.formula
                        else value
                    )
                    amounts.append((quantity * unit_value, quantity, unit_value))
                else:
                    amounts.append((_amount(element, value), None, None))
        else:
            variables["QUANTITY"] = ZERO
            if element.method == "QUANTITY":
                return []
            amounts.append((_amount(element, value), None, None))
        return amounts

    def _amount(element, value):
        if element.method == "FIXED":
            return value * prorata if element.prorated else value
        if element.method == "RATE":
            return evaluate(element.rate_base or "BASE", variables) * value / 100
        return evaluate(element.formula, variables)

    def add_element_lines(selected):
        for element in selected:
            if not applicable(element):
                continue
            try:
                amounts = compute_element(element)
            except FormulaError as exc:
                result.anomaly("FORMULA", f"{element.code}: {exc}")
                continue
            total = ZERO
            for amount, quantity, unit_value in amounts:
                amount = money(amount, unit)
                if amount == 0 and element.code != "BASE":
                    continue
                total += amount
                result.lines.append(
                    Line(
                        code=element.code,
                        label=element.name,
                        kind=element.kind,
                        amount=amount,
                        quantity=quantity,
                        rate=(
                            unit_value
                            if unit_value is not None
                            else (
                                element.default_value
                                if element.method == "RATE"
                                else None
                            )
                        ),
                        is_contributory=element.is_contributory,
                        is_taxable=element.is_taxable,
                        on_payslip=element.on_payslip,
                        order=element.payslip_order,
                    )
                )
            if element.code not in reserved:
                variables[element.code] = variables.get(element.code, ZERO) + total

    def totals():
        gross = contributory = taxable = bik = ZERO
        for line in result.lines:
            sign = (
                1
                if line.kind == "GAIN"
                else -1 if line.kind == "GROSS_DEDUCTION" else 0
            )
            if not sign:
                continue
            gross += sign * line.amount
            if line.is_contributory:
                contributory += sign * line.amount
            if line.is_taxable:
                taxable += sign * line.amount
        bik = sum(
            (
                line.amount
                for line in result.lines
                if line.kind == "GAIN" and line.code in bik_codes
            ),
            ZERO,
        )
        return gross, contributory, taxable, bik

    bik_codes = {e.code for e in elements if e.is_benefit_in_kind}
    gross_elements = [e for e in elements if e.kind in ("GAIN", "GROSS_DEDUCTION")]
    add_element_lines([e for e in gross_elements if not e.is_benefit_in_kind])
    gross, contributory, taxable, _ = totals()
    variables.update(
        {
            "CASH_GROSS": gross,
            "CASH_TAXABLE": taxable,
            "CASH_CONTRIBUTORY": contributory,
        }
    )
    add_element_lines([e for e in gross_elements if e.is_benefit_in_kind])
    gross, contributory, taxable, bik = totals()
    variables.update(
        {"GROSS": gross, "CONTRIBUTORY": contributory, "TAXABLE": taxable, "BIK": bik}
    )
    result.gross, result.contributory_base, result.taxable_base = (
        gross,
        contributory,
        taxable,
    )
    result.benefits_in_kind = bik

    # Statutory deductions (BN-95) ------------------------------------------
    used_versions = {}
    for deduction in deductions_at(end):
        try:
            if deduction.condition_formula and not evaluate(
                deduction.condition_formula, variables
            ):
                variables[deduction.code] = ZERO
                variables[f"{deduction.code}_EMPLOYER"] = ZERO
                continue
            employee_amount = employer_amount = ZERO
            line_base = None
            if deduction.method == "RATE":
                line_base = evaluate(deduction.base_formula, variables)
                if deduction.floor is not None and 0 < line_base < deduction.floor:
                    line_base = deduction.floor
                if deduction.ceiling is not None:
                    line_base = min(line_base, deduction.ceiling)
                line_base = max(line_base, ZERO)
                employee_amount = line_base * deduction.employee_rate / 100
                employer_amount = line_base * deduction.employer_rate / 100
            elif deduction.method == "SCALE":
                line_base = max(evaluate(deduction.base_formula, variables), ZERO)
                divisor = deduction.result_divisor or Decimal("1")
                employee_amount = (
                    apply_scale(scale_at(deduction.scale_code, end), line_base)
                    / divisor
                )
            else:
                line_base = variables.get(deduction.percent_of_code, ZERO)
                employee_amount = line_base * deduction.employee_rate / 100
                employer_amount = (
                    variables.get(f"{deduction.percent_of_code}_EMPLOYER", ZERO)
                    * deduction.employer_rate
                    / 100
                )
        except FormulaError as exc:
            result.anomaly("FORMULA", f"{deduction.code}: {exc}")
            continue
        employee_amount, employer_amount = money(employee_amount, unit), money(
            employer_amount, unit
        )
        variables[deduction.code] = employee_amount
        variables[f"{deduction.code}_EMPLOYER"] = employer_amount
        used_versions[deduction.code] = deduction.id
        if employee_amount == 0 and employer_amount == 0:
            continue
        kind = "TAX" if deduction.body in TAX_BODIES else "CONTRIBUTION"
        result.lines.append(
            Line(
                code=deduction.code,
                label=deduction.name,
                kind=kind,
                body=deduction.body,
                base=money(line_base, Decimal("1")) if line_base is not None else None,
                rate=deduction.employee_rate if deduction.method != "SCALE" else None,
                employer_rate=(
                    deduction.employer_rate if deduction.method != "SCALE" else None
                ),
                amount=employee_amount,
                employer_amount=employer_amount,
                on_payslip=deduction.on_payslip,
                order=500 + deduction.order,
            )
        )
        if kind == "TAX":
            result.taxes += employee_amount
        else:
            result.employee_contributions += employee_amount
        result.employer_contributions += employer_amount

    net = gross - result.employee_contributions - result.taxes
    variables["NET_BEFORE_DEDUCTIONS"] = net

    # Deductions from net (BN-98, BN-99) ------------------------------------
    add_element_lines([e for e in elements if e.kind == "NET_DEDUCTION"])
    other = sum(
        (line.amount for line in result.lines if line.kind == "NET_DEDUCTION"), ZERO
    )
    available = net - other - bik
    loans = (
        Loan.objects.filter(employee=employee, status="ACTIVE") if employee.pk else []
    )
    for loan in loans:
        if (loan.first_year, loan.first_month) > (period.year, period.month):
            continue
        installment = min(loan.installment, loan.remaining)
        if installment <= 0:
            continue
        installment = money(installment, unit)
        result.lines.append(
            Line(
                code=f"{loan.kind}-{loan.id}",
                label=f"{loan.get_kind_display()} repayment",
                kind="NET_DEDUCTION",
                amount=installment,
                base=money(loan.remaining, unit),
                order=900,
            )
        )
        result.loan_repayments.append((loan, installment))
        other += installment
        available -= installment
    third_parties = (
        ThirdPartyDeduction.objects.filter(
            employee=employee, is_active=True, start_date__lte=end
        ).filter(Q(end_date__isnull=True) | Q(end_date__gte=start))
        if employee.pk
        else []
    )
    for deduction in third_parties:
        amount = deduction.monthly_amount or ZERO
        if deduction.rate_of_net:
            amount = max(amount, available * deduction.rate_of_net / 100)
        if deduction.total_ceiling is not None:
            amount = min(amount, deduction.total_ceiling - deduction.deducted)
        amount = money(max(amount, ZERO), unit)
        if amount <= 0:
            continue
        result.lines.append(
            Line(
                code=f"{deduction.kind}-{deduction.id}",
                label=f"{deduction.get_kind_display()} – {deduction.beneficiary}",
                kind="NET_DEDUCTION",
                amount=amount,
                order=950,
            )
        )
        result.third_party_repayments.append((deduction, amount))
        other += amount
        available -= amount

    result.other_deductions = other
    result.net_salary = net - other
    result.net_payable = result.net_salary - bik

    # Anomalies (BN-90, BN-106) --------------------------------------------
    if base_full <= 0:
        result.anomaly("ZERO_BASE", "The base salary is equal to zero.")
    minimum = params.get("SMIG")
    if minimum and base_full > 0:
        full_time = params.get("LEGAL_WEEKLY_HOURS", Decimal("40"))
        required = minimum * (weekly_hours / full_time if full_time else 1)
        if base_full < required:
            result.anomaly(
                "BELOW_MINIMUM_WAGE",
                f"Base salary {base_full} is below the minimum wage ({money(required, unit)}).",
            )
    grid = grid_salary_from_id(classification_id, end)
    if grid is not None and 0 < base_full < grid:
        result.anomaly(
            "BELOW_GRID",
            f"Base salary {base_full} is below the salary grid of the category ({grid}).",
        )
    if result.net_payable < 0:
        result.anomaly(
            "NEGATIVE_NET", f"The net payable is negative ({result.net_payable})."
        )
    method = employee.method_of_payment or "TRANSFER"
    if method == "TRANSFER" and not (employee.account_number and employee.bank_name):
        result.anomaly("NO_BANK_DETAILS", "Payment by transfer without bank details.")

    result.snapshot = {
        "computed_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "contract": contract.reference if contract else None,
        "terms": {k: _str(v) for k, v in terms.items()},
        "variables": {
            k: _str(v) for k, v in variables.items() if isinstance(v, (Decimal, int))
        },
        "deduction_versions": used_versions,
        "inputs": [
            {
                "element": i.element.code,
                "quantity": _str(i.quantity),
                "amount": _str(i.amount),
                "source": getattr(i, "source", ""),
            }
            for i in inputs
        ],
    }
    result.lines.sort(key=lambda line: line.order)
    return result


def grid_salary_from_id(classification_id, day):
    if not classification_id:
        return None
    row = (
        SalaryGrid.objects.filter(
            classification_id=classification_id, effective_from__lte=day
        )
        .order_by("-effective_from")
        .first()
    )
    return row.base_salary if row else None
