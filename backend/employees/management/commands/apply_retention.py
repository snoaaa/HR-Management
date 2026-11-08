import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import get_int_setting
from employees.models import Employee, EmployeeHistory

PERSONAL_FIELDS = {
    "given_names": "Anonymised",
    "place_of_birth": "",
    "nationality": "",
    "identity_document_type": "",
    "identity_document_number": "",
    "identity_document_validity": None,
    "address": "",
    "phone_number": "",
    "phone_number_2": None,
    "phone_number_3": None,
    "personal_email": None,
    "professional_email": None,
    "emergency_contact_name": "",
    "emergency_contact_number": "",
    "emergency_contact_relationship": None,
    "emergency_contact_name_2": None,
    "emergency_contact_number_2": None,
    "emergency_contact_relationship_2": None,
    "emergency_contact_name_3": None,
    "emergency_contact_number_3": None,
    "emergency_contact_relationship_3": None,
    "bank_name": None,
    "bank_branch": None,
    "account_number": None,
    "bank_key": None,
}


class Command(BaseCommand):
    help = (
        "BN-177: anonymise the archived employees whose last contract ended more than "
        "RETENTION_YEARS ago (minimisation of personal data). Payroll amounts are kept."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true", help="List without changing anything."
        )

    def handle(self, *args, dry_run=False, **options):
        years = get_int_setting("RETENTION_YEARS", 10)
        limit = timezone.now().date() - datetime.timedelta(days=int(years * 365.25))
        count = 0
        for employee in Employee.objects.filter(status="ARCHIVED").exclude(
            given_names="Anonymised"
        ):
            ends = [
                c.effective_end_date
                for c in employee.contracts.all()
                if c.effective_end_date
            ]
            last = max(ends) if ends else employee.date_of_hire
            if last is None or last > limit:
                continue
            count += 1
            if dry_run:
                self.stdout.write(f"Would anonymise {employee}")
                continue
            for field, value in PERSONAL_FIELDS.items():
                setattr(employee, field, value)
            employee.surname = f"Former employee {employee.matriculation_number}"
            employee.photograph = None
            employee.save()
            for document in employee.documents.all():
                document.file.delete(save=False)
                document.delete()
            employee.family_members.all().delete()
            employee.history.all().delete()
            EmployeeHistory.objects.create(
                employee=employee,
                field_name="record",
                new_value=f"Anonymised after {years} years of retention",
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"{count} record(s) {'to anonymise' if dry_run else 'anonymised'}."
            )
        )
