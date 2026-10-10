"""
M-15 – HR indicators (BN-155 → BN-162).

Every indicator is computed from the detailed data, so the dashboards are
always consistent with the records. Filters (BN-160): period, department,
site, category and contract type.
"""

import datetime
from collections import Counter, OrderedDict
from decimal import Decimal

from django.db.models import Q, Sum
from django.utils import timezone

from employees.models import Employee
from users.models import User
from users.permissions import is_admin, scope_employees

ZERO = Decimal("0")
PAYROLL_ROLES = {
    User.Roles.HR_MANAGER,
    User.Roles.PAYROLL_OFFICER,
    User.Roles.ACCOUNTANT,
    User.Roles.GENERAL_MANAGEMENT,
}
AGE_BRACKETS = (
    (0, 25, "< 25"),
    (25, 35, "25–34"),
    (35, 45, "35–44"),
    (45, 55, "45–54"),
    (55, 200, "55 +"),
)
SENIORITY_BRACKETS = (
    (0, 1, "< 1 year"),
    (1, 5, "1–4 years"),
    (5, 10, "5–9 years"),
    (10, 20, "10–19 years"),
    (20, 100, "20 years +"),
)


def can_see_payroll_indicators(user):
    return is_admin(user) or user.role in PAYROLL_ROLES


def _years(start, day):
    if not start:
        return 0
    return day.year - start.year - ((day.month, day.day) < (start.month, start.day))


def _bracket(value, brackets):
    for low, high, label in brackets:
        if low <= value < high:
            return label
    return brackets[-1][2]


def filtered_employees(user, filters, day=None):
    queryset = scope_employees(
        user,
        Employee.objects.select_related(
            "department", "position", "classification", "workplace"
        ),
    )
    if filters.get("department"):
        queryset = queryset.filter(department_id=filters["department"])
    if filters.get("site"):
        queryset = queryset.filter(workplace_id=filters["site"])
    if filters.get("category"):
        queryset = queryset.filter(classification__category=filters["category"])
    if filters.get("contract_type"):
        queryset = queryset.filter(contract_type=filters["contract_type"])
    return queryset


def _in_force(employee, day):
    contracts = [c for c in employee.contracts.all() if c.status != "DRAFT"]
    if contracts:
        return any(c.is_in_force(day) for c in contracts)
    return employee.status == "ACTIVE" and (
        not employee.date_of_hire or employee.date_of_hire <= day
    )


def headcount(user, filters, day=None):
    """BN-156."""
    day = day or timezone.now().date()
    employees = [
        e
        for e in filtered_employees(user, filters).prefetch_related(
            "contracts__termination"
        )
        if e.status != "ARCHIVED" and _in_force(e, day)
    ]
    count = Counter()
    keys = (
        "department",
        "position",
        "category",
        "contract_type",
        "sex",
        "age",
        "seniority",
        "site",
    )
    groups = {key: Counter() for key in keys}
    for e in employees:
        count["total"] += 1
        groups["department"][e.department.name if e.department else "—"] += 1
        groups["position"][e.position.title if e.position else "—"] += 1
        groups["category"][e.classification.category if e.classification else "—"] += 1
        groups["contract_type"][e.get_contract_type_display()] += 1
        groups["sex"][e.get_sex_display()] += 1
        groups["age"][_bracket(_years(e.date_of_birth, day), AGE_BRACKETS)] += 1
        groups["seniority"][
            _bracket(_years(e.date_of_hire, day), SENIORITY_BRACKETS)
        ] += 1
        groups["site"][e.workplace.name if e.workplace else "—"] += 1
    order = {
        "age": [b[2] for b in AGE_BRACKETS],
        "seniority": [b[2] for b in SENIORITY_BRACKETS],
    }
    result = {"date": day, "total": count["total"]}
    for key, counter in groups.items():
        labels = order.get(key) or sorted(counter, key=lambda k: -counter[k])
        result[f"by_{key}"] = [
            {"label": label, "value": counter[label]}
            for label in labels
            if counter[label]
        ]
    return result


def _months(start, end):
    months = []
    day = start.replace(day=1)
    while day <= end:
        months.append((day.year, day.month))
        day = (day + datetime.timedelta(days=32)).replace(day=1)
    return months


