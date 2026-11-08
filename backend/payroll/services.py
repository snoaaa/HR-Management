"""
Payroll cycle (BN-93 → BN-112). The calculation itself is in engine.py.
"""

import calendar
import datetime
from decimal import Decimal

from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone

from employees.models import Employee

from . import engine
from .models import (
    BackPayAdjustment,
    LeaveProvision,
    LoanRepayment,
    PayrollPeriod,
    Payslip,
    PayslipLine,
    PeriodTransition,
    SalaryElement,
    ThirdPartyRepayment,
    VariableInput,
)

ZERO = Decimal("0")


class PayrollError(Exception):
    pass


# --------------------------------------------------------------------------
# Period life cycle (BN-93)
# --------------------------------------------------------------------------

# Transitions allowed by hand; VALIDATED is reached through validate() only.
TRANSITIONS = {
    "OPENED": {"IN_PREPARATION"},
    "IN_PREPARATION": {"OPENED"},
    "CALCULATED": {"IN_PREPARATION", "VERIFIED"},
    "VERIFIED": {"CALCULATED", "IN_PREPARATION"},
    "VALIDATED": {"PAID"},
    "PAID": {"POSTED"},
    "POSTED": {"CLOSED"},
    "CLOSED": set(),
}


def _transition(period, new_status, user, comment=""):
    PeriodTransition.objects.create(
        period=period,
        from_status=period.status,
        to_status=new_status,
        user=user,
        comment=comment,
    )
    period.status = new_status
    period.save(update_fields=["status"])


def open_period(year, month, user):
    period, created = PayrollPeriod.objects.get_or_create(year=year, month=month)
    if created:
        PeriodTransition.objects.create(
            period=period, from_status="", to_status="OPENED", user=user
        )
    return period


def change_status(period, new_status, user, comment=""):
    if new_status not in TRANSITIONS.get(period.status, set()):
        raise PayrollError(
            f"The period cannot go from {period.get_status_display()} to {new_status}."
        )
    if new_status == "PAID" and not period.payment_date:
        period.payment_date = timezone.now().date()
        period.save(update_fields=["payment_date"])
    if new_status == "PAID":
        _accounting("generate_payment_entry", period, user)  # BN-134
    if new_status == "POSTED" and not period.entries.filter(source="PAYROLL").exists():
        raise PayrollError("The payroll entry has not been generated.")
    _transition(period, new_status, user, comment)
    return period


def _accounting(function, *args):
    """Run an accounting function; its errors block the payroll operation."""
    from accounting import services as accounting

    try:
        return getattr(accounting, function)(*args)
    except accounting.AccountingError as exc:
        raise PayrollError(f"Accounting: {exc}")


def _check_editable(period):
    if period.is_locked:
        raise PayrollError(
            "The period is validated: reverse it to change anything (BN-108)."
        )


# --------------------------------------------------------------------------
# Employees and variable inputs (BN-94)
# --------------------------------------------------------------------------


def employees_of(period, department=None, employee=None):
    from contracts.models import Contract

    start, end = period.start_date, period.end_date
    ids = set(
        Contract.objects.exclude(status="DRAFT")
        .filter(start_date__lte=end)
        .filter(
            Q(termination__isnull=True, end_date__isnull=True)
            | Q(termination__isnull=True, end_date__gte=start)
            | Q(termination__termination_date__gte=start)
        )
        .values_list("employee_id", flat=True)
    )
    queryset = Employee.objects.filter(pk__in=ids)
    if department:
        queryset = queryset.filter(department_id=department)
    if employee:
        queryset = queryset.filter(pk=employee)
    return queryset.select_related("department", "classification")


def _element(code):
    element = SalaryElement.objects.filter(code=code, is_active=True).first()
    if element is None:
        raise PayrollError(f"The salary element {code} is missing from the catalogue.")
    return element


