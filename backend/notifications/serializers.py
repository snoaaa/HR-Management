from rest_framework import serializers

from .models import (
    ApprovalCircuit,
    ApprovalLevel,
    ApprovalTask,
    Notification,
    NotificationPreference,
)


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ("id", "title", "message", "link", "category", "is_read", "created_at")
        read_only_fields = ("id", "title", "message", "link", "category", "created_at")


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = ("in_app", "email")


class ApprovalLevelSerializer(serializers.ModelSerializer):
    substitute_name = serializers.CharField(
        source="substitute.username", read_only=True
    )

    class Meta:
        model = ApprovalLevel
        fields = ("id", "order", "approver", "substitute", "substitute_name")


class ApprovalCircuitSerializer(serializers.ModelSerializer):
    levels = ApprovalLevelSerializer(many=True)

    class Meta:
        model = ApprovalCircuit
        fields = ("id", "request_type", "name", "levels")

    def _save_levels(self, circuit, levels):
        circuit.levels.all().delete()
        for index, level in enumerate(sorted(levels, key=lambda lv: lv["order"])):
            ApprovalLevel.objects.create(
                circuit=circuit,
                order=index + 1,
                approver=level["approver"],
                substitute=level.get("substitute"),
            )

    def create(self, validated_data):
        levels = validated_data.pop("levels", [])
        circuit = ApprovalCircuit.objects.create(**validated_data)
        self._save_levels(circuit, levels)
        return circuit

    def update(self, instance, validated_data):
        levels = validated_data.pop("levels", None)
        instance = super().update(instance, validated_data)
        if levels is not None:
            self._save_levels(instance, levels)
        return instance


class ApprovalTaskSerializer(serializers.ModelSerializer):
    approver_name = serializers.CharField(
        source="approver_user.get_full_name", read_only=True
    )
    decided_by_name = serializers.CharField(
        source="decided_by.username", read_only=True
    )
    link = serializers.SerializerMethodField()

    class Meta:
        model = ApprovalTask
        fields = (
            "id",
            "request_type",
            "object_id",
            "level",
            "approver_user",
            "approver_name",
            "approver_role",
            "summary",
            "status",
            "comment",
            "decided_by_name",
            "decided_at",
            "created_at",
            "link",
        )

    def get_link(self, task):
        target = task.target
        return getattr(target, "approval_link", "") if target else ""
