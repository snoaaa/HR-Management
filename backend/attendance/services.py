"""
Calendars, expected hours and the daily attendance computation.

Rules applied (all thresholds are settings, never constants):
- the expected hours of a day come, in this order, from the published
  timetable (M-07), a schedule exception, then the assigned schedule model;
- a weekly rest day or a public holiday expects no work: any time worked
  that day is rest-day or public-holiday overtime (BN-39);
- unclocked gaps between two clockings count as break; the rest of the
  scheduled break is deducted from the time worked;
- lateness below LATENESS_TOLERANCE_MINUTES is not counted;
- overtime worked inside the night window (NIGHT_START → NIGHT_END) is night
  overtime, the rest is day overtime.
"""

import datetime

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from core.models import get_int_setting, get_setting

from .models import (
    AttendancePeriod,
    Clocking,
    DailyAttendance,
    Mission,
    PublicHoliday,
    ScheduleAssignment,
    ScheduleException,
    WorkingCalendar,
)

DEFAULT_REST_DAYS = [5, 6]


class AttendanceError(Exception):
    pass


# --------------------------------------------------------------------------
# Time helpers
# --------------------------------------------------------------------------


def to_minutes(value):
    return value.hour * 60 + value.minute


def span_minutes(start, end):
    """Minutes between two times; an end before the start crosses midnight."""
    minutes = to_minutes(end) - to_minutes(start)
    return minutes + 24 * 60 if minutes <= 0 else minutes


def _interval(start, end):
    a = to_minutes(start)
    b = a + span_minutes(start, end)
    return a, b


def _overlap(a, b):
    return max(0, min(a[1], b[1]) - max(a[0], b[0]))


def _parse_time(value):
    hours, minutes = value.split(":")[:2]
    return datetime.time(int(hours), int(minutes))


def night_windows():
    start = to_minutes(_parse_time(get_setting("NIGHT_START", "22:00")))
    end = to_minutes(_parse_time(get_setting("NIGHT_END", "06:00")))
    if end <= start:
        # e.g. 22:00 → 06:00: two windows over the day plus the next morning.
        return [(0, end), (start, 24 * 60 + end)]
    return [(start, end)]


def daterange(start, end):
    day = start
    while day <= end:
        yield day
        day += datetime.timedelta(days=1)


# --------------------------------------------------------------------------
# Calendars (BN-61, BN-08)
# --------------------------------------------------------------------------


def calendar_for(site):
    calendar = None
    if site is not None:
        calendar = WorkingCalendar.objects.filter(site=site).first()
    if calendar is None:
        calendar = WorkingCalendar.objects.filter(site__isnull=True).first()
    return calendar


def rest_days_for(site):
    calendar = calendar_for(site)
    return calendar.rest_days if calendar is not None else DEFAULT_REST_DAYS


def holiday_on(day, site=None):
    queryset = PublicHoliday.objects.filter(Q(site__isnull=True) | Q(site=site))
    return queryset.filter(
        Q(date=day) | Q(recurring=True, date__month=day.month, date__day=day.day)
    ).first()


def is_rest_day(day, site=None):
    return day.weekday() in rest_days_for(site)


def is_working_day(day, site=None):
    return not is_rest_day(day, site) and holiday_on(day, site) is None


def working_days_between(start, end, site=None):
    """BN-52: days between two dates, rest days and public holidays excluded."""
    rest_days = rest_days_for(site)
    holidays = PublicHoliday.objects.filter(Q(site__isnull=True) | Q(site=site))
    fixed = set(holidays.filter(recurring=False).values_list("date", flat=True))
    recurring = {
        (d.month, d.day)
        for d in holidays.filter(recurring=True).values_list("date", flat=True)
    }
    count = 0
    for day in daterange(start, end):
        if day.weekday() in rest_days:
            continue
        if day in fixed or (day.month, day.day) in recurring:
            continue
        count += 1
    return count


# --------------------------------------------------------------------------
# Expected hours (BN-59, BN-60)
# --------------------------------------------------------------------------


