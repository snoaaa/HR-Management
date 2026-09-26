from django.contrib import admin

from .models import (EducationAndExperience, Employee, EmployeeDocument,
                     EmployeeHistory, FamilyMember)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = (
        "matriculation_number",
        "surname",
        "given_names",
        "status",
        "department",
        "position",
    )
    list_filter = ("status", "department", "contract_type", "workplace")
    search_fields = (
        "matriculation_number",
        "surname",
        "given_names",
        "personal_email",
        "professional_email",
    )


@admin.register(FamilyMember)
class FamilyMemberAdmin(admin.ModelAdmin):
    list_display = ("employee", "name", "relationship")
    list_filter = ("relationship",)


@admin.register(EmployeeDocument)
class EmployeeDocumentAdmin(admin.ModelAdmin):
    list_display = ("employee", "document_type", "name", "validity_date")
    list_filter = ("document_type",)


@admin.register(EducationAndExperience)
class EducationAndExperienceAdmin(admin.ModelAdmin):
    list_display = ("employee", "entry_type", "title", "institution_or_company")
    list_filter = ("entry_type",)


@admin.register(EmployeeHistory)
class EmployeeHistoryAdmin(admin.ModelAdmin):
    list_display = ("employee", "author", "field_name", "modification_date")
    list_filter = ("field_name", "modification_date")
    search_fields = (
        "employee__matriculation_number",
        "employee__surname",
        "field_name",
    )
    readonly_fields = (
        "employee",
        "author",
        "field_name",
        "previous_value",
        "new_value",
        "modification_date",
    )
