from django.utils import timezone
from rest_framework import serializers

from users.permissions import can_view_salary

from .models import (
    Contract,
    ContractAmendment,
    ContractRenewal,
    ContractSuspension,
    ContractTermination,
)

SALARY_FIELDS = ("base_salary",)


class SalaryMaskMixin:
    """BN-172: remove the salary for the profiles not authorised to see it."""

    def mask(self, data, employee):
        request = self.context.get("request")
        if request is not None and not can_view_salary(request.user, employee):
            for field in SALARY_FIELDS:
                if field in data:
                    data[field] = None
            data["salary_hidden"] = True
        return data


class ContractAmendmentSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(
        source="created_by.username", read_only=True
    )

    class Meta:
        model = ContractAmendment
        fields = "__all__"

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        if request is not None and not can_view_salary(
            request.user, instance.contract.employee
        ):
            for key in ("previous_values", "new_values"):
                if "base_salary" in data[key]:
                    data[key] = {**data[key], "base_salary": "***"}
        return data


class ContractRenewalSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContractRenewal
        fields = "__all__"


class ContractSuspensionSerializer(serializers.ModelSerializer):
    reason_label = serializers.CharField(source="get_reason_display", read_only=True)

    class Meta:
        model = ContractSuspension
        fields = "__all__"
        read_only_fields = ("contract", "created_by")


class ContractTerminationSerializer(serializers.ModelSerializer):
    reason_label = serializers.CharField(source="get_reason_display", read_only=True)

    class Meta:
        model = ContractTermination
        fields = "__all__"
        read_only_fields = ("contract", "created_by", "final_settlement")


class ContractSerializer(SalaryMaskMixin, serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    employee_matriculation = serializers.CharField(
        source="employee.matriculation_number", read_only=True
    )
    contract_type_label = serializers.CharField(
        source="get_contract_type_display", read_only=True
    )
    position_title = serializers.CharField(source="position.title", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    workplace_name = serializers.CharField(source="workplace.name", read_only=True)
    classification_label = serializers.CharField(
        source="classification.__str__", read_only=True
    )
    amendments = ContractAmendmentSerializer(many=True, read_only=True)
    renewals = ContractRenewalSerializer(many=True, read_only=True)
    suspensions = ContractSuspensionSerializer(many=True, read_only=True)
    termination = ContractTerminationSerializer(read_only=True)
    effective_end_date = serializers.DateField(read_only=True)
    in_force_today = serializers.SerializerMethodField()

    class Meta:
        model = Contract
        fields = "__all__"
        read_only_fields = (
            "reference",
            "status",
            "renewal_count",
            "created_by",
            "created_at",
        )

    def get_in_force_today(self, contract):
        return contract.is_in_force(timezone.now().date())

    def validate(self, attrs):
        instance = self.instance
        if instance is not None and instance.status != "DRAFT":
            raise serializers.ValidationError(
                "A contract in force is changed through an amendment, "
                "a renewal, a suspension or a termination."
            )
        return attrs

    def to_representation(self, instance):
        return self.mask(super().to_representation(instance), instance.employee)


class AmendmentRequestSerializer(serializers.Serializer):
    effective_date = serializers.DateField()
    reason = serializers.CharField(max_length=255)
    base_salary = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=False
    )
    position_id = serializers.IntegerField(required=False, allow_null=True)
    classification_id = serializers.IntegerField(required=False, allow_null=True)
    department_id = serializers.IntegerField(required=False, allow_null=True)
    workplace_id = serializers.IntegerField(required=False, allow_null=True)
    weekly_hours = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False
    )
    end_date = serializers.DateField(required=False, allow_null=True)


class RenewalRequestSerializer(serializers.Serializer):
    new_end_date = serializers.DateField()


class ResumeRequestSerializer(serializers.Serializer):
    end_date = serializers.DateField()
