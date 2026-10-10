from django.db import migrations


def sync(apps, schema_editor):
    from core.models import sync_default_settings

    sync_default_settings(apps.get_model("core", "Setting"))


class Migration(migrations.Migration):

    dependencies = [("core", "0004_sync_settings_sprint10")]

    operations = [migrations.RunPython(sync, migrations.RunPython.noop)]
