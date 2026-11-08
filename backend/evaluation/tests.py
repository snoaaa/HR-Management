import datetime
from decimal import Decimal

from django.test import TestCase

from core.testing import client_for, make_employee, make_structure, make_user
from payroll.models import VariableInput
from training.models import TrainingNeed
from users.models import User

from .models import Campaign, Evaluation

CRITERIA = [
    {"code": "QUALITY", "label": "Quality of work", "weight": 2},
    {"code": "TEAM", "label": "Team work", "weight": 1},
]


class EvaluationTests(TestCase):
    def setUp(self):
        self.structure = make_structure()
        self.hr = make_user("hr", User.Roles.HR_MANAGER)
        self.head = make_user("head", User.Roles.HEAD_OF_DEPARTMENT)
        self.structure["department"].manager = self.head
        self.structure["department"].save()
        self.emp_user = make_user("emp", User.Roles.EMPLOYEE)
        self.employee = make_employee(self.structure, user=self.emp_user)
        campaign = client_for(self.hr).post(
            "/api/evaluation/campaigns/",
            {
                "name": "Annual review 2026",
                "year": 2026,
                "start_date": "2026-11-01",
                "end_date": "2026-12-15",
                "criteria": CRITERIA,
                "scale_max": 5,
                "objectives_weight": 50,
            },
            format="json",
        )
        self.assertEqual(campaign.status_code, 201, campaign.content)
        self.campaign = Campaign.objects.get()
        client_for(self.hr).post(f"/api/evaluation/campaigns/{self.campaign.id}/open/")
        self.evaluation = Evaluation.objects.get()

    def run_cycle(self, proposal="NONE", **extra):
        client_for(self.emp_user).post(
            f"/api/evaluation/evaluations/{self.evaluation.id}/self_assessment/",
            {"scores": {"QUALITY": 4, "TEAM": 5}, "comment": "Good year"},
            format="json",
        )
        manager = client_for(self.head)
        manager.post(
            f"/api/evaluation/evaluations/{self.evaluation.id}/objectives/",
            {
                "objectives": [
                    {
                        "title": "Deliver the payroll module",
                        "weight": 1,
                        "achievement_percent": "100",
                    },
                    {
                        "title": "Train the users",
                        "weight": 1,
                        "achievement_percent": "60",
                    },
                ]
            },
            format="json",
        )
        response = manager.post(
            f"/api/evaluation/evaluations/{self.evaluation.id}/manager_assessment/",
            {
                "manager_scores": {"QUALITY": 4, "TEAM": 3},
                "manager_comment": "Solid",
                "proposal": proposal,
                **extra,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def test_score_and_evaluator(self):
        self.assertEqual(self.evaluation.evaluator, self.head)
        data = self.run_cycle()
        # Criteria: (4x2 + 3x1)/3/5 = 73.33 %; objectives: 80 %; half each.
        self.assertEqual(Decimal(data["final_score"]), Decimal("76.67"))
        pdf = client_for(self.hr).get(
            f"/api/evaluation/evaluations/{self.evaluation.id}/print_record/"
        )
        self.assertTrue(pdf.content.startswith(b"%PDF"))

    def test_bonus_proposal_reaches_payroll(self):
        self.run_cycle("BONUS", bonus_amount="50000")
        client_for(self.hr).post(
            f"/api/evaluation/evaluations/{self.evaluation.id}/validate/"
        )
        entry = VariableInput.objects.get(employee=self.employee)
        self.assertEqual(entry.element.code, "PERFORMANCE")
        self.assertEqual(entry.amount, Decimal("50000"))

    def test_training_proposal_creates_a_need(self):
        self.run_cycle("TRAINING", training_subject="Advanced Excel")
        client_for(self.hr).post(
            f"/api/evaluation/evaluations/{self.evaluation.id}/validate/"
        )
        self.assertEqual(TrainingNeed.objects.get().subject, "Advanced Excel")

    def test_only_the_employee_self_evaluates(self):
        response = client_for(self.head).post(
            f"/api/evaluation/evaluations/{self.evaluation.id}/self_assessment/",
            {"scores": {"QUALITY": 5, "TEAM": 5}},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        missing = client_for(self.emp_user).post(
            f"/api/evaluation/evaluations/{self.evaluation.id}/self_assessment/",
            {"scores": {"QUALITY": 5}},
            format="json",
        )
        self.assertEqual(missing.status_code, 400)

    def test_campaign_summary(self):
        self.run_cycle()
        summary = (
            client_for(self.hr)
            .get(f"/api/evaluation/campaigns/{self.campaign.id}/summary/")
            .json()
        )
        self.assertEqual(summary["completed"], 1)
        self.assertEqual(datetime.date.today().year >= 2026, True)
