from django.conf import settings
from django.db import models
from django.utils import timezone

from organisation.models import Classification, Department, Position, Site


class Employee(models.Model):
    """
    BN-09: Create, consult, modify, deactivate and archive an employee record.
    BN-10 to BN-16: Comprehensive employee data.
    """

    STATUS_CHOICES = (
        ("ACTIVE", "Active"),
        ("INACTIVE", "Inactive"),
        ("ARCHIVED", "Archived"),
    )
    SEX_CHOICES = (
        ("M", "Male"),
        ("F", "Female"),
    )
    MARITAL_STATUS_CHOICES = (
        ("SINGLE", "Single"),
        ("MARRIED", "Married"),
        ("DIVORCED", "Divorced"),
        ("WIDOWED", "Widowed"),
    )
    PAYMENT_METHOD_CHOICES = (
        ("TRANSFER", "Bank Transfer"),
        ("CHEQUE", "Cheque"),
        ("CASH", "Cash"),
    )
    CONTRACT_TYPE_CHOICES = (
        ("PERMANENT", "Permanent Contract"),
        ("FIXED_TERM", "Fixed-Term Contract"),
        ("INTERNSHIP", "Internship Agreement"),
        ("TEMPORARY", "Temporary Work"),
        ("APPRENTICESHIP", "Apprenticeship"),
        ("SERVICE", "Service Contract"),
    )

    # User link (optional, for login)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="employee_profile",
    )

    # Core
    matriculation_number = models.CharField(max_length=50, unique=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="ACTIVE")

    # Civil Identity (BN-11)
    surname = models.CharField(max_length=150)
    given_names = models.CharField(max_length=150)
    date_of_birth = models.DateField()
    place_of_birth = models.CharField(max_length=150)
    sex = models.CharField(max_length=1, choices=SEX_CHOICES)
    nationality = models.CharField(max_length=100)
    marital_status = models.CharField(max_length=20, choices=MARITAL_STATUS_CHOICES)
    identity_document_type = models.CharField(max_length=100)
    identity_document_number = models.CharField(max_length=100)
    identity_document_validity = models.DateField(blank=True, null=True)
    photograph = models.ImageField(upload_to="employee_photos/", blank=True, null=True)

    # Contact Details (BN-12)
    address = models.TextField()
    phone_number = models.CharField(max_length=50)
    phone_number_2 = models.CharField(max_length=50, blank=True, null=True)
    phone_number_3 = models.CharField(max_length=50, blank=True, null=True)
    personal_email = models.EmailField(blank=True, null=True)
    professional_email = models.EmailField(blank=True, null=True)

    emergency_contact_name = models.CharField(max_length=150)
    emergency_contact_number = models.CharField(max_length=50)
    emergency_contact_relationship = models.CharField(
        max_length=100, blank=True, null=True
    )

    emergency_contact_name_2 = models.CharField(max_length=150, blank=True, null=True)
    emergency_contact_number_2 = models.CharField(max_length=50, blank=True, null=True)
    emergency_contact_relationship_2 = models.CharField(
        max_length=100, blank=True, null=True
    )

    emergency_contact_name_3 = models.CharField(max_length=150, blank=True, null=True)
    emergency_contact_number_3 = models.CharField(max_length=50, blank=True, null=True)
    emergency_contact_relationship_3 = models.CharField(
        max_length=100, blank=True, null=True
    )

    # Social & Tax (BN-14)
    social_insurance_number = models.CharField(max_length=100, blank=True, null=True)
    tax_identification_number = models.CharField(max_length=100, blank=True, null=True)
    professional_identification = models.CharField(
        max_length=100, blank=True, null=True
    )

    # Bank Details (BN-15)
    bank_name = models.CharField(max_length=150, blank=True, null=True)
    bank_branch = models.CharField(max_length=150, blank=True, null=True)
    account_number = models.CharField(max_length=100, blank=True, null=True)
    bank_key = models.CharField(max_length=10, blank=True, null=True)
    method_of_payment = models.CharField(
        max_length=20, choices=PAYMENT_METHOD_CHOICES, default="TRANSFER"
    )

    # Administrative Situation (BN-16)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="employees",
    )
    position = models.ForeignKey(
        Position,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="employees",
    )
    classification = models.ForeignKey(
        Classification,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="employees",
    )
    contract_type = models.CharField(max_length=20, choices=CONTRACT_TYPE_CHOICES)
    date_of_hire = models.DateField()
    workplace = models.ForeignKey(
        Site, on_delete=models.SET_NULL, blank=True, null=True, related_name="employees"
    )

    def __str__(self):
        return f"[{self.matriculation_number}] {self.surname} {self.given_names}"

    def save(self, *args, **kwargs):
        if not self.matriculation_number:
            # BN-10: Auto-allocate unique matriculation number
            year = timezone.now().year
            last_employee = (
                Employee.objects.filter(matriculation_number__startswith=f"EMP-{year}")
                .order_by("id")
                .last()
            )
            if last_employee and "-" in last_employee.matriculation_number:
                try:
                    last_id = int(last_employee.matriculation_number.split("-")[-1])
                    new_id = last_id + 1
                except ValueError:
                    new_id = 1
            else:
                new_id = 1
            self.matriculation_number = f"EMP-{year}-{new_id:03d}"
        super().save(*args, **kwargs)


class FamilyMember(models.Model):
    """
    BN-13: Record the family situation and dependent children.
    """

    RELATIONSHIP_CHOICES = (
        ("SPOUSE", "Spouse"),
        ("CHILD", "Child"),
        ("OTHER", "Other"),
    )
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="family_members"
    )
    name = models.CharField(max_length=150)
    date_of_birth = models.DateField()
    relationship = models.CharField(max_length=20, choices=RELATIONSHIP_CHOICES)

    def __str__(self):
        return f"{self.name} ({self.get_relationship_display()})"


class EmployeeDocument(models.Model):
    """
    BN-17: Attach scanned documents to the record.
    """

    DOCUMENT_TYPES = (
        ("ID", "Identity Document"),
        ("DIPLOMA", "Diploma/Certificate"),
        ("CONTRACT", "Contract"),
        ("MEDICAL", "Medical Certificate"),
        ("DISCIPLINARY", "Disciplinary Letter"),
        ("OTHER", "Other"),
    )
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="documents"
    )
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    name = models.CharField(max_length=150)
    file = models.FileField(upload_to="employee_documents/")
    validity_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"{self.employee.matriculation_number} - {self.name}"


class EducationAndExperience(models.Model):
    """
    BN-18: Record the education, diplomas, professional experience and languages.
    """

    ENTRY_TYPES = (
        ("EDUCATION", "Education/Diploma"),
        ("EXPERIENCE", "Professional Experience"),
        ("LANGUAGE", "Language"),
    )
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="education_experience"
    )
    entry_type = models.CharField(max_length=20, choices=ENTRY_TYPES)
    title = models.CharField(max_length=200)
    institution_or_company = models.CharField(max_length=200)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.title} ({self.get_entry_type_display()})"


class EmployeeHistory(models.Model):
    """
    BN-21: Keep the complete history of every modification of the record.
    """

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="history"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    modification_date = models.DateTimeField(auto_now_add=True)
    field_name = models.CharField(max_length=100)
    previous_value = models.TextField(blank=True, null=True)
    new_value = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Mod: {self.employee.matriculation_number} - {self.field_name} at {self.modification_date}"
