"""
Business rules of M-07.
"""

import datetime

from django.db import transaction
from django.utils import timezone

from attendance.services import _interval, daterange, holiday_on
from core.models import get_int_setting

from .models import Timetable, TimetableEntry


class PlanningError(Exception):
    pass


def planned_shift(employee, day):
    """Shift of a published timetable (used by the attendance computation)."""
    entry = (
        TimetableEntry.objects.filter(
            employee=employee, date=day, timetable__status="PUBLISHED"
        )
        .select_related("shift")
        .order_by("shift__start_time")
        .first()
    )
    return entry.shift if entry else None


def _absolute(entry):
    """Start and end of an entry in minutes from 1 Jan 1970 (for rest checks)."""
    base = (entry.date - datetime.date(1970, 1, 1)).days * 24 * 60
    start, end = _interval(entry.shift.start_time, entry.shift.end_time)
    return base + start, base + end


def conflicts_for(entry, others=None):
    """
    BN-63: employee on leave, already assigned, minimum rest not respected,
    weekly maximum exceeded. Returns a list of messages.
    """
    from leave.services import leave_on

    messages = []
    employee = entry.employee
    if leave_on(employee, entry.date) is not None:
        messages.append(f"{employee.full_name} is on leave on {entry.date:%d/%m/%Y}.")
    if holiday_on(entry.date, employee.workplace) is not None:
        messages.append(f"{entry.date:%d/%m/%Y} is a public holiday.")

    if others is None:
        others = TimetableEntry.objects.filter(
            employee=employee,
            date__range=(
                entry.date - datetime.timedelta(days=7),
                entry.date + datetime.timedelta(days=7),
            ),
        ).select_related("shift")
    others = [o for o in others if o.pk != entry.pk and o.employee_id == employee.id]

    start, end = _absolute(entry)
    min_rest = get_int_setting("MIN_REST_BETWEEN_SHIFTS_HOURS", 11) * 60
    for other in others:
        o_start, o_end = _absolute(other)
        if o_start < end and start < o_end:
            messages.append(
                f"{employee.full_name} is already assigned to {other.shift.name} on {other.date:%d/%m/%Y}."
            )
        elif 0 <= start - o_end < min_rest or 0 <= o_start - end < min_rest:
            messages.append(
                f"Less than {min_rest // 60} h of rest between {other.shift.name} "
                f"({other.date:%d/%m}) and {entry.shift.name} ({entry.date:%d/%m})."
            )

    monday = entry.date - datetime.timedelta(days=entry.date.weekday())
    sunday = monday + datetime.timedelta(days=6)
    week = [o for o in others if monday <= o.date <= sunday] + [entry]
    total = sum(o.shift.duration_minutes for o in week)
    maximum = get_int_setting("MAX_WEEKLY_HOURS", 48) * 60
    if total > maximum:
        messages.append(
            f"{employee.full_name} would work {total / 60:.1f} h in the week of "
            f"{monday:%d/%m} (maximum {maximum // 60} h)."
        )
    return list(dict.fromkeys(messages))


def timetable_conflicts(timetable):
    entries = list(
        timetable.entries.select_related("employee", "shift", "employee__workplace")
    )
    employees = {e.employee_id for e in entries}
    context = list(
        TimetableEntry.objects.filter(
            employee_id__in=employees,
            date__range=(
                timetable.start_date - datetime.timedelta(days=7),
                timetable.end_date + datetime.timedelta(days=7),
            ),
        ).select_related("shift")
    )
    result = []
    for entry in entries:
        messages = conflicts_for(entry, context)
        if messages:
            result.append({"entry_id": entry.id, "messages": messages})
    return result


@transaction.atomic
def add_entry(timetable, employee, day, shift, force=False):
    if not (timetable.start_date <= day <= timetable.end_date):
        raise PlanningError("The date is outside the period of the timetable.")
    entry = TimetableEntry(
        timetable=timetable, employee=employee, date=day, shift=shift
    )
    messages = conflicts_for(entry)
    if messages and not force:
        raise PlanningError(" ".join(messages))
    entry.save()
    _refresh_attendance(timetable, entry)
    return entry, messages


def _refresh_attendance(timetable, entry):
    from attendance.services import compute_day

    if timetable.status == "PUBLISHED" and entry.date <= timezone.now().date():
        compute_day(entry.employee, entry.date)


