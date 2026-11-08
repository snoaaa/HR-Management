from django.db import migrations


def sync(apps, schema_editor):
    from documents.default_templates import sync_default_templates

    sync_default_templates(apps.get_model("documents", "DocumentTemplate"))


class Migration(migrations.Migration):

    dependencies = [("documents", "0002_seed_templates")]

    operations = [migrations.RunPython(sync, migrations.RunPython.noop)]