def _split_overtime(hours, params):
    """
    Split the overtime of ONE week into the legal tiers (decree 68/DF/249:
    41st to 48th hour +20 %, 49th to 56th +30 %, beyond +40 %). The tier
    sizes (8 h and 8 h) are the parameters OT_TIER1_HOURS / OT_TIER2_HOURS.
    """
    tier1 = Decimal(params.get("OT_TIER1_HOURS", 0))
    tier2 = Decimal(params.get("OT_TIER2_HOURS", 0))
    first = min(hours, tier1)
    second = min(max(hours - tier1, ZERO), tier2)
    third = max(hours - tier1 - tier2, ZERO)
    return first, second, third


def _split_weekly_overtime(by_week, params):
    totals = [ZERO, ZERO, ZERO]
    for hours in by_week.values():
        for index, part in enumerate(_split_overtime(Decimal(str(hours)), params)):
            totals[index] += part
    return [t.quantize(Decimal("0.01")) for t in totals]


@transaction.atomic
def pull_inputs(period, user, employees=None):
    """
    Retrieve automatically the variable elements from attendance (approved
    overtime, unjustified absences), leave (unpaid days, allowances) and
    career (back pay). Manual inputs are kept.
    """
    _check_editable(period)
    from attendance.services import payroll_inputs as attendance_inputs
    from leave.services import payroll_inputs as leave_inputs

    start, end = period.start_date, period.end_date
    params = engine.parameters_at(end)
    employees = employees if employees is not None else employees_of(period)
    created = 0
    for employee in employees:
        VariableInput.objects.filter(period=period, employee=employee).exclude(
            source="MANUAL"
        ).exclude(source="SETTLEMENT").delete()
        BackPayAdjustment.objects.filter(
            employee=employee, target_period=period
        ).delete()
        rows = []
        att = attendance_inputs(employee, start, end)
        tiers = _split_weekly_overtime(att["overtime_day_hours_by_week"], params)
        for code, hours in zip(("OT_TIER1", "OT_TIER2", "OT_TIER3"), tiers):
            if hours:
                rows.append((code, hours, None, "ATTENDANCE", "Approved overtime"))
        for code, key in (
            ("OT_NIGHT", "overtime_night_hours"),
            ("OT_REST_DAY", "overtime_rest_day_hours"),
            ("OT_HOLIDAY", "overtime_holiday_hours"),
        ):
            hours = Decimal(str(att[key]))
            if hours:
                rows.append((code, hours, None, "ATTENDANCE", "Approved overtime"))
        lv = leave_inputs(employee, start, end)
        absence_days = (
            Decimal(att["unjustified_absence_days"]) + lv["unpaid_leave_days"]
        )
        if absence_days:
            rows.append(
                (
                    "ABSENCE",
                    absence_days,
                    None,
                    "ATTENDANCE",
                    f"{att['unjustified_absence_days']} unjustified absence(s), "
                    f"{lv['unpaid_leave_days']} unpaid leave day(s)",
                )
            )
        for allowance in lv["leave_allowances"]:
            rows.append(
                (
                    "LEAVE_ALLOWANCE",
                    Decimal(allowance["days"]),
                    allowance["amount"],
                    "LEAVE",
                    "Leave allowance",
                )
            )
        for source_period, amount in back_pay_for(employee, period):
            rows.append(
                ("BACK_PAY", None, amount, "CAREER", f"Back pay for {source_period}")
            )
            BackPayAdjustment.objects.create(
                employee=employee,
                source_period=source_period,
                target_period=period,
                amount=amount,
            )
        for code, quantity, amount, source, comment in rows:
            VariableInput.objects.create(
                period=period,
                employee=employee,
                element=_element(code),
                quantity=quantity,
                amount=amount,
                source=source,
                comment=comment,
                created_by=user,
            )
            created += 1
    if period.status == "OPENED":
        _transition(period, "IN_PREPARATION", user, "Variable elements retrieved")
    return created


# --------------------------------------------------------------------------
# Calculation (BN-104) and persistence
# --------------------------------------------------------------------------


