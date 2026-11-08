"""
M-07 – Timetable and work planning (BN-62 → BN-67).
"""

from django.conf import settings
from django.db import models

from employees.models import Employee
from organisation.models import Department


class Shift(models.Model):
    """A duty period (morning, afternoon, night, weekend duty...)."""

    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    start_time = models.TimeField()
    end_time = models.TimeField(help_text="Before the start time = ends the next day.")
    break_minutes = models.PositiveIntegerField(default=0)
    color = models.CharField(max_length=7, default="#00A09D")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["start_time"]

    def __str__(self):
        return f"{self.name} ({self.start_time:%H:%M}-{self.end_time:%H:%M})"

    @property
    def duration_minutes(self):
        from attendance.services import span_minutes

        return max(0, span_minutes(self.start_time, self.end_time) - self.break_minutes)


class Timetable(models.Model):
    """BN-62: timetable of a team over a chosen period."""

    STATUSES = (("DRAFT", "Draft"), ("PUBLISHED", "Published"))

    name = models.CharField(max_length=150)
    department = models.ForeignKey(
        Department, on_delete=models.CASCADE, related_name="timetables"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUSES, default="DRAFT")
    published_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return self.name


class TimetableEntry(models.Model):
    timetable = models.ForeignKey(
        Timetable, on_delete=models.CASCADE, related_name="entries"
    )
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="timetable_entries"
    )
    date = models.DateField()
    shift = models.ForeignKey(Shift, on_delete=models.PROTECT)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["date", "shift__start_time"]
        unique_together = ("timetable", "employee", "date", "shift")


class ShiftSwapRequest(models.Model):
    """BN-65: exchange or replacement of a shift, approved by the manager."""

    STATUSES = (
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REFUSED", "Refused"),
        ("MODIFICATION", "Modification requested"),
    )

    entry = models.ForeignKey(
        TimetableEntry, on_delete=models.CASCADE, related_name="swap_requests"
    )
    replacement = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="+"
    )
    swap_with = models.ForeignKey(
        TimetableEntry,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="+",
        help_text="Shift of the replacement taken in exchange (empty = simple replacement).",
    )
    reason = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUSES, default="PENDING")
    decision_comment = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    approval_link = "/planning#swaps"

    def approval_requester(self):
        return self.entry.employee

    def approval_summary(self):
        return (
            f"Shift exchange {self.entry.date:%d/%m/%Y} {self.entry.shift.name}: "
            f"{self.entry.employee.full_name} → {self.replacement.full_name}"
        )

    def on_approval_completed(self, user):
        from .services import apply_swap

        apply_swap(self, user)

    def on_approval_refused(self, user, comment):
        self.status = "REFUSED"
        self.decision_comment = comment
        self.save(update_fields=["status", "decision_comment"])

    def on_modification_requested(self, user, comment):
        self.status = "MODIFICATION"
        self.decision_comment = comment
        self.save(update_fields=["status", "decision_comment"])
