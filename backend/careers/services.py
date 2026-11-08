"""
Business rules of M-08.

An act is recorded, approved (BN-76 when it affects the payroll), then
applied on its effective date through a contract amendment. The payroll
therefore reflects it automatically, including back pay when the effective
date is in a past period (BN-100).
"""

import datetime
import uuid
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.utils import timezone

from contracts import services as contracts
from contracts.models import ContractAmendment
from employees.models import Employee, EmployeeHistory

from .models import CareerAct, DepartmentVersion

SITUATION_FIELDS = ("position_id", "classification_id", "department_id", "workplace_id")
TEMPORARY_TYPES = ("TEMPORARY_ASSIGNMENT", "ACTING", "SECONDMENT")


class CareerError(Exception):
    pass


def _today():
    return timezone.now().date()


def validate_act(act):
    if act.act_type in ("PROMOTION",) and not (
        act.new_position_id or act.new_classification_id
    ):
        raise CareerError(
            "A promotion requires a new position or a new category / grade."
        )
    if act.act_type == "TRANSFER" and not (
        act.new_department_id or act.new_workplace_id or act.new_position_id
    ):
        raise CareerError(
            "A transfer requires a destination department, site or position."
        )
    if (
        act.act_type == "SALARY_REVISION"
        and act.new_base_salary is None
        and act.increase_percent is None
        and act.bonus_value is None
    ):
        raise CareerError(
            "A salary revision requires a new salary, a percentage or a bonus value."
        )
    if act.act_type in TEMPORARY_TYPES and not act.end_date:
        raise CareerError(
            "A temporary assignment requires an end date (automatic return)."
        )
    if act.end_date and act.end_date < act.effective_date:
        raise CareerError("The end date is before the effective date.")
    if act.act_type == "DISCIPLINARY":
        if not act.disciplinary_measure:
            raise CareerError("Choose the disciplinary measure.")
        if act.disciplinary_measure == "SUSPENSION" and not act.suspension_days:
            raise CareerError("A suspension requires its number of days.")
    if act.act_type == "DEPARTURE" and not act.departure_reason:
        raise CareerError("Choose the reason of the departure.")


@transaction.atomic
def submit(act, user):
    """Record the act; acts affecting the payroll go through approval (BN-76)."""
    from notifications.services import start_approval

    if act.status not in ("DRAFT", "MODIFICATION"):
        raise CareerError("This act has already been submitted.")
    validate_act(act)
    act.status = "SUBMITTED"
    act.save(update_fields=["status"])
    if act.affects_payroll:
        start_approval(act, "CAREER_ACT", user)
    else:
        approve(act, user)
    act.refresh_from_db()
    return act


def approve(act, user):
    act.status = "APPROVED"
    act.save(update_fields=["status"])
    if act.effective_date <= _today():
        apply(act, user)


def _situation(employee, contract):
    situation = {field: getattr(employee, field) for field in SITUATION_FIELDS}
    if contract is not None:
        terms = contract.terms_at(_today())
        situation["base_salary"] = str(terms.get("base_salary") or 0)
    return situation


def _new_salary(act, contract):
    current = (
        Decimal(contract.terms_at(act.effective_date).get("base_salary") or 0)
        if contract
        else Decimal(0)
    )
    if act.new_base_salary is not None:
        return act.new_base_salary
    if act.increase_percent is not None:
        return (current * (1 + act.increase_percent / 100)).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
    if act.act_type == "PROMOTION" and act.new_classification_id:
        from payroll.engine import grid_salary_from_id

        grid = grid_salary_from_id(act.new_classification_id, act.effective_date)
        if grid is not None and grid > current:
            return grid  # BN-68: automatic effect on the base salary
    return None


