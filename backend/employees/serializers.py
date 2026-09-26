from rest_framework import serializers

from .models import (EducationAndExperience, Employee, EmployeeDocument,
                     EmployeeHistory, FamilyMember)


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
    class Meta:
        model = EmployeeHistory
        fields = "__all__"


class EmployeeSerializer(serializers.ModelSerializer):
    family_members = FamilyMemberSerializer(many=True, read_only=True)
    documents = EmployeeDocumentSerializer(many=True, read_only=True)
    education_experience = EducationAndExperienceSerializer(many=True, read_only=True)

    class Meta:
        model = Employee
        fields = "__all__"
        read_only_fields = ["matriculation_number"]
