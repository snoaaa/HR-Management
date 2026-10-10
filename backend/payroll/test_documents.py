"""Sprint 9 – payroll and HR documents (BN-113 → BN-127)."""

import datetime
import io
from decimal import Decimal

from django.core import mail
from django.test import TestCase
from pypdf import PdfReader

from contracts import services as contract_services
from contracts.models import Contract
from core.testing import client_for, make_employee, make_structure, make_user
from documents.models import IssuedDocument
from users.models import User

from . import services


def pdf_text(content):
    return "".join(page.extract_text() for page in PdfReader(io.BytesIO(content)).pages)


class PayrollDocumentTests(TestCase):
    def setUp(self):
        self.structure = make_structure()
        self.officer = make_user("payroll", User.Roles.PAYROLL_OFFICER)
        self.emp_user = make_user("emp", User.Roles.EMPLOYEE, email="emp@example.com")
        self.employee = self.hire(self.emp_user, "Doe", "TRANSFER")
        self.cash = self.hire(None, "Cash", "CASH")
        self.period = services.open_period(2026, 9, self.officer)
        services.calculate_period(self.period, self.officer)
        services.validate(self.period, self.officer)
        self.client = client_for(self.officer)

    def hire(self, user, surname, method):
        employee = make_employee(
            self.structure,
            user=user,
            surname=surname,
            date_of_hire=datetime.date(2026, 1, 1),
            bank_name="Afriland",
            account_number="0001",
            method_of_payment=method,
            social_insurance_number="CNPS-1",
            tax_identification_number="NIU-1",
        )
        contract = Contract.objects.create(
            employee=employee,
            contract_type="PERMANENT",
            start_date=datetime.date(2026, 1, 1),
            base_salary=Decimal("300000"),
        )
        contract_services.activate(contract, self.officer)
        return employee

    def payslip(self):
        return self.period.payslips.get(employee=self.employee)

    def test_payslip_with_legal_mentions_and_duplicate(self):
        first = self.client.get(f"/api/payroll/payslips/{self.payslip().id}/pdf/")
        self.assertEqual(first.status_code, 200)
        text = pdf_text(first.content)
        for mention in (
            "PAYSLIP",
            "EMP-",
            "CNPS-1",
            "NIU-1",
            "262",
            "PVID",
            "IRPP",
            "Leave balance",
        ):
            self.assertIn(mention, text)
        self.assertNotIn("DUPLICATE", text)
        second = self.client.get(f"/api/payroll/payslips/{self.payslip().id}/pdf/")
        self.assertIn("DUPLICATE", pdf_text(second.content))
        self.assertEqual(
            IssuedDocument.objects.filter(template_code="PAYSLIP").count(), 2
        )

    def test_batch_in_one_file(self):
        response = self.client.post(
            f"/api/payroll/periods/{self.period.id}/batch_payslips/", {}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(PdfReader(io.BytesIO(response.content)).pages), 2)

    def test_payroll_book_and_statements(self):
        book = self.client.get(f"/api/payroll/periods/{self.period.id}/payroll_book/")
        self.assertIn("PAYROLL BOOK", pdf_text(book.content))
        xlsx = self.client.get(
            f"/api/payroll/periods/{self.period.id}/payroll_book/?file_format=xlsx"
        )
        self.assertTrue(xlsx.content.startswith(b"PK"))
        statement = self.client.get(
            f"/api/payroll/periods/{self.period.id}/contribution_statement/"
        )
        text = pdf_text(statement.content)
        self.assertIn("CNPS", text)
        self.assertIn("15/10/2026", text)

    def test_declaration_and_bank_files(self):
        cnps = self.client.get(
            f"/api/payroll/periods/{self.period.id}/declaration_export/?body=CNPS"
        )
        content = cnps.content.decode("utf-8-sig")
        self.assertIn("PVID employee", content.splitlines()[0])
        self.assertEqual(len(content.strip().splitlines()), 3)
        bank = self.client.get(
            f"/api/payroll/periods/{self.period.id}/bank_file/"
        ).content.decode("utf-8-sig")
        lines = bank.strip().splitlines()
        self.assertEqual(len(lines), 2)  # header + the transfer, not the cash payment
        self.assertIn("262020", lines[1])
        order = self.client.get(f"/api/payroll/periods/{self.period.id}/payment_order/")
        self.assertIn("Afriland", pdf_text(order.content))
        cash = self.client.get(f"/api/payroll/periods/{self.period.id}/cash_list/")
        self.assertIn("Cash", pdf_text(cash.content))

    def test_annual_documents(self):
        statement = client_for(self.emp_user).get(
            "/api/payroll/annual-statement/?year=2026"
        )
        self.assertIn("ANNUAL SALARY STATEMENT", pdf_text(statement.content))
        summary = self.client.get("/api/payroll/annual-summary/?year=2026").json()
        self.assertEqual(len(summary), 2)
        self.assertEqual(Decimal(str(summary[0]["irpp"])), Decimal("15573"))

    def test_email_protected_payslip(self):
        response = self.client.post(f"/api/payroll/payslips/{self.payslip().id}/email/")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(len(mail.outbox), 1)
        attachment = mail.outbox[0].attachments[0][1]
        self.assertTrue(PdfReader(io.BytesIO(attachment)).is_encrypted)

    def test_certificates_and_decisions(self):
        own = client_for(self.emp_user)
        for code in (
            "WORK_CERTIFICATE",
            "EMPLOYMENT_ATTESTATION",
            "SALARY_ATTESTATION",
            "PRESENCE_ATTESTATION",
        ):
            response = own.get(f"/api/documents/certificates/{code}/")
            self.assertEqual(response.status_code, 200, (code, response.content[:200]))
        attestation = pdf_text(
            own.get("/api/documents/certificates/SALARY_ATTESTATION/").content
        )
        self.assertRegex(attestation, r"base salary of 300\s000 XAF")
        forged = own.get(
            f"/api/documents/certificates/WORK_CERTIFICATE/?employee={self.cash.id}"
        )
        self.assertEqual(forged.status_code, 403)
        hr = client_for(make_user("hr", User.Roles.HR_MANAGER))
        decision = hr.post(
            "/api/documents/decisions/",
            {
                "code": "PROMOTION_DECISION",
                "employee": self.employee.id,
                "subject": "Promoted to senior developer",
                "effective_date": "2026-10-01",
            },
            format="json",
        )
        self.assertEqual(decision.status_code, 200)
        self.assertIn("Promoted to senior developer", pdf_text(decision.content))
        self.assertEqual(
            own.post("/api/documents/decisions/", {}, format="json").status_code, 403
        )

    def test_template_change_without_development(self):
        hr = client_for(make_user("hr", User.Roles.HR_MANAGER))
        template = hr.get("/api/documents/templates/?search=").json()
        attestation = next(t for t in template if t["code"] == "EMPLOYMENT_ATTESTATION")
        hr.patch(
            f"/api/documents/templates/{attestation['id']}/",
            {"body": attestation["body"] + "<p>Custom footer mention</p>"},
            format="json",
        )
        response = client_for(self.emp_user).get(
            "/api/documents/certificates/EMPLOYMENT_ATTESTATION/"
        )
        self.assertIn("Custom footer mention", pdf_text(response.content))
