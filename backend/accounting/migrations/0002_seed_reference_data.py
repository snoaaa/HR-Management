from django.db import migrations


def seed(apps, schema_editor):
    from accounting.reference_data import load

    load(apps)


class Migration(migrations.Migration):

    dependencies = [("accounting", "0001_initial")]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
