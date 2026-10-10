import datetime
from decimal import Decimal

from django.test import TestCase

from attendance.models import AttendancePeriod, Clocking
from attendance.services import compute_day
from contracts import services as contract_services
from contracts.models import Contract
from core.testing import client_for, make_employee, make_structure, make_user
from users.models import User

from . import engine, services
from .models import (
    ElementValue,
    Loan,
    PayrollParameter,
    PayrollPeriod,
    SalaryElement,
)

D = Decimal


def lines(payslip):
    return {line.code: line for line in payslip.lines.all()}


class PayrollTests(TestCase):
    def setUp(self):
        self.structure = make_structure()
        self.officer = make_user("payroll", User.Roles.PAYROLL_OFFICER)
        self.head = make_user("head", User.Roles.HEAD_OF_DEPARTMENT)
        self.structure["department"].manager = self.head
        self.structure["department"].save()
        self.emp_user = make_user("emp", User.Roles.EMPLOYEE)
        self.employee = self.hire(self.emp_user, "Doe", datetime.date(2026, 1, 1))
        self.client_officer = client_for(self.officer)

    def hire(self, user, surname, start, salary="300000", **contract):
        employee = make_employee(
            self.structure,
            user=user,
            surname=surname,
            date_of_hire=start,
            bank_name="Afriland",
            account_number="0001234",
            method_of_payment="TRANSFER",
        )
        record = Contract.objects.create(
            employee=employee,
            contract_type=contract.pop("contract_type", "PERMANENT"),
            start_date=start,
            base_salary=D(salary),
            classification=self.structure["classification"],
            **contract,
        )
        contract_services.activate(record, self.officer)
        return employee

    def period(self, month=9):
        return services.open_period(2026, month, self.officer)

    def run_payroll(self, month=9):
        period = self.period(month)
        services.calculate_period(period, self.officer)
        return period, period.payslips.get(employee=self.employee, status="CALCULATED")

    def test_reference_payslip(self):
        _, payslip = self.run_payroll()
        detail = lines(payslip)
        self.assertEqual(payslip.gross, D("300000"))
        self.assertEqual(detail["PVID"].amount, D("12600"))
        self.assertEqual(detail["PVID"].employer_amount, D("12600"))
        self.assertEqual(detail["PF"].employer_amount, D("21000"))
        self.assertEqual(detail["AT"].employer_amount, D("5250"))
        self.assertEqual(detail["CFC"].amount, D("3000"))
        self.assertEqual(detail["IRPP"].amount, D("15573"))
        self.assertEqual(detail["CAC"].amount, D("1557"))
        self.assertEqual(detail["CRTV"].amount, D("3250"))
        self.assertEqual(detail["TDL"].amount, D("2000"))
        self.assertEqual(payslip.employee_contributions, D("15600"))
        self.assertEqual(payslip.taxes, D("22380"))
        self.assertEqual(payslip.net_payable, D("262020"))
        self.assertEqual(payslip.employer_contributions, D("46350"))
        self.assertNotIn("SENIORITY", detail)
        self.assertEqual(payslip.anomalies, [])

    def test_prorata_for_hiring_during_the_month(self):
        Contract.objects.filter(employee=self.employee).update(
            start_date=datetime.date(2026, 9, 16)
        )
        _, payslip = self.run_payroll()
        self.assertEqual(payslip.paid_days, 15)
        self.assertEqual(payslip.base_salary, D("150000"))

    def test_overtime_and_absences_from_attendance(self):
        monday = datetime.date(2026, 9, 7)
        for offset in range(5):
            day = monday + datetime.timedelta(days=offset)
            if offset < 2:
                continue  # two unjustified absences
            Clocking.objects.create(
                employee=self.employee,
                date=day,
                time_in=datetime.time(8),
                time_out=datetime.time(19),
            )
        for day in range(1, 31):
            record = compute_day(self.employee, datetime.date(2026, 9, day))
            if record.overtime_status == "PENDING":
                record.overtime_status = "APPROVED"
                record.save()
            if record.status == "ABSENT" and record.date not in (
                monday,
                monday + datetime.timedelta(days=1),
            ):
                record.absence_justified = True
                record.save()
        _, payslip = self.run_payroll()
        detail = lines(payslip)
        hourly = D("300000") / D("173.33")
        self.assertEqual(detail["OT_TIER1"].quantity, D("6"))
        self.assertEqual(
            detail["OT_TIER1"].amount, engine.money(D(6) * hourly * D("1.2"))
        )
        self.assertEqual(detail["ABSENCE"].quantity, D("2"))
        self.assertEqual(
            detail["ABSENCE"].amount, engine.money(D(2) * D("300000") / 22)
        )
        self.assertEqual(
            payslip.gross,
            D("300000") + detail["OT_TIER1"].amount - detail["ABSENCE"].amount,
        )

    def test_loan_repayment_and_lock(self):
        loan = Loan.objects.create(
            employee=self.employee,
            amount=D("100000"),
            installment=D("40000"),
            granted_on=datetime.date(2026, 8, 20),
            first_year=2026,
            first_month=9,
        )
        period, payslip = self.run_payroll()
        self.assertEqual(lines(payslip)[f"LOAN-{loan.id}"].amount, D("40000"))
        self.assertEqual(payslip.net_payable, D("222020"))
        services.validate(period, self.officer)
        self.assertEqual(loan.remaining, D("60000"))
        self.assertEqual(
            AttendancePeriod.objects.get(year=2026, month=9).status, "LOCKED"
        )
        with self.assertRaises(services.PayrollError):
            services.calculate_period(period, self.officer)
        services.reverse(period, self.officer, "Wrong bonus")
        self.assertEqual(loan.remaining, D("100000"))
        services.calculate_period(period, self.officer)
        self.assertEqual(period.payslips.filter(status="REVERSED").count(), 1)

    def test_blocking_anomalies_prevent_validation(self):
        self.employee.account_number = ""
        self.employee.save()
        period, payslip = self.run_payroll()
        self.assertTrue(payslip.has_blocking_anomaly)
        response = self.client_officer.post(
            f"/api/payroll/periods/{period.id}/validate/"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("bank details", response.json()["detail"])

    def test_minimum_wage_and_grid(self):
        Contract.objects.filter(employee=self.employee).update(base_salary=D("30000"))
        _, payslip = self.run_payroll()
        codes = {a["code"] for a in payslip.anomalies}
        self.assertIn("BELOW_MINIMUM_WAGE", codes)

    def test_new_rate_applies_only_from_its_effective_date(self):
        _, september = self.run_payroll()
        PayrollParameter.objects.create(
            code="CNPS_CEILING",
            name="CNPS ceiling",
            value=D("100000"),
            effective_from=datetime.date(2026, 10, 1),
        )
        recalculated = engine.calculate(
            self.employee, PayrollPeriod.objects.get(year=2026, month=9)
        )
        self.assertEqual(recalculated.net_payable, september.net_payable)
        _, october = self.run_payroll(10)
        self.assertEqual(lines(october)["PVID"].amount, D("4200"))

    def test_back_pay_after_retroactive_raise(self):
        period, _ = self.run_payroll()
        services.validate(period, self.officer)
        contract = Contract.objects.get(employee=self.employee)
        contract_services.amend(
            contract,
            {"base_salary": D("330000")},
            datetime.date(2026, 9, 1),
            "Promotion",
            self.officer,
        )
        _, october = self.run_payroll(10)
        detail = lines(october)
        self.assertEqual(detail["BACK_PAY"].amount, D("30000"))
        self.assertEqual(october.base_salary, D("330000"))

    def test_element_value_levels(self):
        housing = SalaryElement.objects.get(code="HOUSING")
        ElementValue.objects.create(
            element=housing,
            department=self.structure["department"],
            value=D("20000"),
            effective_from=datetime.date(2026, 1, 1),
        )
        ElementValue.objects.create(
            element=housing,
            employee=self.employee,
            value=D("50000"),
            effective_from=datetime.date(2026, 1, 1),
        )
        _, payslip = self.run_payroll()
        self.assertEqual(lines(payslip)["HOUSING"].amount, D("50000"))

    def test_thirteenth_month_in_december(self):
        thirteenth = SalaryElement.objects.get(code="THIRTEENTH_MONTH")
        ElementValue.objects.create(
            element=thirteenth,
            classification=self.structure["classification"],
            value=D("1"),
            effective_from=datetime.date(2026, 1, 1),
        )
        _, november = self.run_payroll(11)
        self.assertNotIn("THIRTEENTH_MONTH", lines(november))
        _, december = self.run_payroll(12)
        self.assertEqual(lines(december)["THIRTEENTH_MONTH"].amount, D("300000"))

    def test_simulations(self):
        response = self.client_officer.post(
            "/api/payroll/simulate/",
            {"year": 2026, "month": 9, "base_salary": 300000},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(D(str(response.json()["net_payable"])), D("262020"))
        response = self.client_officer.post(
            "/api/payroll/simulate/",
            {
                "year": 2026,
                "month": 9,
                "employee": self.employee.id,
                "overrides": {"base_salary": 400000},
            },
            format="json",
        )
        self.assertEqual(D(str(response.json()["gross"])), D("400000"))
        self.assertFalse(PayrollPeriod.objects.filter(year=2026, month=9).exists())

    def test_final_settlement(self):
        contract = Contract.objects.get(employee=self.employee)
        termination = contract_services.terminate(
            contract,
            {
                "reason": "DISMISSAL",
                "notification_date": datetime.date(2026, 9, 1),
                "termination_date": datetime.date(2026, 9, 30),
                "notice_worked": False,
                "notice_days": 30,
                "leave_balance_days": D("6"),
            },
            self.officer,
        )
        settlement = services.final_settlement(termination, self.officer)
        codes = {item["code"]: D(item["amount"]) for item in settlement["items"]}
        self.assertEqual(codes["NOTICE_INDEMNITY"], D("300000"))
        self.assertIn("LEAVE_COMPENSATION", codes)
        self.assertNotIn("SEVERANCE", codes)  # less than two years
        _, payslip = self.run_payroll()
        self.assertEqual(lines(payslip)["NOTICE_INDEMNITY"].amount, D("300000"))

    def test_declarations_and_access(self):
        period, _ = self.run_payroll()
        services.validate(period, self.officer)
        declarations = {d["body"]: d for d in services.declarations(period)}
        self.assertEqual(declarations["CNPS"]["employee"], D("12600"))
        self.assertEqual(declarations["CNPS"]["employer"], D("38850"))
        self.assertEqual(declarations["CNPS"]["due_date"], datetime.date(2026, 10, 15))

        accountant = client_for(make_user("acc", User.Roles.ACCOUNTANT))
        self.assertEqual(
            accountant.get(
                f"/api/payroll/periods/{period.id}/declarations/"
            ).status_code,
            200,
        )
        self.assertEqual(accountant.get("/api/payroll/payslips/").json(), [])
        mine = client_for(self.emp_user).get("/api/payroll/payslips/mine/").json()
        self.assertEqual(len(mine), 1)
        head = client_for(self.head)
        self.assertEqual(head.get("/api/payroll/payslips/").status_code, 403)

    def test_formulas_are_checked(self):
        response = self.client_officer.post(
            "/api/payroll/elements/",
            {
                "code": "BAD",
                "name": "Bad",
                "method": "FORMULA",
                "formula": "BASE * UNKNOWN",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        response = self.client_officer.post(
            "/api/payroll/elements/",
            {
                "code": "BAD2",
                "name": "Bad",
                "method": "FORMULA",
                "formula": "__import__('os')",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