@transaction.atomic
def apply(act, user):
    """Apply the act on its effective date."""
    if act.status != "APPROVED":
        raise CareerError("Only an approved act can be applied.")
    employee = act.employee
    contract = contracts.active_contract(
        employee, act.effective_date
    ) or contracts.active_contract(employee)
    act.previous_situation = _situation(employee, contract)

    if act.act_type in ("PROMOTION", "TRANSFER", "SALARY_REVISION") + TEMPORARY_TYPES:
        changes = {}
        for field, value in (
            ("position_id", act.new_position_id),
            ("classification_id", act.new_classification_id),
            ("department_id", act.new_department_id),
            ("workplace_id", act.new_workplace_id),
        ):
            if value is not None:
                changes[field] = value
        salary = _new_salary(act, contract)
        if salary is not None:
            changes["base_salary"] = salary
        if act.bonus_element and act.bonus_value is not None:
            _revise_bonus(act)
        if changes:
            if contract is not None:
                try:
                    contracts.amend(
                        contract,
                        changes,
                        act.effective_date,
                        f"{act.get_act_type_display()}: {act.reason}"[:255],
                        user,
                    )
                except contracts.ContractError as exc:
                    if "does not change anything" not in str(exc):
                        raise CareerError(str(exc))
            else:
                _update_employee(employee, changes, user, act)
    elif act.act_type == "DISCIPLINARY":
        if act.disciplinary_measure == "SUSPENSION":
            if contract is None:
                raise CareerError("The employee has no contract to suspend.")
            contracts.suspend(
                contract,
                {
                    "reason": "DISCIPLINARY",
                    "start_date": act.effective_date,
                    "end_date": act.effective_date
                    + datetime.timedelta(days=act.suspension_days - 1),
                    "is_paid": False,
                    "counts_for_seniority": False,
                    "comment": act.reason[:500],
                },
                user,
            )
            # The suspension ends automatically: the contract is active again.
            if (
                act.effective_date + datetime.timedelta(days=act.suspension_days)
                <= _today()
            ):
                contracts.apply_due_terminations(user)
        elif act.disciplinary_measure == "DISMISSAL":
            _terminate(act, contract, "DISMISSAL", user)
    elif act.act_type == "DEPARTURE":
        _terminate(act, contract, act.departure_reason, user)

    act.status = "APPLIED"
    act.applied_at = timezone.now()
    act.save(update_fields=["previous_situation", "status", "applied_at"])
    EmployeeHistory.objects.create(
        employee=employee,
        author=user,
        field_name="career",
        previous_value=str(act.previous_situation),
        new_value=f"{act.get_act_type_display()} effective {act.effective_date}",
    )
    return act


def _revise_bonus(act):
    from payroll.models import ElementValue, SalaryElement

    element = SalaryElement.objects.filter(code=act.bonus_element).first()
    if element is None:
        raise CareerError(f"Unknown salary element {act.bonus_element}.")
    ElementValue.objects.filter(
        element=element,
        employee=act.employee,
        effective_to__isnull=True,
        effective_from__lt=act.effective_date,
    ).update(effective_to=act.effective_date - datetime.timedelta(days=1))
    ElementValue.objects.create(
        element=element,
        employee=act.employee,
        value=act.bonus_value,
        effective_from=act.effective_date,
        comment=f"{act.get_act_type_display()} #{act.id}",
    )


def _update_employee(employee, changes, user, act):
    for field, value in changes.items():
        if field == "base_salary":
            continue
        old = getattr(employee, field)
        setattr(employee, field, value)
        EmployeeHistory.objects.create(
            employee=employee,
            author=user,
            field_name=field.replace("_id", ""),
            previous_value=str(old),
            new_value=f"{value} ({act.get_act_type_display()})",
        )
    employee.save()


