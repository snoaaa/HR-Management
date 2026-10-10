import datetime

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from core.testing import client_for, make_employee, make_structure, make_user
from notifications.models import ApprovalTask
from users.models import User

from . import services
from .models import Clocking, DailyAttendance

MONDAY = datetime.date(2026, 9, 7)
SATURDAY = datetime.date(2026, 9, 12)
LABOUR_DAY = datetime.date(2026, 5, 1)


def t(value):
    return datetime.time.fromisoformat(value)


class AttendanceComputationTests(TestCase):
    def setUp(self):
        self.structure = make_structure()
        self.head = make_user("head", User.Roles.HEAD_OF_DEPARTMENT)
        self.structure["department"].manager = self.head
        self.structure["department"].save()
        self.emp_user = make_user("emp", User.Roles.EMPLOYEE)
        self.employee = make_employee(self.structure, user=self.emp_user)
        self.hr = make_user("hr", User.Roles.HR_MANAGER)

    def clock(self, day, start, end):
        Clocking.objects.create(
            employee=self.employee, date=day, time_in=t(start), time_out=t(end)
        )

    def test_lateness_and_day_overtime(self):
        self.clock(MONDAY, "08:10", "12:00")
        self.clock(MONDAY, "13:00", "17:30")
        record = services.compute_day(self.employee, MONDAY)
        self.assertEqual(record.status, "PRESENT")
        self.assertEqual(record.expected_minutes, 480)
        self.assertEqual(record.worked_minutes, 500)
        self.assertEqual(record.late_minutes, 10)
        self.assertEqual(record.overtime_day_minutes, 20)
        self.assertEqual(record.overtime_status, "PENDING")

    def test_break_is_deducted_from_a_continuous_day(self):
        self.clock(MONDAY, "08:00", "17:00")
        record = services.compute_day(self.employee, MONDAY)
        self.assertEqual(record.worked_minutes, 480)
        self.assertEqual(record.overtime_minutes, 0)
        self.assertEqual(record.missing_minutes, 0)

    def test_lateness_under_tolerance_is_ignored(self):
        self.clock(MONDAY, "08:04", "17:00")
        record = services.compute_day(self.employee, MONDAY)
        self.assertEqual(record.late_minutes, 0)
        self.assertEqual(record.missing_minutes, 4)

    def test_night_overtime(self):
        self.clock(MONDAY, "08:00", "17:00")
        self.clock(MONDAY, "20:00", "23:00")
        record = services.compute_day(self.employee, MONDAY)
        self.assertEqual(record.worked_minutes, 660)
        self.assertEqual(record.overtime_night_minutes, 60)
        self.assertEqual(record.overtime_day_minutes, 120)

    def test_absence_rest_day_and_holiday(self):
        self.assertEqual(services.compute_day(self.employee, MONDAY).status, "ABSENT")
        self.clock(SATURDAY, "09:00", "12:00")
        saturday = services.compute_day(self.employee, SATURDAY)
        self.assertEqual(saturday.status, "REST")
        self.assertEqual(saturday.overtime_rest_day_minutes, 180)
        self.clock(LABOUR_DAY, "08:00", "10:00")
        holiday = services.compute_day(self.employee, LABOUR_DAY)
        self.assertEqual(holiday.status, "HOLIDAY")
        self.assertEqual(holiday.overtime_holiday_minutes, 120)

    def test_unjustified_absence_goes_to_payroll(self):
        record = services.compute_day(self.employee, MONDAY)
        inputs = services.payroll_inputs(self.employee, MONDAY, MONDAY)
        self.assertEqual(inputs["unjustified_absence_days"], 1)
        response = client_for(self.hr).post(
            f"/api/attendance/days/{record.id}/justify/",
            {"justified": True, "justification": "Medical certificate"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        inputs = services.payroll_inputs(self.employee, MONDAY, MONDAY)
        self.assertEqual(inputs["unjustified_absence_days"], 0)

    def test_overtime_must_be_approved_by_line_manager(self):
        self.clock(MONDAY, "08:00", "19:00")
        record = services.compute_day(self.employee, MONDAY)
        self.assertEqual(
            services.payroll_inputs(self.employee, MONDAY, MONDAY)[
                "overtime_day_hours"
            ],
            0,
        )
        other_head = make_user("other", User.Roles.HEAD_OF_DEPARTMENT)
        refused = client_for(other_head).post(
            "/api/attendance/days/decide_overtime/",
            {"ids": [record.id], "decision": "APPROVED"},
            format="json",
        )
        self.assertEqual(refused.json()["decided"], 0)
        approved = client_for(self.head).post(
            "/api/attendance/days/decide_overtime/",
            {"ids": [record.id], "decision": "APPROVED"},
            format="json",
        )
        self.assertEqual(approved.json()["decided"], 1)
        self.assertEqual(
            services.payroll_inputs(self.employee, MONDAY, MONDAY)[
                "overtime_day_hours"
            ],
            2,
        )

    def test_mission_is_not_an_absence(self):
        client_for(self.hr).post(
            "/api/attendance/missions/",
            {
                "employee": self.employee.id,
                "start_date": str(MONDAY),
                "end_date": str(MONDAY + datetime.timedelta(days=1)),
                "place": "Yaoundé",
                "purpose": "Audit",
            },
            format="json",
        )
        self.assertEqual(
            DailyAttendance.objects.get(employee=self.employee, date=MONDAY).status,
            "MISSION",
        )

    def test_import_with_control_report(self):
        content = (
            "matriculation;date;time_in;time_out\n"
            f"{self.employee.matriculation_number};2026-09-07;08:00;17:00\n"
            "UNKNOWN;2026-09-07;08:00;17:00\n"
            f"{self.employee.matriculation_number};08/09/2026;08:00;16:00\n"
        )
        upload = SimpleUploadedFile(
            "badges.csv", content.encode(), content_type="text/csv"
        )
        response = client_for(self.hr).post(
            "/api/attendance/clockings/import/", {"file": upload}, format="multipart"
        )
        report = response.json()
        self.assertEqual(report["imported"], 2)
        self.assertEqual(len(report["rejected"]), 1)
        self.assertEqual(report["rejected"][0]["line"], 3)
        tuesday = DailyAttendance.objects.get(
            employee=self.employee, date=MONDAY + datetime.timedelta(days=1)
        )
        self.assertEqual(tuesday.missing_minutes, 60)

    def test_regularisation_keeps_original_visible(self):
        self.clock(MONDAY, "09:30", "17:00")
        original = Clocking.objects.get(employee=self.employee)
        response = client_for(self.emp_user).post(
            "/api/attendance/regularisations/",
            {
                "employee": self.employee.id,
                "clocking": original.id,
                "date": str(MONDAY),
                "time_in": "08:00",
                "time_out": "17:00",
                "justification": "Badge reader out of order",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        task = ApprovalTask.objects.get(request_type="CLOCKING_REGULARISATION")
        self.assertEqual(task.approver_user, self.head)
        decided = client_for(self.head).post(
            f"/api/notifications/approvals/{task.id}/decide/",
            {"decision": "APPROVED"},
            format="json",
        )
        self.assertEqual(decided.status_code, 200)
        original.refresh_from_db()
        self.assertFalse(original.is_active)
        self.assertEqual(Clocking.objects.filter(employee=self.employee).count(), 2)
        record = DailyAttendance.objects.get(employee=self.employee, date=MONDAY)
        self.assertEqual(record.late_minutes, 0)

    def test_locked_period_refuses_changes(self):
        services.lock_period(2026, 9)
        response = client_for(self.hr).post(
            "/api/attendance/clockings/",
            {
                "employee": self.employee.id,
                "date": str(MONDAY),
                "time_in": "08:00",
                "time_out": "17:00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("locked", response.json()["detail"])

    def test_employee_cannot_enter_clockings_manually(self):
        response = client_for(self.emp_user).post(
            "/api/attendance/clockings/",
            {
                "employee": self.employee.id,
                "date": str(MONDAY),
                "time_in": "08:00",
                "time_out": "17:00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        own = client_for(self.emp_user).post("/api/attendance/clockings/clock/")
        self.assertEqual(own.status_code, 200)

    def test_sheet_and_export(self):
        self.clock(MONDAY, "08:00", "17:00")
        services.recompute(self.employee, MONDAY, MONDAY + datetime.timedelta(days=4))
        client = client_for(self.hr)
        weekly = client.get(
            f"/api/attendance/sheet/?start={MONDAY}&end=2026-09-11&granularity=weekly"
        ).json()
        self.assertEqual(len(weekly), 1)
        self.assertEqual(weekly[0]["absent_days"], 4)
        self.assertEqual(weekly[0]["worked_hours"], 8)
        xlsx = client.get(
            f"/api/attendance/sheet/?start={MONDAY}&end=2026-09-11&file_format=xlsx"
        )
        self.assertTrue(xlsx.content.startswith(b"PK"))

    def test_consolidation(self):
        response = client_for(self.hr).post(
            "/api/attendance/periods/consolidate/",
            {"year": 2026, "month": 9},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["status"], "CONSOLIDATED")
        self.assertEqual(response.json()["summary"]["unjustified_absences"], 22)
