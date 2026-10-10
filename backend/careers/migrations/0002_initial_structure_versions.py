import datetime

from django.db import migrations


def seed(apps, schema_editor):
    """BN-06: the existing structure becomes the first version of each unit."""
    Department = apps.get_model("organisation", "Department")
    Version = apps.get_model("careers", "DepartmentVersion")
    for d in Department.objects.all():
        if not Version.objects.filter(department_ref=d.pk).exists():
            Version.objects.create(
                department=d,
                department_ref=d.pk,
                effective_from=datetime.date(2000, 1, 1),
                name=d.name,
                code=d.code,
                unit_type=d.unit_type,
                parent_id=d.parent_id,
                site_id=d.site_id,
                manager_id=d.manager_id,
                cost_centre_id=d.cost_centre_id,
            )


class Migration(migrations.Migration):

    dependencies = [
        ("careers", "0001_initial"),
        ("organisation", "0002_classification_is_executive"),
    ]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
