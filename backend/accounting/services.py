"""
Generation of the OHADA payroll entries and accounting books (BN-128 → BN-147).

Every entry is built in memory, checked (total debit == total credit,
period open), then saved with a continuous number per journal. A posted
entry is never changed: corrections are reversal entries.
"""

import csv
import datetime
import io
from collections import OrderedDict
from decimal import Decimal

from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone

from core.models import Sequence, get_setting

from .models import (
    Account,
    AccountingPeriod,
    AccountMapping,
    FiscalYear,
    Journal,
    JournalEntry,
    JournalLine,
)

ZERO = Decimal("0")
PERSONNEL_ACCOUNTS_PREFIX = ("421", "422", "423")


class AccountingError(Exception):
    pass


# --------------------------------------------------------------------------
# Periods (BN-137)
# --------------------------------------------------------------------------


def period_for(day, create=True):
    fiscal_year = FiscalYear.objects.filter(year=day.year).first()
    if fiscal_year is None:
        if not create:
            return None
        fiscal_year = FiscalYear.objects.create(year=day.year)
    period, _ = AccountingPeriod.objects.get_or_create(
        fiscal_year=fiscal_year, month=day.month
    )
    return period


def check_open(day):
    period = period_for(day)
    if period.status == "CLOSED" or period.fiscal_year.status == "CLOSED":
        raise AccountingError(f"The accounting period {period} is closed.")
    return period


def close_period(period, user=None):
    period.status = "CLOSED"
    period.save(update_fields=["status"])
    return period


def close_fiscal_year(fiscal_year, user=None):
    """Closing of the financial year: every month is closed."""
    fiscal_year.periods.update(status="CLOSED")
    for month in range(1, 13):
        AccountingPeriod.objects.get_or_create(
            fiscal_year=fiscal_year, month=month, defaults={"status": "CLOSED"}
        )
    fiscal_year.status = "CLOSED"
    fiscal_year.closed_at = timezone.now()
    fiscal_year.save(update_fields=["status", "closed_at"])
    FiscalYear.objects.get_or_create(year=fiscal_year.year + 1)
    return fiscal_year


# --------------------------------------------------------------------------
# Mapping (BN-129)
# --------------------------------------------------------------------------


def mapping_for(source_type, code, day):
    queryset = AccountMapping.objects.filter(
        source_type=source_type, effective_from__lte=day
    ).select_related(
        "debit_account",
        "credit_account",
        "employer_debit_account",
        "employer_credit_account",
    )
    mapping = (
        queryset.filter(source_code=code).order_by("-effective_from").first()
        if code
        else None
    )
    if mapping is None:
        mapping = queryset.filter(source_code="").order_by("-effective_from").first()
    if mapping is None:
        raise AccountingError(
            f"No account mapping for {source_type} {code or '(default)'}."
        )
    return mapping


# --------------------------------------------------------------------------
# Building entries
# --------------------------------------------------------------------------


class EntryBuilder:
    """Accumulates lines; equal keys are merged (consolidation)."""

    def __init__(self, breakdown):
        self.breakdown = breakdown
        self.lines = OrderedDict()

    def add(
        self, account, debit=ZERO, credit=ZERO, label="", employee=None, third_party=""
    ):
        if account is None:
            raise AccountingError(
                f"Missing account for '{label}'. Complete the account mapping."
            )
        debit, credit = Decimal(debit), Decimal(credit)
        if debit < 0:
            debit, credit = ZERO, credit - debit
        if credit < 0:
            credit, debit = ZERO, debit - credit
        if debit == 0 and credit == 0:
            return
        personnel = account.number.startswith(PERSONNEL_ACCOUNTS_PREFIX)
        department = cost_centre = None
        if employee is not None and self.breakdown in ("DEPARTMENT", "COST_CENTRE"):
            department = employee.department
            if self.breakdown == "COST_CENTRE" and department is not None:
                cost_centre = department.cost_centre
                department = None
        key = (
            account.id,
            "D" if debit else "C",
            employee.id if (personnel and employee is not None) else None,
            department.id if department else None,
            cost_centre.id if cost_centre else None,
            third_party,
            label if not personnel else "",
        )
        line = self.lines.get(key)
        if line is None:
            self.lines[key] = {
                "account": account,
                "label": label,
                "debit": debit,
                "credit": credit,
                "employee": employee if personnel else None,
                "department": department,
                "cost_centre": cost_centre,
                "third_party": third_party,
            }
        else:
            line["debit"] += debit
            line["credit"] += credit

    @property
    def totals(self):
        debit = sum((line["debit"] for line in self.lines.values()), ZERO)
        credit = sum((line["credit"] for line in self.lines.values()), ZERO)
        return debit, credit


