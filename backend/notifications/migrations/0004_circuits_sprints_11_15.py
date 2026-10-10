from django.db import migrations

CIRCUITS = {
    # BN-76: acts with an effect on payroll are approved by the HR manager.
    "CAREER_ACT": ("Career act", ["HR_MANAGER"]),
    # BN-22: a recruitment need is validated by the general management.
    "RECRUITMENT_NEED": ("Recruitment need", ["HR_MANAGER", "GENERAL_MANAGEMENT"]),
    # BN-148: correction of personal data requested by an employee.
    "PROFILE_CORRECTION": ("Correction of personal data", ["HR_OFFICER"]),
    # BN-78: training request of an employee.
    "TRAINING_REQUEST": ("Training request", ["LINE_MANAGER", "HR_MANAGER"]),
}


def seed(apps, schema_editor):
    Circuit = apps.get_model("notifications", "ApprovalCircuit")
    Level = apps.get_model("notifications", "ApprovalLevel")
    for request_type, (name, approvers) in CIRCUITS.items():
        circuit, created = Circuit.objects.get_or_create(
            request_type=request_type, defaults={"name": name}
        )
        if created:
            for order, approver in enumerate(approvers, start=1):
                Level.objects.create(circuit=circuit, order=order, approver=approver)


class Migration(migrations.Migration):

    dependencies = [("notifications", "0003_alter_approvalcircuit_request_type")]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
