from django.db import migrations


def seed_templates(apps, schema_editor):
    from documents.default_templates import sync_default_templates

    sync_default_templates(apps.get_model("documents", "DocumentTemplate"))


class Migration(migrations.Migration):

    dependencies = [("documents", "0001_initial")]

    operations = [migrations.RunPython(seed_templates, migrations.RunPython.noop)]