def _journal(kind):
    journal = Journal.objects.filter(kind=kind).order_by("id").first()
    if journal is None:
        raise AccountingError(f"No journal of kind {kind}.")
    return journal


@transaction.atomic
def save_entry(
    builder,
    journal,
    day,
    label,
    source,
    user=None,
    payroll_period=None,
    reference="",
    reversal_of=None,
):
    """BN-132: an unbalanced entry is refused; BN-138: continuous numbering."""
    debit, credit = builder.totals
    if not builder.lines:
        raise AccountingError("The entry has no line.")
    if debit != credit:
        raise AccountingError(f"Unbalanced entry: debit {debit} ≠ credit {credit}.")
    period = check_open(day)
    number = Sequence.next_value(f"journal-{journal.code}-{day.year}")
    entry = JournalEntry.objects.create(
        journal=journal,
        number=f"{journal.code}{day.year}-{number:06d}",
        date=day,
        period=period,
        label=label[:255],
        source=source,
        payroll_period=payroll_period,
        reference=reference[:100],
        reversal_of=reversal_of,
        created_by=user,
    )
    JournalLine.objects.bulk_create(
        [
            JournalLine(
                entry=entry,
                account=line["account"],
                label=line["label"][:255],
                debit=line["debit"],
                credit=line["credit"],
                employee=line["employee"],
                department=line["department"],
                cost_centre=line["cost_centre"],
                third_party=line["third_party"],
            )
            for line in builder.lines.values()
        ]
    )
    from users.utils import log_audit_action

    log_audit_action(
        user,
        f"Posted entry {entry.number} ({source})",
        "Accounting",
        details={"total": str(debit)},
    )
    return entry


def _breakdown():
    """BN-133 / OP-02: CONSOLIDATED, DEPARTMENT or COST_CENTRE."""
    return get_setting("ACCOUNTING_BREAKDOWN", "DEPARTMENT")


