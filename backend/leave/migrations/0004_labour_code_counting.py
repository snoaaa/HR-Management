from django.db import migrations

# Labour Code art. 89: annual leave and exceptional leave are counted in
# jours ouvrables (every day except the weekly rest day and public holidays).
OUVRABLE_TYPES = ("ANNUAL", "FAMILY", "PATERNITY", "COMPENSATORY")


def apply(apps, schema_editor):
    LeaveType = apps.get_model("leave", "LeaveType")
    LeaveType.objects.filter(
        code__in=OUVRABLE_TYPES, counting_rule="WORKING_DAYS"
    ).update(counting_rule="OUVRABLE_DAYS")
    from core.models import sync_default_settings

    sync_default_settings(apps.get_model("core", "Setting"))


class Migration(migrations.Migration):

    dependencies = [
        ("leave", "0003_entitlementrule_minor_age_limit_and_more"),
        ("core", "0003_sync_settings_sprint5"),
    ]

    operations = [migrations.RunPython(apply, migrations.RunPython.noop)]