def movements(user, filters, start, end):
    """BN-157: hiring, departures, turnover, promotions and transfers."""
    from careers.models import CareerAct
    from contracts.models import ContractTermination

    employees = filtered_employees(user, filters)
    ids = set(employees.values_list("id", flat=True))
    hires = []
    for e in employees.prefetch_related("contracts"):
        contracts = [c for c in e.contracts.all() if c.status != "DRAFT"]
        first = min((c.start_date for c in contracts), default=e.date_of_hire)
        if first and start <= first <= end:
            hires.append(first)
    departures = list(
        ContractTermination.objects.filter(
            contract__employee_id__in=ids, termination_date__range=(start, end)
        ).values_list("termination_date", flat=True)
    )
    acts = CareerAct.objects.filter(
        employee_id__in=ids,
        status__in=("APPLIED", "ENDED"),
        effective_date__range=(start, end),
    )
    promotions = list(
        acts.filter(act_type="PROMOTION").values_list("effective_date", flat=True)
    )
    transfers = list(
        acts.filter(
            act_type__in=("TRANSFER", "TEMPORARY_ASSIGNMENT", "SECONDMENT")
        ).values_list("effective_date", flat=True)
    )
    head_start = headcount(user, filters, start)["total"]
    head_end = headcount(user, filters, end)["total"]
    average = (head_start + head_end) / 2 or 1
    series = []
    for year, month in _months(start, end):

        def in_month(dates):
            return sum(1 for d in dates if d.year == year and d.month == month)

        series.append(
            {
                "month": f"{year}-{month:02d}",
                "hires": in_month(hires),
                "departures": in_month(departures),
                "promotions": in_month(promotions),
                "transfers": in_month(transfers),
            }
        )
    return {
        "start": start,
        "end": end,
        "hires": len(hires),
        "departures": len(departures),
        "promotions": len(promotions),
        "transfers": len(transfers),
        "headcount_start": head_start,
        "headcount_end": head_end,
        "turnover_rate": round(len(departures) / average * 100, 2),
        "series": series,
    }


def time_indicators(user, filters, start, end):
    """BN-158: absenteeism, lateness, overtime, leave taken and remaining."""
    from attendance.models import DailyAttendance
    from leave.models import LeaveRequest
    from leave.services import balance

    employees = filtered_employees(user, filters)
    records = DailyAttendance.objects.filter(
        employee__in=employees, date__range=(start, end)
    )
    expected = records.aggregate(s=Sum("expected_minutes"))["s"] or 0
    absent = (
        records.filter(status="ABSENT").aggregate(s=Sum("expected_minutes"))["s"] or 0
    )
    sick_days = 0
    leave_taken = ZERO
    for request in LeaveRequest.objects.filter(
        employee__in=employees,
        status__in=("APPROVED", "INTERRUPTED"),
        start_date__lte=end,
        end_date__gte=start,
    ).select_related("leave_type"):
        leave_taken += request.days
        if request.leave_type.code == "SICK":
            first = max(start, request.start_date)
            last = min(end, request.effective_end_date)
            sick_days += (last - first).days + 1
    sick_minutes = sick_days * 8 * 60
    remaining = ZERO
    for employee in employees.filter(status="ACTIVE"):
        remaining += balance(employee, end.year, min(end, timezone.now().date()))[
            "remaining"
        ]
    late = records.filter(late_minutes__gt=0)
    overtime = records.filter(overtime_status="APPROVED")
    overtime_minutes = sum(r.overtime_minutes for r in overtime)
    return {
        "start": start,
        "end": end,
        "absenteeism_rate": (
            round((absent + sick_minutes) / expected * 100, 2) if expected else 0
        ),
        "unjustified_absence_days": records.filter(
            status="ABSENT", absence_justified=False
        ).count(),
        "lateness_count": late.count(),
        "lateness_minutes": late.aggregate(s=Sum("late_minutes"))["s"] or 0,
        "overtime_hours": round(overtime_minutes / 60, 2),
        "pending_overtime_days": records.filter(overtime_status="PENDING").count(),
        "leave_taken_days": leave_taken,
        "leave_remaining_days": remaining,
    }


def payroll_indicators(user, filters, start, end):
    """BN-159: payroll cost, evolution, distribution, average cost, charges."""
    from payroll.models import Payslip

    employees = filtered_employees(user, filters)
    payslips = (
        Payslip.objects.filter(employee__in=employees, status="VALIDATED")
        .filter(
            Q(period__year__gt=start.year)
            | Q(period__year=start.year, period__month__gte=start.month)
        )
        .filter(
            Q(period__year__lt=end.year)
            | Q(period__year=end.year, period__month__lte=end.month)
        )
        .select_related("period", "employee__department")
    )
    totals = payslips.aggregate(
        gross=Sum("gross"),
        employer=Sum("employer_contributions"),
        net=Sum("net_payable"),
        employee=Sum("employee_contributions"),
        taxes=Sum("taxes"),
    )
    totals = {k: v or ZERO for k, v in totals.items()}
    cost = totals["gross"] + totals["employer"]
    by_month = OrderedDict((f"{y}-{m:02d}", ZERO) for y, m in _months(start, end))
    by_department = Counter()
    payslip_count = 0
    for payslip in payslips:
        key = f"{payslip.period.year}-{payslip.period.month:02d}"
        by_month[key] = (
            by_month.get(key, ZERO) + payslip.gross + payslip.employer_contributions
        )
        department = (
            payslip.employee.department.name if payslip.employee.department else "—"
        )
        by_department[department] += payslip.gross + payslip.employer_contributions
        payslip_count += 1
    return {
        "start": start,
        "end": end,
        "total_cost": cost,
        "gross": totals["gross"],
        "net_payable": totals["net"],
        "employer_contributions": totals["employer"],
        "employee_contributions": totals["employee"],
        "taxes": totals["taxes"],
        # One payslip = one employee-month: average monthly cost per employee.
        "average_cost_per_employee": (
            round(cost / payslip_count) if payslip_count else 0
        ),
        "employer_charges_weight": (
            round(totals["employer"] / totals["gross"] * 100, 2)
            if totals["gross"]
            else 0
        ),
        "by_month": [{"label": k, "value": v} for k, v in by_month.items()],
        "by_department": [
            {"label": k, "value": v} for k, v in by_department.most_common()
        ],
    }