def assignment_for(employee, day):
    base = ScheduleAssignment.objects.filter(effective_from__lte=day).filter(
        Q(effective_to__isnull=True) | Q(effective_to__gte=day)
    )
    for lookup in (
        {"employee": employee},
        {"position_id": employee.position_id, "employee__isnull": True},
        {"department_id": employee.department_id, "employee__isnull": True},
        {"site_id": employee.workplace_id, "employee__isnull": True},
        # No target at all: the schedule of the whole organisation.
        {
            "employee__isnull": True,
            "position__isnull": True,
            "department__isnull": True,
            "site__isnull": True,
        },
    ):
        if any(value is None for key, value in lookup.items() if key.endswith("_id")):
            continue
        assignment = (
            base.filter(**lookup)
            .select_related("schedule")
            .order_by("-effective_from")
            .first()
        )
        if assignment is not None:
            return assignment
    return None


def _planned_shift(employee, day):
    try:
        from planning.services import planned_shift
    except ImportError:
        return None
    return planned_shift(employee, day)


def expected_for(employee, day):
    """
    Expected work of the employee on a day, or None when no work is expected.
    Returns {"start", "end", "break_minutes", "minutes", "flexible", "source"}.
    """
    site = employee.workplace
    shift = _planned_shift(employee, day)
    if shift is not None:
        minutes = max(
            0, span_minutes(shift.start_time, shift.end_time) - shift.break_minutes
        )
        return {
            "start": shift.start_time,
            "end": shift.end_time,
            "break_minutes": shift.break_minutes,
            "minutes": minutes,
            "flexible": False,
            "source": "TIMETABLE",
        }
    exception = ScheduleException.objects.filter(employee=employee, date=day).first()
    if exception is not None:
        if exception.is_day_off or not exception.start_time or not exception.end_time:
            return None
        minutes = (
            span_minutes(exception.start_time, exception.end_time)
            - exception.break_minutes
        )
        return {
            "start": exception.start_time,
            "end": exception.end_time,
            "break_minutes": exception.break_minutes,
            "minutes": max(0, minutes),
            "flexible": False,
            "source": "EXCEPTION",
        }
    if not is_working_day(day, site):
        return None
    assignment = assignment_for(employee, day)
    if assignment is None:
        return None
    schedule = assignment.schedule
    if schedule.schedule_type == "SHIFT":
        # Shift workers only work when planned in a published timetable.
        return None
    schedule_day = schedule.days.filter(weekday=day.weekday()).first()
    if schedule_day is None:
        return None
    flexible = schedule.schedule_type == "FLEXIBLE"
    return {
        "start": schedule_day.start_time,
        "end": schedule_day.end_time,
        "break_minutes": schedule_day.break_minutes,
        "minutes": (
            schedule.flexible_daily_minutes
            if flexible
            else schedule_day.expected_minutes
        ),
        "flexible": flexible,
        "source": "SCHEDULE",
    }


# --------------------------------------------------------------------------
# Daily computation (BN-38, BN-39)
# --------------------------------------------------------------------------


def _employment_status(employee, day):
    """Return None when employed and working normally, else a status."""
    contracts = list(
        employee.contracts.exclude(status="DRAFT")
        .select_related("termination")
        .prefetch_related("suspensions")
    )
    if contracts:
        in_force = [c for c in contracts if c.is_in_force(day)]
        if not in_force:
            return "NOT_EMPLOYED"
        for contract in in_force:
            for suspension in contract.suspensions.all():
                if suspension.start_date <= day and (
                    suspension.end_date is None or suspension.end_date >= day
                ):
                    return "SUSPENDED"
        return None
    if employee.date_of_hire and employee.date_of_hire > day:
        return "NOT_EMPLOYED"
    return None


def _leave_on(employee, day):
    try:
        from leave.services import leave_on
    except ImportError:
        return None
    return leave_on(employee, day)


def period_locked(day):
    return AttendancePeriod.objects.filter(
        year=day.year, month=day.month, status="LOCKED"
    ).exists()


