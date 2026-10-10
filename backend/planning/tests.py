import datetime

from django.test import TestCase

from attendance.models import Clocking
from attendance.services import compute_day
from core.testing import client_for, make_employee, make_structure, make_user
from notifications.models import ApprovalTask, Notification
from users.models import User

from .models import Shift, Timetable, TimetableEntry

MONDAY = datetime.date(2026, 9, 7)


class PlanningTests(TestCase):
    def setUp(self):
        self.structure = make_structure()
        self.head = make_user("head", User.Roles.HEAD_OF_DEPARTMENT)
        self.structure["department"].manager = self.head
        self.structure["department"].save()
        self.emp_user = make_user("emp", User.Roles.EMPLOYEE)
        self.employee = make_employee(self.structure, user=self.emp_user)
        self.colleague_user = make_user("col", User.Roles.EMPLOYEE)
        self.colleague = make_employee(
            self.structure, user=self.colleague_user, surname="Smith"
        )
        self.morning = Shift.objects.get(code="M")
        self.night = Shift.objects.get(code="N")
        self.client_head = client_for(self.head)
        response = self.client_head.post(
            "/api/planning/timetables/",
            {
                "name": "Week 37",
                "department": self.structure["department"].id,
                "start_date": str(MONDAY),
                "end_date": str(MONDAY + datetime.timedelta(days=6)),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.timetable_id = response.json()["id"]

    def add(self, employee, day, shift, force=False):
        return self.client_head.post(
            f"/api/planning/timetables/{self.timetable_id}/entries/",
            {
                "employee": employee.id,
                "date": str(day),
                "shift": shift.id,
                "force": force,
            },
            format="json",
        )

    def test_head_cannot_plan_another_department(self):
        response = self.client_head.post(
            "/api/planning/timetables/",
            {
                "name": "Sales",
                "department": self.structure["other_department"].id,
                "start_date": str(MONDAY),
                "end_date": str(MONDAY),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_conflicts_are_detected(self):
        self.assertEqual(self.add(self.employee, MONDAY, self.night).status_code, 201)
        # Night 22:00-06:00 then Morning 06:00 next day: no rest at all.
        rest = self.add(
            self.employee, MONDAY + datetime.timedelta(days=1), self.morning
        )
        self.assertEqual(rest.status_code, 400)
        self.assertIn("rest", rest.json()["detail"])
        double = self.add(self.employee, MONDAY, self.night)
        self.assertEqual(double.status_code, 400)
        forced = self.add(
            self.employee, MONDAY + datetime.timedelta(days=1), self.morning, force=True
        )
        self.assertEqual(forced.status_code, 201)
        grid = self.client_head.get(
            f"/api/planning/timetables/{self.timetable_id}/grid/"
        ).json()
        self.assertEqual(len(grid["rows"]), 1)
        self.assertTrue(grid["conflicts"])

    def test_weekly_maximum(self):
        for offset in range(6):
            self.add(
                self.employee,
                MONDAY + datetime.timedelta(days=offset),
                self.morning,
                force=True,
            )
        response = self.add(
            self.employee, MONDAY + datetime.timedelta(days=6), self.morning
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("maximum", response.json()["detail"])

    def test_publish_notifies_and_drives_attendance(self):
        self.add(self.employee, MONDAY + datetime.timedelta(days=5), self.morning)
        Clocking.objects.create(
            employee=self.employee,
            date=MONDAY + datetime.timedelta(days=5),
            time_in=datetime.time(6, 0),
            time_out=datetime.time(14, 0),
        )
        response = self.client_head.post(
            f"/api/planning/timetables/{self.timetable_id}/publish/"
        )
        self.assertEqual(response.json()["status"], "PUBLISHED")
        self.assertTrue(
            Notification.objects.filter(
                user=self.emp_user, category="PLANNING"
            ).exists()
        )
        # A Saturday shift is a working day for the employee planned on it.
        record = compute_day(self.employee, MONDAY + datetime.timedelta(days=5))
        self.assertEqual(record.status, "PRESENT")
        self.assertEqual(record.expected_minutes, 450)
        comparison = self.client_head.get(
            f"/api/planning/timetables/{self.timetable_id}/comparison/"
        ).json()
        self.assertEqual(comparison[0]["status"], "OK")
        pdf = self.client_head.get(
            f"/api/planning/timetables/{self.timetable_id}/print_timetable/"
        )
        self.assertTrue(pdf.content.startswith(b"%PDF"))
        mine = client_for(self.emp_user).get("/api/planning/entries/").json()
        self.assertEqual(len(mine), 1)

    def test_duplicate(self):
        self.add(self.employee, MONDAY, self.morning)
        response = self.client_head.post(
            f"/api/planning/timetables/{self.timetable_id}/duplicate/",
            {"start_date": str(MONDAY + datetime.timedelta(days=7))},
            format="json",
        )
        copy = Timetable.objects.get(pk=response.json()["id"])
        self.assertEqual(copy.entries.get().date, MONDAY + datetime.timedelta(days=7))

    def test_shift_swap_with_manager_approval(self):
        timetable = Timetable.objects.get(pk=self.timetable_id)
        future = datetime.date.today() + datetime.timedelta(days=10)
        timetable.end_date = future + datetime.timedelta(days=5)
        timetable.start_date = future
        timetable.save()
        entry = TimetableEntry.objects.create(
            timetable=timetable, employee=self.employee, date=future, shift=self.morning
        )
        response = client_for(self.emp_user).post(
            "/api/planning/swaps/",
            {
                "entry": entry.id,
                "replacement": self.colleague.id,
                "reason": "Family event",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        task = ApprovalTask.objects.get(request_type="SHIFT_SWAP")
        self.client_head.post(
            f"/api/notifications/approvals/{task.id}/decide/",
            {"decision": "APPROVED"},
            format="json",
        )
        entry.refresh_from_db()
        self.assertEqual(entry.employee, self.colleague)
