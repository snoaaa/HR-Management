from rest_framework import serializers

from .models import (
    AttendancePeriod,
    Clocking,
    ClockingRegularisation,
    DailyAttendance,
    Mission,
    PublicHoliday,
    ScheduleAssignment,
    ScheduleException,
    WorkingCalendar,
    WorkSchedule,
    WorkScheduleDay,
)


class WorkingCalendarSerializer(serializers.ModelSerializer):
    site_name = serializers.CharField(source="site.name", read_only=True)

    class Meta:
        model = WorkingCalendar
        fields = "__all__"

    def validate_rest_days(self, value):
        if not all(isinstance(d, int) and 0 <= d <= 6 for d in value):
            raise serializers.ValidationError("Rest days are numbers from 0 to 6.")
        return sorted(set(value))


class PublicHolidaySerializer(serializers.ModelSerializer):
    site_name = serializers.CharField(source="site.name", read_only=True)

    class Meta:
        model = PublicHoliday
        fields = "__all__"


class WorkScheduleDaySerializer(serializers.ModelSerializer):
    expected_minutes = serializers.IntegerField(read_only=True)

    class Meta:
        model = WorkScheduleDay
        fields = (
            "id",
            "weekday",
            "start_time",
            "end_time",
            "break_minutes",
            "expected_minutes",
        )


class WorkScheduleSerializer(serializers.ModelSerializer):
    days = WorkScheduleDaySerializer(many=True, required=False)
    weekly_minutes = serializers.IntegerField(read_only=True)

    class Meta:
        model = WorkSchedule
        fields = "__all__"

    def _save_days(self, schedule, days):
        schedule.days.all().delete()
        for day in days:
            WorkScheduleDay.objects.create(schedule=schedule, **day)

    def create(self, validated_data):
        days = validated_data.pop("days", [])
        schedule = WorkSchedule.objects.create(**validated_data)
        self._save_days(schedule, days)
        return schedule

    def update(self, instance, validated_data):
        days = validated_data.pop("days", None)
        instance = super().update(instance, validated_data)
        if days is not None:
            self._save_days(instance, days)
        return instance


class ScheduleAssignmentSerializer(serializers.ModelSerializer):
    schedule_name = serializers.CharField(source="schedule.name", read_only=True)
    target_label = serializers.CharField(read_only=True)

    class Meta:
        model = ScheduleAssignment
        fields = "__all__"

    def validate(self, attrs):
        targets = [attrs.get(k) for k in ("employee", "position", "department", "site")]
        if sum(t is not None for t in targets) > 1:
            raise serializers.ValidationError(
                "Assign the schedule to one target only (employee, position, team or site)."
            )
        end = attrs.get("effective_to")
        if end and end < attrs["effective_from"]:
            raise serializers.ValidationError("The end date is before the start date.")
        return attrs


class ScheduleExceptionSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)

    class Meta:
        model = ScheduleException
        fields = "__all__"


class ClockingSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    source_label = serializers.CharField(source="get_source_display", read_only=True)

    class Meta:
        model = Clocking
        fields = "__all__"
        read_only_fields = (
            "source",
            "is_active",
            "replaced_by",
            "created_by",
            "created_at",
        )


class ClockingRegularisationSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)

    class Meta:
        model = ClockingRegularisation
        fields = "__all__"
        read_only_fields = ("status", "decision_comment", "created_by", "created_at")


class MissionSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)

    class Meta:
        model = Mission
        fields = "__all__"
        read_only_fields = ("created_by",)

    def validate(self, attrs):
        if attrs["end_date"] < attrs["start_date"]:
            raise serializers.ValidationError("The end date is before the start date.")
        return attrs


class DailyAttendanceSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    overtime_minutes = serializers.IntegerField(read_only=True)
    is_unjustified_absence = serializers.BooleanField(read_only=True)

    class Meta:
        model = DailyAttendance
        fields = "__all__"


class AttendancePeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendancePeriod
        fields = "__all__"
        read_only_fields = ("status", "consolidated_at", "locked_at", "summary")
