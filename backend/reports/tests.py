import datetime
from decimal import Decimal

from django.core import mail
from django.test import TestCase
from django.utils import timezone

from contracts import services as contract_services
from contracts.models import Contract
from core.testing import client_for, make_employee, make_structure, make_user
from notifications.models import ApprovalTask, Notification
from notifications.services import escalate_overdue
from payroll import services as payroll
from users.models import User

from . import services
from .models import ReportSchedule, SavedReport


class ReportTests(TestCase):
    def setUp(self):
        self.structure = make_structure()
        self.hr = make_user("hr", User.Roles.HR_MANAGER, email="hr@example.com")
        self.gm = make_user("gm", User.Roles.GENERAL_MANAGEMENT)
        self.emp_user = make_user("emp", User.Roles.EMPLOYEE)
        self.employees = []
        for index, (sex, birth) in enumerate((("M", 1990), ("F", 1999), ("F", 1970))):
            employee = make_employee(
                self.structure,
                user=self.emp_user if index == 0 else None,
                surname=f"E{index}",
                sex=sex,
                date_of_birth=datetime.date(birth, 1, 1),
                date_of_hire=datetime.date(2026, 1, 1),
                bank_name="B",
                account_number="1",
            )
            contract = Contract.objects.create(
                employee=employee,
                contract_type="PERMANENT",
                start_date=datetime.date(2026, 1, 1),
                base_salary=Decimal("300000"),
            )
            contract_services.activate(contract, self.hr)
            self.employees.append(employee)

    def test_headcount_and_filters(self):
        data = client_for(self.hr).get("/api/reports/indicators/headcount/").json()
        self.assertEqual(data["total"], 3)
        self.assertEqual(
            {r["label"]: r["value"] for r in data["by_sex"]}, {"Female": 2, "Male": 1}
        )
        self.assertIn("55 +", [r["label"] for r in data["by_age"]])
        other = (
            client_for(self.hr)
            .get(
                f"/api/reports/indicators/headcount/?department={self.structure['other_department'].id}"
            )
            .json()
        )
        self.assertEqual(other["total"], 0)
        xlsx = client_for(self.hr).get(
            "/api/reports/indicators/headcount/?group=sex&file_format=xlsx"
        )
        self.assertTrue(xlsx.content.startswith(b"PK"))

    def test_movements_and_payroll_indicators(self):
        period = payroll.open_period(2026, 9, self.hr)
        payroll.calculate_period(period, self.hr)
        payroll.validate(period, self.hr)
        movements = services.movements(
            self.hr, {}, datetime.date(2026, 1, 1), datetime.date(2026, 12, 31)
        )
        self.assertEqual(movements["hires"], 3)
        data = (
            client_for(self.gm)
            .get("/api/reports/indicators/payroll/?start=2026-01-01&end=2026-12-31")
            .json()
        )
        self.assertEqual(Decimal(str(data["gross"])), Decimal("900000"))
        self.assertGreater(Decimal(str(data["employer_charges_weight"])), 0)
        self.assertEqual(
            client_for(self.emp_user)
            .get("/api/reports/indicators/payroll/")
            .status_code,
            403,
        )

    def test_dashboard_per_profile(self):
        employee_view = client_for(self.emp_user).get("/api/reports/dashboard/").json()
        self.assertIn("me", employee_view)
        self.assertNotIn("payroll", employee_view)
        self.assertNotIn("hr", employee_view)
        hr_view = client_for(self.hr).get("/api/reports/dashboard/").json()
        self.assertEqual(hr_view["hr"]["headcount"]["total"], 3)
        self.assertIn("payroll", hr_view)

    def test_custom_report_and_schedule(self):
        client = client_for(self.hr)
        response = client.post(
            "/api/reports/saved/",
            {
                "name": "Women by department",
                "dataset": "EMPLOYEES",
                "fields": ["surname", "department__name"],
                "filters": {"sex": "F"},
                "group_by": "department__name",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        result = client.get(f"/api/reports/saved/{response.json()['id']}/run/").json()
        self.assertEqual(result["rows"], [["Engineering", 2]])
        report = SavedReport.objects.get()
        ReportSchedule.objects.create(
            report=report, frequency="DAILY", recipients="boss@example.com"
        )
        self.assertEqual(services.send_scheduled_reports(), 1)
        self.assertEqual(mail.outbox[-1].to, ["boss@example.com"])
        self.assertEqual(services.send_scheduled_reports(), 0)  # once a day
        bad = client.post(
            "/api/reports/saved/",
            {"name": "x", "dataset": "EMPLOYEES", "fields": ["password"]},
            format="json",
        )
        self.assertEqual(bad.status_code, 400)

    def test_escalation(self):
        from django.contrib.contenttypes.models import ContentType

        task = ApprovalTask.objects.create(
            content_type=ContentType.objects.get_for_model(User),
            object_id=self.hr.id,
            request_type="LEAVE",
            approver_role="HEAD_OF_DEPARTMENT",
            summary="Leave request",
        )
        ApprovalTask.objects.filter(pk=task.pk).update(
            created_at=timezone.now() - datetime.timedelta(days=5)
        )
        self.assertEqual(escalate_overdue(), 1)
        self.assertTrue(
            Notification.objects.filter(
                user=self.hr, title__startswith="Escalation"
            ).exists()
        )
        self.assertEqual(escalate_overdue(), 0)
