import datetime

from django.http import HttpResponse
from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.exports import export_rows
from core.pdf import column_widths, render_pdf
from payroll.models import PayrollPeriod
from users.permissions import ModulePermission
from users.utils import log_audit_action

from . import services
from .pdf_templates import BOOK_TEMPLATE
from .models import (
    Account,
    AccountingPeriod,
    AccountMapping,
    Budget,
    FiscalYear,
    Journal,
    JournalEntry,
    JournalLine,
)


class AccountSerializer(serializers.ModelSerializer):
    account_class = serializers.CharField(read_only=True)

    class Meta:
        model = Account
        fields = "__all__"

    def validate_number(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("An account number contains digits only.")
        return value


class JournalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Journal
        fields = "__all__"


class AccountingPeriodSerializer(serializers.ModelSerializer):
    year = serializers.IntegerField(source="fiscal_year.year", read_only=True)

    class Meta:
        model = AccountingPeriod
        fields = "__all__"


class FiscalYearSerializer(serializers.ModelSerializer):
    periods = AccountingPeriodSerializer(many=True, read_only=True)

    class Meta:
        model = FiscalYear
        fields = "__all__"


class MappingSerializer(serializers.ModelSerializer):
    debit_label = serializers.CharField(source="debit_account.__str__", read_only=True)
    credit_label = serializers.CharField(
        source="credit_account.__str__", read_only=True
    )
    employer_debit_label = serializers.CharField(
        source="employer_debit_account.__str__", read_only=True
    )
    employer_credit_label = serializers.CharField(
        source="employer_credit_account.__str__", read_only=True
    )

    class Meta:
        model = AccountMapping
        fields = "__all__"


class JournalLineSerializer(serializers.ModelSerializer):
    account_number = serializers.CharField(source="account.number", read_only=True)
    account_name = serializers.CharField(source="account.name", read_only=True)
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    cost_centre_name = serializers.CharField(source="cost_centre.name", read_only=True)

    class Meta:
        model = JournalLine
        exclude = ("entry",)


class EntrySerializer(serializers.ModelSerializer):
    journal_code = serializers.CharField(source="journal.code", read_only=True)
    payroll_period_label = serializers.CharField(
        source="payroll_period.__str__", read_only=True
    )
    total_debit = serializers.DecimalField(
        max_digits=16, decimal_places=2, read_only=True
    )
    total_credit = serializers.DecimalField(
        max_digits=16, decimal_places=2, read_only=True
    )
    is_reversed = serializers.SerializerMethodField()

    class Meta:
        model = JournalEntry
        fields = "__all__"

    def get_is_reversed(self, entry):
        return hasattr(entry, "reversed_by")


class EntryDetailSerializer(EntrySerializer):
    lines = JournalLineSerializer(many=True, read_only=True)


class BudgetSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)
    account_label = serializers.CharField(source="account.__str__", read_only=True)

    class Meta:
        model = Budget
        fields = "__all__"


def _dates(request):
    today = timezone.now().date()
    try:
        start = datetime.date.fromisoformat(
            request.query_params.get("start") or f"{today.year}-01-01"
        )
        end = datetime.date.fromisoformat(request.query_params.get("end") or str(today))
    except ValueError:
        start, end = datetime.date(today.year, 1, 1), today
    return start, end


class AccountingView:
    permission_classes = [ModulePermission]
    permission_module = "accounting"


class AccountViewSet(AccountingView, viewsets.ModelViewSet):
    """BN-128: chart of accounts; BN-143: import from the accounting software."""

    queryset = Account.objects.all()
    serializer_class = AccountSerializer
    search_fields = ("number", "name")
    action_permissions = {"import_chart": "modify"}

    def perform_destroy(self, instance):
        if instance.lines.exists():
            instance.is_active = False
            instance.save(update_fields=["is_active"])
        else:
            instance.delete()

    @action(
        detail=False,
        methods=["post"],
        url_path="import",
        parser_classes=[MultiPartParser, FormParser],
    )
    def import_chart(self, request):
        upload = request.FILES.get("file")
        if upload is None:
            return Response(
                {"detail": "Send a CSV file (number;name) in 'file'."}, status=400
            )
        report = services.import_chart(upload.read())
        log_audit_action(
            request.user,
            f"Imported chart of accounts ({report['created']} new)",
            "Accounting",
            request,
        )
        return Response(report)


class JournalViewSet(AccountingView, viewsets.ModelViewSet):
    queryset = Journal.objects.all()
    serializer_class = JournalSerializer
    search_fields = ("code", "name")


class MappingViewSet(AccountingView, viewsets.ModelViewSet):
    """BN-129: mapping of the payroll items to the accounts (versioned)."""

    queryset = AccountMapping.objects.select_related(
        "debit_account",
        "credit_account",
        "employer_debit_account",
        "employer_credit_account",
    )
    serializer_class = MappingSerializer
    filterset_fields = ("source_type",)
    search_fields = ("source_code", "debit_account__number", "credit_account__number")


