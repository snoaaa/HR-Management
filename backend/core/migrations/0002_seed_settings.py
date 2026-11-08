from django.db import migrations


def seed_settings(apps, schema_editor):
    from core.models import DEFAULT_SETTINGS

    Setting = apps.get_model("core", "Setting")
    for key, (value, description) in DEFAULT_SETTINGS.items():
        Setting.objects.get_or_create(
            key=key, defaults={"value": value, "description": description}
        )


class Migration(migrations.Migration):

    dependencies = [("core", "0001_initial")]

    operations = [migrations.RunPython(seed_settings, migrations.RunPython.noop)]
