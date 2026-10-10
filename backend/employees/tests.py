from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from core.testing import client_for, make_employee, make_structure, make_user
from employees.models import Employee, EmployeeHistory, FamilyMember
from organisation.models import Classification, Department, Position, Site
from users.models import AuditLog

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


class EmployeeAccessTests(TestCase):
    """BN-154 / BN-171 / BN-21 / BN-19."""

    def setUp(self):
        self.structure = make_structure()
        self.hr = make_user("hr", User.Roles.HR_MANAGER)
        self.emp_user = make_user("emp", User.Roles.EMPLOYEE)
        self.head = make_user("head", User.Roles.HEAD_OF_DEPARTMENT)
        self.structure["department"].manager = self.head
        self.structure["department"].save()
        self.me = make_employee(self.structure, user=self.emp_user)
        self.colleague = make_employee(self.structure, surname="Smith")
        self.outsider = make_employee(
            self.structure,
            surname="Other",
            department=self.structure["other_department"],
        )

    def test_employee_sees_only_own_record(self):
        response = client_for(self.emp_user).get("/api/employees/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([e["id"] for e in response.json()], [self.me.id])
        detail = client_for(self.emp_user).get(f"/api/employees/{self.colleague.id}/")
        self.assertEqual(detail.status_code, 404)

    def test_employee_cannot_modify_records(self):
        response = client_for(self.emp_user).patch(
            f"/api/employees/{self.me.id}/", {"address": "Hacked"}, format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_head_of_department_sees_team_only(self):
        response = client_for(self.head).get("/api/employees/")
        ids = {e["id"] for e in response.json()}
        self.assertEqual(ids, {self.me.id, self.colleague.id})

    def test_hr_sees_everyone(self):
        response = client_for(self.hr).get("/api/employees/")
        self.assertEqual(len(response.json()), 3)

    def test_update_is_historised_and_audited(self):
        response = client_for(self.hr).patch(
            f"/api/employees/{self.me.id}/", {"address": "Bonapriso"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        history = self.me.history.get(field_name="address")
        self.assertEqual(history.previous_value, "Akwa")
        self.assertEqual(history.new_value, "Bonapriso")
        self.assertEqual(history.author, self.hr)
        self.assertTrue(AuditLog.objects.filter(module="Employees").exists())

    def test_delete_archives_instead(self):
        client_for(self.hr).delete(f"/api/employees/{self.me.id}/")
        self.me.refresh_from_db()
        self.assertEqual(self.me.status, "ARCHIVED")

    def test_export_csv_and_xlsx(self):
        client = client_for(self.hr)
        csv_response = client.get("/api/employees/export/?file_format=csv")
        self.assertEqual(csv_response.status_code, 200)
        self.assertIn("Smith", csv_response.content.decode("utf-8"))
        xlsx = client.get("/api/employees/export/?file_format=xlsx")
        self.assertEqual(xlsx.status_code, 200)
        self.assertTrue(xlsx.content.startswith(b"PK"))
        pdf = client.get("/api/employees/export/?file_format=pdf")
        self.assertTrue(pdf.content.startswith(b"%PDF"))
        self.assertEqual(
            client_for(self.emp_user).get("/api/employees/export/").status_code, 403
        )

    def test_matriculation_numbers_are_unique(self):
        numbers = {self.me.matriculation_number, self.colleague.matriculation_number}
        self.assertEqual(len(numbers), 2)