class FiscalYearViewSet(AccountingView, viewsets.ModelViewSet):
    """BN-137: financial years and their monthly periods."""

    queryset = FiscalYear.objects.prefetch_related("periods__fiscal_year")
    serializer_class = FiscalYearSerializer
    action_permissions = {
        "close": "validate",
        "close_period": "validate",
        "reopen_period": "validate",
    }
    http_method_names = ["get", "post", "head", "options"]

    def perform_create(self, serializer):
        year = serializer.save()
        for month in range(1, 13):
            AccountingPeriod.objects.get_or_create(fiscal_year=year, month=month)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        year = self.get_object()
        services.close_fiscal_year(year, request.user)
        log_audit_action(
            request.user, f"Closed financial year {year.year}", "Accounting", request
        )
        return Response(self.get_serializer(year).data)

    @action(detail=True, methods=["post"])
    def close_period(self, request, pk=None):
        year = self.get_object()
        period = year.periods.filter(month=request.data.get("month")).first()
        if period is None:
            return Response({"detail": "Unknown month."}, status=400)
        services.close_period(period, request.user)
        log_audit_action(
            request.user, f"Closed accounting period {period}", "Accounting", request
        )
        return Response(self.get_serializer(year).data)

    @action(detail=True, methods=["post"])
    def reopen_period(self, request, pk=None):
        year = self.get_object()
        if year.status == "CLOSED":
            return Response({"detail": "The financial year is closed."}, status=400)
        year.periods.filter(month=request.data.get("month")).update(status="OPEN")
        log_audit_action(
            request.user,
            f"Reopened period {request.data.get('month')}/{year.year}",
            "Accounting",
            request,
        )
        return Response(self.get_serializer(year).data)


