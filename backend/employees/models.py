import datetime

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
    TITLE_CHOICES = (
        ("MR", "Mr"),
        ("MRS", "Mrs"),
        ("MS", "Ms"),
        ("DR", "Dr"),
        ("PR", "Pr"),
    )
    # The ten regions of Cameroon.
    REGION_CHOICES = (
        ("ADAMAWA", "Adamawa"),
        ("CENTRE", "Centre"),
        ("EAST", "East"),
        ("FAR_NORTH", "Far North"),
        ("LITTORAL", "Littoral"),
        ("NORTH", "North"),
        ("NORTH_WEST", "North-West"),
        ("WEST", "West"),
        ("SOUTH", "South"),
        ("SOUTH_WEST", "South-West"),
    )
    EDUCATION_CHOICES = (
        ("NONE", "No diploma"),
        ("CEP", "CEP / FSLC (primary)"),
        ("BEPC", "BEPC / GCE O Level"),
        ("PROBATOIRE", "Probatoire / CAP"),
        ("BAC", "Baccalauréat / GCE A Level"),
        ("BTS", "BTS / HND (Bac+2)"),
        ("LICENCE", "Licence / Bachelor (Bac+3)"),
        ("MASTER", "Master / Engineer (Bac+5)"),
        ("DOCTORATE", "Doctorate"),
    )
    BLOOD_GROUP_CHOICES = tuple(
        (g, g) for g in ("A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-")
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
    title = models.CharField(max_length=5, choices=TITLE_CHOICES, blank=True)
    surname = models.CharField(max_length=150)
    maiden_name = models.CharField(max_length=150, blank=True)
    given_names = models.CharField(max_length=150)
    date_of_birth = models.DateField()
    place_of_birth = models.CharField(max_length=150)
    sex = models.CharField(max_length=1, choices=SEX_CHOICES)
    nationality = models.CharField(max_length=100)
    marital_status = models.CharField(max_length=20, choices=MARITAL_STATUS_CHOICES)
    identity_document_type = models.CharField(max_length=100)
    identity_document_number = models.CharField(max_length=100)
    identity_document_validity = models.DateField(blank=True, null=True)
    identity_document_issue_date = models.DateField(blank=True, null=True)
    identity_document_issue_place = models.CharField(max_length=150, blank=True)
    blood_group = models.CharField(
        max_length=3, choices=BLOOD_GROUP_CHOICES, blank=True
    )
    has_disability = models.BooleanField(
        default=False, help_text="Recognised disability (adapted work station)."
    )
    education_level = models.CharField(
        max_length=20, choices=EDUCATION_CHOICES, blank=True
    )
    spoken_languages = models.CharField(
        max_length=150, blank=True, help_text="For example: French, English."
    )
    photograph = models.ImageField(upload_to="employee_photos/", blank=True, null=True)

    # Contact Details (BN-12)
    address = models.TextField()
    city = models.CharField(max_length=100, blank=True)
    region = models.CharField(max_length=20, choices=REGION_CHOICES, blank=True)
    postal_box = models.CharField("P.O. Box", max_length=50, blank=True)
    professional_phone = models.CharField(max_length=50, blank=True)
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
    cnps_registration_date = models.DateField(
        "CNPS registration date", blank=True, null=True
    )
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

    @property
    def full_name(self):
        return f"{self.given_names} {self.surname}"

    @property
    def age(self):
        birth = self.date_of_birth
        if not birth:
            return None
        if isinstance(birth, str):
            birth = datetime.date.fromisoformat(birth)
        today = timezone.now().date()
        return (
            today.year
            - birth.year
            - ((today.month, today.day) < (birth.month, birth.day))
        )

    @property
    def number_of_children(self):
        if not self.pk:
            return 0
        return self.family_members.filter(relationship="CHILD").count()

    @property
    def seniority_years(self):
        """BN-16: seniority computed from the date of hire."""
        if not self.date_of_hire:
            return 0
        hire = self.date_of_hire
        if isinstance(hire, str):
            hire = datetime.date.fromisoformat(hire)
        return round((timezone.now().date() - hire).days / 365.25, 2)

    def save(self, *args, **kwargs):
        if not self.matriculation_number:
            # BN-10: unique, non-reusable number following a configurable format.
            self.matriculation_number = next_matriculation_number()
        super().save(*args, **kwargs)


def next_matriculation_number():
    """
    The format comes from the setting MATRICULATION_FORMAT, e.g.
    "EMP-{year}-{seq:03d}". The sequence is stored in a counter so that a
    number is never reused, even if a record were removed.
    """
    from django.db import transaction

    from core.models import Sequence, get_setting

    year = timezone.now().year
    fmt = get_setting("MATRICULATION_FORMAT", "EMP-{year}-{seq:03d}")
    with transaction.atomic():
        seq = Sequence.next_value(f"matriculation-{year}")
        number = fmt.format(year=year, seq=seq)
        while Employee.objects.filter(matriculation_number=number).exists():
            seq = Sequence.next_value(f"matriculation-{year}")
            number = fmt.format(year=year, seq=seq)
    return number


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


class CorrectionRequest(models.Model):
    """BN-148: the employee asks for the correction of an erroneous item."""

    # Items of the record that the employee may ask to correct.
    FIELDS = (
        ("address", "Address"),
        ("phone_number", "Telephone"),
        ("phone_number_2", "Second telephone"),
        ("personal_email", "Personal e-mail"),
        ("marital_status", "Marital status"),
        ("emergency_contact_name", "Emergency contact"),
        ("emergency_contact_number", "Emergency contact number"),
        ("emergency_contact_relationship", "Emergency contact relationship"),
        ("identity_document_number", "Identity document number"),
        ("identity_document_validity", "Identity document validity"),
        ("bank_name", "Bank"),
        ("bank_branch", "Bank branch"),
        ("account_number", "Account number"),
        ("bank_key", "Bank key"),
        ("place_of_birth", "Place of birth"),
        ("city", "City"),
        ("region", "Region"),
        ("postal_box", "P.O. Box"),
        ("maiden_name", "Maiden name"),
        ("blood_group", "Blood group"),
        ("spoken_languages", "Spoken languages"),
        ("nationality", "Nationality"),
        ("social_insurance_number", "Social insurance number"),
        ("tax_identification_number", "Tax identification number"),
    )
    STATUSES = (
        ("PENDING", "Pending"),
        ("APPROVED", "Applied"),
        ("REFUSED", "Refused"),
        ("MODIFICATION", "Modification requested"),
    )

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="correction_requests"
    )
    field_name = models.CharField(max_length=50, choices=FIELDS)
    current_value = models.TextField(blank=True)
    requested_value = models.TextField()
    reason = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUSES, default="PENDING")
    decision_comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    approval_link = "/my/profile"

    def approval_requester(self):
        return self.employee

    def approval_summary(self):
        return f"Correction of {self.get_field_name_display().lower()}: {self.employee.full_name}"

    def on_approval_completed(self, user):
        previous = getattr(self.employee, self.field_name)
        value = self.requested_value
        if self.field_name == "identity_document_validity":
            value = datetime.date.fromisoformat(value) if value else None
        setattr(self.employee, self.field_name, value)
        self.employee.save(update_fields=[self.field_name])
        EmployeeHistory.objects.create(
            employee=self.employee,
            author=user,
            field_name=self.field_name,
            previous_value="" if previous is None else str(previous),
            new_value=f"{self.requested_value} (correction requested by the employee)",
        )
        self.status = "APPROVED"
        self.save(update_fields=["status"])

    def on_approval_refused(self, user, comment):
        self.status = "REFUSED"
        self.decision_comment = comment
        self.save(update_fields=["status", "decision_comment"])

    def on_modification_requested(self, user, comment):
        self.status = "MODIFICATION"
        self.decision_comment = comment
        self.save(update_fields=["status", "decision_comment"])
