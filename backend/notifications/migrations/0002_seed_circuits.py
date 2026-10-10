from django.db import migrations

DEFAULT_CIRCUITS = {
    # BN-51: line manager, then HR department.
    "LEAVE": ("Leave request", ["LINE_MANAGER", "HR_MANAGER"]),
    # BN-40: overtime approved by the line manager before payroll.
    "OVERTIME": ("Overtime", ["LINE_MANAGER"]),
    # BN-44: regularisation of a clocking.
    "CLOCKING_REGULARISATION": ("Clocking regularisation", ["LINE_MANAGER"]),
    # BN-65: exchange of shifts.
    "SHIFT_SWAP": ("Shift exchange", ["LINE_MANAGER"]),
}


def seed_circuits(apps, schema_editor):
    Circuit = apps.get_model("notifications", "ApprovalCircuit")
    Level = apps.get_model("notifications", "ApprovalLevel")
    for request_type, (name, approvers) in DEFAULT_CIRCUITS.items():
        circuit, created = Circuit.objects.get_or_create(
            request_type=request_type, defaults={"name": name}
        )
        if created:
            for order, approver in enumerate(approvers, start=1):
                Level.objects.create(circuit=circuit, order=order, approver=approver)


class Migration(migrations.Migration):

    dependencies = [("notifications", "0001_initial")]

    operations = [migrations.RunPython(seed_circuits, migrations.RunPython.noop)]