@transaction.atomic
def publish(timetable, user):
    """BN-64: publish and notify the employees concerned."""
    from notifications.services import notify

    if not timetable.entries.exists():
        raise PlanningError("The timetable is empty.")
    timetable.status = "PUBLISHED"
    timetable.published_at = timezone.now()
    timetable.save(update_fields=["status", "published_at"])
    employees = {e.employee for e in timetable.entries.select_related("employee__user")}
    notify(
        [e.user for e in employees if e.user],
        f"Timetable published: {timetable.name}",
        f"Your shifts from {timetable.start_date:%d/%m} to {timetable.end_date:%d/%m/%Y} are available.",
        "/my-space#timetable",
        "PLANNING",
    )
    from attendance.services import compute_day

    today = timezone.now().date()
    for entry in timetable.entries.filter(date__lte=today).select_related("employee"):
        compute_day(entry.employee, entry.date)
    return timetable


@transaction.atomic
def duplicate(timetable, new_start, user, name=None):
    """BN-66: copy a timetable to another period (same weekday pattern)."""
    offset = new_start - timetable.start_date
    copy = Timetable.objects.create(
        name=name or f"{timetable.name} (copy)",
        department=timetable.department,
        start_date=new_start,
        end_date=timetable.end_date + offset,
        created_by=user,
    )
    TimetableEntry.objects.bulk_create(
        [
            TimetableEntry(
                timetable=copy,
                employee=entry.employee,
                date=entry.date + offset,
                shift=entry.shift,
                note=entry.note,
            )
            for entry in timetable.entries.all()
        ]
    )
    return copy


@transaction.atomic
def apply_swap(swap, user):
    """BN-65: apply an approved exchange or replacement."""
    entry = swap.entry
    original_employee = entry.employee
    entry.employee = swap.replacement
    entry.note = f"Replaces {original_employee.full_name}"
    entry.save(update_fields=["employee", "note"])
    if swap.swap_with is not None:
        other = swap.swap_with
        other.employee = original_employee
        other.note = f"Exchange with {swap.replacement.full_name}"
        other.save(update_fields=["employee", "note"])
    swap.status = "APPROVED"
    swap.save(update_fields=["status"])
    from attendance.services import compute_day

    for day_entry in filter(None, [entry, swap.swap_with]):
        if day_entry.date <= timezone.now().date():
            compute_day(original_employee, day_entry.date)
            compute_day(swap.replacement, day_entry.date)


def planned_vs_actual(timetable):
    """BN-67: compare the planned shifts with the attendance recorded."""
    from attendance.models import DailyAttendance

    rows = []
    today = timezone.now().date()
    for entry in timetable.entries.select_related("employee", "shift").order_by(
        "date", "employee__surname"
    ):
        record = DailyAttendance.objects.filter(
            employee=entry.employee, date=entry.date
        ).first()
        planned = entry.shift.duration_minutes
        worked = record.worked_minutes if record else 0
        if entry.date > today:
            state = "FUTURE"
        elif record is None or record.status == "ABSENT":
            state = "ABSENT"
        elif record.late_minutes or record.early_departure_minutes:
            state = "DIFFERENCE"
        else:
            state = "OK"
        rows.append(
            {
                "entry_id": entry.id,
                "date": entry.date,
                "employee": entry.employee.full_name,
                "shift": entry.shift.name,
                "planned_minutes": planned,
                "worked_minutes": worked,
                "difference_minutes": worked - planned if entry.date <= today else 0,
                "late_minutes": record.late_minutes if record else 0,
                "status": state,
            }
        )
    return rows


def grid(timetable):
    """Weekly or monthly grid: one row per employee, one column per day."""
    days = list(daterange(timetable.start_date, timetable.end_date))
    entries = timetable.entries.select_related("employee", "shift")
    rows = {}
    for entry in entries:
        row = rows.setdefault(
            entry.employee_id,
            {
                "employee_id": entry.employee_id,
                "employee": entry.employee.full_name,
                "cells": {},
            },
        )
        row["cells"].setdefault(entry.date.isoformat(), []).append(
            {
                "entry_id": entry.id,
                "shift_id": entry.shift_id,
                "code": entry.shift.code,
                "name": entry.shift.name,
                "color": entry.shift.color,
                "note": entry.note,
            }
        )
    return {
        "days": [d.isoformat() for d in days],
        "rows": sorted(rows.values(), key=lambda r: r["employee"]),
    }