def _terminate(act, contract, reason, user):
    if contract is None:
        raise CareerError("The employee has no contract in force.")
    if hasattr(contract, "termination"):
        return contract.termination
    reason_map = {
        "END_OF_CONTRACT": "END_OF_CONTRACT",
        "RESIGNATION": "RESIGNATION",
        "DISMISSAL": "DISMISSAL",
        "RETIREMENT": "RETIREMENT",
        "DEATH": "DEATH",
        "MUTUAL": "MUTUAL",
    }
    termination = contracts.terminate(
        contract,
        {
            "reason": reason_map.get(reason, "MUTUAL"),
            "notification_date": min(_today(), act.effective_date),
            "termination_date": act.effective_date,
            "notice_worked": act.notice_worked,
            "comment": act.reason[:500],
        },
        user,
    )
    # BN-73: the departure triggers the final settlement of accounts.
    try:
        from payroll.services import PayrollError, final_settlement

        final_settlement(termination, user)
    except (ImportError, PayrollError):
        pass
    return termination


def end_temporary(act, user=None):
    """BN-70: automatic return to the original situation."""
    if act.act_type not in TEMPORARY_TYPES or act.status != "APPLIED":
        return None
    contract = contracts.active_contract(act.employee)
    previous = act.previous_situation or {}
    changes = {
        field: previous.get(field)
        for field in SITUATION_FIELDS
        if previous.get(field) is not None
    }
    if "base_salary" in previous:
        changes["base_salary"] = Decimal(previous["base_salary"])
    return_date = act.end_date + datetime.timedelta(days=1)
    if contract is not None and changes:
        try:
            contracts.amend(
                contract,
                changes,
                return_date,
                f"End of {act.get_act_type_display().lower()}",
                user,
            )
        except contracts.ContractError as exc:
            if "does not change anything" not in str(exc):
                raise CareerError(str(exc))
    act.status = "ENDED"
    act.save(update_fields=["status"])
    return act


def apply_due_acts(user=None, today=None):
    """Daily job: apply approved acts reaching their date, end temporary ones."""
    today = today or _today()
    done = 0
    for act in CareerAct.objects.filter(status="APPROVED", effective_date__lte=today):
        apply(act, user)
        done += 1
    for act in CareerAct.objects.filter(
        status="APPLIED", act_type__in=TEMPORARY_TYPES, end_date__lt=today
    ):
        end_temporary(act, user)
        done += 1
    return done


@transaction.atomic
def general_increase(
    user, percent, effective_date, reason, department=None, classification=None
):
    """BN-71: general increase for a population, one act per employee."""
    employees = Employee.objects.filter(status="ACTIVE")
    if department:
        employees = employees.filter(department_id=department)
    if classification:
        employees = employees.filter(classification_id=classification)
    batch = uuid.uuid4().hex[:12]
    acts = []
    for employee in employees:
        if contracts.active_contract(employee, effective_date) is None:
            continue
        act = CareerAct.objects.create(
            employee=employee,
            act_type="SALARY_REVISION",
            salary_scope="GENERAL",
            increase_percent=percent,
            effective_date=effective_date,
            reason=reason,
            batch=batch,
            created_by=user,
            status="APPROVED",
        )
        if effective_date <= _today():
            apply(act, user)
        acts.append(act)
    return batch, acts


