"""
Business rules of M-06.

Entitlement (BN-48): every month of effective service gives
`days_per_month` days, plus the extra days of the seniority bracket, both
pro rata of the days really worked in the month (unpaid suspensions and
leaves that do not count for seniority are excluded). All values come from
the dated EntitlementRule.
"""

import calendar
import datetime
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone

from attendance.services import daterange, working_days_between
from core.models import get_int_setting

from .models import EntitlementRule, LeaveAdjustment, LeaveRequest

TWO_PLACES = Decimal("0.01")
CONSUMED_STATUSES = ("APPROVED", "INTERRUPTED")
PENDING_STATUSES = ("SUBMITTED", "MODIFICATION")


class LeaveError(Exception):
    pass


def q2(value):
    return Decimal(value).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


# --------------------------------------------------------------------------
# Counting (BN-52)
# --------------------------------------------------------------------------


def count_days(leave_type, employee, start, end):
    if end < start:
        raise LeaveError("The end date is before the start date.")
    if leave_type.counting_rule == "CALENDAR_DAYS":
        return Decimal((end - start).days + 1)
    if leave_type.counting_rule == "OUVRABLE_DAYS":
        return Decimal(ouvrable_days_between(start, end, employee.workplace))
    return Decimal(working_days_between(start, end, employee.workplace))


def ouvrable_days_between(start, end, site=None):
    """
    Jours ouvrables (Labour Code art. 89): every day except the legal weekly
    rest day (Sunday by default, setting LEGAL_WEEKLY_REST_DAY) and the
    public holidays.
    """
    from attendance.services import holiday_on

    rest_day = get_int_setting("LEGAL_WEEKLY_REST_DAY", 6)
    count = 0
    for day in daterange(start, end):
        if day.weekday() == rest_day or holiday_on(day, site) is not None:
            continue
        count += 1
    return count


# --------------------------------------------------------------------------
# Entitlement and balance (BN-48, BN-49)
# --------------------------------------------------------------------------


def rule_at(day):
    return EntitlementRule.objects.filter(effective_from__lte=day).first()


def _service_days_in(employee, first, last):
    """Days of effective service between two dates (inclusive)."""
    contracts = list(
        employee.contracts.exclude(status="DRAFT")
        .select_related("termination")
        .prefetch_related("suspensions")
    )
    days = 0
    for day in daterange(first, last):
        if contracts:
            in_force = [c for c in contracts if c.is_in_force(day)]
            if not in_force:
                continue
            suspended = any(
                not s.counts_for_seniority
                and s.start_date <= day
                and (s.end_date is None or s.end_date >= day)
                for c in in_force
                for s in c.suspensions.all()
            )
            if suspended:
                continue
        elif employee.date_of_hire and day < employee.date_of_hire:
            continue
        days += 1
    excluded = LeaveRequest.objects.filter(
        employee=employee,
        status__in=CONSUMED_STATUSES,
        leave_type__counts_for_seniority=False,
        start_date__lte=last,
        end_date__gte=first,
    )
    for request in excluded:
        overlap_first = max(first, request.start_date)
        overlap_last = min(last, request.effective_end_date)
        if overlap_last >= overlap_first:
            days -= (overlap_last - overlap_first).days + 1
    return max(0, days)


def seniority_years(employee, day):
    hire = employee.date_of_hire
    if not hire or hire > day:
        return 0
    years = day.year - hire.year - ((day.month, day.day) < (hire.month, hire.day))
    return max(0, years)


def _extra_days_for(rule, years):
    extra = Decimal("0")
    for bracket in sorted(
        rule.seniority_brackets or [], key=lambda b: b.get("years", 0)
    ):
        if years >= bracket.get("years", 0):
            extra = Decimal(str(bracket.get("extra_days", 0)))
    return extra


def _age(birth, day):
    if not birth:
        return 99
    return day.year - birth.year - ((day.month, day.day) < (birth.month, birth.day))


def _young_children(employee, day, age_limit):
    """Dependent children under `age_limit` years at `day`."""
    count = 0
    for child in employee.family_members.filter(relationship="CHILD"):
        if child.date_of_birth <= day and _age(child.date_of_birth, day) < age_limit:
            count += 1
    return count