# --------------------------------------------------------------------------
# Dashboards per profile (BN-155)
# --------------------------------------------------------------------------


def dashboard(user):
    from contracts.services import upcoming_deadlines
    from notifications.services import tasks_for

    today = timezone.now().date()
    month_start = today.replace(day=1)
    data = {
        "role": user.role,
        "pending_approvals": tasks_for(user).count(),
        "widgets": [],
    }
    employee = Employee.objects.filter(user=user).first()
    if employee is not None:
        from leave.services import balance
        from planning.models import TimetableEntry

        data["me"] = {
            "leave_balance": balance(employee, today.year, today),
            "next_shifts": [
                {
                    "date": e.date,
                    "shift": e.shift.name,
                    "start": e.shift.start_time,
                    "end": e.shift.end_time,
                }
                for e in TimetableEntry.objects.filter(
                    employee=employee, date__gte=today, timetable__status="PUBLISHED"
                )
                .select_related("shift")
                .order_by("date")[:5]
            ],
        }
        last = (
            employee.payslips.filter(status="VALIDATED")
            .order_by("-period__year", "-period__month")
            .first()
        )
        if last is not None:
            data["me"]["last_payslip"] = {
                "id": last.id,
                "period": str(last.period),
                "net_payable": last.net_payable,
            }
    scoped = filtered_employees(user, {})
    if user.role != User.Roles.EMPLOYEE or user.managed_departments.exists():
        from attendance.models import DailyAttendance
        from leave.models import LeaveRequest

        today_records = DailyAttendance.objects.filter(employee__in=scoped, date=today)
        data["team"] = {
            "headcount": headcount(user, {}, today)["total"],
            "present_today": today_records.filter(status="PRESENT").count(),
            "absent_today": today_records.filter(status="ABSENT").count(),
            "on_leave_today": LeaveRequest.objects.filter(
                employee__in=scoped,
                status="APPROVED",
                start_date__lte=today,
                end_date__gte=today,
            ).count(),
            "pending_overtime": DailyAttendance.objects.filter(
                employee__in=scoped, overtime_status="PENDING"
            ).count(),
        }
    if user.role in (
        User.Roles.HR_MANAGER,
        User.Roles.HR_OFFICER,
        User.Roles.GENERAL_MANAGEMENT,
    ) or is_admin(user):
        data["hr"] = {
            "movements": movements(user, {}, month_start.replace(month=1), today),
            "contract_alerts": len(upcoming_deadlines(today)),
            "headcount": headcount(user, {}, today),
        }
    if can_see_payroll_indicators(user):
        start = (today.replace(day=1) - datetime.timedelta(days=330)).replace(day=1)
        data["payroll"] = payroll_indicators(user, {}, start, today)
        from payroll.models import PayrollPeriod

        current = PayrollPeriod.objects.filter(
            year=today.year, month=today.month
        ).first()
        data["payroll"]["current_period_status"] = (
            current.status if current else "NOT_OPENED"
        )
    return data


# --------------------------------------------------------------------------
# Personalised reports (BN-161)
# --------------------------------------------------------------------------

