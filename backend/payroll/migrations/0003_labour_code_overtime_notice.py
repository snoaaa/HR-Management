from decimal import Decimal

from django.db import migrations


def apply(apps, schema_editor):
    Parameter = apps.get_model("payroll", "PayrollParameter")
    # Overtime tiers are weekly (decree 68/DF/249): 8 h then 8 h. Only the
    # seeded monthly values are converted; edited values are kept.
    for code in ("OT_TIER1_HOURS", "OT_TIER2_HOURS"):
        Parameter.objects.filter(code=code, value=Decimal("32")).update(
            value=Decimal("8"),
            name=f"Overtime tier {code[7]} (hours per week)",
        )
    from payroll.reference_data import load

    load(apps)  # adds the NOTICE_DAYS scale


class Migration(migrations.Migration):

    dependencies = [("payroll", "0002_seed_reference_data")]

    operations = [migrations.RunPython(apply, migrations.RunPython.noop)]