def build_payroll_entry(payroll_period):
    """BN-131: Dr personnel expenses and employer charges, Cr personnel and bodies."""
    day = payroll_period.end_date
    builder = EntryBuilder(_breakdown())
    payslips = payroll_period.payslips.filter(status="VALIDATED").select_related(
        "employee", "employee__department", "employee__department__cost_centre"
    )
    if not payslips:
        raise AccountingError("The period has no validated payslip.")
    for payslip in payslips:
        employee = payslip.employee
        for line in payslip.lines.all():
            if line.kind in ("GAIN", "GROSS_DEDUCTION"):
                mapping = mapping_for("ELEMENT", line.code, day)
                if line.kind == "GAIN":
                    builder.add(
                        mapping.debit_account,
                        debit=line.amount,
                        label=line.label,
                        employee=employee,
                    )
                    builder.add(
                        mapping.credit_account,
                        credit=line.amount,
                        label=line.label,
                        employee=employee,
                    )
                else:
                    builder.add(
                        mapping.credit_account,
                        debit=line.amount,
                        label=line.label,
                        employee=employee,
                    )
                    builder.add(
                        mapping.debit_account,
                        credit=line.amount,
                        label=line.label,
                        employee=employee,
                    )
            elif line.kind in ("CONTRIBUTION", "TAX"):
                mapping = mapping_for("DEDUCTION", line.code, day)
                if line.amount:
                    builder.add(
                        mapping.debit_account,
                        debit=line.amount,
                        label=line.label,
                        employee=employee,
                    )
                    builder.add(
                        mapping.credit_account,
                        credit=line.amount,
                        label=line.label,
                        employee=employee,
                        third_party=line.body,
                    )
                if line.employer_amount:
                    label = f"{line.label} (employer)"
                    builder.add(
                        mapping.employer_debit_account,
                        debit=line.employer_amount,
                        label=label,
                        employee=employee,
                    )
                    builder.add(
                        mapping.employer_credit_account,
                        credit=line.employer_amount,
                        label=label,
                        employee=employee,
                        third_party=line.body,
                    )
            elif line.kind == "NET_DEDUCTION":
                prefix = line.code.split("-")[0]
                if prefix in ("LOAN", "ADVANCE"):
                    mapping = mapping_for("LOAN", "", day)
                elif (
                    prefix in ("GARNISHMENT", "ALIMONY", "UNION", "OTHER")
                    and "-" in line.code
                ):
                    mapping = mapping_for("THIRD_PARTY", "", day)
                else:
                    mapping = mapping_for("ELEMENT", line.code, day)
                builder.add(
                    mapping.debit_account,
                    debit=line.amount,
                    label=line.label,
                    employee=employee,
                )
                builder.add(
                    mapping.credit_account,
                    credit=line.amount,
                    label=line.label,
                    employee=employee,
                )
    return builder


def generate_payroll_entry(payroll_period, user=None):
    if payroll_period.entries.filter(
        source="PAYROLL", reversed_by__isnull=True
    ).exists():
        raise AccountingError("The payroll entry of this period already exists.")
    builder = build_payroll_entry(payroll_period)
    count = payroll_period.payslips.filter(status="VALIDATED").count()
    entry = save_entry(
        builder,
        _journal("PAYROLL"),
        payroll_period.end_date,
        f"Payroll {payroll_period}",
        "PAYROLL",
        user,
        payroll_period,
        reference=f"Payroll {payroll_period} – {count} payslip(s)",
    )
    generate_provision_entry(payroll_period, user)
    return entry


def generate_provision_entry(payroll_period, user=None):
    """BN-136: change of the provision for paid leave (allocation or reversal)."""
    from payroll.models import LeaveProvision, PayrollPeriod

    current = (
        LeaveProvision.objects.filter(period=payroll_period).aggregate(s=Sum("amount"))[
            "s"
        ]
        or ZERO
    )
    previous_period = (
        PayrollPeriod.objects.filter(
            Q(year__lt=payroll_period.year)
            | Q(year=payroll_period.year, month__lt=payroll_period.month),
            status__in=PayrollPeriod.LOCKED_STATUSES,
        )
        .order_by("-year", "-month")
        .first()
    )
    previous = ZERO
    if previous_period is not None:
        previous = (
            LeaveProvision.objects.filter(period=previous_period).aggregate(
                s=Sum("amount")
            )["s"]
            or ZERO
        )
    change = current - previous
    if change == 0:
        return None
    mapping = mapping_for("PROVISION", "", payroll_period.end_date)
    builder = EntryBuilder("CONSOLIDATED")
    label = (
        "Leave provision – allocation" if change > 0 else "Leave provision – reversal"
    )
    builder.add(mapping.debit_account, debit=change, label=label)
    builder.add(mapping.credit_account, credit=change, label=label)
    return save_entry(
        builder,
        _journal("MISC"),
        payroll_period.end_date,
        f"{label} {payroll_period}",
        "PROVISION",
        user,
        payroll_period,
    )


