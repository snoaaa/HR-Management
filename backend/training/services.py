"""Business rules of M-09."""

import datetime
from collections import defaultdict
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from employees.models import EmployeeDocument, EmployeeHistory

from .models import (
    EmployeeSkill,
    Participation,
    PositionSkill,
    TrainingNeed,
    TrainingPlan,
    TrainingSession,
)

ZERO = Decimal("0")


class TrainingError(Exception):
    pass


def register(session, employees, user=None):
    if session.status in ("DONE", "CANCELLED"):
        raise TrainingError("The session is closed.")
    current = session.participations.exclude(status="CANCELLED").count()
    added = []
    for employee in employees:
        if session.participations.filter(employee=employee).exists():
            continue
        if (
            session.max_participants
            and current + len(added) >= session.max_participants
        ):
            raise TrainingError(
                f"The session is full ({session.max_participants} participants)."
            )
        added.append(Participation.objects.create(session=session, employee=employee))
        if employee.user:
            from notifications.services import notify

            notify(
                employee.user,
                f"Training: {session.title}",
                f"You are registered from {session.start_date:%d/%m/%Y} at {session.place}.",
                "/my/training",
                "INFO",
            )
    TrainingNeed.objects.filter(
        employee__in=[p.employee for p in added],
        session__isnull=True,
        status="IDENTIFIED",
        skill__in=session.skills.all(),
    ).update(session=session, status="PLANNED")
    return added


def _add_months(day, months):
    month = day.month - 1 + months
    year = day.year + month // 12
    month = month % 12 + 1
    import calendar

    return day.replace(
        year=year, month=month, day=min(day.day, calendar.monthrange(year, month)[1])
    )


@transaction.atomic
def record_result(participation, data, user=None):
    """BN-80: result, certificate and its validity, attached to the employee record."""
    for field in ("status", "result", "satisfaction", "effectiveness", "comment"):
        if field in data:
            setattr(participation, field, data[field])
    if data.get("certificate"):
        participation.certificate = data["certificate"]
    session = participation.session
    if (
        participation.result == "PASSED"
        and not participation.certificate_validity
        and session.certificate_validity_months
    ):
        participation.certificate_validity = _add_months(
            session.end_date, session.certificate_validity_months
        )
    if data.get("certificate_validity"):
        participation.certificate_validity = data["certificate_validity"]
    participation.save()
    employee = participation.employee
    if participation.result == "PASSED":
        for skill in session.skills.all():
            current = EmployeeSkill.objects.filter(
                employee=employee, skill=skill
            ).first()
            required = PositionSkill.objects.filter(
                position=employee.position, skill=skill
            ).first()
            target = max(
                (current.level + 1) if current else 2,
                required.required_level if required else 0,
            )
            EmployeeSkill.objects.update_or_create(
                employee=employee,
                skill=skill,
                defaults={
                    "level": min(5, target),
                    "assessed_at": session.end_date,
                    "source": session.title,
                },
            )
        TrainingNeed.objects.filter(employee=employee, session=session).update(
            status="DONE"
        )
        if participation.certificate:
            EmployeeDocument.objects.create(
                employee=employee,
                document_type="DIPLOMA",
                name=f"Certificate – {session.title}",
                file=participation.certificate.name,
                validity_date=participation.certificate_validity,
            )
        EmployeeHistory.objects.create(
            employee=employee,
            author=user,
            field_name="training",
            new_value=f"Training passed: {session.title}",
        )
    return participation


def close_session(session):
    session.status = "DONE"
    session.save(update_fields=["status"])
    session.participations.filter(status="REGISTERED").update(status="ATTENDED")
    return session


def skill_gaps(employee):
    """BN-77: required profile of the position compared with the employee."""
    gaps = []
    owned = {s.skill_id: s.level for s in employee.skills.all()}
    for required in PositionSkill.objects.filter(
        position=employee.position
    ).select_related("skill"):
        level = owned.get(required.skill_id, 0)
        gaps.append(
            {
                "skill": required.skill.name,
                "required": required.required_level,
                "level": level,
                "gap": max(0, required.required_level - level),
            }
        )
    return gaps


def costs(year):
    """BN-81: training cost per employee and per department, versus the plan budget."""
    by_employee = defaultdict(lambda: ZERO)
    by_department = defaultdict(lambda: ZERO)
    effectiveness = []
    sessions = TrainingSession.objects.filter(start_date__year=year).exclude(
        status="CANCELLED"
    )
    total = ZERO
    for session in sessions:
        total += session.cost
        share = session.cost_per_participant
        for participation in session.participations.exclude(
            status="CANCELLED"
        ).select_related("employee__department"):
            by_employee[participation.employee.full_name] += share
            name = (
                participation.employee.department.name
                if participation.employee.department
                else "—"
            )
            by_department[name] += share
            if participation.effectiveness:
                effectiveness.append(participation.effectiveness)
    plan = TrainingPlan.objects.filter(year=year).first()
    budget = plan.budget if plan else ZERO
    planned = sum(
        (n.estimated_cost or ZERO for n in TrainingNeed.objects.filter(year=year)), ZERO
    )
    return {
        "year": year,
        "budget": budget,
        "spent": total,
        "remaining": budget - total,
        "needs_estimated": planned,
        "sessions": sessions.count(),
        "trained_employees": len(by_employee),
        "average_effectiveness": (
            round(sum(effectiveness) / len(effectiveness), 2) if effectiveness else None
        ),
        "by_employee": [
            {"label": k, "value": v}
            for k, v in sorted(by_employee.items(), key=lambda i: -i[1])
        ],
        "by_department": [
            {"label": k, "value": v}
            for k, v in sorted(by_department.items(), key=lambda i: -i[1])
        ],
    }


def expiring_certificates(days=60):
    today = timezone.now().date()
    return Participation.objects.filter(
        certificate_validity__range=(today, today + datetime.timedelta(days=days))
    ).select_related("employee", "session")
