"""
M-12 – production of the payroll documents (BN-113 → BN-122).
"""

import csv
import io
from decimal import Decimal

from django.core.mail import EmailMessage
from django.db.models import Sum

from core.models import get_setting
from documents.services import issue_document, render_batch, render_document

from .models import Payslip, PayslipLine
from .services import declarations, payment_summary

ZERO = Decimal("0")
GAIN_KINDS = ("GAIN",)
BODY_LABELS = {
    "CNPS": "Social insurance (CNPS)",
    "TAX": "Tax administration (IRPP / CAC)",
    "CFC": "Crédit Foncier",
    "FNE": "National Employment Fund",
    "COMMUNE": "Council (TDL)",
    "CRTV": "Audiovisual fee (CRTV)",
    "OTHER": "Other bodies",
}


def currency():
    return get_setting("CURRENCY", "XAF")


def payslip_context(payslip):
    lines = []
    for line in payslip.lines.filter(on_payslip=True):
        line.is_gain = line.kind in GAIN_KINDS
        lines.append(line)
    contract = payslip.contract
    terms = payslip.snapshot.get("terms", {})
    classification = (
        contract.classification if contract else payslip.employee.classification
    )
    seniority = payslip.snapshot.get("variables", {}).get("SENIORITY_YEARS", "0")
    return {
        "payslip": payslip,
        "employee": payslip.employee,
        "period": payslip.period,
        "lines": lines,
        "classification": classification,
        "weekly_hours": terms.get("weekly_hours", "40"),
        "seniority": Decimal(str(seniority)).quantize(Decimal("0.1")),
        "currency": currency(),
    }


def payslip_pdf(payslip, user, duplicate=False):
    """BN-113 / BN-115: individual payslip; a reprint is marked as duplicate."""
    already = payslip.employee.issued_documents.filter(
        template_code="PAYSLIP", reference__endswith=f"-P{payslip.id}"
    ).exists()
    issued = issue_document(
        "PAYSLIP",
        payslip_context(payslip),
        employee=payslip.employee,
        user=user,
        title=f"Payslip {payslip.period}",
        duplicate=duplicate or already,
        reference=f"PAY-{payslip.period.year}{payslip.period.month:02d}-P{payslip.id}"
        + ("-DUP" if (duplicate or already) else ""),
    )
    return issued


def batch_payslips_pdf(payslips, user, period):
    """BN-114: one single file for a selection of payslips."""
    contexts = [payslip_context(p) for p in payslips]
    pdf = render_batch("PAYSLIP", contexts)
    return issue_document(
        "PAYSLIP",
        {},
        user=user,
        title=f"Payslips {period} ({len(contexts)})",
        recipient="Batch",
        pdf=pdf,
    )


def _totals(payslips):
    keys = (
        "base_salary",
        "gross",
        "employee_contributions",
        "taxes",
        "other_deductions",
        "net_payable",
        "employer_contributions",
    )
    totals = {key: sum((getattr(p, key) for p in payslips), ZERO) for key in keys}
    totals["count"] = len(payslips)
    totals["cost"] = totals["gross"] + totals["employer_contributions"]
    return totals


def validated_payslips(period):
    return list(
        period.payslips.filter(status="VALIDATED")
        .select_related("employee", "employee__department")
        .order_by("employee__department__name", "employee__surname")
    )


def payroll_book(period):
    """BN-117: payroll book with totals per department and for the organisation."""
    payslips = validated_payslips(period) or list(
        period.payslips.exclude(status="REVERSED")
    )
    groups = {}
    for payslip in payslips:
        name = (
            payslip.employee.department.name
            if payslip.employee.department
            else "Without department"
        )
        groups.setdefault(name, []).append(payslip)
    context = {
        "period": period,
        "groups": [
            {"name": name, "payslips": items, "totals": _totals(items)}
            for name, items in groups.items()
        ],
        "totals": _totals(payslips),
    }
    return context, payslips


PAYROLL_BOOK_COLUMNS = [
    (
        "Department",
        lambda p: p.employee.department.name if p.employee.department else "",
    ),
    ("Matriculation", lambda p: p.employee.matriculation_number),
    ("Employee", lambda p: p.employee.full_name),
    ("Days paid", lambda p: p.paid_days),
    ("Base", lambda p: p.base_salary),
    ("Gross", lambda p: p.gross),
    ("Contributory base", lambda p: p.contributory_base),
    ("Taxable base", lambda p: p.taxable_base),
    ("Employee contributions", lambda p: p.employee_contributions),
    ("Taxes", lambda p: p.taxes),
    ("Other deductions", lambda p: p.other_deductions),
    ("Net payable", lambda p: p.net_payable),
    ("Employer contributions", lambda p: p.employer_contributions),
]


def contribution_statement(period):
    """BN-118: per body and per due date."""
    bodies = []
    for body in declarations(period):
        for item in body["items"]:
            item["total"] = item["employee"] + item["employer"]
        bodies.append({**body, "label": BODY_LABELS.get(body["body"], body["body"])})
    return {"period": period, "bodies": bodies}


def _csv(headers, rows):
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(headers)
    writer.writerows(rows)
    return "﻿" + buffer.getvalue()


