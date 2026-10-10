import datetime
from decimal import Decimal

from django.test import TestCase

from contracts import services as contract_services
from contracts.models import Contract
from core.testing import client_for, make_employee, make_structure, make_user
from notifications.models import ApprovalTask
from organisation.models import Classification, Department, Position
from payroll import engine
from payroll import services as payroll
from payroll.models import PayrollPeriod
from users.models import User

from . import services
from .models import CareerAct

D = Decimal


class CareerTests(TestCase):
    def setUp(self):
        self.structure = make_structure()
        self.hr = make_user("hr", User.Roles.HR_MANAGER)
        self.head = make_user("head", User.Roles.HEAD_OF_DEPARTMENT)
        self.structure["department"].manager = self.head
        self.structure["department"].save()
        self.employee = make_employee(
            self.structure,
            date_of_hire=datetime.date(2025, 1, 1),
            bank_name="B",
            account_number="1",
        )
        self.contract = Contract.objects.create(
            employee=self.employee,
            contract_type="PERMANENT",
            start_date=datetime.date(2025, 1, 1),
            base_salary=D("300000"),
            department=self.structure["department"],
        )
        contract_services.activate(self.contract, self.hr)
        self.senior = Position.objects.create(title="Senior developer", code="SDEV")
        self.grade_a = Classification.objects.create(
            category="Supervisor", grade="A", echelon="1"
        )

    def create(self, client, **data):
        payload = {"employee": self.employee.id, "reason": "Excellent results", **data}
        response = client.post("/api/careers/acts/", payload, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()

    def approve_task(self, act_id):
        task = ApprovalTask.objects.get(
            object_id=act_id, request_type="CAREER_ACT", status="PENDING"
        )
        client_for(self.hr).post(
            f"/api/notifications/approvals/{task.id}/decide/",
            {"decision": "APPROVED"},
            format="json",
        )

    def test_promotion_proposed_by_head_approved_by_hr(self):
        act = self.create(
            client_for(self.head),
            act_type="PROMOTION",
            effective_date="2026-09-01",
            new_position=self.senior.id,
            new_classification=self.grade_a.id,
            new_base_salary="380000",
            submit=True,
        )
        self.assertEqual(act["status"], "SUBMITTED")
        self.approve_task(act["id"])
        record = CareerAct.objects.get(pk=act["id"])
        self.assertEqual(record.status, "APPLIED")
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.position, self.senior)
        self.contract.refresh_from_db()
        self.assertEqual(
            self.contract.terms_at(datetime.date(2026, 9, 15))["base_salary"],
            D("380000"),
        )
        self.assertEqual(record.previous_situation["base_salary"], "300000.00")
        result = engine.calculate(self.employee, PayrollPeriod(year=2026, month=9))
        self.assertEqual(result.base_salary, D("380000"))
        pdf = client_for(self.hr).get(f"/api/careers/acts/{act['id']}/print_decision/")
        self.assertTrue(pdf.content.startswith(b"%PDF"))

    def test_back_pay_for_retroactive_revision(self):
        period = payroll.open_period(2026, 9, self.hr)
        payroll.calculate_period(period, self.hr)
        payroll.validate(period, self.hr)
        act = self.create(
            client_for(self.hr),
            act_type="SALARY_REVISION",
            effective_date="2026-09-01",
            increase_percent="10",
            submit=True,
        )
        self.approve_task(act["id"])
        october = payroll.open_period(2026, 10, self.hr)
        payroll.calculate_period(october, self.hr)
        lines = {line.code: line for line in october.payslips.get().lines.all()}
        self.assertEqual(lines["BACK_PAY"].amount, D("30000"))

    def test_transfer_and_temporary_return(self):
        sales = self.structure["other_department"]
        act = self.create(
            client_for(self.hr),
            act_type="TEMPORARY_ASSIGNMENT",
            effective_date="2026-03-01",
            end_date="2026-05-31",
            new_department=sales.id,
            submit=True,
        )
        self.approve_task(act["id"])
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.department, sales)
        services.apply_due_acts(self.hr)
        self.assertEqual(CareerAct.objects.get(pk=act["id"]).status, "ENDED")
        self.contract.refresh_from_db()
        self.assertEqual(
            self.contract.terms_at(datetime.date(2026, 6, 15))["department_id"],
            self.structure["department"].id,
        )

    def test_disciplinary_suspension_reduces_pay(self):
        act = self.create(
            client_for(self.hr),
            act_type="DISCIPLINARY",
            effective_date="2026-09-01",
            disciplinary_measure="SUSPENSION",
            suspension_days=3,
            submit=True,
        )
        self.approve_task(act["id"])
        result = engine.calculate(self.employee, PayrollPeriod(year=2026, month=9))
        self.assertEqual(result.paid_days, D("27"))

    def test_warning_needs_no_approval(self):
        act = self.create(
            client_for(self.hr),
            act_type="DISCIPLINARY",
            effective_date="2026-09-01",
            disciplinary_measure="WARNING",
            submit=True,
        )
        self.assertEqual(act["status"], "APPLIED")

    def test_departure_triggers_final_settlement(self):
        act = self.create(
            client_for(self.hr),
            act_type="DEPARTURE",
            effective_date="2026-09-30",
            departure_reason="RESIGNATION",
            submit=True,
        )
        self.approve_task(act["id"])
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.termination.reason, "RESIGNATION")
        self.assertIn("items", self.contract.termination.final_settlement)

    def test_general_increase_and_timeline(self):
        response = client_for(self.hr).post(
            "/api/careers/acts/general_increase/",
            {
                "increase_percent": "5",
                "effective_date": "2026-01-01",
                "department": self.structure["department"].id,
            },
            format="json",
        )
        self.assertEqual(response.json()["count"], 1)
        self.contract.refresh_from_db()
        self.assertEqual(
            self.contract.terms_at(datetime.date(2026, 2, 1))["base_salary"],
            D("315000"),
        )
        events = (
            client_for(self.hr)
            .get(f"/api/careers/acts/timeline/{self.employee.id}/")
            .json()
        )
        self.assertEqual(events[0]["type"], "HIRING")
        self.assertIn("SALARY_REVISION", {e["type"] for e in events})

    def test_head_cannot_see_salaries(self):
        act = self.create(
            client_for(self.hr),
            act_type="SALARY_REVISION",
            effective_date="2026-09-01",
            new_base_salary="400000",
        )
        data = client_for(self.head).get(f"/api/careers/acts/{act['id']}/").json()
        self.assertIsNone(data["new_base_salary"])


class StructureHistoryTests(TestCase):
    def test_structure_as_at_a_past_date(self):
        hr = make_user("hr", User.Roles.HR_MANAGER)
        unit = Department.objects.create(name="Finance", code="FIN")
        unit.versions.update(effective_from=datetime.date(2025, 1, 1))
        unit.name = "Finance & Accounting"
        unit.save()
        past = services.structure_at(datetime.date(2025, 6, 1))
        self.assertEqual(past[0]["name"], "Finance")
        unit.delete()
        self.assertEqual(
            services.structure_at(datetime.date(2025, 6, 1))[0]["name"], "Finance"
        )
        self.assertEqual(services.structure_at(datetime.date.today()), [])
        pdf = client_for(hr).get("/api/careers/org-chart/?file_format=pdf")
        self.assertTrue(pdf.content.startswith(b"%PDF"))
