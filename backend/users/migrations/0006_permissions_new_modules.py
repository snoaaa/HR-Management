from django.db import migrations


def seed(apps, schema_editor):
    """Default permissions of the modules that have none yet (sprints 10 to 15)."""
    from users.permissions import DEFAULT_MATRIX

    RolePermission = apps.get_model("users", "RolePermission")
    existing = set(RolePermission.objects.values_list("module", flat=True).distinct())
    rows = [
        RolePermission(role=role, module=module, action=action)
        for module, actions in DEFAULT_MATRIX.items()
        if module not in existing
        for action, roles in actions.items()
        for role in roles
    ]
    RolePermission.objects.bulk_create(rows, ignore_conflicts=True)


class Migration(migrations.Migration):

    dependencies = [("users", "0005_seed_role_permissions")]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
