from django.db import migrations


def refresh(apps, schema_editor):
    from documents.default_templates import refresh_untouched_templates

    refresh_untouched_templates(apps.get_model("documents", "DocumentTemplate"))


class Migration(migrations.Migration):

    dependencies = [("documents", "0004_sync_templates_sprint9")]

    operations = [migrations.RunPython(refresh, migrations.RunPython.noop)]
