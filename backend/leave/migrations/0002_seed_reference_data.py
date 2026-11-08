import datetime
from decimal import Decimal

from django.db import migrations

# code: name, paid, consumes, document, deduction, seniority, allowance,
#       counting, max days, colour
LEAVE_TYPES = {
    "ANNUAL": (
        "Annual leave",
        True,
        True,
        False,
        False,
        True,
        True,
        "WORKING_DAYS",
        None,
        "#714B67",
    ),
    "SICK": (
        "Sick leave",
        True,
        False,
        True,
        False,
        True,
        False,
        "CALENDAR_DAYS",
        None,
        "#e03e3e",
    ),
    "MATERNITY": (
        "Maternity leave",
        True,
        False,
        True,
        False,
        True,
        False,
        "CALENDAR_DAYS",
        98,
        "#d946ef",
    ),
    "PATERNITY": (
        "Paternity leave",
        True,
        False,
        True,
        False,
        True,
        False,
        "WORKING_DAYS",
        3,
        "#0096d6",
    ),
    "FAMILY": (
        "Exceptional leave – family event",
        True,
        False,
        True,
        False,
        True,
        False,
        "WORKING_DAYS",
        10,
        "#f59e0b",
    ),
    "UNPAID": (
        "Unpaid leave",
        False,
        False,
        False,
        True,
        False,
        False,
        "WORKING_DAYS",
        None,
        "#6b7280",
    ),
    "COMPENSATORY": (
        "Compensatory rest",
        True,
        False,
        False,
        False,
        True,
        False,
        "WORKING_DAYS",
        None,
        "#00A09D",
    ),
    "TECH_UNEMPLOYMENT": (
        "Technical unemployment",
        False,
        False,
        False,
        True,
        False,
        False,
        "WORKING_DAYS",
        None,
        "#9e8a98",
    ),
}


def seed(apps, schema_editor):
    LeaveType = apps.get_model("leave", "LeaveType")
    Rule = apps.get_model("leave", "EntitlementRule")
    for code, values in LEAVE_TYPES.items():
        (
            name,
            paid,
            consumes,
            document,
            deduction,
            seniority,
            allowance,
            counting,
            maximum,
            color,
        ) = values
        LeaveType.objects.get_or_create(
            code=code,
            defaults={
                "name": name,
                "is_paid": paid,
                "consumes_entitlement": consumes,
                "requires_document": document,
                "generates_deduction": deduction,
                "counts_for_seniority": seniority,
                "pays_leave_allowance": allowance,
                "counting_rule": counting,
                "max_days_per_request": maximum,
                "color": color,
            },
        )
    if not Rule.objects.exists():
        # Labour Code: 1.5 working days per month of effective service,
        # increased by 2 days per period of 5 years of seniority.
        Rule.objects.create(
            name="Labour Code – general rule",
            effective_from=datetime.date(2000, 1, 1),
            days_per_month=Decimal("1.5"),
            seniority_brackets=[
                {"years": 5, "extra_days": 2},
                {"years": 10, "extra_days": 4},
                {"years": 15, "extra_days": 6},
                {"years": 20, "extra_days": 8},
                {"years": 25, "extra_days": 10},
            ],
            allowance_reference_months=12,
            allowance_days_divisor=Decimal("26"),
        )


class Migration(migrations.Migration):

    dependencies = [("leave", "0001_initial")]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