def generate_payment_entry(payroll_period, user=None, day=None):
    """BN-134: Dr remuneration due, Cr bank or cash, on the payment date."""
    if payroll_period.entries.filter(
        source="PAYMENT", reversed_by__isnull=True
    ).exists():
        raise AccountingError("The payment entry of this period already exists.")
    day = day or payroll_period.payment_date or timezone.now().date()
    net_pay = mapping_for("NET_PAY", "", day).credit_account
    builder = EntryBuilder("CONSOLIDATED")
    for payslip in payroll_period.payslips.filter(status="VALIDATED").select_related(
        "employee"
    ):
        if payslip.net_payable <= 0:
            continue
        treasury = mapping_for(
            "CASH" if payslip.payment_method == "CASH" else "BANK", "", day
        ).credit_account
        builder.add(
            net_pay,
            debit=payslip.net_payable,
            label="Salaries paid",
            employee=payslip.employee,
        )
        builder.add(
            treasury, credit=payslip.net_payable, label=f"Salaries {payroll_period}"
        )
    return save_entry(
        builder,
        _journal("BANK"),
        day,
        f"Payment of salaries {payroll_period}",
        "PAYMENT",
        user,
        payroll_period,
    )


def generate_settlement_entry(payroll_period, body, user=None, day=None):
    """BN-135: settlement of the contributions / taxes of a body."""
    from payroll.models import PayslipLine

    day = day or timezone.now().date()
    lines = PayslipLine.objects.filter(
        payslip__period=payroll_period, payslip__status="VALIDATED", body=body
    )
    if not lines.exists():
        raise AccountingError(f"Nothing to settle for {body}.")
    already = payroll_period.entries.filter(
        source="SETTLEMENT", reference=f"SETTLE-{body}", reversed_by__isnull=True
    )
    if already.exists():
        raise AccountingError(f"The settlement of {body} is already posted.")
    bank = mapping_for("BANK", "", day).credit_account
    builder = EntryBuilder("CONSOLIDATED")
    for line in lines:
        mapping = mapping_for("DEDUCTION", line.code, day)
        if line.amount:
            builder.add(
                mapping.credit_account,
                debit=line.amount,
                label=line.label,
                third_party=body,
            )
            builder.add(bank, credit=line.amount, label=f"Settlement {body}")
        if line.employer_amount:
            builder.add(
                mapping.employer_credit_account,
                debit=line.employer_amount,
                label=f"{line.label} (employer)",
                third_party=body,
            )
            builder.add(bank, credit=line.employer_amount, label=f"Settlement {body}")
    return save_entry(
        builder,
        _journal("BANK"),
        day,
        f"Settlement {body} {payroll_period}",
        "SETTLEMENT",
        user,
        payroll_period,
        reference=f"SETTLE-{body}",
    )


@transaction.atomic
def reverse_entry(entry, user=None, day=None):
    """BN-138: correction by a reversal entry."""
    if hasattr(entry, "reversed_by"):
        raise AccountingError(f"Entry {entry.number} is already reversed.")
    # The reversal is dated in an open period (today by default).
    day = day or timezone.now().date()
    builder = EntryBuilder("CONSOLIDATED")
    for line in entry.lines.select_related(
        "account", "employee", "department", "cost_centre"
    ):
        key = (len(builder.lines),)
        builder.lines[key] = {
            "account": line.account,
            "label": f"Reversal – {line.label}",
            "debit": line.credit,
            "credit": line.debit,
            "employee": line.employee,
            "department": line.department,
            "cost_centre": line.cost_centre,
            "third_party": line.third_party,
        }
    return save_entry(
        builder,
        entry.journal,
        day,
        f"Reversal of {entry.number}",
        "REVERSAL",
        user,
        entry.payroll_period,
        reference=entry.number,
        reversal_of=entry,
    )


def reverse_payroll_period(payroll_period, user=None):
    """Called when a validated payroll is reversed (BN-108)."""
    entries = payroll_period.entries.filter(
        source__in=("PAYROLL", "PROVISION", "PAYMENT"), reversed_by__isnull=True
    )
    for entry in entries:
        reverse_entry(entry, user)