def _persist(period, result, reversal_of=None):
    employee = result.employee
    from leave.services import remaining_balance

    try:
        leave_balance = remaining_balance(employee, period.end_date)
    except Exception:
        leave_balance = None
    payslip = Payslip.objects.create(
        period=period,
        employee=employee,
        contract=result.contract,
        paid_days=result.paid_days,
        prorata=result.prorata,
        base_salary=result.base_salary,
        gross=result.gross,
        contributory_base=result.contributory_base,
        taxable_base=result.taxable_base,
        employee_contributions=result.employee_contributions,
        employer_contributions=result.employer_contributions,
        taxes=result.taxes,
        other_deductions=result.other_deductions,
        net_salary=result.net_salary,
        benefits_in_kind=result.benefits_in_kind,
        net_payable=result.net_payable,
        payment_method=employee.method_of_payment or "TRANSFER",
        bank_name=employee.bank_name or "",
        bank_account=" ".join(
            filter(
                None, [employee.bank_branch, employee.account_number, employee.bank_key]
            )
        ),
        anomalies=result.anomalies,
        snapshot=result.snapshot,
        leave_balance=leave_balance,
        reversal_of=reversal_of,
    )
    PayslipLine.objects.bulk_create(
        [
            PayslipLine(
                payslip=payslip,
                code=line.code,
                label=line.label,
                kind=line.kind,
                body=line.body,
                base=line.base,
                rate=line.rate,
                employer_rate=line.employer_rate,
                quantity=line.quantity,
                amount=line.amount,
                employer_amount=line.employer_amount,
                is_contributory=line.is_contributory,
                is_taxable=line.is_taxable,
                on_payslip=line.on_payslip,
                order=line.order,
            )
            for line in result.lines
        ]
    )
    LoanRepayment.objects.bulk_create(
        [
            LoanRepayment(loan=loan, payslip=payslip, amount=amount)
            for loan, amount in result.loan_repayments
        ]
    )
    ThirdPartyRepayment.objects.bulk_create(
        [
            ThirdPartyRepayment(deduction=deduction, payslip=payslip, amount=amount)
            for deduction, amount in result.third_party_repayments
        ]
    )
    return payslip


@transaction.atomic
def calculate_period(period, user, department=None, employee=None):
    """BN-104: whole organisation, one department or one employee."""
    _check_editable(period)
    employees = list(employees_of(period, department, employee))
    if not employees:
        raise PayrollError("No employee under contract for this selection.")
    if period.status == "OPENED":
        pull_inputs(period, user, employees)
    period.payslips.filter(employee__in=employees, status="CALCULATED").delete()
    payslips = [_persist(period, engine.calculate(e, period)) for e in employees]
    if period.status in ("OPENED", "IN_PREPARATION", "VERIFIED"):
        _transition(
            period, "CALCULATED", user, f"{len(payslips)} payslip(s) calculated"
        )
    return payslips


def simulate(employee, period, overrides=None):
    """BN-105: calculation without any effect (nothing is saved)."""
    return engine.calculate(employee, period, overrides=overrides)


def simulate_hiring(
    period, base_salary, classification_id=None, weekly_hours=40, elements=None
):
    """BN-105: payslip of a hiring proposal, for an employee not yet recorded."""
    candidate = Employee(
        surname="Simulation",
        given_names="Hiring",
        method_of_payment="CASH",
        classification_id=classification_id,
    )
    return engine.calculate(
        candidate,
        period,
        overrides={
            "base_salary": base_salary,
            "classification_id": classification_id,
            "weekly_hours": weekly_hours,
            "elements": elements or {},
        },
        inputs=[],
    )


# --------------------------------------------------------------------------
# Verification, validation, reversal (BN-106 → BN-108)
# --------------------------------------------------------------------------


def blocking_anomalies(period):
    result = []
    for payslip in period.payslips.filter(status="CALCULATED").select_related(
        "employee"
    ):
        for anomaly in payslip.anomalies:
            if anomaly.get("blocking"):
                result.append(
                    {
                        "employee": payslip.employee.full_name,
                        "payslip": payslip.id,
                        **anomaly,
                    }
                )
    return result