def acquired_days(employee, year, until):
    """
    Days acquired during `year` for the months completed at `until`.
    Labour Code: 1.5 jours ouvrables per month of effective service
    (2.5 under 18), + 2 days per 5 years of seniority, + extra days for
    mothers per child under 6; every value comes from the dated rule.
    """
    total = Decimal("0")
    for month in range(1, 13):
        first = datetime.date(year, month, 1)
        last = datetime.date(year, month, calendar.monthrange(year, month)[1])
        if last > until:
            break
        rule = rule_at(last)
        if rule is None:
            continue
        month_length = Decimal(last.day)
        fraction = Decimal(_service_days_in(employee, first, last)) / month_length
        yearly_extra = _extra_days_for(rule, seniority_years(employee, last))
        if employee.sex == "F" and rule.mother_extra_days_per_child:
            yearly_extra += rule.mother_extra_days_per_child * _young_children(
                employee, last, rule.mother_child_age_limit
            )
        monthly = rule.days_per_month
        if _age(employee.date_of_birth, last) < rule.minor_age_limit:
            monthly = max(monthly, rule.minor_days_per_month)
        total += fraction * (monthly + yearly_extra / 12)
    return q2(total)


def _tracking_start_year(employee):
    start = get_int_setting("LEAVE_TRACKING_START_YEAR", timezone.now().year)
    if employee.date_of_hire:
        start = max(start, employee.date_of_hire.year)
    opening = (
        LeaveAdjustment.objects.filter(employee=employee, kind="OPENING")
        .order_by("year")
        .first()
    )
    if opening is not None:
        start = min(start, opening.year)
    return start


def _taken(employee, year, statuses):
    total = Decimal("0")
    for request in LeaveRequest.objects.filter(
        employee=employee,
        status__in=statuses,
        leave_type__consumes_entitlement=True,
        start_date__year=year,
    ):
        total += request.days
    return total


def balance(employee, year, until=None):
    """
    BN-49: acquired, taken, pending and remaining days of a leave year.
    `carried_over` is the remaining balance of the previous year (capped by
    the rule) plus any opening balance.
    """
    until = until or datetime.date(year, 12, 31)
    start_year = _tracking_start_year(employee)
    carried = Decimal("0")
    if year > start_year:
        previous = balance(employee, year - 1)
        carried = previous["remaining"]
        rule = rule_at(datetime.date(year - 1, 12, 31))
        if rule is not None and rule.max_carry_over_days is not None:
            carried = min(carried, rule.max_carry_over_days)
    adjustments = LeaveAdjustment.objects.filter(employee=employee, year=year)
    opening = adjustments.filter(kind="OPENING").aggregate(s=Sum("days"))["s"] or 0
    extra = adjustments.exclude(kind="OPENING").aggregate(s=Sum("days"))["s"] or 0
    acquired = (
        acquired_days(employee, year, until) if year >= start_year else Decimal("0")
    )
    taken = _taken(employee, year, CONSUMED_STATUSES)
    pending = _taken(employee, year, PENDING_STATUSES)
    carried = q2(Decimal(carried) + Decimal(opening))
    acquired = q2(acquired + Decimal(extra))
    remaining = q2(carried + acquired - taken)
    return {
        "year": year,
        "carried_over": carried,
        "acquired": acquired,
        "taken": q2(taken),
        "pending": q2(pending),
        "remaining": remaining,
        "available": q2(remaining - pending),
    }


def remaining_balance(employee, day):
    return balance(employee, day.year, day)["remaining"]


# --------------------------------------------------------------------------
# Queries used by the other modules
# --------------------------------------------------------------------------


def leave_on(employee, day):
    return (
        LeaveRequest.objects.filter(
            employee=employee, status__in=CONSUMED_STATUSES, start_date__lte=day
        )
        .filter(
            Q(interruption_date__isnull=True, end_date__gte=day)
            | Q(interruption_date__gte=day)
        )
        .select_related("leave_type")
        .first()
    )


def is_on_leave(user, day):
    from employees.models import Employee

    employee = Employee.objects.filter(user=user).first()
    return employee is not None and leave_on(employee, day) is not None


