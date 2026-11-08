from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from core import backups
from core.testing import client_for, make_structure, make_user
from employees.models import Employee
from leave.models import LeaveAdjustment
from users.models import User

EMPLOYEES_CSV = (
    "surname;given_names;date_of_birth;sex;date_of_hire;department_code;phone_number\n"
    "Mbarga;Paul;12/03/1988;M;2019-02-01;ENG;699000000\n"
    "Ngo;;1990-01-01;F;2020-01-01;ENG;6\n"
    "Ewane;Anne;1992-05-05;F;2021-01-01;UNKNOWN;6\n"
)


class ImportTests(TestCase):
    """BN-179."""

    def setUp(self):
        self.structure = make_structure()
        self.admin = make_user("admin", User.Roles.SYSTEM_ADMINISTRATOR)
        self.client_admin = client_for(self.admin)

    def post(self, kind, content, dry_run, name="data.csv"):
        upload = SimpleUploadedFile(
            name, content.encode("utf-8"), content_type="text/csv"
        )
        return self.client_admin.post(
            f"/api/imports/{kind}/",
            {"file": upload, "dry_run": dry_run},
            format="multipart",
        ).json()

    def test_dry_run_then_import_with_report(self):
        report = self.post("employees", EMPLOYEES_CSV, "true")
        self.assertEqual(report["valid"], 1)
        self.assertEqual([r["line"] for r in report["rejected"]], [3, 4])
        self.assertIn("given_names", report["rejected"][0]["reason"])
        self.assertIn("UNKNOWN", report["rejected"][1]["reason"])
        self.assertFalse(Employee.objects.exists())
        report = self.post("employees", EMPLOYEES_CSV, "false")
        self.assertEqual(report["imported"], 1)
        employee = Employee.objects.get()
        self.assertEqual(employee.department, self.structure["department"])

        contracts = (
            "matriculation_number;contract_type;start_date;base_salary\n"
            f"{employee.matriculation_number};PERMANENT;2019-02-01;350000\n"
        )
        self.assertEqual(self.post("contracts", contracts, "false")["imported"], 1)
        self.assertEqual(employee.contracts.get().status, "ACTIVE")
        balances = f"matriculation_number;year;days\n{employee.matriculation_number};2026;12.5\n"
        self.assertEqual(self.post("leave_balances", balances, "false")["imported"], 1)
        self.assertEqual(LeaveAdjustment.objects.get().kind, "OPENING")

    def test_excel_and_template(self):
        from io import BytesIO

        from openpyxl import Workbook

        template = self.client_admin.get("/api/imports/employees/")
        self.assertIn("surname", template.content.decode("utf-8-sig"))
        workbook = Workbook()
        workbook.active.append(
            ["surname", "given_names", "date_of_birth", "sex", "date_of_hire"]
        )
        workbook.active.append(["Fouda", "Jean", "1985-01-01", "M", "2018-01-01"])
        buffer = BytesIO()
        workbook.save(buffer)
        upload = SimpleUploadedFile("data.xlsx", buffer.getvalue())
        report = self.client_admin.post(
            "/api/imports/employees/",
            {"file": upload, "dry_run": "false"},
            format="multipart",
        ).json()
        self.assertEqual(report["imported"], 1)

    def test_reserved_to_administrators(self):
        employee = make_user("emp", User.Roles.EMPLOYEE)
        self.assertEqual(
            client_for(employee).get("/api/imports/employees/").status_code, 403
        )


class BackupTests(TestCase):
    """BN-183."""

    def test_backup_check_and_restore(self):
        admin = make_user("admin", User.Roles.SYSTEM_ADMINISTRATOR)
        client = client_for(admin)
        name = client.post("/api/backups/").json()["name"]
        report = client.get(f"/api/backups/{name}/check/").json()
        self.assertGreater(report["objects"], 0)
        self.assertIn("users.user", report["models"])
        self.assertEqual(
            client.get("/api/backups/../settings.py/check/").status_code, 404
        )
        self.assertEqual(
            client.post(f"/api/backups/{name}/restore/", {}, format="json").status_code,
            400,
        )
        make_user("intruder")
        result = backups.restore_backup(backups.backup_dir() / name)
        self.assertTrue(result["objects"])
        self.assertFalse(User.objects.filter(username="intruder").exists())
        self.assertTrue(User.objects.filter(username="admin").exists())