@transaction.atomic
def validate(period, user):
    if period.status not in ("CALCULATED", "VERIFIED"):
        raise PayrollError("Only a calculated or verified period can be validated.")
    anomalies = blocking_anomalies(period)
    if anomalies:
        raise PayrollError(
            f"{len(anomalies)} blocking anomaly(ies) remain: "
            + "; ".join(f"{a['employee']}: {a['message']}" for a in anomalies[:5])
        )
    period.payslips.filter(status="CALCULATED").update(status="VALIDATED")
    period.validated_at = timezone.now()
    period.validated_by = user
    period.save(update_fields=["validated_at", "validated_by"])
    _transition(period, "VALIDATED", user)
    _close_repaid_loans(period)
    compute_provisions(period)
    from attendance.services import lock_period

    lock_period(period.year, period.month)
    # BN-131: the accounting entry is generated at the validation.
    _accounting("generate_payroll_entry", period, user)
    return period


def _close_repaid_loans(period):
    for repayment in LoanRepayment.objects.filter(
        payslip__period=period
    ).select_related("loan"):
        if repayment.loan.remaining <= 0:
            repayment.loan.status = "REPAID"
            repayment.loan.save(update_fields=["status"])


@transaction.atomic
def reverse(period, user, reason):
    """BN-108: a validated period is corrected only by reversal + recalculation."""
    if period.status not in ("VALIDATED", "PAID"):
        raise PayrollError(
            "Only a validated or paid (not posted) period can be reversed."
        )
    if not reason:
        raise PayrollError("The reason of the reversal is required.")
    period.payslips.filter(status="VALIDATED").update(status="REVERSED")
    for loan_repayment in LoanRepayment.objects.filter(
        payslip__period=period
    ).select_related("loan"):
        if loan_repayment.loan.status == "REPAID":
            loan_repayment.loan.status = "ACTIVE"
            loan_repayment.loan.save(update_fields=["status"])
    # BN-138: the entries are corrected by reversal, never deleted.
    _accounting("reverse_payroll_period", period, user)
    period.provisions.all().delete()
    _transition(period, "IN_PREPARATION", user, f"Reversal: {reason}")
    from attendance.services import unlock_period

    unlock_period(period.year, period.month)
    return period


# --------------------------------------------------------------------------
# Comparison (BN-107)
# --------------------------------------------------------------------------


def previous_period(period):
    year, month = (
        (period.year, period.month - 1) if period.month > 1 else (period.year - 1, 12)
    )
    return PayrollPeriod.objects.filter(year=year, month=month).first()


def compare(period):
    previous = previous_period(period)
    threshold = Decimal(
        engine.parameters_at(period.end_date).get("VARIATION_ALERT_PERCENT", 10)
    )
    current = {
        p.employee_id: p
        for p in period.payslips.exclude(status="REVERSED").prefetch_related("lines")
    }
    before = {}
    if previous is not None:
        before = {
            p.employee_id: p
            for p in previous.payslips.filter(status="VALIDATED").prefetch_related(
                "lines"
            )
        }
    rows = []
    for employee_id in sorted(set(current) | set(before)):
        now, then = current.get(employee_id), before.get(employee_id)
        name = (now or then).employee.full_name
        lines_now = {}
        lines_then = {}
        for payslip, target in ((now, lines_now), (then, lines_then)):
            if payslip is None:
                continue
            for line in payslip.lines.all():
                target[(line.code, line.label)] = (
                    target.get((line.code, line.label), ZERO) + line.amount
                )
            target[("GROSS", "Gross salary")] = payslip.gross
            target[("NET", "Net payable")] = payslip.net_payable
        for key in sorted(set(lines_now) | set(lines_then)):
            a, b = lines_then.get(key, ZERO), lines_now.get(key, ZERO)
            if a == b:
                continue
            variation = ((b - a) / a * 100) if a else Decimal("100")
            rows.append(
                {
                    "employee_id": employee_id,
                    "employee": name,
                    "code": key[0],
                    "label": key[1],
                    "previous": a,
                    "current": b,
                    "difference": b - a,
                    "variation_percent": round(variation, 1),
                    "significant": abs(variation) >= threshold,
                    "status": (
                        "NEW" if then is None else "LEFT" if now is None else "CHANGED"
                    ),
                }
            )
    return {
        "previous_period": str(previous) if previous else None,
        "threshold": threshold,
        "rows": rows,
    }


