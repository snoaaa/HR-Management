import datetime

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


class SelfServiceTests(TestCase):
    """BN-148 / BN-177."""

    def setUp(self):
        self.structure = make_structure()
        self.officer = make_user("officer", User.Roles.HR_OFFICER)
        self.emp_user = make_user("emp", User.Roles.EMPLOYEE)
        self.employee = make_employee(self.structure, user=self.emp_user)

    def test_correction_request_approved_by_hr(self):
        from notifications.models import ApprovalTask

        response = client_for(self.emp_user).post(
            "/api/employees/corrections/",
            {
                "field_name": "address",
                "requested_value": "Bastos, Yaoundé",
                "reason": "Moved",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["current_value"], "Akwa")
        task = ApprovalTask.objects.get(request_type="PROFILE_CORRECTION")
        client_for(self.officer).post(
            f"/api/notifications/approvals/{task.id}/decide/",
            {"decision": "APPROVED"},
            format="json",
        )
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.address, "Bastos, Yaoundé")
        self.assertTrue(self.employee.history.filter(field_name="address").exists())

    def test_personal_data_export(self):
        data = client_for(self.emp_user).get("/api/employees/me/data/").json()
        self.assertEqual(data["record"]["surname"], "Doe")
        self.assertEqual(data["account"]["username"], "emp")

    def test_retention(self):
        from django.core.management import call_command

        self.employee.status = "ARCHIVED"
        self.employee.date_of_hire = datetime.date(2005, 1, 1)
        self.employee.save()
        call_command("apply_retention")
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.given_names, "Anonymised")
        self.assertEqual(self.employee.address, "")


class EmployeeRecordAndExportTests(TestCase):
    def setUp(self):
        self.structure = make_structure()
        self.hr = make_user("hr_record", User.Roles.HR_MANAGER)
        self.client_hr = client_for(self.hr)
        self.employee = make_employee(
            self.structure, city="Douala", region="LITTORAL", title="MR"
        )

    def test_record_pdf_and_new_fields(self):
        data = self.client_hr.get(f"/api/employees/{self.employee.pk}/").json()
        self.assertEqual(data["region_label"], "Littoral")
        self.assertEqual(data["number_of_children"], 0)
        self.assertIsNotNone(data["age"])
        pdf = self.client_hr.get(f"/api/employees/{self.employee.pk}/record/")
        self.assertEqual(pdf.status_code, 200)
        self.assertTrue(pdf.content.startswith(b"%PDF"))

    def test_generic_table_export(self):
        payload = {
            "title": "Leave requests",
            "headers": ["Employee", "Days"],
            "rows": [["John Doe", 5], ["Jane Roe", 2.5]],
        }
        for fmt, magic in (("pdf", b"%PDF"), ("xlsx", b"PK")):
            response = self.client_hr.post(
                "/api/exports/table/", {**payload, "file_format": fmt}, format="json"
            )
            self.assertEqual(response.status_code, 200, fmt)
            self.assertTrue(response.content.startswith(magic), fmt)
        bad = self.client_hr.post(
            "/api/exports/table/", {**payload, "rows": "x"}, format="json"
        )
        self.assertEqual(bad.status_code, 400)
