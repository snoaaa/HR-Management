from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from organisation.models import CompanyIdentity, Site, Department, Position
from employees.models import Employee
from django.utils import timezone
import datetime

User = get_user_model()


class Command(BaseCommand):
    help = "Seed the database with initial data for testing and development"

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting database seeding...")

        # Create Users
        self.stdout.write("Creating users...")
        users_data = [
            {
                "username": "admin",
                "email": "admin@example.com",
                "password": "password123",
                "role": "SYSTEM_ADMINISTRATOR",
                "first_name": "System",
                "last_name": "Admin",
            },
            {
                "username": "hrmanager",
                "email": "hr@example.com",
                "password": "password123",
                "role": "HR_MANAGER",
                "first_name": "HR",
                "last_name": "Manager",
            },
            {
                "username": "employee1",
                "email": "emp1@example.com",
                "password": "password123",
                "role": "EMPLOYEE",
                "first_name": "John",
                "last_name": "Doe",
            },
            {
                "username": "employee2",
                "email": "emp2@example.com",
                "password": "password123",
                "role": "EMPLOYEE",
                "first_name": "Jane",
                "last_name": "Smith",
            },
        ]
        created_users = {}
        for u_data in users_data:
            user, created = User.objects.get_or_create(username=u_data["username"])
            if created:
                user.email = u_data["email"]
                user.set_password(u_data["password"])
                user.role = u_data["role"]
                user.first_name = u_data["first_name"]
                user.last_name = u_data["last_name"]
                if u_data["role"] == "SYSTEM_ADMINISTRATOR":
                    user.is_superuser = True
                    user.is_staff = True
                user.save()
            created_users[u_data["username"]] = user

        # Create Organisation Data
        self.stdout.write("Creating organisation data...")
        company, _ = CompanyIdentity.objects.get_or_create(
            corporate_name="Tech Innovations Inc.",
            defaults={
                "legal_form": "LLC",
                "address": "123 Tech Lane, Silicon Valley",
                "legal_representative": "CEO Alice",
            },
        )

        site, _ = Site.objects.get_or_create(
            code="HQ01",
            defaults={
                "name": "Headquarters",
                "address": "123 Tech Lane, Silicon Valley",
            },
        )

        dept, _ = Department.objects.get_or_create(
            code="ENG01",
            defaults={
                "name": "Engineering",
                "unit_type": "DEPARTMENT",
                "site": site,
                "manager": created_users.get("hrmanager"),
            },
        )

        pos, _ = Position.objects.get_or_create(
            code="DEV01",
            defaults={
                "title": "Software Developer",
                "mission": "Develop amazing software",
            },
        )

        # Create Employees
        self.stdout.write("Creating employees...")
        employee1, _ = Employee.objects.get_or_create(
            user=created_users["employee1"],
            defaults={
                "surname": "Doe",
                "given_names": "John",
                "date_of_birth": datetime.date(1990, 1, 1),
                "place_of_birth": "New York",
                "sex": "M",
                "nationality": "American",
                "marital_status": "SINGLE",
                "identity_document_type": "Passport",
                "identity_document_number": "P123456",
                "address": "456 Elm St",
                "phone_number": "555-0101",
                "department": dept,
                "position": pos,
                "contract_type": "PERMANENT",
                "date_of_hire": timezone.now().date(),
            },
        )

        employee2, _ = Employee.objects.get_or_create(
            user=created_users["employee2"],
            defaults={
                "surname": "Smith",
                "given_names": "Jane",
                "date_of_birth": datetime.date(1992, 5, 12),
                "place_of_birth": "London",
                "sex": "F",
                "nationality": "British",
                "marital_status": "SINGLE",
                "identity_document_type": "Passport",
                "identity_document_number": "P654321",
                "address": "789 Pine St",
                "phone_number": "555-0102",
                "department": dept,
                "position": pos,
                "contract_type": "PERMANENT",
                "date_of_hire": timezone.now().date(),
            },
        )

        self.seed_sprint_data(created_users, dept, pos, site)
        self.stdout.write(self.style.SUCCESS("Successfully seeded database!"))

    def seed_sprint_data(self, created_users, dept, pos, site):
        """
        Data needed by the modules of sprints 3 to 9: payroll and accounting
        users, a classification, and an active contract with bank details for
        every employee who has none yet.
        """
        from decimal import Decimal

        from contracts.models import Contract
        from contracts.services import activate
        from organisation.models import Classification

        self.stdout.write("Creating payroll users, classification and contracts...")
        for username, role, first, last in (
            ("payroll", "PAYROLL_OFFICER", "Payroll", "Officer"),
            ("accountant", "ACCOUNTANT", "Chief", "Accountant"),
        ):
            user, created = User.objects.get_or_create(username=username)
            if created:
                user.email = f"{username}@example.com"
                user.set_password("password123")
                user.role = role
                user.first_name, user.last_name = first, last
                user.save()

        classification, _ = Classification.objects.get_or_create(
            category="Employee", grade="B", echelon="1", defaults={"coefficient": 200}
        )
        if pos.classification_id is None:
            pos.classification = classification
            pos.save(update_fields=["classification"])

        admin_user = created_users.get("admin")
        for index, employee in enumerate(
            Employee.objects.exclude(status="ARCHIVED").order_by("id"), start=1
        ):
            changed = []
            for field, value in (
                ("bank_name", "Afriland First Bank"),
                ("account_number", f"10005-0000{index:04d}"),
                ("method_of_payment", "TRANSFER"),
                ("social_insurance_number", f"CNPS-{index:06d}"),
                ("tax_identification_number", f"NIU-{index:09d}"),
            ):
                if not getattr(employee, field):
                    setattr(employee, field, value)
                    changed.append(field)
            if employee.classification_id is None:
                employee.classification = classification
                changed.append("classification")
            if changed:
                employee.save(update_fields=changed)
            if employee.contracts.exists():
                continue
            is_manager = employee.user and employee.user.role == "HR_MANAGER"
            contract = Contract.objects.create(
                employee=employee,
                contract_type="PERMANENT",
                start_date=employee.date_of_hire,
                base_salary=Decimal("650000" if is_manager else "350000"),
                weekly_hours=Decimal("40"),
                workplace=employee.workplace or site,
                department=employee.department or dept,
                position=employee.position or pos,
                classification=employee.classification,
                created_by=admin_user,
            )
            activate(contract, admin_user)
