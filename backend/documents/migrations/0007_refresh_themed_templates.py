from django.db import migrations


def refresh(apps, schema_editor):
    from documents.default_templates import refresh_untouched_templates

    refresh_untouched_templates(apps.get_model("documents", "DocumentTemplate"))


class Migration(migrations.Migration):
    """Themed PDF layout: wider code column, signatory title."""

    dependencies = [("documents", "0006_sync_templates_sprint11")]

    operations = [migrations.RunPython(refresh, migrations.RunPython.noop)]
