import datetime
from decimal import Decimal

from django.forms.models import model_to_dict
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from contracts.models import ContractTermination
from employees.models import Employee
from users.permissions import (
    ModulePermission,
    can_view_salary,
    has_module_permission,
    scope_employees,
)
from users.utils import log_audit_action

from django.http import HttpResponse

from core.exports import export_rows
from documents.services import issue_document, render_batch, render_document

from . import documents as payroll_documents
from . import engine, services
from .models import (
    ElementValue,
    Loan,
    ParameterChange,
    PayrollParameter,
    PayrollPeriod,
    Payslip,
    SalaryElement,
    SalaryGrid,
    Scale,
    StatutoryDeduction,
    ThirdPartyDeduction,
    VariableInput,
)
from .serializers import (
    ElementValueSerializer,
    LoanSerializer,
    ParameterChangeSerializer,
    PayrollParameterSerializer,
    PayrollPeriodSerializer,
    PayslipDetailSerializer,
    PayslipSerializer,
    SalaryElementSerializer,
    SalaryGridSerializer,
    ScaleSerializer,
    StatutoryDeductionSerializer,
    ThirdPartyDeductionSerializer,
    VariableInputSerializer,
)


def _json(instance):
    data = model_to_dict(instance)
    return {
        k: str(v) if isinstance(v, (Decimal, datetime.date)) else v
        for k, v in data.items()
    }