# --------------------------------------------------------------------------
# Books and statements (BN-141 → BN-145)
# --------------------------------------------------------------------------


def lines_queryset(start=None, end=None):
    queryset = JournalLine.objects.select_related(
        "entry", "entry__journal", "account", "employee", "department"
    )
    if start:
        queryset = queryset.filter(entry__date__gte=start)
    if end:
        queryset = queryset.filter(entry__date__lte=end)
    return queryset


def journal_book(start, end, journal=None):
    entries = (
        JournalEntry.objects.filter(date__range=(start, end))
        .select_related("journal")
        .prefetch_related("lines__account")
    )
    if journal:
        entries = entries.filter(journal__code=journal)
    return entries.order_by("journal__code", "number")


def general_ledger(start, end, account_prefix=""):
    result = OrderedDict()
    queryset = lines_queryset(start, end).order_by(
        "account__number", "entry__date", "entry__number", "id"
    )
    if account_prefix:
        queryset = queryset.filter(account__number__startswith=account_prefix)
    opening = (
        JournalLine.objects.filter(entry__date__lt=start)
        .values("account__number")
        .annotate(d=Sum("debit"), c=Sum("credit"))
    )
    openings = {
        row["account__number"]: (row["d"] or ZERO) - (row["c"] or ZERO)
        for row in opening
    }
    for line in queryset:
        account = result.setdefault(
            line.account.number,
            {
                "account": line.account.number,
                "name": line.account.name,
                "opening": openings.get(line.account.number, ZERO),
                "lines": [],
                "debit": ZERO,
                "credit": ZERO,
            },
        )
        balance = (
            account["opening"]
            + account["debit"]
            - account["credit"]
            + line.debit
            - line.credit
        )
        account["debit"] += line.debit
        account["credit"] += line.credit
        account["lines"].append(
            {
                "date": line.entry.date,
                "entry": line.entry.number,
                "journal": line.entry.journal.code,
                "label": line.label,
                "debit": line.debit,
                "credit": line.credit,
                "balance": balance,
                "employee": line.employee.full_name if line.employee else "",
            }
        )
    for account in result.values():
        account["closing"] = account["opening"] + account["debit"] - account["credit"]
    return list(result.values())


def trial_balance(start, end):
    rows = []
    for account in Account.objects.order_by("number"):
        before = JournalLine.objects.filter(
            account=account, entry__date__lt=start
        ).aggregate(d=Sum("debit"), c=Sum("credit"))
        during = JournalLine.objects.filter(
            account=account, entry__date__range=(start, end)
        ).aggregate(d=Sum("debit"), c=Sum("credit"))
        opening = (before["d"] or ZERO) - (before["c"] or ZERO)
        debit, credit = during["d"] or ZERO, during["c"] or ZERO
        if not opening and not debit and not credit:
            continue
        closing = opening + debit - credit
        rows.append(
            {
                "account": account.number,
                "name": account.name,
                "opening": opening,
                "debit": debit,
                "credit": credit,
                "closing_debit": max(closing, ZERO),
                "closing_credit": max(-closing, ZERO),
            }
        )
    return rows


