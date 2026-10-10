"""M-03 – Recruitment and onboarding (BN-22 → BN-27)."""

from django.conf import settings
from django.db import models

from employees.models import Employee
from organisation.models import Department, Position, Site


class RecruitmentNeed(models.Model):
    """BN-22: recruitment need attached to a position of the organisation chart."""

    STATUSES = (
        ("DRAFT", "Draft"),
        ("SUBMITTED", "Waiting for approval"),
        ("MODIFICATION", "Modification requested"),
        ("APPROVED", "Approved"),
        ("REFUSED", "Refused"),
        ("FILLED", "Filled"),
    )

    position = models.ForeignKey(
        Position, on_delete=models.PROTECT, related_name="recruitment_needs"
    )
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, related_name="recruitment_needs"
    )
    number_of_posts = models.PositiveSmallIntegerField(default=1)
    contract_type = models.CharField(
        max_length=20, choices=Employee.CONTRACT_TYPE_CHOICES, default="PERMANENT"
    )
    justification = models.TextField()
    desired_start = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUSES, default="DRAFT")
    decision_comment = models.TextField(blank=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.position.title} – {self.department.name}"

    @property
    def approval_link(self):
        return "/recruitment#needs"

    def approval_requester(self):
        return Employee.objects.filter(user=self.requested_by).first()

    def approval_summary(self):
        return f"Recruitment: {self.number_of_posts} × {self.position.title} ({self.department.name})"

    def on_approval_completed(self, user):
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


class JobOffer(models.Model):
    """BN-23: job offer published to receive applications."""

    STATUSES = (("DRAFT", "Draft"), ("PUBLISHED", "Published"), ("CLOSED", "Closed"))

    need = models.ForeignKey(
        RecruitmentNeed,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="offers",
    )
    title = models.CharField(max_length=200)
    position = models.ForeignKey(Position, on_delete=models.PROTECT, related_name="+")
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, related_name="+"
    )
    location = models.ForeignKey(
        Site, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    contract_type = models.CharField(
        max_length=20, choices=Employee.CONTRACT_TYPE_CHOICES, default="PERMANENT"
    )
    description = models.TextField()
    requirements = models.TextField(blank=True)
    closing_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUSES, default="DRAFT")
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-published_at", "-id"]

    def __str__(self):
        return self.title


class Application(models.Model):
    """BN-23 / BN-24 / BN-27: application and its stage."""

    STAGES = (
        ("RECEIVED", "Received"),
        ("PRESELECTED", "Pre-selected"),
        ("INTERVIEW", "Interview"),
        ("TEST", "Test"),
        ("SELECTED", "Selected"),
        ("REJECTED", "Rejected"),
        ("HIRED", "Hired"),
    )

    offer = models.ForeignKey(
        JobOffer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applications",
    )
    surname = models.CharField(max_length=150)
    given_names = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=50)
    date_of_birth = models.DateField(null=True, blank=True)
    place_of_birth = models.CharField(max_length=150, blank=True)
    sex = models.CharField(max_length=1, choices=Employee.SEX_CHOICES, blank=True)
    nationality = models.CharField(max_length=100, blank=True)
    marital_status = models.CharField(
        max_length=20, choices=Employee.MARITAL_STATUS_CHOICES, blank=True
    )
    identity_document_type = models.CharField(max_length=100, blank=True)
    identity_document_number = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    cv = models.FileField(upload_to="applications/", null=True, blank=True)
    cover_letter = models.FileField(upload_to="applications/", null=True, blank=True)
    motivation = models.TextField(blank=True)
    stage = models.CharField(max_length=20, choices=STAGES, default="RECEIVED")
    score = models.PositiveSmallIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)
    in_pool = models.BooleanField(
        default=False, help_text="BN-27: kept for future needs."
    )
    source = models.CharField(max_length=20, default="PUBLIC")
    employee = models.OneToOneField(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="application",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def full_name(self):
        return f"{self.given_names} {self.surname}"


class ApplicationEvent(models.Model):
    """BN-24: every change of stage is kept."""

    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, related_name="events"
    )
    stage = models.CharField(max_length=20)
    comment = models.TextField(blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["at"]


class OnboardingTask(models.Model):
    """BN-26: onboarding checklist with a person responsible for each item."""

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="onboarding_tasks"
    )
    title = models.CharField(max_length=200)
    responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="onboarding_tasks",
    )
    due_date = models.DateField(null=True, blank=True)
    done = models.BooleanField(default=False)
    done_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["done", "due_date", "id"]
