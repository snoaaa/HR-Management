"""M-10 – Performance evaluation (BN-82 → BN-86)."""

from decimal import Decimal

from django.conf import settings
from django.db import models

from employees.models import Employee
from organisation.models import Department


class Campaign(models.Model):
    """BN-82: evaluation campaign with its period, population and form."""

    STATUSES = (("DRAFT", "Draft"), ("OPEN", "Open"), ("CLOSED", "Closed"))

    name = models.CharField(max_length=150)
    year = models.PositiveSmallIntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    departments = models.ManyToManyField(
        Department, blank=True, help_text="Empty = whole organisation."
    )
    criteria = models.JSONField(
        default=list,
        help_text='Evaluation form: [{"code": "QUALITY", "label": "Quality of work", "weight": 2}].',
    )
    scale_max = models.PositiveSmallIntegerField(default=5)
    objectives_weight = models.PositiveSmallIntegerField(
        default=50, help_text="Share of the objectives in the final score (%)."
    )
    status = models.CharField(max_length=10, choices=STATUSES, default="DRAFT")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )

    class Meta:
        ordering = ["-year", "-start_date"]

    def __str__(self):
        return self.name


class Evaluation(models.Model):
    """BN-83 / BN-84: individual evaluation."""

    STATUSES = (
        ("SELF_ASSESSMENT", "Waiting for the self-evaluation"),
        ("MANAGER_ASSESSMENT", "Waiting for the manager"),
        ("COMPLETED", "Completed"),
        ("VALIDATED", "Validated by HR"),
    )
    PROPOSALS = (
        ("NONE", "No proposal"),
        ("PROMOTION", "Promotion"),
        ("TRAINING", "Training"),
        ("BONUS", "Performance bonus"),
    )

    campaign = models.ForeignKey(
        Campaign, on_delete=models.CASCADE, related_name="evaluations"
    )
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="evaluations"
    )
    evaluator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="evaluations_to_do",
    )
    status = models.CharField(
        max_length=20, choices=STATUSES, default="SELF_ASSESSMENT"
    )
    self_scores = models.JSONField(default=dict, blank=True)
    self_comment = models.TextField(blank=True)
    manager_scores = models.JSONField(default=dict, blank=True)
    manager_comment = models.TextField(blank=True)
    strengths = models.TextField(blank=True)
    improvements = models.TextField(blank=True)
    actions_decided = models.TextField(blank=True)
    final_score = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    proposal = models.CharField(max_length=20, choices=PROPOSALS, default="NONE")
    bonus_amount = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    training_subject = models.CharField(max_length=200, blank=True)
    proposal_applied = models.BooleanField(default=False)
    validated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["campaign", "employee__surname"]
        unique_together = ("campaign", "employee")

    def __str__(self):
        return f"{self.campaign} – {self.employee.full_name}"


class Objective(models.Model):
    """BN-83: individual objective and its achievement."""

    evaluation = models.ForeignKey(
        Evaluation, on_delete=models.CASCADE, related_name="objectives"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    weight = models.PositiveSmallIntegerField(default=1)
    target = models.CharField(max_length=200, blank=True)
    achievement_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="0 to 100 % (and more if exceeded).",
    )
    comment = models.TextField(blank=True)

    class Meta:
        ordering = ["id"]

    @property
    def score(self):
        return Decimal(self.achievement_percent or 0)
