from rest_framework import serializers

from users.permissions import can_view_salary

from .models import EntitlementRule, LeaveAdjustment, LeaveRequest, LeaveType


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = "__all__"


class EntitlementRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = EntitlementRule
        fields = "__all__"

    def validate_seniority_brackets(self, value):
        for bracket in value:
            if (
                not isinstance(bracket, dict)
                or "years" not in bracket
                or "extra_days" not in bracket
            ):
                raise serializers.ValidationError(
                    'Each bracket is {"years": n, "extra_days": n}.'
                )
        return value


class LeaveAdjustmentSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)

    class Meta:
        model = LeaveAdjustment
        fields = "__all__"
        read_only_fields = ("created_by",)


class LeaveRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    department_name = serializers.CharField(
        source="employee.department.name", read_only=True
    )
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    leave_type_color = serializers.CharField(source="leave_type.color", read_only=True)
    replacement_name = serializers.CharField(
        source="replacement.full_name", read_only=True
    )
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    effective_end_date = serializers.DateField(read_only=True)

    class Meta:
        model = LeaveRequest
        fields = "__all__"
        read_only_fields = (
            "days",
            "status",
            "decision_comment",
            "overlap_warning",
            "interruption_date",
            "original_start_date",
            "original_end_date",
            "allowance_amount",
            "submitted_at",
            "decided_at",
            "created_by",
        )
        extra_kwargs = {"employee": {"required": False}}

    def validate(self, attrs):
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start and end and end < start:
            raise serializers.ValidationError("The end date is before the start date.")
        if self.instance is not None and self.instance.status not in (
            "DRAFT",
            "MODIFICATION",
        ):
            raise serializers.ValidationError(
                "A submitted request is changed by cancellation, interruption or postponement."
            )
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        if request is not None and not can_view_salary(request.user, instance.employee):
            data["allowance_amount"] = None
        return data
