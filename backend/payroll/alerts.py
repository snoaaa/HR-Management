"""BN-165: alert the payroll officer of the due dates of the cycle."""

import calendar
import datetime

from core.models import get_int_setting
from users.models import User

from .models import PayrollPeriod

ROLES = [User.Roles.PAYROLL_OFFICER, User.Roles.HR_MANAGER]
NOTICE_DAYS = 3


def payroll_due_alerts(today):
    alerts = []
    due_day = get_int_setting("PAYROLL_DUE_DAY", 25)
    last_day = calendar.monthrange(today.year, today.month)[1]
    payroll_due = datetime.date(today.year, today.month, min(due_day, last_day))
    period = PayrollPeriod.objects.filter(year=today.year, month=today.month).first()
    if 0 <= (payroll_due - today).days <= NOTICE_DAYS and (
        period is None or not period.is_locked
    ):
        alerts.append(
            {
                "key": f"PAYROLL-DUE-{today:%Y-%m}",
                "title": f"Payroll of {today:%m/%Y} to validate",
                "message": f"The payroll must be validated by {payroll_due:%d/%m/%Y}.",
                "link": "/payroll",
                "roles": ROLES,
            }
        )
    declaration_day = get_int_setting("DECLARATION_DUE_DAY", 15)
    declaration_due = datetime.date(
        today.year, today.month, min(declaration_day, last_day)
    )
    previous = today.replace(day=1) - datetime.timedelta(days=1)
    if 0 <= (declaration_due - today).days <= NOTICE_DAYS:
        alerts.append(
            {
                "key": f"DECLARATIONS-{previous:%Y-%m}",
                "title": f"Declarations of {previous:%m/%Y} due",
                "message": (
                    f"Social contributions and taxes withheld for {previous:%m/%Y} "
                    f"must be declared and paid by {declaration_due:%d/%m/%Y}."
                ),
                "link": "/payroll#declarations",
                "roles": ROLES,
            }
        )
    return alerts