# --------------------------------------------------------------------------
# Payment and declarations (BN-110, BN-111)
# --------------------------------------------------------------------------


def payment_summary(period):
    payslips = period.payslips.filter(status="VALIDATED").select_related("employee")
    by_method, by_bank = {}, {}
    for payslip in payslips:
        by_method.setdefault(payslip.payment_method, ZERO)
        by_method[payslip.payment_method] += payslip.net_payable
        if payslip.payment_method == "TRANSFER":
            bank = by_bank.setdefault(
                payslip.bank_name or "—", {"count": 0, "total": ZERO, "payslips": []}
            )
            bank["count"] += 1
            bank["total"] += payslip.net_payable
            bank["payslips"].append(payslip)
    return {
        "by_method": by_method,
        "by_bank": by_bank,
        "total": sum(by_method.values(), ZERO),
    }


def declarations(period):
    """BN-111: amounts due to each body, with their due date."""
    from core.models import get_int_setting

    due_day = get_int_setting("DECLARATION_DUE_DAY", 15)
    year, month = (
        (period.year, period.month + 1) if period.month < 12 else (period.year + 1, 1)
    )
    due_date = datetime.date(
        year, month, min(due_day, calendar.monthrange(year, month)[1])
    )
    lines = PayslipLine.objects.filter(
        payslip__period=period,
        payslip__status="VALIDATED",
        kind__in=("CONTRIBUTION", "TAX"),
    )
    bodies = {}
    for line in lines:
        body = bodies.setdefault(
            line.body,
            {"body": line.body, "items": {}, "employee": ZERO, "employer": ZERO},
        )
        item = body["items"].setdefault(
            line.code,
            {
                "code": line.code,
                "label": line.label,
                "base": ZERO,
                "employee": ZERO,
                "employer": ZERO,
            },
        )
        item["base"] += line.base or ZERO
        item["employee"] += line.amount
        item["employer"] += line.employer_amount
        body["employee"] += line.amount
        body["employer"] += line.employer_amount
    result = []
    for body in bodies.values():
        body["items"] = list(body["items"].values())
        body["total"] = body["employee"] + body["employer"]
        body["due_date"] = due_date
        result.append(body)
    return sorted(result, key=lambda b: b["body"])


# --------------------------------------------------------------------------
# Leave allowance base, provisions (BN-56, BN-112), back pay (BN-100)
# --------------------------------------------------------------------------


def leave_allowance_base(employee, day, months):
    """Sum of the elements entering the leave allowance base over `months`."""
    payslips = (
        Payslip.objects.filter(employee=employee, status="VALIDATED")
        .filter(
            Q(period__year__lt=day.year)
            | Q(period__year=day.year, period__month__lt=day.month)
        )
        .order_by("-period__year", "-period__month")[:months]
    )
    codes = set(
        SalaryElement.objects.filter(in_leave_allowance_base=True).values_list(
            "code", flat=True
        )
    )
    total, count = ZERO, 0
    for payslip in payslips:
        count += 1
        total += sum(
            (
                line.amount if line.kind == "GAIN" else -line.amount
                for line in payslip.lines.filter(
                    code__in=codes, kind__in=("GAIN", "GROSS_DEDUCTION")
                )
            ),
            ZERO,
        )
    return total, count


def compute_provisions(period):
    from leave.services import compute_leave_allowance, remaining_balance

    period.provisions.all().delete()
    for payslip in period.payslips.filter(status="VALIDATED").select_related(
        "employee"
    ):
        days = remaining_balance(payslip.employee, period.end_date)
        if days <= 0:
            continue
        amount = compute_leave_allowance(payslip.employee, days, period.end_date)
        LeaveProvision.objects.create(
            period=period,
            employee=payslip.employee,
            days=days,
            daily_rate=(amount / days).quantize(Decimal("0.01")),
            amount=engine.money(amount),
        )


