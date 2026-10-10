"""
BN-179: import of the initial data from the existing spreadsheets, with a
control report of the rejected lines. A dry run validates the file without
saving anything; the real import saves every valid line.
"""

import csv
import datetime
import io
from decimal import Decimal, InvalidOperation

from django.db import transaction

KINDS = {
    "EMPLOYEES": [
        "matriculation_number",
        "surname",
        "given_names",
        "date_of_birth",
        "place_of_birth",
        "sex",
        "nationality",
        "marital_status",
        "identity_document_type",
        "identity_document_number",
        "address",
        "phone_number",
        "personal_email",
        "emergency_contact_name",
        "emergency_contact_number",
        "department_code",
        "position_code",
        "contract_type",
        "date_of_hire",
        "bank_name",
        "account_number",
        "method_of_payment",
        "social_insurance_number",
        "tax_identification_number",
    ],
    "CONTRACTS": [
        "matriculation_number",
        "contract_type",
        "start_date",
        "end_date",
        "base_salary",
        "weekly_hours",
        "position_code",
        "department_code",
        "trial_period_end",
        "notice_period_days",
    ],
    "LEAVE_BALANCES": ["matriculation_number", "year", "days", "reason"],
    "SALARY_ELEMENTS": [
        "matriculation_number",
        "element_code",
        "value",
        "effective_from",
    ],
    "LOANS": [
        "matriculation_number",
        "kind",
        "remaining_amount",
        "installment",
        "first_year",
        "first_month",
    ],
}
REQUIRED = {
    "EMPLOYEES": ["surname", "given_names", "date_of_birth", "sex", "date_of_hire"],
    "CONTRACTS": ["matriculation_number", "contract_type", "start_date", "base_salary"],
    "LEAVE_BALANCES": ["matriculation_number", "year", "days"],
    "SALARY_ELEMENTS": [
        "matriculation_number",
        "element_code",
        "value",
        "effective_from",
    ],
    "LOANS": [
        "matriculation_number",
        "remaining_amount",
        "installment",
        "first_year",
        "first_month",
    ],
}


class RowError(Exception):
    pass


def template_csv(kind):
    return "﻿" + ";".join(KINDS[kind]) + "\n"