def compute_day(employee, day, notify_manager=True):
    """Compute (or recompute) the attendance of one employee for one day."""
    if period_locked(day):
        return DailyAttendance.objects.filter(employee=employee, date=day).first()
    existing = DailyAttendance.objects.filter(employee=employee, date=day).first()
    record = existing or DailyAttendance(employee=employee, date=day)
    previous_overtime = existing.overtime_minutes if existing else 0
    previous_status = existing.overtime_status if existing else "NONE"

    for field in (
        "expected_minutes",
        "worked_minutes",
        "late_minutes",
        "early_departure_minutes",
        "missing_minutes",
        "overtime_day_minutes",
        "overtime_night_minutes",
        "overtime_rest_day_minutes",
        "overtime_holiday_minutes",
    ):
        setattr(record, field, 0)
    record.expected_start = record.expected_end = None
    record.open_clocking = False

    site = employee.workplace
    clockings = list(
        Clocking.objects.filter(employee=employee, date=day, is_active=True).order_by(
            "time_in"
        )
    )
    closed = [c for c in clockings if c.time_out is not None]
    record.open_clocking = len(closed) != len(clockings)
    intervals = [_interval(c.time_in, c.time_out) for c in closed]
    raw_worked = sum(b - a for a, b in intervals)

    status = _employment_status(employee, day)
    expected = None
    if status is None:
        if _leave_on(employee, day) is not None:
            status = "LEAVE"
        elif Mission.objects.filter(
            employee=employee, start_date__lte=day, end_date__gte=day
        ).exists():
            status = "MISSION"

    if status is None:
        expected = expected_for(employee, day)
        holiday = holiday_on(day, site)
        if expected is None or holiday is not None:
            status = "HOLIDAY" if holiday is not None else "REST"
            if holiday is not None:
                record.overtime_holiday_minutes = raw_worked
            else:
                record.overtime_rest_day_minutes = raw_worked
            record.worked_minutes = raw_worked
            expected = None

    if expected is not None:
        record.expected_start = expected["start"]
        record.expected_end = expected["end"]
        record.expected_minutes = expected["minutes"]
        if not intervals:
            status = "ABSENT" if not record.open_clocking else "PRESENT"
            record.missing_minutes = expected["minutes"]
        else:
            status = "PRESENT"
            # Only the unclocked gaps inside the scheduled hours count as break.
            window = _interval(expected["start"], expected["end"])
            gaps = sum(
                _overlap((intervals[i][1], intervals[i + 1][0]), window)
                for i in range(len(intervals) - 1)
            )
            break_to_deduct = max(0, expected["break_minutes"] - gaps)
            worked = max(0, raw_worked - break_to_deduct)
            record.worked_minutes = worked
            if not expected["flexible"]:
                tolerance = get_int_setting("LATENESS_TOLERANCE_MINUTES", 5)
                late = intervals[0][0] - to_minutes(expected["start"])
                record.late_minutes = late if late > tolerance else 0
                expected_end = _interval(expected["start"], expected["end"])[1]
                early = expected_end - intervals[-1][1]
                record.early_departure_minutes = max(0, early)
            record.missing_minutes = max(0, expected["minutes"] - worked)
            overtime = max(0, worked - expected["minutes"])
            if overtime:
                window = _interval(expected["start"], expected["end"])
                night = sum(
                    max(
                        0,
                        _overlap(iv, nw)
                        - _overlap((max(iv[0], nw[0]), min(iv[1], nw[1])), window),
                    )
                    for iv in intervals
                    for nw in night_windows()
                )
                record.overtime_night_minutes = min(overtime, night)
                record.overtime_day_minutes = overtime - record.overtime_night_minutes
    elif status in ("LEAVE", "MISSION", "SUSPENDED", "NOT_EMPLOYED"):
        record.worked_minutes = raw_worked if status == "MISSION" else 0

    record.status = status
    if record.status != "ABSENT":
        record.absence_justified = False if not existing else existing.absence_justified
    # BN-40: overtime must be approved again when it changes.
    if record.overtime_minutes == 0:
        record.overtime_status = "NONE"
    elif record.overtime_minutes != previous_overtime or previous_status == "NONE":
        record.overtime_status = "PENDING"
    record.save()
    if (
        notify_manager
        and record.overtime_status == "PENDING"
        and previous_status != "PENDING"
    ):
        _notify_overtime(record)
    return record


