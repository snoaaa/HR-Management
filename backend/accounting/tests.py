import datetime
from decimal import Decimal

from django.db.models import Sum
from django.test import TestCase

from contracts import services as contract_services
from contracts.models import Contract
from core.models import Setting
from core.testing import client_for, make_employee, make_structure, make_user
from payroll import services as payroll
from users.models import User

from . import services
from .models import AccountingPeriod, JournalEntry, JournalLine

D = Decimal


class AccountingTests(TestCase):
    def setUp(self):
        self.structure = make_structure()
        self.officer = make_user("payroll", User.Roles.PAYROLL_OFFICER)
        self.accountant = make_user("acc", User.Roles.ACCOUNTANT)
        self.employee = make_employee(
            self.structure,
            date_of_hire=datetime.date(2026, 1, 1),
            bank_name="Afriland",
            account_number="0001",
            method_of_payment="TRANSFER",
        )
        contract = Contract.objects.create(
            employee=self.employee,
            contract_type="PERMANENT",
            start_date=datetime.date(2026, 1, 1),
            base_salary=D("300000"),
        )
        contract_services.activate(contract, self.officer)
        self.period = payroll.open_period(2026, 9, self.officer)
        payroll.calculate_period(self.period, self.officer)
        payroll.validate(self.period, self.officer)
        self.entry = JournalEntry.objects.get(source="PAYROLL")

    def balance(self, number, entry=None):
        lines = JournalLine.objects.filter(account__number=number)
        if entry is not None:
            lines = lines.filter(entry=entry)
        agg = lines.aggregate(d=Sum("debit"), c=Sum("credit"))
        return (agg["c"] or 0) - (agg["d"] or 0)

    def test_validation_posts_a_balanced_entry(self):
        self.assertEqual(self.entry.total_debit, self.entry.total_credit)
        self.assertTrue(self.entry.number.startswith("PAIE2026-"))
        # 422 holds exactly the net payable; CNPS the employee + employer shares.
        self.assertEqual(self.balance("422", self.entry), D("262020"))
        self.assertEqual(
            self.balance("431", self.entry),
            D("12600") + D("12600") + D("21000") + D("5250"),
        )
        self.assertEqual(self.balance("4471", self.entry), D("15573"))
        self.assertEqual(-self.balance("6611", self.entry), D("300000"))
        self.assertEqual(-self.balance("6641", self.entry), D("38850"))
        expense_lines = self.entry.lines.filter(account__number="6611")
        self.assertEqual(expense_lines.get().department, self.structure["department"])
        # The personnel account keeps the employee (sub-ledger, BN-140).
        personnel = self.entry.lines.filter(account__number="422")
        self.assertEqual({line.employee for line in personnel}, {self.employee})
        reconciliation = services.reconciliation(self.period)
        self.assertTrue(reconciliation["ok"], reconciliation)

    def test_entries_are_immutable(self):
        self.entry.label = "changed"
        with self.assertRaises(PermissionError):
            self.entry.save()
        with self.assertRaises(PermissionError):
            self.entry.delete()

    def test_unbalanced_entry_refused(self):
        builder = services.EntryBuilder("CONSOLIDATED")
        builder.add(self.entry.lines.first().account, debit=D("10"), label="x")
        with self.assertRaises(services.AccountingError):
            services.save_entry(
                builder, self.entry.journal, datetime.date(2026, 9, 30), "x", "MANUAL"
            )

    def test_payment_and_settlement(self):
        payroll.change_status(self.period, "PAID", self.officer)
        payment = JournalEntry.objects.get(source="PAYMENT")
        self.assertEqual(self.balance("422"), 0)
        self.assertEqual(self.balance("5211", payment), D("262020"))
        services.generate_settlement_entry(self.period, "CNPS", self.accountant)
        self.assertEqual(self.balance("431"), 0)

    def test_payroll_reversal_posts_reversals(self):
        payroll.reverse(self.period, self.officer, "Wrong element")
        self.assertTrue(
            JournalEntry.objects.filter(
                source="REVERSAL", reversal_of=self.entry
            ).exists()
        )
        self.assertEqual(self.balance("422"), 0)
        payroll.calculate_period(self.period, self.officer)
        payroll.validate(self.period, self.officer)
        self.assertEqual(JournalEntry.objects.filter(source="PAYROLL").count(), 2)

    def test_closed_period_refuses_entries(self):
        services.close_period(
            AccountingPeriod.objects.get(fiscal_year__year=2026, month=9)
        )
        with self.assertRaises(services.AccountingError):
            services.generate_payment_entry(self.period, day=datetime.date(2026, 9, 30))

    def test_consolidated_breakdown(self):
        Setting.objects.update_or_create(
            key="ACCOUNTING_BREAKDOWN", defaults={"value": "CONSOLIDATED"}
        )
        builder = services.build_payroll_entry(self.period)
        expense = [
            line for line in builder.lines.values() if line["account"].number == "6611"
        ]
        self.assertIsNone(expense[0]["department"])

    def test_books_export_and_access(self):
        client = client_for(self.accountant)
        trial = client.get(
            "/api/accounting/books/trial-balance/?start=2026-01-01&end=2026-12-31"
        ).json()
        self.assertEqual(
            sum(D(str(r["debit"])) for r in trial),
            sum(D(str(r["credit"])) for r in trial),
        )
        ledger = client.get(
            "/api/accounting/books/ledger/?start=2026-01-01&end=2026-12-31&account=422"
        ).json()
        self.assertEqual(ledger[0]["account"], "422")
        csv = client.get("/api/accounting/entries/export/").content.decode("utf-8-sig")
        self.assertIn("PAIE2026-", csv)
        self.entry.refresh_from_db()
        self.assertIsNotNone(self.entry.exported_at)
        pdf = client.get(
            "/api/accounting/books/ledger/?file_format=pdf&start=2026-01-01&end=2026-12-31"
        )
        self.assertTrue(pdf.content.startswith(b"%PDF"))
        employee = client_for(make_user("emp", User.Roles.EMPLOYEE))
        self.assertEqual(employee.get("/api/accounting/entries/").status_code, 403)

    def test_accounting_documents_in_every_format(self):
        client = client_for(self.accountant)
        dates = "start=2026-01-01&end=2026-12-31"
        for book in (
            "journal",
            "ledger",
            "trial-balance",
            "balances",
            "analysis",
            "financial-statements",
            "entries",
        ):
            pdf = client.get(f"/api/accounting/books/{book}/?file_format=pdf&{dates}")
            self.assertTrue(pdf.content.startswith(b"%PDF"), book)
            xlsx = client.get(f"/api/accounting/books/{book}/?file_format=xlsx&{dates}")
            self.assertEqual(xlsx.status_code, 200, book)
            self.assertTrue(xlsx.content.startswith(b"PK"), book)
        voucher = client.get(f"/api/accounting/documents/voucher/{self.entry.pk}/")
        self.assertTrue(voucher.content.startswith(b"%PDF"))
        reconciliation = client.get(
            f"/api/accounting/documents/reconciliation/{self.period.pk}/"
        )
        self.assertTrue(reconciliation.content.startswith(b"%PDF"))
        self.assertEqual(client.get("/api/accounting/books/unknown/").status_code, 404)

    def test_import_chart(self):
        report = services.import_chart(
            "number;name\n6618;Autres rémunérations\nabc;bad\n"
        )
        self.assertEqual(report["created"], 1)
        self.assertEqual(len(report["rejected"]), 1)