def declaration_export(period, body):
    """
    BN-119: statutory declaration per employee. CNPS gives the declaration
    of personnel and contributions (DIPE layout); TAX gives the taxes withheld.
    """
    payslips = validated_payslips(period)
    codes_by_body = {}
    for line in (
        PayslipLine.objects.filter(payslip__in=payslips, body=body)
        .values("code", "label")
        .distinct()
    ):
        codes_by_body[line["code"]] = line["label"]
    codes = sorted(codes_by_body)
    headers = [
        "Period",
        "Matriculation",
        "CNPS number",
        "NIU",
        "Surname",
        "Given names",
        "Days paid",
        "Gross",
        "Contributory base",
        "Taxable base",
    ]
    for code in codes:
        headers += [f"{code} base", f"{code} employee", f"{code} employer"]
    rows = []
    for payslip in payslips:
        employee = payslip.employee
        detail = {line.code: line for line in payslip.lines.filter(body=body)}
        row = [
            f"{period.year}{period.month:02d}",
            employee.matriculation_number,
            employee.social_insurance_number or "",
            employee.tax_identification_number or "",
            employee.surname,
            employee.given_names,
            payslip.paid_days,
            payslip.gross,
            payslip.contributory_base,
            payslip.taxable_base,
        ]
        for code in codes:
            line = detail.get(code)
            row += [
                line.base if line else 0,
                line.amount if line else 0,
                line.employer_amount if line else 0,
            ]
        rows.append(row)
    return _csv(headers, rows)


def annual_statement(employee, year):
    """BN-120: annual individual salary statement."""
    payslips = list(
        Payslip.objects.filter(employee=employee, status="VALIDATED", period__year=year)
        .select_related("period")
        .order_by("period__month")
    )
    keys = (
        "gross",
        "taxable_base",
        "contributory_base",
        "employee_contributions",
        "taxes",
        "net_payable",
    )
    totals = {key: sum((getattr(p, key) for p in payslips), ZERO) for key in keys}
    withheld = (
        PayslipLine.objects.filter(
            payslip__in=payslips, kind__in=("CONTRIBUTION", "TAX")
        )
        .values("label")
        .annotate(amount=Sum("amount"))
        .order_by("label")
    )
    return {
        "employee": employee,
        "year": year,
        "payslips": payslips,
        "totals": totals,
        "withheld": [w for w in withheld if w["amount"]],
    }


ANNUAL_SUMMARY_KEYS = (
    "gross",
    "taxable_base",
    "contributory_base",
    "employee_contributions",
    "employer_contributions",
    "taxes",
    "net_payable",
)


def annual_summary(year):
    """BN-120: annual summary for the tax administration, one row per employee."""
    rows = {}
    for payslip in Payslip.objects.filter(
        status="VALIDATED", period__year=year
    ).select_related("employee"):
        employee = payslip.employee
        row = rows.setdefault(
            employee.id,
            {
                "matriculation": employee.matriculation_number,
                "niu": employee.tax_identification_number or "",
                "name": employee.full_name,
                "months": 0,
                **{k: ZERO for k in ANNUAL_SUMMARY_KEYS},
            },
        )
        row["months"] += 1
        for key in ANNUAL_SUMMARY_KEYS:
            row[key] += getattr(payslip, key)
    for row in rows.values():
        lines = (
            PayslipLine.objects.filter(
                payslip__employee__matriculation_number=row["matriculation"],
                payslip__status="VALIDATED",
                payslip__period__year=year,
                code__in=("IRPP", "CAC"),
            )
            .values("code")
            .annotate(total=Sum("amount"))
        )
        totals = {line["code"]: line["total"] for line in lines}
        row["irpp"] = totals.get("IRPP", ZERO)
        row["cac"] = totals.get("CAC", ZERO)
    return sorted(rows.values(), key=lambda r: r["name"])


def bank_file(period, bank=None):
    """
    BN-121: transfer file per bank. Generic layout (semicolon CSV) until the
    format of the bank is confirmed (OP-03):
    reference;matriculation;name;bank;account;amount;currency
    """
    summary = payment_summary(period)
    rows = []
    for name, data in summary["by_bank"].items():
        if bank and name != bank:
            continue
        for payslip in data["payslips"]:
            rows.append(
                [
                    f"SAL{period.year}{period.month:02d}-{payslip.employee.matriculation_number}",
                    payslip.employee.matriculation_number,
                    payslip.employee.full_name,
                    name,
                    payslip.bank_account,
                    payslip.net_payable,
                    currency(),
                ]
            )
    return _csv(
        ["reference", "matriculation", "name", "bank", "account", "amount", "currency"],
        rows,
    )


def payment_order_contexts(period):
    """BN-121: one payment order per bank, with the total to debit."""
    summary = payment_summary(period)
    return [
        {
            "period": period,
            "bank": name,
            "payslips": data["payslips"],
            "count": data["count"],
            "total": data["total"],
            "currency": currency(),
        }
        for name, data in summary["by_bank"].items()
    ]


def cash_list_context(period):
    payslips = [p for p in validated_payslips(period) if p.payment_method == "CASH"]
    return {
        "period": period,
        "payslips": payslips,
        "currency": currency(),
        "total": sum((p.net_payable for p in payslips), ZERO),
    }


def email_payslip(payslip, user):
    """BN-116: send the payslip protected by a password (the matriculation)."""
    from pypdf import PdfReader, PdfWriter

    employee = payslip.employee
    address = (
        employee.professional_email
        or employee.personal_email
        or (employee.user.email if employee.user else "")
    )
    if not address:
        raise ValueError("The employee has no e-mail address.")
    pdf = render_document("PAYSLIP", payslip_context(payslip))
    reader = PdfReader(io.BytesIO(pdf))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt(user_password=employee.matriculation_number, algorithm="AES-128")
    protected = io.BytesIO()
    writer.write(protected)
    message = EmailMessage(
        subject=f"Payslip {payslip.period}",
        body=(
            f"Dear {employee.given_names},\n\nPlease find attached your payslip of {payslip.period}.\n"
            "The document is protected: the password is your matriculation number.\n"
        ),
        to=[address],
    )
    message.attach(
        f"payslip-{payslip.period.year}-{payslip.period.month:02d}.pdf",
        protected.getvalue(),
        "application/pdf",
    )
    message.send()
    return address