def _notify_overtime(record):
    from notifications.services import line_manager_of, notify

    manager = line_manager_of(record.employee)
    if manager is not None:
        hours = record.overtime_minutes / 60
        notify(
            manager,
            f"Overtime to approve: {record.employee.full_name}",
            f"{hours:.2f} h on {record.date:%d/%m/%Y}.",
            "/attendance#overtime",
            "APPROVAL",
        )


def recompute(employee, start, end=None):
    end = min(end or start, timezone.now().date())
    return [compute_day(employee, day) for day in daterange(start, end)]


def check_not_locked(day):
    if period_locked(day):
        raise AttendanceError(
            f"The attendance of {day:%m/%Y} is locked: the payroll is validated."
        )


# --------------------------------------------------------------------------
# Clockings (BN-36, BN-37, BN-44)
# --------------------------------------------------------------------------


def validate_clocking(employee, day, time_in, time_out, exclude_id=None):
    check_not_locked(day)
    if day > timezone.now().date():
        raise AttendanceError("A clocking cannot be recorded in the future.")
    if time_out is not None and time_out == time_in:
        raise AttendanceError("The exit must be after the entry.")
    others = Clocking.objects.filter(employee=employee, date=day, is_active=True)
    if exclude_id:
        others = others.exclude(pk=exclude_id)
    new = (
        _interval(time_in, time_out)
        if time_out
        else (to_minutes(time_in), to_minutes(time_in) + 1)
    )
    for other in others:
        existing = (
            _interval(other.time_in, other.time_out)
            if other.time_out
            else (to_minutes(other.time_in), to_minutes(other.time_in) + 1)
        )
        if _overlap(new, existing):
            raise AttendanceError("This clocking overlaps another clocking of the day.")


def self_clock(employee, user, now=None):
    """BN-37: self-recording. Opens an entry or closes the open one."""
    now = timezone.localtime(now or timezone.now())
    day, current = now.date(), now.time().replace(second=0, microsecond=0)
    check_not_locked(day)
    open_clocking = Clocking.objects.filter(
        employee=employee, date=day, time_out__isnull=True, is_active=True
    ).first()
    if open_clocking is not None:
        open_clocking.time_out = current
        open_clocking.save(update_fields=["time_out"])
        clocking = open_clocking
    else:
        clocking = Clocking.objects.create(
            employee=employee, date=day, time_in=current, source="SELF", created_by=user
        )
    compute_day(employee, day)
    return clocking


@transaction.atomic
def apply_regularisation(regularisation, user):
    """BN-44: the original clocking stays visible but is replaced."""
    check_not_locked(regularisation.date)
    new = Clocking.objects.create(
        employee=regularisation.employee,
        date=regularisation.date,
        time_in=regularisation.time_in,
        time_out=regularisation.time_out,
        source="REGULARISATION",
        created_by=user,
    )
    if regularisation.clocking is not None:
        original = regularisation.clocking
        original.is_active = False
        original.replaced_by = new
        original.save(update_fields=["is_active", "replaced_by"])
    regularisation.status = "APPROVED"
    regularisation.save(update_fields=["status"])
    compute_day(regularisation.employee, regularisation.date)
    return new


IMPORT_FORMAT = (
    "CSV with a header line. Accepted columns: "
    "matriculation;date;time_in;time_out (one pair per line) or "
    "matriculation;timestamp;direction with direction IN or OUT. "
    "Dates as YYYY-MM-DD or DD/MM/YYYY, times as HH:MM. Separator ; or ,"
)


def _parse_date(value):
    value = value.strip()
    if "/" in value:
        d, m, y = value.split("/")
        return datetime.date(int(y), int(m), int(d))
    return datetime.date.fromisoformat(value)