def back_pay_for(employee, period):
    """
    BN-100: for every validated period whose terms were changed afterwards
    with an effective date inside it (promotion, salary revision), pay the
    difference of gross in the current period.
    """
    from contracts.models import ContractAmendment

    lookback = int(
        engine.parameters_at(period.end_date).get("BACK_PAY_LOOKBACK_MONTHS", 12)
    )
    result = []
    payslips = (
        Payslip.objects.filter(employee=employee, status="VALIDATED")
        .filter(
            Q(period__year__lt=period.year)
            | Q(period__year=period.year, period__month__lt=period.month)
        )
        .select_related("period")
        .order_by("-period__year", "-period__month")[:lookback]
    )
    for payslip in payslips:
        source = payslip.period
        changed = ContractAmendment.objects.filter(
            contract__employee=employee,
            effective_date__lte=source.end_date,
            created_at__gt=payslip.calculated_at,
        ).exists()
        if not changed:
            continue
        recalculated = engine.calculate(employee, source)
        already = (
            BackPayAdjustment.objects.filter(employee=employee, source_period=source)
            .exclude(target_period=period)
            .aggregate(s=Sum("amount"))["s"]
            or ZERO
        )
        difference = engine.money(recalculated.gross - payslip.gross - already)
        if difference > 0:
            result.append((source, difference))
    return result


# --------------------------------------------------------------------------
# Final settlement (BN-103, BN-73)
# --------------------------------------------------------------------------


def final_settlement(termination, user=None, record=True):
    """
    Outstanding salary is paid by the normal payroll (pro rata). This adds
    the compensation of the remaining leave, the notice indemnity when the
    notice is not worked by decision of the employer, and the severance
    allowance in case of dismissal, according to the parameters.
    """
    from leave.services import compute_leave_allowance

    contract = termination.contract
    employee = contract.employee
    day = termination.termination_date
    params = engine.parameters_at(day)
    base = Decimal(contract.terms_at(day)["base_salary"] or 0)
    items = []

    days = Decimal(termination.leave_balance_days or 0)
    if days > 0:
        items.append(
            (
                "LEAVE_COMPENSATION",
                "Compensation of remaining leave",
                days,
                compute_leave_allowance(employee, days, day),
            )
        )

    if not termination.notice_worked and termination.reason in ("DISMISSAL", "MUTUAL"):
        divisor = Decimal(params.get("NOTICE_DAY_DIVISOR", 30))
        amount = base / divisor * termination.notice_days if divisor else ZERO
        items.append(
            (
                "NOTICE_INDEMNITY",
                "Notice indemnity",
                Decimal(termination.notice_days),
                amount,
            )
        )

    min_years = Decimal(params.get("SEVERANCE_MIN_YEARS", 2))
    years = engine._seniority_years(employee, day)
    if (
        termination.reason == "DISMISSAL"
        and contract.contract_type == "PERMANENT"
        and years >= min_years
    ):
        total, count = leave_allowance_base(employee, day, 12)
        average = total / count if count else base
        rate_years = engine.apply_scale(engine.scale_at("SEVERANCE", day), years)
        items.append(
            (
                "SEVERANCE",
                "Severance allowance",
                years.quantize(Decimal("0.01")),
                average * rate_years / 100,
            )
        )

    breakdown = [
        {
            "code": code,
            "label": label,
            "quantity": str(qty),
            "amount": str(engine.money(amount)),
        }
        for code, label, qty, amount in items
        if amount > 0
    ]
    total = sum((Decimal(item["amount"]) for item in breakdown), ZERO)
    if record:
        termination.final_settlement = {
            "items": breakdown,
            "total": str(total),
            "computed_at": timezone.now().isoformat(timespec="seconds"),
        }
        termination.save(update_fields=["final_settlement"])
        period = open_period(day.year, day.month, user)
        if not period.is_locked:
            VariableInput.objects.filter(
                period=period, employee=employee, source="SETTLEMENT"
            ).delete()
            for item in breakdown:
                VariableInput.objects.create(
                    period=period,
                    employee=employee,
                    element=_element(item["code"]),
                    quantity=Decimal(item["quantity"]),
                    amount=Decimal(item["amount"]),
                    source="SETTLEMENT",
                    comment="Final settlement",
                    created_by=user,
                )
    return {"items": breakdown, "total": total}
