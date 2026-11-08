from django.http import FileResponse, HttpResponse
import datetime

from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from employees.models import Employee
from users.permissions import (
    ModulePermission,
    can_view_salary,
    has_module_permission,
    scope_employees,
)
from users.utils import log_audit_action

from .models import DocumentRequest, DocumentTemplate, IssuedDocument
from .services import issue_document, render_document


class DocumentTemplateSerializer(serializers.ModelSerializer):
    updated_by_name = serializers.CharField(
        source="updated_by.username", read_only=True
    )

    class Meta:
        model = DocumentTemplate
        fields = "__all__"
        read_only_fields = ("updated_by", "updated_at")


class IssuedDocumentSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    issued_by_name = serializers.CharField(source="issued_by.username", read_only=True)

    class Meta:
        model = IssuedDocument
        fields = "__all__"


class DocumentRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)

    class Meta:
        model = DocumentRequest
        fields = "__all__"
        read_only_fields = ("employee", "status", "issued_document")


class DocumentTemplateViewSet(viewsets.ModelViewSet):
    """BN-125: the organisation edits its templates without development."""

    search_fields = ("code", "name")
    queryset = DocumentTemplate.objects.all()
    serializer_class = DocumentTemplateSerializer
    permission_classes = [ModulePermission]
    permission_module = "documents"
    action_permissions = {"preview": "print"}

    def perform_create(self, serializer):
        serializer.save(updated_by=self.request.user)

    def perform_update(self, serializer):
        previous = serializer.instance.body
        template = serializer.save(updated_by=self.request.user)
        log_audit_action(
            user=self.request.user,
            action=f"Modified document template {template.code}",
            module="Documents",
            request=self.request,
            details={"previous_value": previous[:2000]},
        )

    @action(detail=True, methods=["get"])
    def preview(self, request, pk=None):
        """Render the template with an employee to check the result."""
        template = self.get_object()
        employee = (
            scope_employees(request.user, Employee.objects.all())
            .filter(pk=request.query_params.get("employee"))
            .first()
        ) or scope_employees(request.user, Employee.objects.all()).first()
        try:
            pdf = render_document(template.code, {"employee": employee})
        except Exception as exc:
            return Response(
                {"detail": f"The template could not be rendered: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{template.code}.pdf"'
        return response


class IssuedDocumentViewSet(viewsets.ReadOnlyModelViewSet):
    """BN-127: every issued document can be found again."""

    serializer_class = IssuedDocumentSerializer
    permission_classes = [ModulePermission]
    permission_module = "documents"
    action_permissions = {"download": "print"}
    filterset_fields = ("employee", "template_code")
    search_fields = ("title", "reference", "recipient")

    def get_queryset(self):
        queryset = IssuedDocument.objects.select_related("employee", "issued_by")
        if has_module_permission(self.request.user, "documents", "create"):
            return queryset
        return scope_employees(self.request.user, queryset, "employee__")

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        document = self.get_object()
        log_audit_action(
            user=request.user,
            action=f"Downloaded document {document.reference}",
            module="Documents",
            request=request,
        )
        return FileResponse(
            document.file.open("rb"),
            as_attachment=True,
            filename=document.file.name.rsplit("/", 1)[-1],
        )


class DocumentRequestViewSet(viewsets.ModelViewSet):
    """BN-152: an employee requests an attestation."""

    serializer_class = DocumentRequestSerializer
    permission_classes = [ModulePermission]
    permission_module = "documents"
    action_permissions = {"create": "consult", "mine": "consult"}

    def get_queryset(self):
        queryset = DocumentRequest.objects.select_related("employee")
        if has_module_permission(self.request.user, "documents", "create"):
            return queryset
        return queryset.filter(employee__user=self.request.user)

    def perform_create(self, serializer):
        from notifications.services import notify_roles
        from users.models import User

        employee = Employee.objects.filter(user=self.request.user).first()
        if employee is None:
            raise serializers.ValidationError(
                "No employee record is linked to this account."
            )
        req = serializer.save(employee=employee)
        notify_roles(
            [User.Roles.HR_OFFICER, User.Roles.HR_MANAGER],
            f"Document requested by {employee.full_name}",
            req.template_code,
            "/documents#requests",
            "REQUEST",
        )


CERTIFICATES = (
    "WORK_CERTIFICATE",
    "EMPLOYMENT_ATTESTATION",
    "SALARY_ATTESTATION",
    "PRESENCE_ATTESTATION",
)


def _pdf(issued):
    response = HttpResponse(issued.file.read(), content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{issued.reference}.pdf"'
    return response


def _target_employee(request, employee_id):
    """HR prints for anyone in its perimeter; an employee only for himself."""
    if employee_id and has_module_permission(request.user, "documents", "create"):
        employee = (
            scope_employees(request.user, Employee.objects.all())
            .filter(pk=employee_id)
            .first()
        )
    else:
        employee = Employee.objects.filter(user=request.user).first()
        if (
            employee_id
            and employee is not None
            and str(employee.id) != str(employee_id)
        ):
            raise PermissionDenied("You can only print your own documents.")
    return employee


def certificate_context(code, employee, user):
    from contracts.services import active_contract
    from core.models import get_setting

    today = timezone.now().date()
    context = {"employee": employee, "currency": get_setting("CURRENCY", "XAF")}
    if code == "WORK_CERTIFICATE":
        contracts = list(
            employee.contracts.exclude(status="DRAFT").order_by("start_date")
        )
        start = contracts[0].start_date if contracts else employee.date_of_hire
        end = contracts[-1].effective_end_date if contracts else None
        context.update(
            {
                "start_date": start,
                "end_date": end or today,
                "position": employee.position.title if employee.position else "",
            }
        )
    elif code == "SALARY_ATTESTATION":
        if not can_view_salary(user, employee):
            raise PermissionDenied("Your profile does not give access to this salary.")
        contract = active_contract(employee, today)
        context["base_salary"] = (
            contract.terms_at(today)["base_salary"] if contract else 0
        )
        from payroll.models import Payslip

        payslips = list(
            Payslip.objects.filter(employee=employee, status="VALIDATED").order_by(
                "-period__year", "-period__month"
            )[:3]
        )
        if payslips:
            context["average_net"] = round(
                sum(p.net_payable for p in payslips) / len(payslips)
            )
            context["months"] = len(payslips)
    elif code == "PRESENCE_ATTESTATION":
        from attendance.models import DailyAttendance

        start = today.replace(day=1)
        context.update(
            {
                "site": employee.workplace.name if employee.workplace else "",
                "start": start,
                "end": today,
                "days_present": DailyAttendance.objects.filter(
                    employee=employee,
                    date__range=(start, today),
                    status__in=("PRESENT", "MISSION"),
                ).count(),
            }
        )
    return context


class CertificateView(APIView):
    """BN-123: administrative certificates (?employee= for HR)."""

    permission_classes = [ModulePermission]
    permission_module = "documents"

    def get(self, request, code):
        code = code.upper()
        if code not in CERTIFICATES:
            return Response(
                {
                    "detail": f"Unknown certificate. Use one of {', '.join(CERTIFICATES)}."
                },
                status=400,
            )
        employee = _target_employee(request, request.query_params.get("employee"))
        if employee is None:
            return Response({"detail": "No employee record."}, status=404)
        issued = issue_document(
            code,
            certificate_context(code, employee, request.user),
            employee=employee,
            user=request.user,
        )
        DocumentRequest.objects.filter(
            employee=employee, template_code=code, status="PENDING"
        ).update(status="ISSUED", issued_document=issued)
        if employee.user and employee.user != request.user:
            from notifications.services import notify

            notify(
                employee.user,
                f"Your document is ready: {issued.title}",
                "",
                "/my-space#documents",
                "INFO",
            )
        log_audit_action(
            request.user,
            f"Issued {code} for {employee.full_name}",
            "Documents",
            request,
        )
        return _pdf(issued)


DECISIONS = ("PROMOTION_DECISION", "TRANSFER_DECISION", "DISCIPLINARY_LETTER")


class DecisionView(APIView):
    """BN-124: decision documents generated from the templates."""

    permission_classes = [ModulePermission]
    permission_module = "documents"

    def post(self, request):
        if not has_module_permission(request.user, "documents", "create"):
            raise PermissionDenied()
        code = str(request.data.get("code", "")).upper()
        if code not in DECISIONS:
            return Response(
                {"detail": f"code must be one of {', '.join(DECISIONS)}."}, status=400
            )
        employee = (
            scope_employees(request.user, Employee.objects.all())
            .filter(pk=request.data.get("employee"))
            .first()
        )
        if employee is None:
            return Response({"detail": "Unknown employee."}, status=404)
        try:
            effective = datetime.date.fromisoformat(
                request.data.get("effective_date") or str(timezone.now().date())
            )
        except ValueError:
            return Response(
                {"detail": "effective_date must be YYYY-MM-DD."}, status=400
            )
        subject = request.data.get("subject") or ""
        if not subject:
            return Response(
                {"detail": "The subject of the decision is required."}, status=400
            )
        issued = issue_document(
            code,
            {
                "employee": employee,
                "subject": subject,
                "details": request.data.get("details", ""),
                "effective_date": effective,
            },
            employee=employee,
            user=request.user,
        )
        log_audit_action(
            request.user,
            f"Issued {code} for {employee.full_name}",
            "Documents",
            request,
            {"subject": subject},
        )
        return _pdf(issued)