# --------------------------------------------------------------------------
# Life cycle (BN-50, BN-51, BN-53, BN-54)
# --------------------------------------------------------------------------


def overlap_warning(request):
    """BN-53: signal when too many members of the team are on leave."""
    department = request.employee.department_id
    if department is None:
        return ""
    from employees.models import Employee

    team = Employee.objects.filter(department_id=department, status="ACTIVE")
    team_size = team.count()
    if team_size <= 1:
        return ""
    absent = (
        LeaveRequest.objects.filter(
            employee__in=team,
            status__in=CONSUMED_STATUSES + PENDING_STATUSES,
            start_date__lte=request.end_date,
            end_date__gte=request.start_date,
        )
        .exclude(employee=request.employee)
        .exclude(pk=request.pk)
        .values("employee")
        .distinct()
        .count()
    )
    threshold = get_int_setting("LEAVE_OVERLAP_THRESHOLD", 30)
    share = (absent + 1) * 100 / team_size
    if share > threshold:
        return (
            f"{absent + 1} of {team_size} team members would be absent "
            f"({share:.0f}% > {threshold}%)."
        )
    return ""


def _check_own_overlap(request):
    clash = (
        LeaveRequest.objects.filter(
            employee=request.employee,
            status__in=CONSUMED_STATUSES + PENDING_STATUSES,
            start_date__lte=request.end_date,
            end_date__gte=request.start_date,
        )
        .exclude(pk=request.pk)
        .first()
    )
    if clash is not None:
        raise LeaveError(
            f"These dates overlap another request ({clash.start_date:%d/%m} → "
            f"{clash.end_date:%d/%m/%Y})."
        )


def prepare(request):
    """Validate a request and compute its number of days."""
    leave_type = request.leave_type
    if not leave_type.is_active:
        raise LeaveError("This type of leave is no longer available.")
    request.days = count_days(
        leave_type, request.employee, request.start_date, request.end_date
    )
    if request.days <= 0:
        raise LeaveError("The period does not contain any day to count.")
    if (
        leave_type.max_days_per_request
        and request.days > leave_type.max_days_per_request
    ):
        raise LeaveError(
            f"This type of leave is limited to {leave_type.max_days_per_request} days per request."
        )
    if leave_type.requires_document and not request.document:
        raise LeaveError("A supporting document is required for this type of leave.")
    _check_own_overlap(request)
    if leave_type.consumes_entitlement:
        available = balance(
            request.employee, request.start_date.year, request.start_date
        )["available"]
        if request.pk:
            # The days of this request are already counted as pending.
            previous = LeaveRequest.objects.get(pk=request.pk)
            if previous.status in PENDING_STATUSES:
                available += previous.days
        if request.days > available:
            raise LeaveError(
                f"Insufficient balance: {request.days} day(s) requested, {available} available."
            )
    request.overlap_warning = overlap_warning(request)
    return request


@transaction.atomic
def submit(request, user):
    from notifications.services import start_approval

    if request.status not in ("DRAFT", "MODIFICATION"):
        raise LeaveError("This request has already been submitted.")
    prepare(request)
    request.status = "SUBMITTED"
    request.submitted_at = timezone.now()
    request.save()
    start_approval(request, "LEAVE", user)
    request.refresh_from_db()
    return request


def approve(request, user):
    """End of the approval circuit."""
    request.status = "APPROVED"
    request.decided_at = timezone.now()
    if request.leave_type.pays_leave_allowance:
        request.allowance_amount = compute_leave_allowance(
            request.employee, request.days, request.start_date
        )
    request.save()
    _refresh_attendance(request)


def _refresh_attendance(request):
    from attendance.services import recompute

    today = timezone.now().date()
    if request.start_date <= today:
        recompute(request.employee, request.start_date, min(request.end_date, today))


@transaction.atomic
def cancel(request, user):
    from notifications.services import pending_tasks

    today = timezone.now().date()
    if request.status in ("CANCELLED", "REFUSED", "INTERRUPTED"):
        raise LeaveError("This request cannot be cancelled.")
    if request.status == "APPROVED" and request.start_date <= today:
        raise LeaveError("The leave has started: interrupt it instead.")
    pending_tasks(request).update(status="CANCELLED")
    request.status = "CANCELLED"
    request.save(update_fields=["status"])
    _refresh_attendance(request)
    return request


