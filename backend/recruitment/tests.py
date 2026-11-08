from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from core.testing import client_for, make_structure, make_user
from employees.models import Employee
from notifications.models import ApprovalTask
from users.models import User

from .models import Application, JobOffer, OnboardingTask, RecruitmentNeed


class RecruitmentTests(TestCase):
    def setUp(self):
        self.structure = make_structure()
        self.hr = make_user("hr", User.Roles.HR_MANAGER)
        self.gm = make_user("gm", User.Roles.GENERAL_MANAGEMENT)
        self.head = make_user("head", User.Roles.HEAD_OF_DEPARTMENT)

    def approved_offer(self):
        need = (
            client_for(self.head)
            .post(
                "/api/recruitment/needs/",
                {
                    "position": self.structure["position"].id,
                    "department": self.structure["department"].id,
                    "justification": "Growth of the team",
                    "submit": True,
                },
                format="json",
            )
            .json()
        )
        for approver in (self.hr, self.gm):
            task = ApprovalTask.objects.get(
                object_id=need["id"], request_type="RECRUITMENT_NEED", status="PENDING"
            )
            client_for(approver).post(
                f"/api/notifications/approvals/{task.id}/decide/",
                {"decision": "APPROVED"},
                format="json",
            )
        self.assertEqual(RecruitmentNeed.objects.get().status, "APPROVED")
        offer = (
            client_for(self.hr)
            .post(
                "/api/recruitment/offers/",
                {
                    "need": need["id"],
                    "title": "Developer",
                    "position": self.structure["position"].id,
                    "department": self.structure["department"].id,
                    "description": "Join us",
                },
                format="json",
            )
            .json()
        )
        client_for(self.hr).post(f"/api/recruitment/offers/{offer['id']}/publish/")
        return JobOffer.objects.get()

    def test_full_recruitment_to_employee_record(self):
        offer = self.approved_offer()
        public = APIClient()
        self.assertEqual(len(public.get("/api/recruitment/public/offers/").json()), 1)
        cv = SimpleUploadedFile(
            "cv.pdf", b"%PDF-1.4 cv", content_type="application/pdf"
        )
        response = public.post(
            f"/api/recruitment/public/offers/{offer.id}/apply/",
            {
                "surname": "Nkoulou",
                "given_names": "Marie",
                "email": "marie@example.com",
                "phone": "690000000",
                "date_of_birth": "1995-04-02",
                "sex": "F",
                "nationality": "Cameroonian",
                "cv": cv,
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 201, response.content)
        application = Application.objects.get()
        client = client_for(self.hr)
        for stage in ("PRESELECTED", "INTERVIEW", "SELECTED"):
            self.assertEqual(
                client.post(
                    f"/api/recruitment/applications/{application.id}/move/",
                    {"stage": stage},
                    format="json",
                ).status_code,
                200,
            )
        hired = client.post(
            f"/api/recruitment/applications/{application.id}/hire/",
            {"date_of_hire": "2026-11-02"},
            format="json",
        ).json()
        employee = Employee.objects.get(pk=hired["employee_id"])
        self.assertEqual(employee.surname, "Nkoulou")
        self.assertEqual(employee.personal_email, "marie@example.com")
        self.assertEqual(employee.department, self.structure["department"])
        self.assertEqual(employee.documents.get().name, "Curriculum vitae")
        self.assertEqual(OnboardingTask.objects.filter(employee=employee).count(), 8)
        self.assertEqual(RecruitmentNeed.objects.get().status, "FILLED")
        self.assertEqual(Application.objects.get().events.count(), 5)

    def test_invalid_stage_and_pool(self):
        offer = self.approved_offer()
        application = Application.objects.create(
            offer=offer,
            surname="A",
            given_names="B",
            email="a@b.c",
            phone="1",
            score=70,
        )
        client = client_for(self.hr)
        bad = client.post(
            f"/api/recruitment/applications/{application.id}/move/",
            {"stage": "SELECTED"},
            format="json",
        )
        self.assertEqual(bad.status_code, 400)
        client.post(
            f"/api/recruitment/applications/{application.id}/move/",
            {"stage": "REJECTED"},
            format="json",
        )
        self.assertTrue(Application.objects.get().in_pool)

    def test_unapproved_need_cannot_be_published(self):
        need = RecruitmentNeed.objects.create(
            position=self.structure["position"],
            department=self.structure["department"],
            justification="x",
        )
        offer = JobOffer.objects.create(
            need=need,
            title="X",
            position=self.structure["position"],
            department=self.structure["department"],
            description="x",
        )
        response = client_for(self.hr).post(
            f"/api/recruitment/offers/{offer.id}/publish/"
        )
        self.assertEqual(response.status_code, 400)

    def test_public_upload_restrictions(self):
        offer = self.approved_offer()
        exe = SimpleUploadedFile(
            "cv.exe", b"MZ", content_type="application/octet-stream"
        )
        response = APIClient().post(
            f"/api/recruitment/public/offers/{offer.id}/apply/",
            {
                "surname": "X",
                "given_names": "Y",
                "email": "x@y.z",
                "phone": "1",
                "cv": exe,
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 400)