def personnel_balances(end):
    """BN-141: balances per employee (personnel accounts) and per body."""
    employees = (
        JournalLine.objects.filter(
            entry__date__lte=end,
            account__number__startswith="42",
            employee__isnull=False,
        )
        .values(
            "employee__id",
            "employee__surname",
            "employee__given_names",
            "account__number",
        )
        .annotate(d=Sum("debit"), c=Sum("credit"))
        .order_by("employee__surname")
    )
    bodies = (
        JournalLine.objects.filter(entry__date__lte=end)
        .filter(
            Q(account__number__startswith="43") | Q(account__number__startswith="44")
        )
        .values("account__number", "account__name")
        .annotate(d=Sum("debit"), c=Sum("credit"))
        .order_by("account__number")
    )
    return {
        "employees": [
            {
                "employee_id": r["employee__id"],
                "employee": f"{r['employee__given_names']} {r['employee__surname']}",
                "account": r["account__number"],
                "balance": (r["c"] or ZERO) - (r["d"] or ZERO),
            }
            for r in employees
            if (r["c"] or ZERO) != (r["d"] or ZERO)
        ],
        "bodies": [
            {
                "account": r["account__number"],
                "name": r["account__name"],
                "balance": (r["c"] or ZERO) - (r["d"] or ZERO),
            }
            for r in bodies
        ],
    }


def reconciliation(payroll_period):
    """BN-142: payroll of the period compared with the entry generated."""
    payslips = payroll_period.payslips.filter(status="VALIDATED")
    payroll = payslips.aggregate(
        gross=Sum("gross"),
        employer=Sum("employer_contributions"),
        net=Sum("net_payable"),
        bik=Sum("benefits_in_kind"),
        employee=Sum("employee_contributions"),
        taxes=Sum("taxes"),
        other=Sum("other_deductions"),
    )
    payroll = {k: v or ZERO for k, v in payroll.items()}
    lines = JournalLine.objects.filter(
        entry__payroll_period=payroll_period,
        entry__source="PAYROLL",
        entry__reversed_by__isnull=True,
    )
    expenses = lines.filter(account__number__startswith="6").aggregate(
        d=Sum("debit"), c=Sum("credit")
    )
    net_pay_account = mapping_for("NET_PAY", "", payroll_period.end_date).credit_account
    net = lines.filter(account=net_pay_account).aggregate(
        d=Sum("debit"), c=Sum("credit")
    )
    entry_expenses = (expenses["d"] or ZERO) - (expenses["c"] or ZERO)
    entry_net = (net["c"] or ZERO) - (net["d"] or ZERO)
    totals = lines.aggregate(d=Sum("debit"), c=Sum("credit"))
    checks = [
        {
            "label": "Personnel expenses (gross + employer charges)",
            "payroll": payroll["gross"] + payroll["employer"],
            "accounting": entry_expenses,
        },
        {
            "label": "Net remuneration due (account 422)",
            "payroll": payroll["net"],
            "accounting": entry_net,
        },
        {
            "label": "Entry balanced",
            "payroll": totals["d"] or ZERO,
            "accounting": totals["c"] or ZERO,
        },
    ]
    for check in checks:
        check["difference"] = check["accounting"] - check["payroll"]
    posted = lines.exists()
    ok = posted and all(c["difference"] == 0 for c in checks)
    return {"posted": posted, "checks": checks, "ok": ok}


def expense_analysis(start, end, group_by="account"):
    """BN-144: personnel expenses per account, department, cost centre or month, vs budget."""
    from .models import Budget

    lines = lines_queryset(start, end).filter(account__number__startswith="66")
    lines = lines.exclude(entry__source="REVERSAL").filter(
        entry__reversed_by__isnull=True
    )
    field = {
        "account": "account__number",
        "department": "department__name",
        "cost_centre": "cost_centre__name",
        "month": "entry__period__month",
    }[group_by]
    rows = lines.values(field).annotate(d=Sum("debit"), c=Sum("credit")).order_by(field)
    budgets = {}
    if group_by == "department":
        for budget in Budget.objects.filter(year=start.year, department__isnull=False):
            budgets[budget.department.name] = (
                budgets.get(budget.department.name, ZERO) + budget.amount
            )
    elif group_by == "account":
        for budget in Budget.objects.filter(year=start.year, account__isnull=False):
            budgets[budget.account.number] = (
                budgets.get(budget.account.number, ZERO) + budget.amount
            )
    result = []
    for row in rows:
        key = row[field] if row[field] is not None else "—"
        amount = (row["d"] or ZERO) - (row["c"] or ZERO)
        budget = budgets.get(key)
        result.append(
            {
                "key": key,
                "amount": amount,
                "budget": budget,
                "variance": (amount - budget) if budget is not None else None,
            }
        )
    return result


