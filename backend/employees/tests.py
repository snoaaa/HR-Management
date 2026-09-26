from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from employees.models import Employee, EmployeeHistory, FamilyMember
from organisation.models import Classification, Department, Position, Site

User = get_user_model()


class EmployeeModelTests(TestCase):
    def setUp(self):
        # Create user
        self.user = User.objects.create_user(
            username="testuser", password="testpassword", email="test@example.com"
        )

        # Create organisation elements
        self.site = Site.objects.create(name="HQ", code="HQ-01")
        self.department = Department.objects.create(
            name="HR", code="HR-01", site=self.site
        )
        self.classification = Classification.objects.create(
            category="Executive", grade="A", echelon="1"
        )
        self.position = Position.objects.create(
            title="HR Manager", code="HRM-01", classification=self.classification
        )

        # Base employee data
        self.employee_data = {
            "surname": "Doe",
            "given_names": "John",
            "date_of_birth": "1990-01-01",
            "place_of_birth": "Cityville",
            "sex": "M",
            "nationality": "Cameroonian",
            "marital_status": "SINGLE",
            "identity_document_type": "ID Card",
            "identity_document_number": "123456789",
            "address": "123 Main St",
            "phone_number": "123-456-7890",
            "contract_type": "PERMANENT",
            "date_of_hire": "2023-01-01",
            "department": self.department,
            "position": self.position,
            "classification": self.classification,
            "workplace": self.site,
            "status": "ACTIVE",
        }

    def test_employee_creation_and_matriculation_number(self):
        """Test that matriculation number is generated automatically (BN-10)."""
        employee = Employee.objects.create(**self.employee_data)
        self.assertTrue(
            employee.matriculation_number.startswith(f"EMP-{timezone.now().year}-")
        )
        self.assertEqual(employee.status, "ACTIVE")

    def test_multiple_employees_matriculation(self):
        """Test matriculation number increments correctly."""
        emp1 = Employee.objects.create(**self.employee_data)
        emp2 = Employee.objects.create(**self.employee_data)

        id1 = int(emp1.matriculation_number.split("-")[-1])
        id2 = int(emp2.matriculation_number.split("-")[-1])
        self.assertEqual(id2, id1 + 1)

    def test_family_member_creation(self):
        """Test family member is successfully linked to employee (BN-13)."""
        employee = Employee.objects.create(**self.employee_data)
        family_member = FamilyMember.objects.create(
            employee=employee,
            name="Jane Doe",
            date_of_birth="2020-01-01",
            relationship="CHILD",
        )
        self.assertEqual(employee.family_members.count(), 1)
        self.assertEqual(employee.family_members.first().name, "Jane Doe")

    def test_employee_history_creation(self):
        """Test the history model functions correctly (BN-21)."""
        employee = Employee.objects.create(**self.employee_data)
        history = EmployeeHistory.objects.create(
            employee=employee,
            author=self.user,
            field_name="status",
            previous_value="ACTIVE",
            new_value="INACTIVE",
        )
        self.assertEqual(employee.history.count(), 1)
        self.assertEqual(employee.history.first().new_value, "INACTIVE")
