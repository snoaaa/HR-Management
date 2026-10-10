import datetime
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from core.testing import client_for, make_employee, make_structure, make_user
from documents.models import IssuedDocument
from notifications.alerts import run_alerts
from notifications.models import Notification
from users.models import User

from . import services
from .models import Contract

TODAY = timezone.now().date()


def days(n):
    return TODAY + datetime.timedelta(days=n)


class ContractTests(TestCase):
    def setUp(self):
        self.structure = make_structure()
        self.hr = make_user("hr", User.Roles.HR_MANAGER)
        self.emp_user = make_user("emp", User.Roles.EMPLOYEE)
        self.employee = make_employee(self.structure, user=self.emp_user)
        self.client_hr = client_for(self.hr)

    def create_contract(self, **extra):
        payload = {
            "employee": self.employee.id,
            "contract_type": "FIXED_TERM",
            "start_date": str(days(-100)),
            "end_date": str(days(20)),
            "trial_period_end": str(days(10)),
            "base_salary": "250000",
            "weekly_hours": "40",
            "position": self.structure["position"].id,
            "department": self.structure["other_department"].id,
            "workplace": self.structure["site"].id,
        }
        payload.update(extra)
        response = self.client_hr.post("/api/contracts/", payload, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()

    def activate(self, contract_id):
        response = self.client_hr.post(f"/api/contracts/{contract_id}/activate/")
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def test_fixed_term_requires_end_date(self):
        response = self.client_hr.post(
            "/api/contracts/",
            {
                "employee": self.employee.id,
                "contract_type": "FIXED_TERM",
                "start_date": str(TODAY),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_activation_feeds_the_employee_record(self):
        contract = self.activate(self.create_contract()["id"])
        self.assertEqual(contract["status"], "ACTIVE")
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.contract_type, "FIXED_TERM")
        self.assertEqual(self.employee.department, self.structure["other_department"])
        self.assertEqual(self.employee.date_of_hire, days(-100))
        self.assertTrue(self.employee.history.filter(field_name="department").exists())

    def test_overlapping_contracts_are_refused(self):
        self.activate(self.create_contract()["id"])
        second = self.create_contract(start_date=str(days(-10)))
        response = self.client_hr.post(f"/api/contracts/{second['id']}/activate/")
        self.assertEqual(response.status_code, 400)

    def test_active_contract_cannot_be_edited_directly(self):
        contract = self.activate(self.create_contract()["id"])
        response = self.client_hr.patch(
            f"/api/contracts/{contract['id']}/", {"base_salary": "1"}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_amendments_keep_versions_and_dates(self):
        contract_id = self.activate(self.create_contract()["id"])["id"]
        first = self.client_hr.post(
            f"/api/contracts/{contract_id}/amend/",
            {
                "effective_date": str(days(-30)),
                "reason": "Annual review",
                "base_salary": "300000",
            },
            format="json",
        )
        self.assertEqual(first.status_code, 201, first.content)
        future = self.client_hr.post(
            f"/api/contracts/{contract_id}/amend/",
            {
                "effective_date": str(days(5)),
                "reason": "Promotion",
                "base_salary": "350000",
            },
            format="json",
        )
        self.assertEqual(future.json()["version"], 2)
        contract = Contract.objects.get(pk=contract_id)
        self.assertEqual(contract.terms_at(days(-50))["base_salary"], Decimal("250000"))
        self.assertEqual(contract.terms_at(TODAY)["base_salary"], Decimal("300000"))
        self.assertEqual(contract.terms_at(days(6))["base_salary"], Decimal("350000"))
        backdated = self.client_hr.post(
            f"/api/contracts/{contract_id}/amend/",
            {"effective_date": str(days(-60)), "reason": "x", "weekly_hours": "35"},
            format="json",
        )
        self.assertEqual(backdated.status_code, 400)
        pdf = self.client_hr.get(f"/api/contracts/{contract_id}/print-amendment/1/")
        self.assertEqual(pdf.status_code, 200)
        self.assertTrue(pdf.content.startswith(b"%PDF"))

    def test_renewal_limit(self):
        contract_id = self.activate(self.create_contract()["id"])["id"]
        ok = self.client_hr.post(
            f"/api/contracts/{contract_id}/renew/",
            {"new_end_date": str(days(200))},
            format="json",
        )
        self.assertEqual(ok.status_code, 201)
        refused = self.client_hr.post(
            f"/api/contracts/{contract_id}/renew/",
            {"new_end_date": str(days(400))},
            format="json",
        )
        self.assertEqual(refused.status_code, 400)
        self.assertIn("maximum", refused.json()["detail"])

    def test_suspension_reduces_seniority(self):
        contract_id = self.activate(
            self.create_contract(contract_type="PERMANENT", end_date=None)["id"]
        )["id"]
        before = services.seniority_days(self.employee)
        response = self.client_hr.post(
            f"/api/contracts/{contract_id}/suspend/",
            {
                "reason": "UNPAID_LEAVE",
                "start_date": str(days(-20)),
                "end_date": str(days(-11)),
                "counts_for_seniority": False,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(services.seniority_days(self.employee), before - 10)

    def test_termination_closes_contract_and_prints_certificate(self):
        contract_id = self.activate(self.create_contract()["id"])["id"]
        response = self.client_hr.post(
            f"/api/contracts/{contract_id}/terminate/",
            {
                "reason": "RESIGNATION",
                "notification_date": str(days(-30)),
                "termination_date": str(days(-1)),
                "notice_worked": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        contract = Contract.objects.get(pk=contract_id)
        self.assertEqual(contract.status, "TERMINATED")
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.status, "INACTIVE")
        pdf = self.client_hr.get(f"/api/contracts/{contract_id}/end_certificate/")
        self.assertTrue(pdf.content.startswith(b"%PDF"))
        self.assertTrue(
            IssuedDocument.objects.filter(template_code="END_OF_CONTRACT").exists()
        )

    def test_printed_contract_is_archived(self):
        contract_id = self.create_contract()["id"]
        response = self.client_hr.get(f"/api/contracts/{contract_id}/print_contract/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b"%PDF"))
        issued = IssuedDocument.objects.get(template_code="CONTRACT")
        self.assertEqual(issued.employee, self.employee)
        self.assertEqual(issued.issued_by, self.hr)

    def test_alerts_are_sent_once(self):
        self.activate(self.create_contract()["id"])
        alerts = self.client_hr.get("/api/contracts/alerts/").json()
        self.assertEqual({a["type"] for a in alerts}, {"CONTRACT_END", "TRIAL_END"})
        run_alerts()
        run_alerts()
        self.assertEqual(
            Notification.objects.filter(user=self.hr, category="ALERT").count(), 2
        )

    def test_salary_visibility(self):
        contract_id = self.create_contract()["id"]
        own = client_for(self.emp_user).get(f"/api/contracts/{contract_id}/").json()
        self.assertEqual(own["base_salary"], "250000.00")
        officer = make_user("officer", User.Roles.HR_OFFICER)
        self.structure["classification"].is_executive = True
        self.structure["classification"].save()
        Contract.objects.filter(pk=contract_id).update(
            classification=self.structure["classification"]
        )
        self.employee.classification = self.structure["classification"]
        self.employee.save()
        hidden = client_for(officer).get(f"/api/contracts/{contract_id}/").json()
        self.assertIsNone(hidden["base_salary"])
        head = make_user("head", User.Roles.HEAD_OF_DEPARTMENT)
        self.assertEqual(
            client_for(head).get(f"/api/contracts/{contract_id}/").status_code, 403
        )
