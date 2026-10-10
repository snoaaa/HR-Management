from django.db import migrations


def seed_permissions(apps, schema_editor):
    from users.permissions import DEFAULT_MATRIX

    RolePermission = apps.get_model("users", "RolePermission")
    rows = []
    for module, actions in DEFAULT_MATRIX.items():
        for action, roles in actions.items():
            for role in roles:
                rows.append(RolePermission(role=role, module=module, action=action))
    RolePermission.objects.bulk_create(rows, ignore_conflicts=True)


class Migration(migrations.Migration):

    dependencies = [("users", "0004_rolepermission")]

    operations = [migrations.RunPython(seed_permissions, migrations.RunPython.noop)]
