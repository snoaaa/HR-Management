import datetime
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from attendance.models import DailyAttendance
from attendance.services import compute_day
from core.testing import client_for, make_employee, make_structure, make_user
from notifications.models import ApprovalTask, Notification
from users.models import User

from . import services
from .models import LeaveRequest, LeaveType

TODAY = timezone.now().date()


def next_monday(weeks=1):
    return TODAY + datetime.timedelta(days=(7 - TODAY.weekday()) + 7 * (weeks - 1))


class LeaveTests(TestCase):
    def setUp(self):
        self.structure = make_structure()
        self.head = make_user("head", User.Roles.HEAD_OF_DEPARTMENT)
        self.structure["department"].manager = self.head
        self.structure["department"].save()
        self.hr = make_user("hr", User.Roles.HR_MANAGER)
        self.emp_user = make_user("emp", User.Roles.EMPLOYEE)
        self.employee = make_employee(
            self.structure, user=self.emp_user, date_of_hire=datetime.date(2020, 1, 1)
        )
        self.annual = LeaveType.objects.get(code="ANNUAL")
        self.unpaid = LeaveType.objects.get(code="UNPAID")

    def request(self, start, end, leave_type=None, user=None, employee=None):
        payload = {
            "leave_type": (leave_type or self.annual).id,
            "start_date": str(start),
            "end_date": str(end),
            "submit": True,
        }
        if employee:
            payload["employee"] = employee.id
        return client_for(user or self.emp_user).post(
            "/api/leave/requests/", payload, format="json"
        )

    def approve_all(self, leave_request_id):
        for approver in (self.head, self.hr):
            task = ApprovalTask.objects.get(
                object_id=leave_request_id, status="PENDING"
            )
            response = client_for(approver).post(
                f"/api/notifications/approvals/{task.id}/decide/",
                {"decision": "APPROVED"},
                format="json",
            )
            self.assertEqual(response.status_code, 200, response.content)

    def test_entitlement_with_seniority(self):
        # Hired in 2020: more than 5 years of seniority gives 2 extra days a year.
        acquired = services.acquired_days(
            self.employee, 2026, datetime.date(2026, 9, 30)
        )
        self.assertEqual(acquired, Decimal("15.00"))

    def test_days_exclude_rest_days_and_holidays(self):
        # 18 → 22 May 2026: 20 May is National Day.
        days = services.count_days(
            self.annual,
            self.employee,
            datetime.date(2026, 5, 18),
            datetime.date(2026, 5, 22),
        )
        self.assertEqual(days, 4)
        days = services.count_days(
            self.annual,
            self.employee,
            datetime.date(2026, 5, 18),
            datetime.date(2026, 5, 24),
        )
        # Jours ouvrables (art. 89): Saturday counts, Sunday does not.
        self.assertEqual(days, 5)

    def test_minor_and_mother_entitlements(self):
        from employees.models import FamilyMember

        until = datetime.date(2026, 9, 30)
        self.employee.date_of_birth = datetime.date(2010, 1, 1)  # under 18
        self.employee.save()
        # 9 months x (2.5 + 2 seniority days / 12)
        self.assertEqual(
            services.acquired_days(self.employee, 2026, until), Decimal("24.00")
        )
        self.employee.date_of_birth = datetime.date(1990, 1, 1)
        self.employee.sex = "F"
        self.employee.save()
        FamilyMember.objects.create(
            employee=self.employee,
            name="Child",
            date_of_birth=datetime.date(2023, 1, 1),
            relationship="CHILD",
        )
        # 9 months x (1.5 + (2 seniority + 2 per child under 6) / 12)
        self.assertEqual(
            services.acquired_days(self.employee, 2026, until), Decimal("16.50")
        )

    def test_request_goes_through_manager_then_hr(self):
        start = next_monday()
        response = self.request(start, start + datetime.timedelta(days=4))
        self.assertEqual(response.status_code, 201, response.content)
        data = response.json()
        self.assertEqual(data["status"], "SUBMITTED")
        self.assertEqual(Decimal(data["days"]), 5)
        task = ApprovalTask.objects.get(object_id=data["id"])
        self.assertEqual(task.approver_user, self.head)
        balance = services.balance(self.employee, start.year)
        self.assertEqual(balance["pending"], 5)
        self.approve_all(data["id"])
        leave_request = LeaveRequest.objects.get(pk=data["id"])
        self.assertEqual(leave_request.status, "APPROVED")
        self.assertIsNotNone(leave_request.allowance_amount)
        self.assertEqual(services.balance(self.employee, start.year)["taken"], 5)
        self.assertTrue(
            Notification.objects.filter(
                user=self.emp_user, title__startswith="Approved"
            ).exists()
        )

    def test_insufficient_balance_is_refused(self):
        start = next_monday()
        response = self.request(start, start + datetime.timedelta(days=40))
        self.assertEqual(response.status_code, 400)
        self.assertIn("Insufficient balance", response.json()["detail"])

    def test_refusal_requires_reason(self):
        start = next_monday()
        request_id = self.request(start, start).json()["id"]
        task = ApprovalTask.objects.get(object_id=request_id)
        client = client_for(self.head)
        no_reason = client.post(
            f"/api/notifications/approvals/{task.id}/decide/",
            {"decision": "REFUSED"},
            format="json",
        )
        self.assertEqual(no_reason.status_code, 400)
        client.post(
            f"/api/notifications/approvals/{task.id}/decide/",
            {"decision": "REFUSED", "comment": "Busy period"},
            format="json",
        )
        self.assertEqual(LeaveRequest.objects.get(pk=request_id).status, "REFUSED")

    def test_team_overlap_warning(self):
        colleague_user = make_user("col", User.Roles.EMPLOYEE)
        colleague = make_employee(self.structure, user=colleague_user, surname="Smith")
        start = next_monday()
        self.request(start, start + datetime.timedelta(days=2), user=colleague_user)
        response = self.request(
            start + datetime.timedelta(days=1), start + datetime.timedelta(days=3)
        )
        self.assertIn("team members", response.json()["overlap_warning"])
        self.assertTrue(colleague.leave_requests.exists())

    def test_cancel_interrupt_postpone(self):
        start = next_monday()
        first = self.request(start, start + datetime.timedelta(days=1)).json()
        cancelled = client_for(self.emp_user).post(
            f"/api/leave/requests/{first['id']}/cancel/"
        )
        self.assertEqual(cancelled.json()["status"], "CANCELLED")

        second = self.request(
            start + datetime.timedelta(days=7), start + datetime.timedelta(days=11)
        ).json()
        self.approve_all(second["id"])
        postponed = client_for(self.emp_user).post(
            f"/api/leave/requests/{second['id']}/postpone/",
            {
                "start_date": str(start + datetime.timedelta(days=14)),
                "end_date": str(start + datetime.timedelta(days=18)),
            },
            format="json",
        )
        self.assertEqual(postponed.json()["status"], "SUBMITTED")
        self.assertEqual(
            postponed.json()["original_start_date"],
            str(start + datetime.timedelta(days=7)),
        )

        past = LeaveRequest.objects.create(
            employee=self.employee,
            leave_type=self.annual,
            start_date=datetime.date(2026, 9, 7),
            end_date=datetime.date(2026, 9, 11),
            days=5,
            status="APPROVED",
        )
        interrupted = client_for(self.hr).post(
            f"/api/leave/requests/{past.id}/interrupt/",
            {"last_day": "2026-09-08"},
            format="json",
        )
        self.assertEqual(interrupted.json()["status"], "INTERRUPTED")
        self.assertEqual(Decimal(interrupted.json()["days"]), 2)
        self.assertEqual(
            DailyAttendance.objects.get(
                employee=self.employee, date=datetime.date(2026, 9, 9)
            ).status,
            "ABSENT",
        )

    def test_leave_feeds_attendance_and_payroll(self):
        LeaveRequest.objects.create(
            employee=self.employee,
            leave_type=self.unpaid,
            start_date=datetime.date(2026, 9, 7),
            end_date=datetime.date(2026, 9, 9),
            days=3,
            status="APPROVED",
        )
        self.assertEqual(
            compute_day(self.employee, datetime.date(2026, 9, 8)).status, "LEAVE"
        )
        inputs = services.payroll_inputs(
            self.employee, datetime.date(2026, 9, 1), datetime.date(2026, 9, 30)
        )
        self.assertEqual(inputs["unpaid_leave_days"], 3)

    def test_employee_only_sees_own_requests_and_prints(self):
        other_user = make_user("other", User.Roles.EMPLOYEE)
        other = make_employee(
            self.structure,
            user=other_user,
            department=self.structure["other_department"],
        )
        start = next_monday()
        self.request(start, start, user=other_user)
        self.assertEqual(
            client_for(self.emp_user).get("/api/leave/requests/").json(), []
        )
        forged = self.request(start, start, employee=other)
        self.assertEqual(forged.status_code, 403)
        balance = client_for(self.emp_user).get("/api/leave/requests/balance/").json()
        self.assertEqual(balance["employee"], self.employee.id)
        pdf = client_for(self.emp_user).get("/api/leave/requests/print_balance/")
        self.assertTrue(pdf.content.startswith(b"%PDF"))
