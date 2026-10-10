"""
M-08 – Career management: promotion, transfer, discipline, departure
(BN-68 → BN-76), and history of the organisation structure (BN-06).
"""

from django.conf import settings
from django.db import models

from employees.models import Employee
from organisation.models import Classification, CostCentre, Department, Position, Site


class CareerAct(models.Model):
    TYPES = (
        ("PROMOTION", "Promotion"),
        ("TRANSFER", "Transfer / affectation"),
        ("SALARY_REVISION", "Salary revision"),
        ("TEMPORARY_ASSIGNMENT", "Temporary assignment"),
        ("ACTING", "Acting position"),
        ("SECONDMENT", "Secondment"),
        ("DISCIPLINARY", "Disciplinary measure"),
        ("DEPARTURE", "Departure"),
    )
    STATUSES = (
        ("DRAFT", "Draft"),
        ("SUBMITTED", "Waiting for approval"),
        ("MODIFICATION", "Modification requested"),
        ("APPROVED", "Approved"),
        ("APPLIED", "Applied"),
        ("ENDED", "Ended (returned to original situation)"),
        ("REFUSED", "Refused"),
        ("CANCELLED", "Cancelled"),
    )
    DISCIPLINARY = (
        ("WARNING", "Warning"),
        ("REPRIMAND", "Reprimand"),
        ("SUSPENSION", "Suspension without pay"),
        ("DISMISSAL", "Dismissal"),
    )
    DEPARTURE_REASONS = (
        ("RESIGNATION", "Resignation"),
        ("DISMISSAL", "Dismissal"),
        ("END_OF_CONTRACT", "End of contract"),
        ("RETIREMENT", "Retirement"),
        ("DEATH", "Death"),
        ("MUTUAL", "Mutual agreement"),
    )
    SALARY_SCOPES = (
        ("INDIVIDUAL", "Individual increase"),
        ("GENERAL", "General increase"),
    )

    employee = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name="career_acts"
    )
    act_type = models.CharField(max_length=30, choices=TYPES)
    status = models.CharField(max_length=20, choices=STATUSES, default="DRAFT")
    effective_date = models.DateField()
    end_date = models.DateField(
        null=True, blank=True, help_text="Temporary acts: automatic return."
    )
    reason = models.TextField()
    decision_reference = models.CharField(max_length=60, blank=True)

    # New situation (BN-68, BN-69, BN-70)
    new_position = models.ForeignKey(
        Position, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    new_classification = models.ForeignKey(
        Classification,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    new_department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    new_workplace = models.ForeignKey(
        Site, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    # Salary (BN-68 automatic effect, BN-71 revisions)
    new_base_salary = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    increase_percent = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    salary_scope = models.CharField(
        max_length=20, choices=SALARY_SCOPES, default="INDIVIDUAL"
    )
    bonus_element = models.CharField(
        max_length=40, blank=True, help_text="Bonus revised (element code)."
    )
    bonus_value = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    # Discipline (BN-72)
    disciplinary_measure = models.CharField(
        max_length=20, choices=DISCIPLINARY, blank=True
    )
    suspension_days = models.PositiveSmallIntegerField(null=True, blank=True)
    document = models.FileField(upload_to="career_documents/", null=True, blank=True)
    # Departure (BN-73)
    departure_reason = models.CharField(
        max_length=20, choices=DEPARTURE_REASONS, blank=True
    )
    notice_worked = models.BooleanField(default=True)

    previous_situation = models.JSONField(default=dict, blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    batch = models.CharField(
        max_length=40, blank=True, help_text="Acts created by one general increase."
    )
    decision_comment = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-effective_date", "-id"]

    def __str__(self):
        return f"{self.get_act_type_display()} – {self.employee.full_name} ({self.effective_date})"

    @property
    def affects_payroll(self):
        if self.act_type == "DISCIPLINARY":
            return self.disciplinary_measure in ("SUSPENSION", "DISMISSAL")
        return self.act_type in (
            "PROMOTION",
            "SALARY_REVISION",
            "TRANSFER",
            "TEMPORARY_ASSIGNMENT",
            "ACTING",
            "SECONDMENT",
            "DEPARTURE",
        )

    # Workflow protocol (BN-76) -------------------------------------------
    @property
    def approval_link(self):
        return f"/careers/{self.id}"

    def approval_requester(self):
        return self.employee

    def approval_summary(self):
        return f"{self.get_act_type_display()}: {self.employee.full_name} from {self.effective_date:%d/%m/%Y}"

    def on_approval_completed(self, user):
        from .services import approve

        approve(self, user)

    def on_approval_refused(self, user, comment):
        self.status = "REFUSED"
        self.decision_comment = comment
        self.save(update_fields=["status", "decision_comment"])

    def on_modification_requested(self, user, comment):
        self.status = "MODIFICATION"
        self.decision_comment = comment
        self.save(update_fields=["status", "decision_comment"])


class DepartmentVersion(models.Model):
    """BN-06: every modification of the structure, with its effective date."""

    # The history survives the deletion of the unit (BN-06).
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="versions",
    )
    department_ref = models.PositiveIntegerField(db_index=True)
    effective_from = models.DateField()
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50)
    unit_type = models.CharField(max_length=20)
    parent = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    site = models.ForeignKey(
        Site, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    cost_centre = models.ForeignKey(
        CostCentre, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    is_deleted = models.BooleanField(default=False)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["department_ref", "-effective_from", "-id"]