def financial_statement_elements(year):
    """BN-145: personnel elements for the OHADA annual financial statements."""
    start, end = datetime.date(year, 1, 1), datetime.date(year, 12, 31)
    lines = lines_queryset(start, end)

    def total(prefix, side="debit"):
        agg = lines.filter(account__number__startswith=prefix).aggregate(
            d=Sum("debit"), c=Sum("credit")
        )
        d, c = agg["d"] or ZERO, agg["c"] or ZERO
        return d - c if side == "debit" else c - d

    def balance(prefix):
        agg = JournalLine.objects.filter(
            entry__date__lte=end, account__number__startswith=prefix
        ).aggregate(d=Sum("debit"), c=Sum("credit"))
        return (agg["c"] or ZERO) - (agg["d"] or ZERO)

    from payroll.models import Payslip

    months = (
        Payslip.objects.filter(period__year=year, status="VALIDATED")
        .values("period__month")
        .distinct()
        .count()
    )
    payslips = Payslip.objects.filter(period__year=year, status="VALIDATED").count()
    return {
        "year": year,
        "personnel_expenses_66": total("66"),
        "taxes_on_salaries_6413": total("6413"),
        "liabilities_to_personnel_42": balance("42"),
        "liabilities_to_social_bodies_43": balance("43"),
        "liabilities_to_state_44": balance("44"),
        "average_headcount": round(payslips / months, 1) if months else 0,
        "months_with_payroll": months,
    }


# --------------------------------------------------------------------------
# Export / import (BN-143, BN-181)
# --------------------------------------------------------------------------

EXPORT_HEADERS = [
    "journal",
    "number",
    "date",
    "account",
    "account_name",
    "label",
    "debit",
    "credit",
    "third_party",
    "department",
    "cost_centre",
    "employee",
    "reference",
]


def export_entries(entries, mark=True):
    """Standard semicolon CSV readable by the usual accounting packages."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(EXPORT_HEADERS)
    for entry in entries:
        for line in entry.lines.select_related(
            "account", "department", "cost_centre", "employee"
        ):
            writer.writerow(
                [
                    entry.journal.code,
                    entry.number,
                    entry.date.strftime("%d/%m/%Y"),
                    line.account.number,
                    line.account.name,
                    line.label,
                    f"{line.debit:.2f}",
                    f"{line.credit:.2f}",
                    line.third_party,
                    line.department.name if line.department else "",
                    line.cost_centre.code if line.cost_centre else "",
                    line.employee.matriculation_number if line.employee else "",
                    entry.reference,
                ]
            )
        if mark and entry.exported_at is None:
            entry.exported_at = timezone.now()
            entry.save(update_fields=["exported_at"])
    return "﻿" + buffer.getvalue()


def import_chart(content):
    """BN-143: import the chart of accounts (number;name) from the accounting software."""
    text = content.decode("utf-8-sig") if isinstance(content, bytes) else content
    delimiter = ";" if text.count(";") >= text.count(",") else ","
    created, updated, rejected = 0, 0, []
    for index, row in enumerate(
        csv.reader(io.StringIO(text), delimiter=delimiter), start=1
    ):
        if not row or (index == 1 and not row[0].strip().isdigit()):
            continue
        number = row[0].strip()
        name = row[1].strip() if len(row) > 1 else ""
        if not number.isdigit() or not name:
            rejected.append(
                {
                    "line": index,
                    "data": row,
                    "reason": "number (digits) and name are required",
                }
            )
            continue
        account, was_created = Account.objects.update_or_create(
            number=number, defaults={"name": name}
        )
        created += was_created
        updated += not was_created
    return {"created": created, "updated": updated, "rejected": rejected}
