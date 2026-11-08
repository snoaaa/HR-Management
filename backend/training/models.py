"""M-09 – Training and skills (BN-77 → BN-81)."""

from decimal import Decimal

from django.conf import settings
from django.db import models

from employees.models import Employee
from organisation.models import Department, Position

LEVELS = [(i, str(i)) for i in range(1, 6)]


class Skill(models.Model):
    """BN-77: repository of skills."""

    name = models.CharField(max_length=150, unique=True)
    category = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return self.name


class PositionSkill(models.Model):
    """BN-77: skills profile required by a position."""

    position = models.ForeignKey(
        Position, on_delete=models.CASCADE, related_name="required_skill_profile"
    )
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="+")
    required_level = models.PositiveSmallIntegerField(choices=LEVELS, default=3)

    class Meta:
        unique_together = ("position", "skill")


class EmployeeSkill(models.Model):
    """BN-77: skills profile of an employee."""

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="skills"
    )
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="+")
    level = models.PositiveSmallIntegerField(choices=LEVELS, default=1)
    assessed_at = models.DateField()
    source = models.CharField(max_length=60, blank=True)

    class Meta:
        unique_together = ("employee", "skill")


class TrainingPlan(models.Model):
    """BN-78: annual training plan and its budget."""

    STATUSES = (("DRAFT", "Draft"), ("APPROVED", "Approved"))

    year = models.PositiveSmallIntegerField(unique=True)
    budget = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=STATUSES, default="DRAFT")
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-year"]

    def __str__(self):
        return f"Training plan {self.year}"


class TrainingNeed(models.Model):
    """BN-78: training needs collected from managers, employees and evaluations."""

    PRIORITIES = (("LOW", "Low"), ("MEDIUM", "Medium"), ("HIGH", "High"))
    ORIGINS = (
        ("MANAGER", "Manager"),
        ("EMPLOYEE", "Employee"),
        ("EVALUATION", "Evaluation"),
        ("HR", "HR"),
    )
    STATUSES = (
        ("IDENTIFIED", "Identified"),
        ("PLANNED", "Planned"),
        ("DONE", "Done"),
        ("REJECTED", "Rejected"),
    )

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, null=True, blank=True, related_name="+"
    )
    department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    skill = models.ForeignKey(
        Skill, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    subject = models.CharField(max_length=200)
    priority = models.CharField(max_length=10, choices=PRIORITIES, default="MEDIUM")
    year = models.PositiveSmallIntegerField()
    estimated_cost = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    origin = models.CharField(max_length=20, choices=ORIGINS, default="MANAGER")
    status = models.CharField(max_length=20, choices=STATUSES, default="IDENTIFIED")
    session = models.ForeignKey(
        "TrainingSession",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="needs",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-year", "-created_at"]


class TrainingSession(models.Model):
    """BN-79: training session."""

    STATUSES = (
        ("PLANNED", "Planned"),
        ("ONGOING", "Ongoing"),
        ("DONE", "Done"),
        ("CANCELLED", "Cancelled"),
    )

    plan = models.ForeignKey(
        TrainingPlan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sessions",
    )
    title = models.CharField(max_length=200)
    organiser = models.CharField(max_length=150)
    trainer = models.CharField(max_length=150, blank=True)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    place = models.CharField(max_length=150)
    cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    max_participants = models.PositiveSmallIntegerField(null=True, blank=True)
    skills = models.ManyToManyField(Skill, blank=True, related_name="sessions")
    certificate_validity_months = models.PositiveSmallIntegerField(
        null=True, blank=True
    )
    status = models.CharField(max_length=10, choices=STATUSES, default="PLANNED")

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return self.title

    @property
    def cost_per_participant(self):
        count = self.participations.exclude(status="CANCELLED").count()
        return (self.cost / count).quantize(Decimal("0.01")) if count else self.cost


class Participation(models.Model):
    """BN-79 / BN-80 / BN-81: participant, attendance, result, certificate, evaluation."""

    STATUSES = (
        ("REGISTERED", "Registered"),
        ("ATTENDED", "Attended"),
        ("ABSENT", "Absent"),
        ("CANCELLED", "Cancelled"),
    )
    RESULTS = (("PENDING", "Pending"), ("PASSED", "Passed"), ("FAILED", "Failed"))

    session = models.ForeignKey(
        TrainingSession, on_delete=models.CASCADE, related_name="participations"
    )
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="trainings"
    )
    status = models.CharField(max_length=20, choices=STATUSES, default="REGISTERED")
    result = models.CharField(max_length=10, choices=RESULTS, default="PENDING")
    certificate = models.FileField(
        upload_to="training_certificates/", null=True, blank=True
    )
    certificate_validity = models.DateField(null=True, blank=True)
    satisfaction = models.PositiveSmallIntegerField(
        choices=LEVELS, null=True, blank=True
    )
    effectiveness = models.PositiveSmallIntegerField(
        choices=LEVELS,
        null=True,
        blank=True,
        help_text="Effect observed by the manager (BN-81).",
    )
    comment = models.TextField(blank=True)

    class Meta:
        unique_together = ("session", "employee")