def read_rows(upload_name, content):
    """Rows of a CSV (; or ,) or Excel file as dictionaries."""
    if upload_name.lower().endswith((".xlsx", ".xlsm")):
        from openpyxl import load_workbook

        sheet = load_workbook(
            io.BytesIO(content), read_only=True, data_only=True
        ).active
        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            return []
        headers = [str(h or "").strip().lower() for h in rows[0]]
        return [
            {
                headers[i]: ("" if v is None else v)
                for i, v in enumerate(row)
                if i < len(headers)
            }
            for row in rows[1:]
            if any(v not in (None, "") for v in row)
        ]
    text = content.decode("utf-8-sig") if isinstance(content, bytes) else content
    delimiter = ";" if text.count(";") >= text.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    return [
        {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
        for row in reader
    ]


def _date(value, field):
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    value = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise RowError(f"{field}: invalid date '{value}' (YYYY-MM-DD or DD/MM/YYYY).")


def _decimal(value, field):
    try:
        return Decimal(str(value).replace(" ", "").replace(",", "."))
    except InvalidOperation:
        raise RowError(f"{field}: invalid number '{value}'.")


def _choice(value, choices, field, default=None):
    if value in ("", None):
        if default is not None:
            return default
        raise RowError(f"{field} is required.")
    value = str(value).strip().upper()
    allowed = {c[0] for c in choices}
    if value not in allowed:
        raise RowError(
            f"{field}: '{value}' is not one of {', '.join(sorted(allowed))}."
        )
    return value


def _employee(row):
    from employees.models import Employee

    employee = Employee.objects.filter(
        matriculation_number=str(row.get("matriculation_number", "")).strip()
    ).first()
    if employee is None:
        raise RowError(f"Unknown matriculation '{row.get('matriculation_number')}'.")
    return employee


def _by_code(model, code, field):
    if code in ("", None):
        return None
    obj = model.objects.filter(code=str(code).strip()).first()
    if obj is None:
        raise RowError(f"{field}: unknown code '{code}'.")
    return obj


def import_employee(row, user):
    from employees.models import Employee, EmployeeHistory
    from organisation.models import Department, Position

    number = str(row.get("matriculation_number") or "").strip()
    if number and Employee.objects.filter(matriculation_number=number).exists():
        raise RowError(f"The matriculation {number} already exists.")
    employee = Employee(
        matriculation_number=number or "",
        surname=row["surname"],
        given_names=row["given_names"],
        date_of_birth=_date(row["date_of_birth"], "date_of_birth"),
        place_of_birth=row.get("place_of_birth") or "To complete",
        sex=_choice(row.get("sex"), Employee.SEX_CHOICES, "sex"),
        nationality=row.get("nationality") or "Cameroonian",
        marital_status=_choice(
            row.get("marital_status"),
            Employee.MARITAL_STATUS_CHOICES,
            "marital_status",
            "SINGLE",
        ),
        identity_document_type=row.get("identity_document_type") or "To complete",
        identity_document_number=row.get("identity_document_number") or "To complete",
        address=row.get("address") or "To complete",
        phone_number=str(row.get("phone_number") or "To complete"),
        personal_email=row.get("personal_email") or None,
        emergency_contact_name=row.get("emergency_contact_name") or "To complete",
        emergency_contact_number=str(
            row.get("emergency_contact_number") or "To complete"
        ),
        department=_by_code(Department, row.get("department_code"), "department_code"),
        position=_by_code(Position, row.get("position_code"), "position_code"),
        contract_type=_choice(
            row.get("contract_type"),
            Employee.CONTRACT_TYPE_CHOICES,
            "contract_type",
            "PERMANENT",
        ),
        date_of_hire=_date(row["date_of_hire"], "date_of_hire"),
        bank_name=row.get("bank_name") or None,
        account_number=str(row.get("account_number") or "") or None,
        method_of_payment=_choice(
            row.get("method_of_payment"),
            Employee.PAYMENT_METHOD_CHOICES,
            "method_of_payment",
            "TRANSFER",
        ),
        social_insurance_number=row.get("social_insurance_number") or None,
        tax_identification_number=row.get("tax_identification_number") or None,
    )
    employee.save()
    EmployeeHistory.objects.create(
        employee=employee,
        author=user,
        field_name="record",
        new_value="Imported from the existing files",
    )
    return employee


def import_contract(row, user):
    from contracts import services
    from contracts.models import Contract
    from employees.models import Employee
    from organisation.models import Department, Position

    employee = _employee(row)
    contract = Contract(
        employee=employee,
        contract_type=_choice(
            row.get("contract_type"), Employee.CONTRACT_TYPE_CHOICES, "contract_type"
        ),
        start_date=_date(row["start_date"], "start_date"),
        end_date=_date(row["end_date"], "end_date") if row.get("end_date") else None,
        trial_period_end=(
            _date(row["trial_period_end"], "trial_period_end")
            if row.get("trial_period_end")
            else None
        ),
        base_salary=_decimal(row["base_salary"], "base_salary"),
        weekly_hours=_decimal(row.get("weekly_hours") or 40, "weekly_hours"),
        notice_period_days=int(row.get("notice_period_days") or 30),
        position=_by_code(Position, row.get("position_code"), "position_code")
        or employee.position,
        department=_by_code(Department, row.get("department_code"), "department_code")
        or employee.department,
        workplace=employee.workplace,
        classification=employee.classification,
        created_by=user,
    )
    try:
        services.validate_contract(contract)
        contract.save()
        services.activate(contract, user)
    except services.ContractError as exc:
        raise RowError(str(exc))
    return contract


def import_leave_balance(row, user):
    from leave.models import LeaveAdjustment

    return LeaveAdjustment.objects.create(
        employee=_employee(row),
        year=int(row["year"]),
        kind="OPENING",
        days=_decimal(row["days"], "days"),
        reason=row.get("reason") or "Opening balance (import)",
        created_by=user,
    )


def import_salary_element(row, user):
    from payroll.models import ElementValue, SalaryElement

    element = SalaryElement.objects.filter(
        code=str(row["element_code"]).strip()
    ).first()
    if element is None:
        raise RowError(f"Unknown salary element '{row['element_code']}'.")
    return ElementValue.objects.create(
        element=element,
        employee=_employee(row),
        value=_decimal(row["value"], "value"),
        effective_from=_date(row["effective_from"], "effective_from"),
        comment="Imported",
    )


def import_loan(row, user):
    from payroll.models import Loan

    remaining = _decimal(row["remaining_amount"], "remaining_amount")
    installment = _decimal(row["installment"], "installment")
    if installment <= 0 or remaining <= 0:
        raise RowError("Amounts must be positive.")
    return Loan.objects.create(
        employee=_employee(row),
        kind=_choice(row.get("kind"), Loan.KINDS, "kind", "LOAN"),
        amount=remaining,
        installment=min(installment, remaining),
        granted_on=datetime.date.today(),
        first_year=int(row["first_year"]),
        first_month=int(row["first_month"]),
        comment="Outstanding balance (import)",
        created_by=user,
    )


HANDLERS = {
    "EMPLOYEES": import_employee,
    "CONTRACTS": import_contract,
    "LEAVE_BALANCES": import_leave_balance,
    "SALARY_ELEMENTS": import_salary_element,
    "LOANS": import_loan,
}


def run_import(kind, upload_name, content, user, dry_run=True):
    if kind not in HANDLERS:
        raise ValueError(f"Unknown import. Use one of {', '.join(HANDLERS)}.")
    rows = read_rows(upload_name, content)
    imported, rejected = 0, []
    for index, row in enumerate(rows, start=2):
        missing = [f for f in REQUIRED[kind] if row.get(f) in (None, "")]
        if missing:
            rejected.append(
                {
                    "line": index,
                    "reason": f"Missing: {', '.join(missing)}",
                    "data": _printable(row),
                }
            )
            continue
        sid = transaction.savepoint()
        try:
            HANDLERS[kind](row, user)
            imported += 1
            if dry_run:
                transaction.savepoint_rollback(sid)
            else:
                transaction.savepoint_commit(sid)
        except (RowError, ValueError, KeyError) as exc:
            transaction.savepoint_rollback(sid)
            rejected.append(
                {"line": index, "reason": str(exc), "data": _printable(row)}
            )
    return {
        "kind": kind,
        "dry_run": dry_run,
        "lines": len(rows),
        "valid" if dry_run else "imported": imported,
        "rejected": rejected,
    }


def _printable(row):
    return {k: str(v) for k, v in row.items()}
