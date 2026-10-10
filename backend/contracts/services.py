"""
Business rules of M-04. Views stay thin and call these functions.
"""

import datetime

from django.db import transaction
from django.utils import timezone

from core.models import get_int_setting
from employees.models import EmployeeHistory

from .models import (
    AMENDABLE_TERMS,
    Contract,
    ContractAmendment,
    ContractRenewal,
    ContractSuspension,
    ContractTermination,
    _encode,
)


class ContractError(Exception):
    pass


# Fields of the employee record fed by the contract ("enter data once").
EMPLOYEE_SYNC_FIELDS = {
    "contract_type": "contract_type",
    "position_id": "position_id",
    "classification_id": "classification_id",
    "department_id": "department_id",
    "workplace_id": "workplace_id",
}


def sync_employee(contract, user, day=None):
    """Copy the administrative situation of the contract to the employee record."""
    day = day or timezone.now().date()
    terms = contract.terms_at(day)
    employee = contract.employee
    values = {"contract_type": contract.contract_type, **terms}
    changed = []
    for source, target in EMPLOYEE_SYNC_FIELDS.items():
        new_value = values.get(source)
        if new_value is None and source != "contract_type":
            continue
        old_value = getattr(employee, target)
        if old_value != new_value:
            setattr(employee, target, new_value)
            changed.append(target)
            EmployeeHistory.objects.create(
                employee=employee,
                author=user,
                field_name=target.replace("_id", ""),
                previous_value="" if old_value is None else str(old_value),
                new_value=f"{new_value} (contract {contract.reference})",
            )
    if employee.status == "INACTIVE" and contract.is_in_force(day):
        employee.status = "ACTIVE"
        changed.append("status")
    if changed:
        employee.save(update_fields=list(set(changed)))


def active_contract(employee, day=None):
    day = day or timezone.now().date()
    for contract in employee.contracts.exclude(status="DRAFT").select_related(
        "termination"
    ):
        if contract.is_in_force(day):
            return contract
    return None


def _check_overlap(contract):
    others = contract.employee.contracts.exclude(pk=contract.pk).filter(
        status__in=("ACTIVE", "SUSPENDED")
    )
    for other in others:
        other_end = other.effective_end_date or datetime.date.max
        this_end = contract.effective_end_date or datetime.date.max
        if other.start_date <= this_end and contract.start_date <= other_end:
            raise ContractError(
                f"The employee already has the contract {other.reference} "
                "in force during this period."
            )


def validate_contract(contract):
    if contract.is_fixed_term and not contract.end_date:
        raise ContractError("A fixed-term contract requires an end date.")
    if contract.end_date and contract.end_date < contract.start_date:
        raise ContractError("The end date is before the start date.")
    if contract.trial_period_end and contract.trial_period_end < contract.start_date:
        raise ContractError("The trial period ends before the start date.")
    if contract.base_salary is not None and contract.base_salary < 0:
        raise ContractError("The salary cannot be negative.")


@transaction.atomic
def activate(contract, user):
    if contract.status != "DRAFT":
        raise ContractError("Only a draft contract can be activated.")
    validate_contract(contract)
    _check_overlap(contract)
    contract.status = "ACTIVE"
    contract.save(update_fields=["status"])
    employee = contract.employee
    if not employee.contracts.exclude(pk=contract.pk).exclude(status="DRAFT").exists():
        if employee.date_of_hire != contract.start_date:
            EmployeeHistory.objects.create(
                employee=employee,
                author=user,
                field_name="date_of_hire",
                previous_value=str(employee.date_of_hire),
                new_value=str(contract.start_date),
            )
            employee.date_of_hire = contract.start_date
            employee.save(update_fields=["date_of_hire"])
    sync_employee(contract, user)
    return contract


@transaction.atomic
def amend(contract, changes, effective_date, reason, user):
    """BN-30: create a new version of the contract terms."""
    if contract.status not in ("ACTIVE", "SUSPENDED"):
        raise ContractError("Only a contract in force can be amended.")
    if effective_date < contract.start_date:
        raise ContractError("The amendment cannot take effect before the contract.")
    last = contract.amendments.order_by("-version").first()
    if last and effective_date < last.effective_date:
        raise ContractError(
            "An amendment cannot take effect before the previous amendment "
            f"({last.effective_date:%d/%m/%Y})."
        )
    previous, new = {}, {}
    for name, value in changes.items():
        if name not in AMENDABLE_TERMS:
            raise ContractError(f"'{name}' cannot be amended.")
        old_value = getattr(contract, name)
        if str(old_value) != str(value):
            previous[name] = _encode(old_value)
            new[name] = _encode(value)
            setattr(contract, name, value)
    if not new:
        raise ContractError("The amendment does not change anything.")
    validate_contract(contract)
    contract.save()
    amendment = ContractAmendment.objects.create(
        contract=contract,
        version=(last.version + 1) if last else 1,
        effective_date=effective_date,
        reason=reason,
        previous_values=previous,
        new_values=new,
        created_by=user,
    )
    if effective_date <= timezone.now().date():
        sync_employee(contract, user)
    return amendment


@transaction.atomic
def renew(contract, new_end_date, user):
    """BN-32: renew a fixed-term contract within the allowed number."""
    if not contract.is_fixed_term:
        raise ContractError("Only a fixed-term contract can be renewed.")
    if contract.status not in ("ACTIVE", "EXPIRED"):
        raise ContractError("This contract cannot be renewed.")
    maximum = get_int_setting("MAX_FIXED_TERM_RENEWALS", 1)
    if contract.renewal_count >= maximum:
        raise ContractError(
            f"The maximum number of renewals ({maximum}) is reached; "
            "a permanent contract must be offered."
        )
    if contract.end_date and new_end_date <= contract.end_date:
        raise ContractError("The new end date must be after the current one.")
    renewal = ContractRenewal.objects.create(
        contract=contract,
        previous_end_date=contract.end_date,
        new_end_date=new_end_date,
        renewal_number=contract.renewal_count + 1,
        created_by=user,
    )
    contract.end_date = new_end_date
    contract.renewal_count += 1
    contract.status = "ACTIVE"
    contract.save(update_fields=["end_date", "renewal_count", "status"])
    return renewal


