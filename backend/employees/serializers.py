from rest_framework import serializers

from .models import (
    EducationAndExperience,
    Employee,
    EmployeeDocument,
    EmployeeHistory,
    FamilyMember,
)


class FamilyMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = FamilyMember
        fields = "__all__"
        read_only_fields = ["employee"]


class EmployeeDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeDocument
        fields = "__all__"
        read_only_fields = ["employee"]


class EducationAndExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = EducationAndExperience
        fields = "__all__"
        read_only_fields = ["employee"]


class EmployeeHistorySerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.username", read_only=True)

    class Meta:
        model = EmployeeHistory
        fields = "__all__"


class EmployeeSerializer(serializers.ModelSerializer):
    family_members = FamilyMemberSerializer(many=True, read_only=True)
    documents = EmployeeDocumentSerializer(many=True, read_only=True)
    education_experience = EducationAndExperienceSerializer(many=True, read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    position_title = serializers.CharField(source="position.title", read_only=True)
    workplace_name = serializers.CharField(source="workplace.name", read_only=True)
    classification_label = serializers.CharField(
        source="classification.__str__", read_only=True
    )
    full_name = serializers.CharField(read_only=True)
    seniority_years = serializers.FloatField(read_only=True)

    class Meta:
        model = Employee
        fields = "__all__"
        read_only_fields = ["matriculation_number"]


class EmployeeSummarySerializer(serializers.ModelSerializer):
    """Light representation used by the other modules (contracts, leave...)."""

    full_name = serializers.CharField(read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)

    class Meta:
        model = Employee
        fields = (
            "id",
            "matriculation_number",
            "full_name",
            "department",
            "department_name",
            "position",
            "status",
        )