DATASET_FIELDS = {
    "EMPLOYEES": {
        "matriculation_number": "Matriculation",
        "surname": "Surname",
        "given_names": "Given names",
        "sex": "Sex",
        "date_of_birth": "Date of birth",
        "nationality": "Nationality",
        "department__name": "Department",
        "position__title": "Position",
        "classification__category": "Category",
        "workplace__name": "Site",
        "contract_type": "Contract type",
        "date_of_hire": "Date of hire",
        "status": "Status",
        "marital_status": "Marital status",
    },
    "CONTRACTS": {
        "reference": "Reference",
        "employee__surname": "Surname",
        "employee__given_names": "Given names",
        "contract_type": "Type",
        "status": "Status",
        "start_date": "Start",
        "end_date": "End",
        "department__name": "Department",
        "position__title": "Position",
        "weekly_hours": "Weekly hours",
    },
    "LEAVE": {
        "employee__surname": "Surname",
        "employee__given_names": "Given names",
        "employee__department__name": "Department",
        "leave_type__name": "Type",
        "start_date": "Start",
        "end_date": "End",
        "days": "Days",
        "status": "Status",
    },
    "ATTENDANCE": {
        "employee__surname": "Surname",
        "employee__given_names": "Given names",
        "employee__department__name": "Department",
        "date": "Date",
        "status": "Status",
        "worked_minutes": "Worked (min)",
        "late_minutes": "Late (min)",
        "missing_minutes": "Missing (min)",
        "overtime_day_minutes": "Overtime day (min)",
    },
    "PAYSLIPS": {
        "employee__surname": "Surname",
        "employee__given_names": "Given names",
        "employee__department__name": "Department",
        "period__year": "Year",
        "period__month": "Month",
        "gross": "Gross",
        "employee_contributions": "Employee contributions",
        "taxes": "Taxes",
        "employer_contributions": "Employer contributions",
        "net_payable": "Net payable",
    },
    "CAREER": {
        "employee__surname": "Surname",
        "employee__given_names": "Given names",
        "act_type": "Act",
        "effective_date": "Effective date",
        "status": "Status",
        "reason": "Reason",
    },
}
NUMERIC = {
    "days",
    "worked_minutes",
    "late_minutes",
    "missing_minutes",
    "overtime_day_minutes",
    "gross",
    "employee_contributions",
    "taxes",
    "employer_contributions",
    "net_payable",
    "weekly_hours",
}


def dataset_queryset(user, dataset):
    from attendance.models import DailyAttendance
    from careers.models import CareerAct
    from contracts.models import Contract
    from leave.models import LeaveRequest
    from payroll.models import Payslip

    if dataset == "EMPLOYEES":
        return scope_employees(user, Employee.objects.all())
    model = {
        "CONTRACTS": Contract,
        "LEAVE": LeaveRequest,
        "ATTENDANCE": DailyAttendance,
        "PAYSLIPS": Payslip,
        "CAREER": CareerAct,
    }[dataset]
    queryset = scope_employees(user, model.objects.all(), "employee__")
    if dataset == "PAYSLIPS":
        if not can_see_payroll_indicators(user):
            return queryset.none()
        queryset = queryset.filter(status="VALIDATED")
    return queryset


def run_report(user, dataset, fields, filters=None, group_by=""):
    allowed = DATASET_FIELDS.get(dataset)
    if allowed is None:
        raise ValueError("Unknown dataset.")
    fields = [f for f in (fields or list(allowed)) if f in allowed]
    queryset = dataset_queryset(user, dataset)
    for key, value in (filters or {}).items():
        base = key.split("__gte")[0].split("__lte")[0].split("__icontains")[0]
        if base in allowed and value not in ("", None):
            queryset = queryset.filter(**{key: value})
    if group_by and group_by in allowed:
        from django.db.models import Count

        sums = {
            f"sum_{f}": Sum(f)
            for f in fields
            if f in NUMERIC or f.split("__")[-1] in NUMERIC
        }
        rows = (
            queryset.values(group_by)
            .annotate(count=Count("id"), **sums)
            .order_by(group_by)
        )
        headers = [allowed[group_by], "Count"] + [
            f"Total {allowed[f[4:]]}" for f in sums
        ]
        return headers, [[r[group_by], r["count"], *[r[k] for k in sums]] for r in rows]
    rows = queryset.values_list(*fields)[:5000]
    return [allowed[f] for f in fields], [list(r) for r in rows]


def send_scheduled_reports(today=None):
    """BN-162: daily job sending the due periodic reports."""
    from django.core.mail import EmailMessage

    from core.exports import export_rows

    from .models import ReportSchedule

    today = today or timezone.now().date()
    sent = 0
    for schedule in ReportSchedule.objects.filter(is_active=True).select_related(
        "report__owner"
    ):
        if not schedule.is_due(today):
            continue
        report = schedule.report
        headers, rows = run_report(
            report.owner, report.dataset, report.fields, report.filters, report.group_by
        )
        response = export_rows(
            headers, rows, report.name, schedule.file_format, title=report.name
        )
        recipients = [r.strip() for r in schedule.recipients.split(",") if r.strip()]
        message = EmailMessage(
            subject=f"[HRMS] {report.name} – {today:%d/%m/%Y}",
            body=f"Please find attached the report {report.name}.",
            to=recipients,
        )
        message.attach(
            f"{report.name}.{schedule.file_format}",
            response.content,
            response["Content-Type"],
        )
        message.send()
        schedule.last_sent_at = timezone.now()
        schedule.save(update_fields=["last_sent_at"])
        sent += 1
    return sent