class EntryViewSet(AccountingView, viewsets.ReadOnlyModelViewSet):
    """BN-131 → BN-140: entries (read-only), generation, reversal, export."""

    action_permissions = {
        "generate": "create",
        "pay": "create",
        "settle": "create",
        "reverse": "modify",
        "export": "export",
        "reconciliation": "consult",
    }
    filterset_fields = {
        "journal": ["exact"],
        "source": ["exact"],
        "payroll_period": ["exact"],
        "date": ["gte", "lte"],
    }
    search_fields = ("number", "label", "reference")

    def get_queryset(self):
        return JournalEntry.objects.select_related(
            "journal", "payroll_period", "period"
        ).prefetch_related("lines")

    def get_serializer_class(self):
        return EntryDetailSerializer if self.action == "retrieve" else EntrySerializer

    def _period(self, request):
        period = PayrollPeriod.objects.filter(
            pk=request.data.get("payroll_period")
        ).first()
        if period is None:
            raise serializers.ValidationError({"detail": "Choose a payroll period."})
        return period

    def _run(self, func, *args):
        try:
            entry = func(*args)
        except services.AccountingError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(
            (
                EntryDetailSerializer(entry).data
                if entry
                else {"detail": "Nothing to post."}
            ),
            status=201,
        )

    @action(detail=False, methods=["post"])
    def generate(self, request):
        return self._run(
            services.generate_payroll_entry, self._period(request), request.user
        )

    @action(detail=False, methods=["post"])
    def pay(self, request):
        return self._run(
            services.generate_payment_entry, self._period(request), request.user
        )

    @action(detail=False, methods=["post"])
    def settle(self, request):
        day = request.data.get("date")
        day = datetime.date.fromisoformat(day) if day else None
        return self._run(
            services.generate_settlement_entry,
            self._period(request),
            str(request.data.get("body", "")).upper(),
            request.user,
            day,
        )

    @action(detail=True, methods=["post"])
    def reverse(self, request, pk=None):
        return self._run(services.reverse_entry, self.get_object(), request.user)

    @action(detail=False, methods=["get"])
    def export(self, request):
        """BN-143 / BN-181: entries of a period in a standard CSV."""
        entries = self.filter_queryset(self.get_queryset())
        if request.query_params.get("only_new") == "true":
            entries = entries.filter(exported_at__isnull=True)
        text = services.export_entries(list(entries))
        log_audit_action(
            request.user,
            f"Exported {entries.count()} accounting entries",
            "Accounting",
            request,
        )
        response = HttpResponse(text, content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="payroll-entries.csv"'
        return response

    @action(detail=False, methods=["get"])
    def reconciliation(self, request):
        """BN-142: payroll vs accounting for a period (?payroll_period=)."""
        period = PayrollPeriod.objects.filter(
            pk=request.query_params.get("payroll_period")
        ).first()
        if period is None:
            return Response({"detail": "Choose a payroll period."}, status=400)
        try:
            return Response(services.reconciliation(period))
        except services.AccountingError as exc:
            return Response({"detail": str(exc)}, status=400)


class BudgetViewSet(AccountingView, viewsets.ModelViewSet):
    queryset = Budget.objects.select_related("department", "account")
    serializer_class = BudgetSerializer
    filterset_fields = ("year", "department")
    search_fields = ("department__name", "account__number")


BOOK_TITLES = {
    "journal": "Journal book",
    "ledger": "General ledger",
    "trial-balance": "Trial balance",
    "balances": "Personnel and social bodies balances",
    "analysis": "Analysis of the personnel expenses",
    "financial-statements": "Personnel items of the financial statements",
    "entries": "List of the accounting entries",
}


def _pdf_response(pdf, filename):
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{filename}.pdf"'
    return response


def _sum(rows, index):
    return sum((r[index] or 0) for r in rows)


class BooksView(AccountingView, APIView):
    """
    BN-141 → BN-145: the accounting documents (journal book, general ledger,
    trial balance, personnel balances, expense analysis, financial statement
    items, entry list) in JSON, or extracted as PDF, Excel or CSV
    (?file_format=pdf|xlsx|csv).
    """

    required_action = "consult"

    def get(self, request, book):
        start, end = _dates(request)
        fmt = request.query_params.get("file_format")
        if book not in BOOK_TITLES:
            return Response(
                {"detail": "Unknown book."}, status=status.HTTP_404_NOT_FOUND
            )
        title = BOOK_TITLES[book]
        period = f"Period from {start:%d/%m/%Y} to {end:%d/%m/%Y}"
        if book == "journal":
            entries = services.journal_book(
                start, end, request.query_params.get("journal")
            )
            if fmt == "pdf":
                totals = {
                    "debit": sum(e.total_debit for e in entries),
                    "credit": sum(e.total_credit for e in entries),
                }
                return self._render(
                    title, "journal", period, rows=entries, totals=totals
                )
            if fmt in ("xlsx", "csv"):
                return self._table(
                    title,
                    period,
                    fmt,
                    [
                        "Journal",
                        "Entry",
                        "Date",
                        "Account",
                        "Account name",
                        "Label",
                        "Debit",
                        "Credit",
                    ],
                    [
                        [
                            e.journal.code,
                            e.number,
                            e.date.strftime("%d/%m/%Y"),
                            line.account.number,
                            line.account.name,
                            line.label,
                            line.debit,
                            line.credit,
                        ]
                        for e in entries
                        for line in e.lines.all()
                    ],
                )
            return Response(EntryDetailSerializer(entries, many=True).data)
        if book == "ledger":
            rows = services.general_ledger(
                start, end, request.query_params.get("account", "")
            )
            if fmt == "pdf":
                return self._render(title, "ledger", period, rows=rows)
            if fmt in ("xlsx", "csv"):
                return self._table(
                    title,
                    period,
                    fmt,
                    ["Account", "Name", "Date", "Entry", "Label", "Debit", "Credit"]
                    + ["Balance"],
                    [
                        [
                            a["account"],
                            a["name"],
                            line["date"].strftime("%d/%m/%Y"),
                            line["entry"],
                            line["label"],
                            line["debit"],
                            line["credit"],
                            line["balance"],
                        ]
                        for a in rows
                        for line in a["lines"]
                    ],
                )
            return Response(rows)
        if book == "trial-balance":
            rows = services.trial_balance(start, end)
            if fmt:
                keys = [
                    "account",
                    "name",
                    "opening",
                    "debit",
                    "credit",
                    "closing_debit",
                    "closing_credit",
                ]
                table = [[r[k] for k in keys] for r in rows]
                return self._table(
                    title,
                    period,
                    fmt,
                    [
                        "Account",
                        "Name",
                        "Opening",
                        "Debit",
                        "Credit",
                        "Closing debit",
                        "Closing credit",
                    ],
                    table,
                    numeric_from=2,
                    totals=True,
                )
            return Response(rows)
        if book == "balances":
            data = services.personnel_balances(end)
            if fmt:
                table = [
                    ["Personnel", r["account"], r["employee"], r["balance"]]
                    for r in data["employees"]
                ] + [
                    ["Social bodies and State", r["account"], r["name"], r["balance"]]
                    for r in data["bodies"]
                ]
                return self._table(
                    title,
                    f"Situation on {end:%d/%m/%Y} (credit balance = amount owed)",
                    fmt,
                    ["Category", "Account", "Third party", "Balance"],
                    table,
                    numeric_from=3,
                    totals=True,
                )
            return Response(data)
        if book == "analysis":
            group_by = request.query_params.get("group_by", "account")
            if group_by not in ("account", "department", "cost_centre", "month"):
                group_by = "account"
            rows = services.expense_analysis(start, end, group_by)
            if fmt:
                label = group_by.replace("_", " ").capitalize()
                return self._table(
                    title,
                    f"{period} · by {label.lower()}",
                    fmt,
                    [label, "Amount", "Budget", "Variance"],
                    [[r["key"], r["amount"], r["budget"], r["variance"]] for r in rows],
                    numeric_from=1,
                    totals=True,
                )
            return Response(rows)
        if book == "financial-statements":
            year = int(request.query_params.get("year", end.year))
            data = services.financial_statement_elements(year)
            if fmt == "pdf":
                return self._render(
                    title, "statements", f"Financial year {year}", data=data
                )
            if fmt in ("xlsx", "csv"):
                return self._table(
                    title,
                    f"Financial year {year}",
                    fmt,
                    ["Item", "Amount"],
                    [[k.replace("_", " ").capitalize(), v] for k, v in data.items()],
                )
            return Response(data)
        # Entry list
        entries = JournalEntry.objects.filter(date__gte=start, date__lte=end)
        if request.query_params.get("journal"):
            entries = entries.filter(journal_id=request.query_params["journal"])
        entries = entries.select_related("journal").prefetch_related("lines")
        table = [
            [
                e.journal.code,
                e.number,
                e.date.strftime("%d/%m/%Y"),
                e.label,
                e.reference,
                e.total_debit,
                e.total_credit,
            ]
            for e in entries.order_by("date", "number")
        ]
        headers = ["Journal", "Number", "Date", "Label", "Reference", "Debit", "Credit"]
        if fmt:
            return self._table(
                title, period, fmt, headers, table, numeric_from=5, totals=True
            )
        return Response([dict(zip(headers, row)) for row in table])

    def _render(self, title, kind, subtitle, **context):
        log_audit_action(
            self.request.user, f"Extracted the {title.lower()}", "Accounting"
        )
        pdf = render_pdf(
            BOOK_TEMPLATE,
            {"title": title, "kind": kind, "subtitle": subtitle, **context},
            footer_text=title,
            landscape=kind == "ledger",
        )
        return _pdf_response(pdf, kind)

    def _table(
        self, title, subtitle, fmt, headers, rows, numeric_from=None, totals=False
    ):
        filename = title.lower().replace(" ", "-")
        if fmt == "pdf" and numeric_from is not None:
            totals_row = None
            if totals and rows:
                totals_row = ["Total"] + [""] * (numeric_from - 1)
                totals_row += [_sum(rows, i) for i in range(numeric_from, len(headers))]
            widths = column_widths(
                headers, rows, [i >= numeric_from for i in range(len(headers))]
            )
            return self._render(
                title,
                "table",
                subtitle,
                columns=[{"label": h, "width": w} for h, w in zip(headers, widths)],
                table=rows,
                numeric_from=numeric_from,
                totals_row=totals_row,
            )
        log_audit_action(
            self.request.user, f"Extracted the {title.lower()}", "Accounting"
        )
        return export_rows(headers, rows, filename, fmt, title=title, subtitle=subtitle)


class EntryDocumentView(AccountingView, APIView):
    """Accounting voucher of one entry and reconciliation statement as PDF."""

    required_action = "consult"

    def get(self, request, kind, pk):
        if kind == "voucher":
            entry = (
                JournalEntry.objects.select_related("journal", "payroll_period")
                .prefetch_related(
                    "lines__account",
                    "lines__employee",
                    "lines__department",
                    "lines__cost_centre",
                )
                .filter(pk=pk)
                .first()
            )
            if entry is None:
                return Response({"detail": "Unknown entry."}, status=404)
            pdf = render_pdf(
                BOOK_TEMPLATE,
                {
                    "title": "Accounting voucher",
                    "kind": "voucher",
                    "subtitle": f"Entry {entry.number}",
                    "entry": entry,
                },
                footer_text=f"Accounting voucher {entry.number}",
            )
            return _pdf_response(pdf, f"voucher-{entry.number}")
        if kind == "reconciliation":
            period = PayrollPeriod.objects.filter(pk=pk).first()
            if period is None:
                return Response({"detail": "Unknown payroll period."}, status=404)
            try:
                data = services.reconciliation(period)
            except services.AccountingError as exc:
                return Response({"detail": str(exc)}, status=400)
            pdf = render_pdf(
                BOOK_TEMPLATE,
                {
                    "title": "Payroll / accounting reconciliation",
                    "kind": "reconciliation",
                    "subtitle": f"Payroll period {period}",
                    "data": data,
                },
                footer_text="Payroll / accounting reconciliation",
            )
            return _pdf_response(pdf, f"reconciliation-{period.pk}")
        return Response({"detail": "Unknown document."}, status=404)