@transaction.atomic
def suspend(contract, data, user):
    """BN-33: suspend the contract."""
    if contract.status != "ACTIVE":
        raise ContractError("Only an active contract can be suspended.")
    suspension = ContractSuspension.objects.create(
        contract=contract, created_by=user, **data
    )
    if suspension.start_date <= timezone.now().date():
        contract.status = "SUSPENDED"
        contract.save(update_fields=["status"])
    return suspension


@transaction.atomic
def resume(contract, end_date, user):
    suspension = contract.suspensions.filter(end_date__isnull=True).first()
    if suspension is None:
        raise ContractError("The contract has no open suspension.")
    if end_date < suspension.start_date:
        raise ContractError("The suspension cannot end before it started.")
    suspension.end_date = end_date
    suspension.save(update_fields=["end_date"])
    contract.status = "ACTIVE"
    contract.save(update_fields=["status"])
    return suspension


def leave_balance_of(employee, day):
    try:
        from leave.services import remaining_balance
    except ImportError:
        return 0
    return remaining_balance(employee, day)


@transaction.atomic
def terminate(contract, data, user):
    """BN-34: record the end of the contract."""
    if contract.status not in ("ACTIVE", "SUSPENDED", "EXPIRED"):
        raise ContractError("This contract cannot be terminated.")
    if hasattr(contract, "termination"):
        raise ContractError("The contract is already terminated.")
    if data["termination_date"] < contract.start_date:
        raise ContractError("The termination date is before the start of the contract.")
    if data["notification_date"] > data["termination_date"]:
        raise ContractError("The notification date is after the last working day.")
    data.setdefault("notice_days", contract.notice_period_days)
    if "leave_balance_days" not in data:
        data["leave_balance_days"] = leave_balance_of(
            contract.employee, data["termination_date"]
        )
    termination = ContractTermination.objects.create(
        contract=contract, created_by=user, **data
    )
    apply_due_terminations(user=user)
    return termination


def apply_due_terminations(user=None, today=None):
    """Daily job: close the contracts whose end is reached."""
    today = today or timezone.now().date()
    closed = []
    for termination in ContractTermination.objects.filter(
        termination_date__lt=today, contract__status__in=("ACTIVE", "SUSPENDED")
    ).select_related("contract__employee"):
        contract = termination.contract
        contract.status = "TERMINATED"
        contract.save(update_fields=["status"])
        _deactivate_employee_if_no_contract(contract, user, today)
        closed.append(contract)
    for contract in Contract.objects.filter(
        status="ACTIVE", end_date__lt=today, termination__isnull=True
    ).select_related("employee"):
        contract.status = "EXPIRED"
        contract.save(update_fields=["status"])
        _deactivate_employee_if_no_contract(contract, user, today)
        closed.append(contract)
    for suspension in ContractSuspension.objects.filter(
        contract__status="SUSPENDED", end_date__lt=today
    ).select_related("contract"):
        if not suspension.contract.suspensions.filter(end_date__isnull=True).exists():
            suspension.contract.status = "ACTIVE"
            suspension.contract.save(update_fields=["status"])
    return closed


def _deactivate_employee_if_no_contract(contract, user, today):
    employee = contract.employee
    if active_contract(employee, today) is None and employee.status == "ACTIVE":
        employee.status = "INACTIVE"
        employee.save(update_fields=["status"])
        EmployeeHistory.objects.create(
            employee=employee,
            author=user,
            field_name="status",
            previous_value="ACTIVE",
            new_value=f"INACTIVE (end of contract {contract.reference})",
        )


def upcoming_deadlines(today=None):
    """BN-31: ends of fixed-term contracts and of trial periods."""
    today = today or timezone.now().date()
    contract_days = get_int_setting("CONTRACT_ALERT_DAYS", 30)
    trial_days = get_int_setting("TRIAL_ALERT_DAYS", 15)
    result = []
    in_force = Contract.objects.filter(
        status__in=("ACTIVE", "SUSPENDED"), termination__isnull=True
    ).select_related("employee")
    for contract in in_force.filter(
        end_date__gte=today,
        end_date__lte=today + datetime.timedelta(days=contract_days),
    ):
        result.append(
            {
                "type": "CONTRACT_END",
                "contract": contract,
                "date": contract.end_date,
                "days_left": (contract.end_date - today).days,
            }
        )
    for contract in in_force.filter(
        trial_period_end__gte=today,
        trial_period_end__lte=today + datetime.timedelta(days=trial_days),
    ):
        result.append(
            {
                "type": "TRIAL_END",
                "contract": contract,
                "date": contract.trial_period_end,
                "days_left": (contract.trial_period_end - today).days,
            }
        )
    return sorted(result, key=lambda item: item["date"])


def seniority_days(employee, day=None):
    """
    BN-33: seniority counts the days under contract, minus the suspensions
    that do not count for seniority.
    """
    day = day or timezone.now().date()
    total = 0
    for contract in employee.contracts.exclude(status="DRAFT"):
        end = min(contract.effective_end_date or day, day)
        if end < contract.start_date:
            continue
        days = (end - contract.start_date).days + 1
        for suspension in contract.suspensions.filter(counts_for_seniority=False):
            days -= suspension.overlap_days(contract.start_date, end)
        total += max(0, days)
    return total
