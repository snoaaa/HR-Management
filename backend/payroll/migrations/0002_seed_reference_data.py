from django.db import migrations


def seed(apps, schema_editor):
    from payroll.reference_data import load

    load(apps)


class Migration(migrations.Migration):

    dependencies = [("payroll", "0001_initial")]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
