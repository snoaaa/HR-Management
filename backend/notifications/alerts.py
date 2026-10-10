"""
BN-164 / BN-165 / BN-20 / BN-31: deadline alerts.

Each provider returns a list of alerts:
    {"key": unique key, "title": ..., "message": ..., "link": ..., "roles": [...]}
The same alert is sent only once per user thanks to the dedupe key.
"""

import datetime

from django.utils import timezone

from core.models import get_int_setting
from users.models import User

from .services import notify_roles

HR_ROLES = [User.Roles.HR_MANAGER, User.Roles.HR_OFFICER]


def contract_alerts(today):
    from contracts.services import upcoming_deadlines

    alerts = []
    for item in upcoming_deadlines(today):
        contract = item["contract"]
        label = (
            "Fixed-term contract ends"
            if item["type"] == "CONTRACT_END"
            else ("Trial period ends")
        )
        alerts.append(
            {
                "key": f"{item['type']}-{contract.id}-{item['date']}",
                "title": f"{label}: {contract.employee.full_name}",
                "message": (
                    f"{label} on {item['date']:%d/%m/%Y} "
                    f"({item['days_left']} days) – contract {contract.reference}."
                ),
                "link": f"/contracts/{contract.id}",
                "roles": HR_ROLES,
            }
        )
    return alerts


def document_alerts(today):
    from employees.models import Employee, EmployeeDocument

    days = get_int_setting("DOCUMENT_ALERT_DAYS", 30)
    limit = today + datetime.timedelta(days=days)
    alerts = []
    for document in EmployeeDocument.objects.filter(
        validity_date__gte=today, validity_date__lte=limit
    ).select_related("employee"):
        alerts.append(
            {
                "key": f"DOC-{document.id}-{document.validity_date}",
                "title": f"Document expires: {document.employee.full_name}",
                "message": f"{document.name} expires on {document.validity_date:%d/%m/%Y}.",
                "link": f"/employees/{document.employee_id}",
                "roles": HR_ROLES,
            }
        )
    for employee in Employee.objects.filter(
        status="ACTIVE",
        identity_document_validity__gte=today,
        identity_document_validity__lte=limit,
    ):
        alerts.append(
            {
                "key": f"ID-{employee.id}-{employee.identity_document_validity}",
                "title": f"Identity document expires: {employee.full_name}",
                "message": (
                    f"{employee.identity_document_type} expires on "
                    f"{employee.identity_document_validity:%d/%m/%Y}."
                ),
                "link": f"/employees/{employee.id}",
                "roles": HR_ROLES,
            }
        )
    return alerts


def _birthday_in(date_of_birth, years):
    try:
        return date_of_birth.replace(year=date_of_birth.year + years)
    except ValueError:  # 29 February
        return date_of_birth.replace(year=date_of_birth.year + years, day=28)


def retirement_and_anniversary_alerts(today):
    from employees.models import Employee

    age = get_int_setting("RETIREMENT_AGE", 60)
    notice = get_int_setting("RETIREMENT_ALERT_DAYS", 180)
    alerts = []
    for employee in Employee.objects.filter(status="ACTIVE"):
        if employee.date_of_birth:
            retirement = _birthday_in(employee.date_of_birth, age)
            if today <= retirement <= today + datetime.timedelta(days=notice):
                alerts.append(
                    {
                        "key": f"RETIREMENT-{employee.id}-{retirement}",
                        "title": f"Retirement approaching: {employee.full_name}",
                        "message": f"Reaches {age} years on {retirement:%d/%m/%Y}.",
                        "link": f"/employees/{employee.id}",
                        "roles": HR_ROLES,
                    }
                )
        hire = employee.date_of_hire
        if hire and hire.month == today.month and hire.day == today.day:
            years = today.year - hire.year
            if years > 0:
                alerts.append(
                    {
                        "key": f"ANNIVERSARY-{employee.id}-{today.year}",
                        "title": f"Work anniversary: {employee.full_name}",
                        "message": f"{years} year(s) in the organisation today.",
                        "link": f"/employees/{employee.id}",
                        "roles": HR_ROLES,
                    }
                )
    return alerts


def payroll_alerts(today):
    try:
        from payroll.alerts import payroll_due_alerts
    except ImportError:
        return []
    return payroll_due_alerts(today)


PROVIDERS = [
    contract_alerts,
    document_alerts,
    retirement_and_anniversary_alerts,
    payroll_alerts,
]


def run_alerts(today=None):
    today = today or timezone.now().date()
    sent = 0
    for provider in PROVIDERS:
        for alert in provider(today):
            sent += len(
                notify_roles(
                    alert["roles"],
                    alert["title"],
                    alert["message"],
                    alert["link"],
                    "ALERT",
                    dedupe_key=alert["key"],
                )
            )
    return sent