def _pdf_response(issued_or_bytes, filename="document.pdf"):
    if hasattr(issued_or_bytes, "file"):
        filename = f"{issued_or_bytes.reference}.pdf"
        content = issued_or_bytes.file.read()
    else:
        content = issued_or_bytes
    response = HttpResponse(content, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    return response


def _csv_response(text, filename):
    response = HttpResponse(text, content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def _require_salary_access(user):
    """BN-172: only explicitly authorised profiles see individual salaries."""
    if not can_view_salary(user):
        raise PermissionDenied(
            "Your profile does not give access to individual salaries."
        )


class SettingViewSet(viewsets.ModelViewSet):
    """
    Base of every payroll setting: each change is historised (BN-92).
    Settings used by a validated payroll keep their version: a change of a
    legal value is made by adding a new version with its effective date.
    """

    permission_classes = [ModulePermission]
    permission_module = "payroll"
    action_permissions = {"create": "modify"}
    object_type = ""

    def _code(self, instance):
        return getattr(instance, "code", None) or str(instance)

    def perform_create(self, serializer):
        instance = serializer.save()
        ParameterChange.objects.create(
            object_type=self.object_type,
            object_code=self._code(instance),
            effective_from=getattr(instance, "effective_from", None),
            new_value=_json(instance),
            author=self.request.user,
        )
        log_audit_action(
            self.request.user,
            f"Created {self.object_type} {self._code(instance)}",
            "Payroll",
            self.request,
        )

    def perform_update(self, serializer):
        previous = _json(serializer.instance)
        instance = serializer.save()
        ParameterChange.objects.create(
            object_type=self.object_type,
            object_code=self._code(instance),
            effective_from=getattr(instance, "effective_from", None),
            previous_value=previous,
            new_value=_json(instance),
            author=self.request.user,
        )
        log_audit_action(
            self.request.user,
            f"Modified {self.object_type} {self._code(instance)}",
            "Payroll",
            self.request,
            {"previous_value": previous, "new_value": _json(instance)},
        )

    def perform_destroy(self, instance):
        last = (
            PayrollPeriod.objects.filter(status__in=PayrollPeriod.LOCKED_STATUSES)
            .order_by("-year", "-month")
            .first()
        )
        effective = getattr(instance, "effective_from", None)
        if last is not None and effective is not None and effective <= last.end_date:
            raise ValidationError(
                {
                    "detail": "This version was used by a validated payroll: add a new version instead."
                }
            )
        ParameterChange.objects.create(
            object_type=self.object_type,
            object_code=self._code(instance),
            previous_value=_json(instance),
            author=self.request.user,
        )
        instance.delete()


class ParameterViewSet(SettingViewSet):
    queryset = PayrollParameter.objects.all()
    serializer_class = PayrollParameterSerializer
    object_type = "Parameter"
    filterset_fields = ("code",)
    search_fields = ("code", "name")


class ScaleViewSet(SettingViewSet):
    search_fields = ("code", "name")
    queryset = Scale.objects.all()
    serializer_class = ScaleSerializer
    object_type = "Scale"


class StatutoryDeductionViewSet(SettingViewSet):
    search_fields = ("code", "name")
    queryset = StatutoryDeduction.objects.all()
    serializer_class = StatutoryDeductionSerializer
    object_type = "Statutory deduction"


class SalaryElementViewSet(SettingViewSet):
    search_fields = ("code", "name")
    queryset = SalaryElement.objects.all()
    serializer_class = SalaryElementSerializer
    object_type = "Salary element"

    def perform_destroy(self, instance):
        if (
            instance.is_system
            or VariableInput.objects.filter(element=instance).exists()
        ):
            raise ValidationError(
                {"detail": "This element is used: deactivate it instead."}
            )
        super().perform_destroy(instance)


class ElementValueViewSet(SettingViewSet):
    search_fields = (
        "element__code",
        "element__name",
        "employee__surname",
        "department__name",
    )
    serializer_class = ElementValueSerializer
    object_type = "Element value"
    filterset_fields = ("element", "employee", "department", "classification")

    def _code(self, instance):
        return f"{instance.element.code}/{instance.level}"

    def get_queryset(self):
        _require_salary_access(self.request.user)
        return ElementValue.objects.select_related(
            "element", "employee", "department", "classification"
        )


class SalaryGridViewSet(SettingViewSet):
    search_fields = ("classification__category", "classification__grade")
    queryset = SalaryGrid.objects.select_related("classification")
    serializer_class = SalaryGridSerializer
    object_type = "Salary grid"

    def _code(self, instance):
        return str(instance.classification)


class ParameterChangeViewSet(viewsets.ReadOnlyModelViewSet):
    """BN-92: history of the payroll settings."""

    queryset = ParameterChange.objects.select_related("author")
    serializer_class = ParameterChangeSerializer
    permission_classes = [ModulePermission]
    permission_module = "payroll"
    filterset_fields = ("object_type", "object_code")


class PeriodViewSet(viewsets.ModelViewSet):
    """BN-93: payroll cycle."""

    queryset = PayrollPeriod.objects.prefetch_related("transitions")
    serializer_class = PayrollPeriodSerializer
    permission_classes = [ModulePermission]
    permission_module = "payroll"
    http_method_names = ["get", "post", "head", "options"]
    action_permissions = {
        "pull_inputs": "modify",
        "calculate": "modify",
        "transition": "modify",
        "validate": "validate",
        "reverse": "validate",
        "anomalies": "consult",
        "comparison": "consult",
        "declarations": "consult",
        "payments": "consult",
        "provisions": "consult",
        "batch_payslips": "print",
        "payroll_book": "print",
        "contribution_statement": "print",
        "declaration_export": "export",
        "bank_file": "export",
        "payment_order": "print",
        "cash_list": "print",
    }

    def create(self, request, *args, **kwargs):
        try:
            year, month = int(request.data["year"]), int(request.data["month"])
            if not 1 <= month <= 12:
                raise ValueError
        except (KeyError, ValueError):
            return Response(
                {"detail": "year and month (1-12) are required."}, status=400
            )
        period = services.open_period(year, month, request.user)
        return Response(self.get_serializer(period).data, status=201)

    def _run(self, func, *args, audit=None, **kwargs):
        try:
            value = func(*args, **kwargs)
        except services.PayrollError as exc:
            raise ValidationError({"detail": str(exc)})
        if audit:
            log_audit_action(self.request.user, audit, "Payroll", self.request)
        return value

    @action(detail=True, methods=["post"])
    def pull_inputs(self, request, pk=None):
        period = self.get_object()
        count = self._run(
            services.pull_inputs,
            period,
            request.user,
            audit=f"Retrieved variable elements of {period}",
        )
        return Response({"created": count, "period": self.get_serializer(period).data})

    @action(detail=True, methods=["post"])
    def calculate(self, request, pk=None):
        """BN-104: ?department= or ?employee= to limit the calculation."""
        period = self.get_object()
        payslips = self._run(
            services.calculate_period,
            period,
            request.user,
            department=request.data.get("department"),
            employee=request.data.get("employee"),
            audit=f"Calculated payroll {period}",
        )
        period.refresh_from_db()
        return Response(
            {"calculated": len(payslips), "period": self.get_serializer(period).data}
        )

    @action(detail=True, methods=["post"])
    def transition(self, request, pk=None):
        period = self.get_object()
        target = request.data.get("status")
        self._run(
            services.change_status,
            period,
            target,
            request.user,
            request.data.get("comment", ""),
            audit=f"Payroll {period} → {target}",
        )
        return Response(self.get_serializer(period).data)

    @action(detail=True, methods=["post"])
    def validate(self, request, pk=None):
        period = self.get_object()
        self._run(
            services.validate, period, request.user, audit=f"Validated payroll {period}"
        )
        return Response(self.get_serializer(period).data)

    @action(detail=True, methods=["post"])
    def reverse(self, request, pk=None):
        period = self.get_object()
        self._run(
            services.reverse,
            period,
            request.user,
            request.data.get("reason", ""),
            audit=f"Reversed payroll {period}: {request.data.get('reason', '')}",
        )
        return Response(self.get_serializer(period).data)

    @action(detail=True, methods=["get"])
    def anomalies(self, request, pk=None):
        period = self.get_object()
        rows = []
        for payslip in period.payslips.exclude(status="REVERSED").select_related(
            "employee"
        ):
            for anomaly in payslip.anomalies:
                rows.append(
                    {
                        "employee": payslip.employee.full_name,
                        "payslip": payslip.id,
                        **anomaly,
                    }
                )
        return Response(rows)

    @action(detail=True, methods=["get"])
    def comparison(self, request, pk=None):
        _require_salary_access(request.user)
        return Response(services.compare(self.get_object()))

    @action(detail=True, methods=["get"])
    def declarations(self, request, pk=None):
        """BN-111: amounts due to the social and tax bodies (consolidated)."""
        return Response(services.declarations(self.get_object()))

    @action(detail=True, methods=["get"])
    def payments(self, request, pk=None):
        summary = services.payment_summary(self.get_object())
        return Response(
            {
                "total": summary["total"],
                "by_method": summary["by_method"],
                "by_bank": {
                    bank: {"count": data["count"], "total": data["total"]}
                    for bank, data in summary["by_bank"].items()
                },
            }
        )

    @action(detail=True, methods=["get"])
    def provisions(self, request, pk=None):
        period = self.get_object()
        rows = [
            {
                "employee": p.employee.full_name,
                "days": p.days,
                "daily_rate": p.daily_rate,
                "amount": p.amount,
            }
            for p in period.provisions.select_related("employee")
        ]
        return Response(
            {"rows": rows, "total": sum((r["amount"] for r in rows), Decimal("0"))}
        )

    def _audit_doc(self, text):
        log_audit_action(self.request.user, text, "Payroll", self.request)

    @action(detail=True, methods=["post"])
    def batch_payslips(self, request, pk=None):
        """BN-114: payslips of the organisation, a department or a selection, in one file."""
        _require_salary_access(request.user)
        period = self.get_object()
        payslips = period.payslips.exclude(status="REVERSED").select_related(
            "employee", "employee__department", "contract", "period"
        )
        if request.data.get("department"):
            payslips = payslips.filter(
                employee__department_id=request.data["department"]
            )
        if request.data.get("employees"):
            payslips = payslips.filter(employee_id__in=request.data["employees"])
        payslips = list(
            payslips.order_by("employee__department__name", "employee__surname")
        )
        if not payslips:
            return Response({"detail": "No payslip for this selection."}, status=400)
        issued = payroll_documents.batch_payslips_pdf(payslips, request.user, period)
        self._audit_doc(f"Printed {len(payslips)} payslips of {period}")
        return _pdf_response(issued)

    @action(detail=True, methods=["get"])
    def payroll_book(self, request, pk=None):
        """BN-117: payroll book and summary with totals per department."""
        _require_salary_access(request.user)
        period = self.get_object()
        context, payslips = payroll_documents.payroll_book(period)
        fmt = request.query_params.get("file_format", "pdf")
        self._audit_doc(f"Printed payroll book {period} ({fmt})")
        if fmt in ("xlsx", "csv"):
            columns = payroll_documents.PAYROLL_BOOK_COLUMNS
            return export_rows(
                [title for title, _ in columns],
                [[getter(p) for _, getter in columns] for p in payslips],
                f"payroll-book-{period.year}-{period.month:02d}",
                fmt,
                title=f"Payroll book {period.month:02d}-{period.year}",
            )
        pdf = render_document("PAYROLL_BOOK", context, landscape=True)
        issued = issue_document(
            "PAYROLL_BOOK",
            context,
            user=request.user,
            title=f"Payroll book {period}",
            pdf=pdf,
        )
        return _pdf_response(issued)

    @action(detail=True, methods=["get"])
    def contribution_statement(self, request, pk=None):
        """BN-118: statement of contributions and taxes withheld."""
        period = self.get_object()
        issued = issue_document(
            "CONTRIBUTION_STATEMENT",
            payroll_documents.contribution_statement(period),
            user=request.user,
            title=f"Contributions and taxes {period}",
        )
        return _pdf_response(issued)

    @action(detail=True, methods=["get"])
    def declaration_export(self, request, pk=None):
        """BN-119: declaration file per body (?body=CNPS|TAX|CFC|FNE|COMMUNE|CRTV)."""
        _require_salary_access(request.user)
        period = self.get_object()
        body = request.query_params.get("body", "CNPS").upper()
        self._audit_doc(f"Exported {body} declaration of {period}")
        return _csv_response(
            payroll_documents.declaration_export(period, body),
            f"declaration-{body.lower()}-{period.year}{period.month:02d}.csv",
        )

    @action(detail=True, methods=["get"])
    def bank_file(self, request, pk=None):
        """BN-121: transfer file, all banks or ?bank=."""
        _require_salary_access(request.user)
        period = self.get_object()
        self._audit_doc(f"Exported bank transfer file of {period}")
        return _csv_response(
            payroll_documents.bank_file(period, request.query_params.get("bank")),
            f"transfers-{period.year}{period.month:02d}.csv",
        )

    @action(detail=True, methods=["get"])
    def payment_order(self, request, pk=None):
        """BN-110 / BN-121: payment order per bank (one page per bank)."""
        period = self.get_object()
        contexts = payroll_documents.payment_order_contexts(period)
        if request.query_params.get("bank"):
            contexts = [
                c for c in contexts if c["bank"] == request.query_params["bank"]
            ]
        if not contexts:
            return Response({"detail": "No transfer in this period."}, status=400)
        issued = issue_document(
            "PAYMENT_ORDER",
            {},
            user=request.user,
            title=f"Payment orders {period}",
            pdf=render_batch("PAYMENT_ORDER", contexts),
        )
        return _pdf_response(issued)

    @action(detail=True, methods=["get"])
    def cash_list(self, request, pk=None):
        """BN-122: employees paid in cash, with the receipt to sign."""
        period = self.get_object()
        issued = issue_document(
            "CASH_LIST",
            payroll_documents.cash_list_context(period),
            user=request.user,
            title=f"Cash payments {period}",
        )
        return _pdf_response(issued)


class PayslipViewSet(viewsets.ReadOnlyModelViewSet):
    """Payslips. Every consultation of an individual payslip is logged (BN-172)."""

    permission_classes = [ModulePermission]
    permission_module = "payroll"
    action_permissions = {"mine": "print", "pdf": "print", "email": "print"}
    filterset_fields = ("period", "employee", "status", "employee__department")
    search_fields = (
        "employee__surname",
        "employee__given_names",
        "employee__matriculation_number",
    )

    def get_serializer_class(self):
        return (
            PayslipDetailSerializer
            if self.action in ("retrieve", "mine")
            else PayslipSerializer
        )

    def get_queryset(self):
        queryset = Payslip.objects.select_related(
            "employee", "employee__department", "period"
        )
        user = self.request.user
        if self.action == "mine" or not can_view_salary(user):
            return queryset.filter(employee__user=user, status="VALIDATED")
        queryset = scope_employees(user, queryset, "employee__")
        if user.role == "HR_OFFICER":
            queryset = queryset.exclude(employee__classification__is_executive=True)
        return queryset

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        log_audit_action(
            request.user,
            f"Consulted payslip #{kwargs.get('pk')}",
            "Payroll",
            request,
            {"employee": response.data.get("employee")},
        )
        return response

    @action(detail=True, methods=["get"])
    def pdf(self, request, pk=None):
        """BN-113 / BN-115: payslip (?duplicate=1 for a marked reprint)."""
        payslip = self.get_object()
        issued = payroll_documents.payslip_pdf(
            payslip,
            request.user,
            duplicate=request.query_params.get("duplicate") in ("1", "true"),
        )
        log_audit_action(
            request.user, f"Printed payslip #{payslip.id}", "Payroll", request
        )
        return _pdf_response(issued)

    @action(detail=True, methods=["post"])
    def email(self, request, pk=None):
        """BN-116: send the payslip by e-mail in a protected PDF."""
        payslip = self.get_object()
        if payslip.status != "VALIDATED":
            return Response(
                {"detail": "Only a validated payslip can be sent."}, status=400
            )
        try:
            address = payroll_documents.email_payslip(payslip, request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        log_audit_action(
            request.user,
            f"E-mailed payslip #{payslip.id} to {address}",
            "Payroll",
            request,
        )
        return Response({"detail": f"Payslip sent to {address}."})

    @action(detail=False, methods=["get"])
    def mine(self, request):
        """BN-150: the employee's own validated payslips."""
        payslips = self.get_queryset().order_by("-period__year", "-period__month")
        return Response(PayslipSerializer(payslips, many=True).data)


class VariableInputViewSet(viewsets.ModelViewSet):
    """BN-94: manual capture of the variable elements of the period."""

    search_fields = (
        "employee__surname",
        "employee__given_names",
        "element__code",
        "element__name",
    )
    serializer_class = VariableInputSerializer
    permission_classes = [ModulePermission]
    permission_module = "payroll"
    action_permissions = {"create": "modify"}
    filterset_fields = ("period", "employee", "element", "source")

    def get_queryset(self):
        _require_salary_access(self.request.user)
        return VariableInput.objects.select_related("employee", "element", "period")

    def perform_create(self, serializer):
        serializer.save(source="MANUAL", created_by=self.request.user)

    def perform_destroy(self, instance):
        if instance.period.is_locked:
            raise ValidationError({"detail": "The period is validated."})
        instance.delete()


class LoanViewSet(viewsets.ModelViewSet):
    """BN-98."""

    search_fields = (
        "employee__surname",
        "employee__given_names",
        "employee__matriculation_number",
    )
    serializer_class = LoanSerializer
    permission_classes = [ModulePermission]
    permission_module = "payroll"
    action_permissions = {"create": "modify"}
    filterset_fields = ("employee", "status", "kind")

    def get_queryset(self):
        _require_salary_access(self.request.user)
        return Loan.objects.select_related("employee")

    def perform_create(self, serializer):
        loan = serializer.save(created_by=self.request.user)
        log_audit_action(
            self.request.user,
            f"Granted {loan.kind} of {loan.amount} to {loan.employee.full_name}",
            "Payroll",
            self.request,
        )


class ThirdPartyDeductionViewSet(viewsets.ModelViewSet):
    """BN-99."""

    search_fields = ("employee__surname", "employee__given_names", "beneficiary")
    serializer_class = ThirdPartyDeductionSerializer
    permission_classes = [ModulePermission]
    permission_module = "payroll"
    action_permissions = {"create": "modify"}
    filterset_fields = ("employee", "kind", "is_active")

    def get_queryset(self):
        _require_salary_access(self.request.user)
        return ThirdPartyDeduction.objects.select_related("employee")


def _result_payload(result):
    return {
        "paid_days": result.paid_days,
        "prorata": result.prorata,
        "base_salary": result.base_salary,
        "gross": result.gross,
        "contributory_base": result.contributory_base,
        "taxable_base": result.taxable_base,
        "employee_contributions": result.employee_contributions,
        "employer_contributions": result.employer_contributions,
        "taxes": result.taxes,
        "other_deductions": result.other_deductions,
        "net_salary": result.net_salary,
        "benefits_in_kind": result.benefits_in_kind,
        "net_payable": result.net_payable,
        "total_cost": result.gross + result.employer_contributions,
        "anomalies": result.anomalies,
        "lines": [
            {
                "code": line.code,
                "label": line.label,
                "kind": line.kind,
                "base": line.base,
                "rate": line.rate,
                "employer_rate": line.employer_rate,
                "quantity": line.quantity,
                "amount": line.amount,
                "employer_amount": line.employer_amount,
            }
            for line in result.lines
        ],
    }


class SimulationView(APIView):
    """
    BN-105: simulation without any effect.
    {"employee": id, "year", "month", "overrides": {...}} answers a question
    of an employee; {"base_salary", "classification", "year", "month"}
    prepares a hiring proposal.
    """

    permission_classes = [ModulePermission]
    permission_module = "payroll"

    def post(self, request):
        _require_salary_access(request.user)
        try:
            year, month = int(request.data["year"]), int(request.data["month"])
        except (KeyError, ValueError):
            return Response({"detail": "year and month are required."}, status=400)
        period = PayrollPeriod.objects.filter(
            year=year, month=month
        ).first() or PayrollPeriod(year=year, month=month)
        overrides = request.data.get("overrides") or {}
        if request.data.get("employee"):
            employee = (
                scope_employees(request.user, Employee.objects.all())
                .filter(pk=request.data["employee"])
                .first()
            )
            if employee is None:
                return Response({"detail": "Unknown employee."}, status=404)
            inputs = None if period.pk else []
            result = engine.calculate(
                employee, period, overrides=overrides, inputs=inputs
            )
        else:
            try:
                base = Decimal(str(request.data["base_salary"]))
            except (KeyError, ArithmeticError):
                return Response(
                    {"detail": "employee or base_salary is required."}, status=400
                )
            result = services.simulate_hiring(
                period,
                base,
                classification_id=request.data.get("classification"),
                weekly_hours=Decimal(str(request.data.get("weekly_hours", 40))),
                elements=overrides.get("elements"),
            )
        return Response(_result_payload(result))


class FinalSettlementView(APIView):
    """BN-103: final settlement of accounts of a terminated contract."""

    permission_classes = [ModulePermission]
    permission_module = "payroll"

    def post(self, request, termination_id):
        _require_salary_access(request.user)
        if not has_module_permission(request.user, "payroll", "modify"):
            raise PermissionDenied()
        termination = (
            ContractTermination.objects.filter(pk=termination_id)
            .select_related("contract__employee")
            .first()
        )
        if termination is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        try:
            settlement = services.final_settlement(termination, request.user)
        except services.PayrollError as exc:
            return Response({"detail": str(exc)}, status=400)
        log_audit_action(
            request.user,
            f"Computed final settlement of {termination.contract.employee.full_name}",
            "Payroll",
            request,
        )
        return Response(settlement)


class AnnualStatementView(APIView):
    """BN-120: annual individual salary statement (?year=&employee=)."""

    permission_classes = [ModulePermission]
    permission_module = "payroll"
    required_action = "print"

    def get(self, request):
        try:
            year = int(request.query_params["year"])
        except (KeyError, ValueError):
            return Response({"detail": "year is required."}, status=400)
        employee_id = request.query_params.get("employee")
        if employee_id and can_view_salary(request.user):
            employee = (
                scope_employees(request.user, Employee.objects.all())
                .filter(pk=employee_id)
                .first()
            )
        else:
            employee = Employee.objects.filter(user=request.user).first()
        if employee is None:
            return Response({"detail": "Unknown employee."}, status=404)
        issued = issue_document(
            "ANNUAL_STATEMENT",
            payroll_documents.annual_statement(employee, year),
            employee=employee,
            user=request.user,
            title=f"Annual statement {year}",
        )
        return _pdf_response(issued)


class AnnualSummaryView(APIView):
    """BN-120: annual summary for the tax administration."""

    permission_classes = [ModulePermission]
    permission_module = "payroll"

    COLUMNS = [
        ("Matriculation", "matriculation"),
        ("NIU", "niu"),
        ("Employee", "name"),
        ("Months", "months"),
        ("Gross", "gross"),
        ("Taxable", "taxable_base"),
        ("Contributory", "contributory_base"),
        ("Employee contributions", "employee_contributions"),
        ("Employer contributions", "employer_contributions"),
        ("IRPP", "irpp"),
        ("CAC", "cac"),
        ("Total taxes", "taxes"),
        ("Net payable", "net_payable"),
    ]

    def get(self, request):
        if not has_module_permission(request.user, "payroll", "export"):
            raise PermissionDenied()
        try:
            year = int(request.query_params["year"])
        except (KeyError, ValueError):
            return Response({"detail": "year is required."}, status=400)
        rows = payroll_documents.annual_summary(year)
        fmt = request.query_params.get("file_format")
        if not fmt:
            return Response(rows)
        log_audit_action(
            request.user, f"Exported annual summary {year}", "Payroll", request
        )
        return export_rows(
            [title for title, _ in self.COLUMNS],
            [[row[key] for _, key in self.COLUMNS] for row in rows],
            f"annual-summary-{year}",
            fmt,
            title=f"Annual salary summary {year}",
        )