def import_clockings(content, user):
    """
    BN-37 / BN-180: import a file produced by a badge or biometric device.
    Returns a control report with the rejected lines.
    """
    import csv
    import io

    from employees.models import Employee

    text = content.decode("utf-8-sig") if isinstance(content, bytes) else content
    dialect = ";" if text.count(";") >= text.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=dialect)
    fields = {f.strip().lower() for f in (reader.fieldnames or [])}
    imported, rejected, touched = 0, [], set()
    pending_in = {}
    employees = {e.matriculation_number: e for e in Employee.objects.all()}

    for line_number, raw in enumerate(reader, start=2):
        row = {(k or "").strip().lower(): (v or "").strip() for k, v in raw.items()}
        try:
            employee = employees.get(row.get("matriculation", ""))
            if employee is None:
                raise AttendanceError(
                    f"Unknown matriculation '{row.get('matriculation')}'."
                )
            if {"date", "time_in"} <= fields:
                day = _parse_date(row["date"])
                time_in = _parse_time(row["time_in"])
                time_out = _parse_time(row["time_out"]) if row.get("time_out") else None
                validate_clocking(employee, day, time_in, time_out)
                Clocking.objects.create(
                    employee=employee,
                    date=day,
                    time_in=time_in,
                    time_out=time_out,
                    source="IMPORT",
                    created_by=user,
                )
            elif {"timestamp", "direction"} <= fields:
                stamp = row["timestamp"].replace("T", " ")
                date_part, time_part = stamp.split(" ")[:2]
                day, moment = _parse_date(date_part), _parse_time(time_part)
                direction = row["direction"].upper()
                key = (employee.id, day)
                if direction == "IN":
                    pending_in[key] = moment
                    continue
                if direction != "OUT" or key not in pending_in:
                    raise AttendanceError("Exit without a matching entry.")
                time_in = pending_in.pop(key)
                validate_clocking(employee, day, time_in, moment)
                Clocking.objects.create(
                    employee=employee,
                    date=day,
                    time_in=time_in,
                    time_out=moment,
                    source="IMPORT",
                    created_by=user,
                )
            else:
                raise AttendanceError("Unrecognised columns. " + IMPORT_FORMAT)
            imported += 1
            touched.add((employee.id, day))
        except (AttendanceError, ValueError, KeyError) as exc:
            rejected.append({"line": line_number, "data": raw, "reason": str(exc)})

    for (employee_id, day), moment in pending_in.items():
        employee = Employee.objects.get(pk=employee_id)
        try:
            validate_clocking(employee, day, moment, None)
            Clocking.objects.create(
                employee=employee,
                date=day,
                time_in=moment,
                source="IMPORT",
                created_by=user,
            )
            imported += 1
            touched.add((employee_id, day))
        except AttendanceError as exc:
            rejected.append(
                {"line": None, "data": {"entry": str(moment)}, "reason": str(exc)}
            )

    for employee_id, day in touched:
        compute_day(Employee.objects.get(pk=employee_id), day)
    return {"imported": imported, "rejected": rejected, "format": IMPORT_FORMAT}


# --------------------------------------------------------------------------
# Period consolidation (BN-45) and transfer to payroll (BN-41)
# --------------------------------------------------------------------------


def month_bounds(year, month):
    start = datetime.date(year, month, 1)
    end = (start + datetime.timedelta(days=32)).replace(day=1) - datetime.timedelta(
        days=1
    )
    return start, end


def active_employees(start, end):
    from employees.models import Employee

    return Employee.objects.exclude(status="ARCHIVED").filter(
        Q(date_of_hire__lte=end) | Q(date_of_hire__isnull=True)
    )


@transaction.atomic
def consolidate_period(year, month, user=None):
    period, _ = AttendancePeriod.objects.get_or_create(year=year, month=month)
    if period.status == "LOCKED":
        raise AttendanceError("The period is locked.")
    start, end = month_bounds(year, month)
    end = min(end, timezone.now().date())
    summary = {
        "employees": 0,
        "absences": 0,
        "unjustified_absences": 0,
        "pending_overtime": 0,
    }
    for employee in active_employees(start, end):
        summary["employees"] += 1
        for day in daterange(start, end):
            record = compute_day(employee, day, notify_manager=False)
            if record.status == "ABSENT":
                summary["absences"] += 1
                if not record.absence_justified:
                    summary["unjustified_absences"] += 1
            if record.overtime_status == "PENDING":
                summary["pending_overtime"] += 1
    period.status = "CONSOLIDATED"
    period.consolidated_at = timezone.now()
    period.summary = summary
    period.save()
    return period


