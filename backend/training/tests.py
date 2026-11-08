import datetime
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from core.testing import client_for, make_employee, make_structure, make_user
from users.models import User

from .models import EmployeeSkill, PositionSkill, Skill, TrainingPlan


class TrainingTests(TestCase):
    def setUp(self):
        self.structure = make_structure()
        self.hr = make_user("hr", User.Roles.HR_MANAGER)
        self.emp_user = make_user("emp", User.Roles.EMPLOYEE)
        self.employee = make_employee(self.structure, user=self.emp_user)
        self.other = make_employee(self.structure, surname="Smith")
        self.skill = Skill.objects.create(name="Payroll law", category="Legal")
        PositionSkill.objects.create(
            position=self.structure["position"], skill=self.skill, required_level=3
        )
        TrainingPlan.objects.create(year=2026, budget=Decimal("1000000"))

    def test_session_results_skills_and_costs(self):
        client = client_for(self.hr)
        self.assertEqual(
            client.get(f"/api/training/gaps/{self.employee.id}/").json()[0]["gap"], 3
        )
        session = client.post(
            "/api/training/sessions/",
            {
                "title": "Cameroon payroll",
                "organiser": "CNPS Academy",
                "start_date": "2026-10-01",
                "end_date": "2026-10-03",
                "place": "Douala",
                "cost": "300000",
                "skills": [self.skill.id],
                "certificate_validity_months": 24,
                "max_participants": 2,
            },
            format="json",
        ).json()
        client.post(
            f"/api/training/sessions/{session['id']}/register/",
            {"employees": [self.employee.id, self.other.id]},
            format="json",
        )
        detail = client.get(f"/api/training/sessions/{session['id']}/").json()
        participation = next(
            p for p in detail["participations"] if p["employee"] == self.employee.id
        )
        certificate = SimpleUploadedFile(
            "certificate.pdf", b"%PDF-1.4", content_type="application/pdf"
        )
        client.post(
            f"/api/training/sessions/{session['id']}/result/{participation['id']}/",
            {
                "status": "ATTENDED",
                "result": "PASSED",
                "effectiveness": 4,
                "certificate": certificate,
            },
            format="multipart",
        )
        skill = EmployeeSkill.objects.get(employee=self.employee)
        self.assertEqual(skill.level, 3)
        document = self.employee.documents.get()
        self.assertEqual(document.validity_date, datetime.date(2028, 10, 3))
        costs = client.get("/api/training/plans/costs/?year=2026").json()
        self.assertEqual(Decimal(str(costs["spent"])), Decimal("300000"))
        self.assertEqual(
            Decimal(str(costs["by_employee"][0]["value"])), Decimal("150000")
        )
        self.assertEqual(costs["average_effectiveness"], 4.0)
        timeline = client.get(f"/api/careers/acts/timeline/{self.employee.id}/").json()
        self.assertIn("TRAINING", {e["type"] for e in timeline})

    def test_session_capacity(self):
        session = (
            client_for(self.hr)
            .post(
                "/api/training/sessions/",
                {
                    "title": "x",
                    "organiser": "y",
                    "start_date": "2026-10-01",
                    "end_date": "2026-10-01",
                    "place": "z",
                    "max_participants": 1,
                },
                format="json",
            )
            .json()
        )
        response = client_for(self.hr).post(
            f"/api/training/sessions/{session['id']}/register/",
            {"employees": [self.employee.id, self.other.id]},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_employee_requests_training_for_himself(self):
        client = client_for(self.emp_user)
        response = client.post(
            "/api/training/needs/", {"subject": "English", "year": 2026}, format="json"
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["employee"], self.employee.id)
        forged = client.post(
            "/api/training/needs/",
            {"subject": "x", "year": 2026, "employee": self.other.id},
            format="json",
        )
        self.assertEqual(forged.status_code, 403)