def timeline(employee):
    """BN-74: chronological career history of an employee."""
    events = []
    for contract in employee.contracts.exclude(status="DRAFT").order_by("start_date"):
        events.append(
            {
                "date": contract.start_date,
                "type": "HIRING" if not events else "CONTRACT",
                "title": f"{contract.get_contract_type_display()} {contract.reference}",
                "detail": contract.position.title if contract.position else "",
            }
        )
        for amendment in contract.amendments.all():
            events.append(
                {
                    "date": amendment.effective_date,
                    "type": "AMENDMENT",
                    "title": f"Amendment {amendment.version}",
                    "detail": amendment.reason,
                }
            )
        for renewal in contract.renewals.all():
            events.append(
                {
                    "date": renewal.created_at.date(),
                    "type": "RENEWAL",
                    "title": f"Renewal until {renewal.new_end_date:%d/%m/%Y}",
                    "detail": "",
                }
            )
        for suspension in contract.suspensions.all():
            events.append(
                {
                    "date": suspension.start_date,
                    "type": "SUSPENSION",
                    "title": suspension.get_reason_display(),
                    "detail": suspension.comment,
                }
            )
        termination = getattr(contract, "termination", None)
        if termination is not None:
            events.append(
                {
                    "date": termination.termination_date,
                    "type": "DEPARTURE",
                    "title": termination.get_reason_display(),
                    "detail": termination.comment,
                }
            )
    for act in employee.career_acts.exclude(
        status__in=("DRAFT", "CANCELLED", "REFUSED")
    ):
        events.append(
            {
                "date": act.effective_date,
                "type": act.act_type,
                "title": act.get_act_type_display(),
                "detail": act.reason,
                "status": act.status,
                "act_id": act.id,
            }
        )
    try:
        from training.models import Participation

        for item in Participation.objects.filter(employee=employee).select_related(
            "session"
        ):
            events.append(
                {
                    "date": item.session.start_date,
                    "type": "TRAINING",
                    "title": item.session.title,
                    "detail": item.get_result_display(),
                }
            )
    except ImportError:
        pass
    if not employee.contracts.exists() and employee.date_of_hire:
        events.append(
            {
                "date": employee.date_of_hire,
                "type": "HIRING",
                "title": "Hiring",
                "detail": "",
            }
        )
    return sorted(events, key=lambda e: (e["date"], e["type"]))


# --------------------------------------------------------------------------
# Structure history (BN-06) and organisation chart (BN-07)
# --------------------------------------------------------------------------


def record_department_version(
    department, user=None, effective_from=None, deleted=False
):
    return DepartmentVersion.objects.create(
        department=None if deleted else department,
        department_ref=department.pk,
        effective_from=effective_from or _today(),
        name=department.name,
        code=department.code,
        unit_type=department.unit_type,
        parent_id=department.parent_id,
        site_id=department.site_id,
        manager_id=department.manager_id,
        cost_centre_id=department.cost_centre_id,
        is_deleted=deleted,
        recorded_by=user,
    )


def structure_at(day):
    """The organisation as it was at a past date."""
    units = []
    refs = DepartmentVersion.objects.values_list("department_ref", flat=True).distinct()
    for ref in refs:
        version = (
            DepartmentVersion.objects.filter(
                department_ref=ref, effective_from__lte=day
            )
            .order_by("-effective_from", "-id")
            .first()
        )
        if version is None or version.is_deleted:
            continue
        units.append(
            {
                "id": ref,
                "name": version.name,
                "code": version.code,
                "unit_type": version.unit_type,
                "parent": version.parent_id,
                "site": version.site_id,
                "manager": version.manager_id,
                "cost_centre": version.cost_centre_id,
            }
        )
    return units


def org_chart(day=None):
    """Tree of the units with their manager and headcount."""
    from users.models import User

    units = structure_at(day) if day else None
    if units is None:
        from organisation.models import Department

        units = [
            {
                "id": d.id,
                "name": d.name,
                "code": d.code,
                "unit_type": d.unit_type,
                "parent": d.parent_id,
                "manager": d.manager_id,
            }
            for d in Department.objects.all()
        ]
    managers = {
        u.id: u.get_full_name() or u.username
        for u in User.objects.filter(
            id__in=[u["manager"] for u in units if u.get("manager")]
        )
    }
    headcount = {}
    for row in Employee.objects.filter(status="ACTIVE").values("department_id"):
        headcount[row["department_id"]] = headcount.get(row["department_id"], 0) + 1
    nodes = {
        u["id"]: {
            **u,
            "manager_name": managers.get(u.get("manager"), ""),
            "headcount": headcount.get(u["id"], 0),
            "children": [],
        }
        for u in units
    }
    roots = []
    for node in nodes.values():
        parent = nodes.get(node["parent"])
        (parent["children"] if parent else roots).append(node)
    return roots


def latest_amendment_for(act):
    contract = contracts.active_contract(act.employee)
    if contract is None:
        return None
    return (
        ContractAmendment.objects.filter(
            contract=contract, effective_date=act.effective_date
        )
        .order_by("-version")
        .first()
    )