def lock_period(year, month):
    """Called when the payroll of the period is validated (BN-45)."""
    period, _ = AttendancePeriod.objects.get_or_create(year=year, month=month)
    period.status = "LOCKED"
    period.locked_at = timezone.now()
    period.save()
    return period


def unlock_period(year, month):
    """Called when a validated payroll is reversed (BN-108)."""
    AttendancePeriod.objects.filter(year=year, month=month).update(
        status="CONSOLIDATED", locked_at=None
    )


def payroll_inputs(employee, start, end):
    """
    Data transferred to the payroll for an employee and a period:
    approved overtime per category (BN-40/BN-97) and unjustified absences
    (BN-41).
    """
    records = DailyAttendance.objects.filter(
        employee=employee, date__range=(start, end)
    )
    approved = records.filter(overtime_status="APPROVED")
    unjustified = records.filter(status="ABSENT", absence_justified=False)
    by_week = {}
    for record in approved:
        iso = record.date.isocalendar()
        key = f"{iso[0]}-W{iso[1]:02d}"
        by_week[key] = by_week.get(key, 0) + record.overtime_day_minutes / 60
    return {
        # Overtime tiers are weekly (decree 68/DF/249).
        "overtime_day_hours_by_week": by_week,
        "overtime_day_hours": sum(r.overtime_day_minutes for r in approved) / 60,
        "overtime_night_hours": sum(r.overtime_night_minutes for r in approved) / 60,
        "overtime_rest_day_hours": sum(r.overtime_rest_day_minutes for r in approved)
        / 60,
        "overtime_holiday_hours": sum(r.overtime_holiday_minutes for r in approved)
        / 60,
        "unjustified_absence_days": unjustified.count(),
        "unjustified_absence_dates": [r.date.isoformat() for r in unjustified],
        "late_minutes": sum(r.late_minutes for r in records.filter(status="PRESENT")),
    }


def attendance_sheet(employees, start, end, granularity="daily"):
    """BN-42: daily / weekly / monthly sheet per employee."""
    rows = []
    records = DailyAttendance.objects.filter(
        employee__in=employees, date__range=(start, end)
    ).select_related("employee", "employee__department")
    grouped = {}
    for record in records:
        if granularity == "weekly":
            iso = record.date.isocalendar()
            key = f"{iso[0]}-W{iso[1]:02d}"
        elif granularity == "monthly":
            key = f"{record.date.year}-{record.date.month:02d}"
        else:
            key = record.date.isoformat()
        bucket = grouped.setdefault(
            (record.employee_id, key),
            {
                "employee_id": record.employee_id,
                "employee": record.employee.full_name,
                "matriculation": record.employee.matriculation_number,
                "department": (
                    record.employee.department.name
                    if record.employee.department
                    else ""
                ),
                "period": key,
                "status": record.get_status_display() if granularity == "daily" else "",
                "expected_hours": 0,
                "worked_hours": 0,
                "late_minutes": 0,
                "early_departure_minutes": 0,
                "missing_hours": 0,
                "overtime_hours": 0,
                "absent_days": 0,
                "unjustified_absent_days": 0,
                "leave_days": 0,
            },
        )
        bucket["expected_hours"] += record.expected_minutes / 60
        bucket["worked_hours"] += record.worked_minutes / 60
        bucket["late_minutes"] += record.late_minutes
        bucket["early_departure_minutes"] += record.early_departure_minutes
        bucket["missing_hours"] += record.missing_minutes / 60
        bucket["overtime_hours"] += record.overtime_minutes / 60
        bucket["absent_days"] += 1 if record.status == "ABSENT" else 0
        bucket["unjustified_absent_days"] += 1 if record.is_unjustified_absence else 0
        bucket["leave_days"] += 1 if record.status == "LEAVE" else 0
    for bucket in grouped.values():
        for key in (
            "expected_hours",
            "worked_hours",
            "missing_hours",
            "overtime_hours",
        ):
            bucket[key] = round(bucket[key], 2)
        rows.append(bucket)
    return sorted(rows, key=lambda r: (r["employee"], r["period"]))
