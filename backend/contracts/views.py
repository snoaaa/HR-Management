from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.models import get_setting
from documents.services import issue_document
from organisation.models import Classification, Department, Position, Site
from users.permissions import ModulePermission, can_view_salary, scope_employees
from users.utils import log_audit_action

from . import services
from .models import AMENDABLE_TERMS, Contract
from .serializers import (
    AmendmentRequestSerializer,
    ContractAmendmentSerializer,
    ContractRenewalSerializer,
    ContractSerializer,
    ContractSuspensionSerializer,
    ContractTerminationSerializer,
    RenewalRequestSerializer,
    ResumeRequestSerializer,
)

LOOKUPS = {
    "position_id": Position,
    "classification_id": Classification,
    "department_id": Department,
    "workplace_id": Site,
}


def _label(name, value):
    model = LOOKUPS.get(name)
    if model is not None and value is not None:
        obj = model.objects.filter(pk=value).first()
        return str(obj) if obj else value
    return "" if value is None else value


def _pdf_response(issued):
    response = HttpResponse(issued.file.read(), content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{issued.reference}.pdf"'
    return response


class ContractViewSet(viewsets.ModelViewSet):
    """M-04: contracts, amendments, renewals, suspensions and terminations."""

    serializer_class = ContractSerializer
    permission_classes = [ModulePermission]
    permission_module = "contracts"
    action_permissions = {
        "activate": "validate",
        "amend": "modify",
        "renew": "modify",
        "suspend": "modify",
        "resume": "modify",
        "terminate": "validate",
        "print_contract": "print",
        "print_amendment": "print",
        "end_certificate": "print",
        "alerts": "consult",
    }
    filterset_fields = ("employee", "status", "contract_type")
    search_fields = (
        "reference",
        "employee__surname",
        "employee__given_names",
        "employee__matriculation_number",
    )

    def get_queryset(self):
        queryset = Contract.objects.select_related(
            "employee",
            "position",
            "department",
            "workplace",
            "classification",
            "termination",
        ).prefetch_related("amendments", "renewals", "suspensions")
        return scope_employees(self.request.user, queryset, "employee__")

    def perform_create(self, serializer):
        contract = serializer.save(created_by=self.request.user)
        try:
            services.validate_contract(contract)
        except services.ContractError as exc:
            contract.delete()
            from rest_framework.exceptions import ValidationError

            raise ValidationError({"detail": str(exc)})
        self._audit(f"Created contract {contract.reference}", contract)

    def perform_destroy(self, contract):
        if contract.status != "DRAFT":
            from rest_framework.exceptions import ValidationError

            raise ValidationError({"detail": "Only a draft contract can be deleted."})
        self._audit(f"Deleted draft contract {contract.reference}", contract)
        contract.delete()

    def _audit(self, text, contract, **details):
        log_audit_action(
            user=self.request.user,
            action=text,
            module="Contracts",
            request=self.request,
            details={"contract_id": contract.id, **details},
        )

    def _run(self, func, *args):
        try:
            return func(*args), None
        except services.ContractError as exc:
            return None, Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )

    def _contract_response(self, contract):
        contract.refresh_from_db()
        return Response(self.get_serializer(contract).data)

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        contract = self.get_object()
        _, error = self._run(services.activate, contract, request.user)
        if error:
            return error
        self._audit(f"Activated contract {contract.reference}", contract)
        return self._contract_response(contract)

    @action(detail=True, methods=["post"])
    def amend(self, request, pk=None):
        """BN-30: create an amendment (new version of the terms)."""
        contract = self.get_object()
        serializer = AmendmentRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        effective_date = data.pop("effective_date")
        reason = data.pop("reason")
        amendment, error = self._run(
            services.amend, contract, data, effective_date, reason, request.user
        )
        if error:
            return error
        self._audit(
            f"Amended contract {contract.reference} (v{amendment.version})",
            contract,
            previous_value=amendment.previous_values,
            new_value=amendment.new_values,
        )
        return Response(
            ContractAmendmentSerializer(amendment, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def renew(self, request, pk=None):
        contract = self.get_object()
        serializer = RenewalRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        renewal, error = self._run(
            services.renew,
            contract,
            serializer.validated_data["new_end_date"],
            request.user,
        )
        if error:
            return error
        self._audit(f"Renewed contract {contract.reference}", contract)
        return Response(ContractRenewalSerializer(renewal).data, status=201)

    @action(detail=True, methods=["post"])
    def suspend(self, request, pk=None):
        contract = self.get_object()
        serializer = ContractSuspensionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        suspension, error = self._run(
            services.suspend, contract, dict(serializer.validated_data), request.user
        )
        if error:
            return error
        self._audit(f"Suspended contract {contract.reference}", contract)
        return Response(ContractSuspensionSerializer(suspension).data, status=201)

    @action(detail=True, methods=["post"])
    def resume(self, request, pk=None):
        contract = self.get_object()
        serializer = ResumeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        _, error = self._run(
            services.resume,
            contract,
            serializer.validated_data["end_date"],
            request.user,
        )
        if error:
            return error
        self._audit(f"Resumed contract {contract.reference}", contract)
        return self._contract_response(contract)

    @action(detail=True, methods=["post"])
    def terminate(self, request, pk=None):
        """BN-34: end of contract."""
        contract = self.get_object()
        serializer = ContractTerminationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        termination, error = self._run(
            services.terminate, contract, dict(serializer.validated_data), request.user
        )
        if error:
            return error
        self._audit(
            f"Terminated contract {contract.reference} ({termination.reason})",
            contract,
        )
        return Response(ContractTerminationSerializer(termination).data, status=201)

    def _context(self, contract):
        show_salary = can_view_salary(self.request.user, contract.employee)
        return {
            "contract": contract,
            "employee": contract.employee,
            "currency": get_setting("CURRENCY", "XAF"),
            "salary_visible": show_salary,
        }

    @action(detail=True, methods=["get"])
    def print_contract(self, request, pk=None):
        """BN-35: printable contract generated from the template."""
        contract = self.get_object()
        issued = issue_document(
            "CONTRACT",
            self._context(contract),
            employee=contract.employee,
            user=request.user,
            title=f"Contract {contract.reference}",
        )
        self._audit(f"Printed contract {contract.reference}", contract)
        return _pdf_response(issued)

    @action(detail=True, methods=["get"], url_path=r"print-amendment/(?P<version>\d+)")
    def print_amendment(self, request, pk=None, version=None):
        contract = self.get_object()
        amendment = contract.amendments.filter(version=version).first()
        if amendment is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        changes = [
            {
                "label": AMENDABLE_TERMS[name],
                "old": _label(name, amendment.previous_values.get(name)),
                "new": _label(name, value),
            }
            for name, value in amendment.new_values.items()
        ]
        issued = issue_document(
            "AMENDMENT",
            {**self._context(contract), "amendment": amendment, "changes": changes},
            employee=contract.employee,
            user=request.user,
            title=f"Amendment {amendment.version} to {contract.reference}",
        )
        self._audit(f"Printed amendment {version} of {contract.reference}", contract)
        return _pdf_response(issued)

    @action(detail=True, methods=["get"])
    def end_certificate(self, request, pk=None):
        contract = self.get_object()
        termination = getattr(contract, "termination", None)
        if termination is None:
            return Response(
                {"detail": "The contract is not terminated."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        issued = issue_document(
            "END_OF_CONTRACT",
            {**self._context(contract), "termination": termination},
            employee=contract.employee,
            user=request.user,
        )
        return _pdf_response(issued)

    @action(detail=False, methods=["get"])
    def alerts(self, request):
        """BN-31: upcoming ends of fixed-term contracts and trial periods."""
        services.apply_due_terminations(user=request.user)
        allowed = set(self.get_queryset().values_list("id", flat=True))
        return Response(
            [
                {
                    "type": item["type"],
                    "date": item["date"],
                    "days_left": item["days_left"],
                    "contract_id": item["contract"].id,
                    "contract_reference": item["contract"].reference,
                    "employee_id": item["contract"].employee_id,
                    "employee_name": item["contract"].employee.full_name,
                }
                for item in services.upcoming_deadlines()
                if item["contract"].id in allowed
            ]
        )

    @action(detail=False, methods=["get"], url_path="current")
    def current(self, request):
        """Contracts in force today (used by payroll and planning screens)."""
        today = timezone.now().date()
        contracts = [c for c in self.get_queryset() if c.is_in_force(today)]
        return Response(self.get_serializer(contracts, many=True).data)