@transaction.atomic
def interrupt(request, last_day, user):
    """BN-54: the employee comes back before the end; unused days return."""
    if request.status != "APPROVED":
        raise LeaveError("Only an approved leave can be interrupted.")
    if not (request.start_date <= last_day < request.end_date):
        raise LeaveError("The interruption date must be within the leave.")
    request.interruption_date = last_day
    request.days = count_days(
        request.leave_type, request.employee, request.start_date, last_day
    )
    request.status = "INTERRUPTED"
    if request.allowance_amount is not None:
        request.allowance_amount = compute_leave_allowance(
            request.employee, request.days, request.start_date
        )
    request.save()
    from attendance.services import recompute

    recompute(request.employee, last_day, min(request.end_date, timezone.now().date()))
    return request


@transaction.atomic
def postpone(request, new_start, new_end, user):
    """BN-54: postponement of an approved leave goes through the approval again."""
    from notifications.services import start_approval

    if request.status != "APPROVED" or request.start_date <= timezone.now().date():
        raise LeaveError(
            "Only an approved leave that has not started can be postponed."
        )
    if request.original_start_date is None:
        request.original_start_date = request.start_date
        request.original_end_date = request.end_date
    request.start_date, request.end_date = new_start, new_end
    request.status = "SUBMITTED"
    request.allowance_amount = None
    prepare(request)
    request.save()
    start_approval(request, "LEAVE", user)
    request.refresh_from_db()
    return request


# --------------------------------------------------------------------------
# Leave allowance (BN-56) and payroll transfer (BN-58)
# --------------------------------------------------------------------------


def compute_leave_allowance(employee, days, day):
    """
    Average monthly remuneration of the reference months (salary elements
    flagged "leave allowance base" in payroll) divided by the divisor of the
    rule, multiplied by the number of days.
    """
    rule = rule_at(day)
    months = rule.allowance_reference_months if rule else 12
    divisor = rule.allowance_days_divisor if rule else Decimal("30")
    total, counted = Decimal("0"), 0
    try:
        from payroll.services import leave_allowance_base

        total, counted = leave_allowance_base(employee, day, months)
    except ImportError:
        pass
    if counted == 0:
        from contracts.services import active_contract

        contract = active_contract(employee, day)
        if contract is None:
            return Decimal("0")
        monthly_average = Decimal(contract.terms_at(day)["base_salary"] or 0)
    else:
        monthly_average = total / counted
    return q2(monthly_average / divisor * Decimal(days))


def payroll_inputs(employee, start, end):
    """
    BN-58: unpaid leave days of the period and leave allowances to pay.
    Only working days of the period are counted for the deduction.
    """
    unpaid_days = Decimal("0")
    paid_leave_days = Decimal("0")
    allowances = []
    requests = LeaveRequest.objects.filter(
        employee=employee,
        status__in=CONSUMED_STATUSES,
        start_date__lte=end,
        end_date__gte=start,
    ).select_related("leave_type")
    for request in requests:
        first = max(start, request.start_date)
        last = min(end, request.effective_end_date)
        if last < first:
            continue
        days = count_days(request.leave_type, employee, first, last)
        if request.leave_type.generates_deduction or not request.leave_type.is_paid:
            unpaid_days += days
        else:
            paid_leave_days += days
        if request.allowance_amount and start <= request.start_date <= end:
            allowances.append(
                {
                    "request_id": request.id,
                    "days": str(request.days),
                    "amount": request.allowance_amount,
                }
            )
    return {
        "unpaid_leave_days": unpaid_days,
        "paid_leave_days": paid_leave_days,
        "leave_allowances": allowances,
    }


def annual_plan(year, employees):
    """BN-55: approved and pending leaves of the year, for a calendar view."""
    return LeaveRequest.objects.filter(
        employee__in=employees,
        status__in=CONSUMED_STATUSES + PENDING_STATUSES,
        start_date__lte=datetime.date(year, 12, 31),
        end_date__gte=datetime.date(year, 1, 1),
    ).select_related("employee", "employee__department", "leave_type")
