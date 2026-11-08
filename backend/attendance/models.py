"""
Calendars and schedules (M-07: BN-59, BN-60, BN-61; M-01: BN-08)
and attendance / time tracking (M-05: BN-36 → BN-45).
"""

from django.conf import settings
from django.db import models

from employees.models import Employee
from organisation.models import Department, Position, Site

WEEKDAYS = (
    (0, "Monday"),
    (1, "Tuesday"),
    (2, "Wednesday"),
    (3, "Thursday"),
    (4, "Friday"),
    (5, "Saturday"),
    (6, "Sunday"),
)


class WorkingCalendar(models.Model):
    """
    BN-61 / BN-08: working days and weekly rest days per site.
    The calendar without site is the default one of the organisation.
    """

    name = models.CharField(max_length=100)
    site = models.OneToOneField(
        Site,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="working_calendar",
    )
    rest_days = models.JSONField(
        default=list, help_text="Weekly rest days, 0 = Monday … 6 = Sunday."
    )

    def __str__(self):
        return self.name


class PublicHoliday(models.Model):
    """BN-61: public holidays, for every site or for one site only."""

    name = models.CharField(max_length=100)
    date = models.DateField()
    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="public_holidays",
        help_text="Empty = applies to every site.",
    )
    recurring = models.BooleanField(
        default=False, help_text="Same day every year (e.g. 20 May)."
    )

    class Meta:
        ordering = ["date"]

    def __str__(self):
        return f"{self.name} ({self.date})"


class WorkSchedule(models.Model):
    """BN-59: work schedule models."""

    TYPES = (
        ("FIXED", "Fixed hours"),
        ("FLEXIBLE", "Flexible hours"),
        ("SHIFT", "Rotating shifts"),
        ("PART_TIME", "Part time"),
    )

    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=100)
    schedule_type = models.CharField(max_length=20, choices=TYPES, default="FIXED")
    flexible_daily_minutes = models.PositiveIntegerField(
        default=0, help_text="Flexible hours: expected duration per working day."
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    @property
    def weekly_minutes(self):
        if self.schedule_type == "FLEXIBLE":
            return self.flexible_daily_minutes * self.days.count()
        return sum(day.expected_minutes for day in self.days.all())


class WorkScheduleDay(models.Model):
    schedule = models.ForeignKey(
        WorkSchedule, on_delete=models.CASCADE, related_name="days"
    )
    weekday = models.PositiveSmallIntegerField(choices=WEEKDAYS)
    start_time = models.TimeField()
    end_time = models.TimeField()
    break_minutes = models.PositiveIntegerField(default=60)

    class Meta:
        ordering = ["schedule", "weekday"]
        unique_together = ("schedule", "weekday")

    @property
    def expected_minutes(self):
        from .services import span_minutes

        return max(0, span_minutes(self.start_time, self.end_time) - self.break_minutes)


class ScheduleAssignment(models.Model):
    """
    BN-60: a schedule is assigned to an employee, a position, a department
    (team) or a site, from an effective date. The most specific applies.
    """

    schedule = models.ForeignKey(
        WorkSchedule, on_delete=models.PROTECT, related_name="assignments"
    )
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, null=True, blank=True, related_name="+"
    )
    position = models.ForeignKey(
        Position, on_delete=models.CASCADE, null=True, blank=True, related_name="+"
    )
    department = models.ForeignKey(
        Department, on_delete=models.CASCADE, null=True, blank=True, related_name="+"
    )
    site = models.ForeignKey(
        Site, on_delete=models.CASCADE, null=True, blank=True, related_name="+"
    )
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-effective_from"]

    @property
    def target_label(self):
        for name in ("employee", "position", "department", "site"):
            value = getattr(self, name)
            if value is not None:
                return f"{name.capitalize()}: {value}"
        return "Organisation"


class ScheduleException(models.Model):
    """BN-60: exception for one employee on one day (other hours, day off)."""

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="schedule_exceptions"
    )
    date = models.DateField()
    is_day_off = models.BooleanField(default=False)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    break_minutes = models.PositiveIntegerField(default=0)
    reason = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ("employee", "date")


class Clocking(models.Model):
    """BN-36 / BN-37: one entry/exit pair; several per day are allowed."""

    SOURCES = (
        ("MANUAL", "Manual entry (HR)"),
        ("SELF", "Self-recording"),
        ("IMPORT", "Badge / biometric import"),
        ("REGULARISATION", "Regularisation"),
    )

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="clockings"
    )
    date = models.DateField()
    time_in = models.TimeField()
    time_out = models.TimeField(null=True, blank=True)
    source = models.CharField(max_length=20, choices=SOURCES, default="MANUAL")
    # BN-44: a regularised clocking stays visible but is no longer used.
    is_active = models.BooleanField(default=True)
    replaced_by = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date", "time_in"]


class ClockingRegularisation(models.Model):
    """BN-44: correction of a forgotten or erroneous clocking, with approval."""

    STATUSES = (
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REFUSED", "Refused"),
        ("MODIFICATION", "Modification requested"),
    )

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="regularisations"
    )
    clocking = models.ForeignKey(
        Clocking,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="regularisations",
        help_text="Clocking to correct; empty for a forgotten clocking.",
    )
    date = models.DateField()
    time_in = models.TimeField()
    time_out = models.TimeField(null=True, blank=True)
    justification = models.TextField()
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

    approval_link = "/attendance#regularisations"

    def approval_requester(self):
        return self.employee

    def approval_summary(self):
        return (
            f"Clocking regularisation {self.date:%d/%m/%Y} – {self.employee.full_name}"
        )

    def on_approval_completed(self, user):
        from .services import apply_regularisation

        apply_regularisation(self, user)

    def on_approval_refused(self, user, comment):
        self.status = "REFUSED"
        self.decision_comment = comment
        self.save(update_fields=["status", "decision_comment"])

    def on_modification_requested(self, user, comment):
        self.status = "MODIFICATION"
        self.decision_comment = comment
        self.save(update_fields=["status", "decision_comment"])


class Mission(models.Model):
    """BN-43: an employee on mission is not counted as absent."""

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="missions"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    place = models.CharField(max_length=150)
    purpose = models.CharField(max_length=255)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        ordering = ["-start_date"]


class DailyAttendance(models.Model):
    """BN-38 / BN-39: computed day of an employee."""

    STATUSES = (
        ("PRESENT", "Present"),
        ("ABSENT", "Absent"),
        ("LEAVE", "On leave"),
        ("MISSION", "On mission"),
        ("HOLIDAY", "Public holiday"),
        ("REST", "Rest day"),
        ("SUSPENDED", "Contract suspended"),
        ("NOT_EMPLOYED", "Not under contract"),
    )
    OVERTIME_STATUSES = (
        ("NONE", "No overtime"),
        ("PENDING", "Waiting for approval"),
        ("APPROVED", "Approved"),
        ("REFUSED", "Refused"),
    )

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="daily_attendance"
    )
    date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUSES)
    expected_start = models.TimeField(null=True, blank=True)
    expected_end = models.TimeField(null=True, blank=True)
    expected_minutes = models.PositiveIntegerField(default=0)
    worked_minutes = models.PositiveIntegerField(default=0)
    late_minutes = models.PositiveIntegerField(default=0)
    early_departure_minutes = models.PositiveIntegerField(default=0)
    missing_minutes = models.PositiveIntegerField(default=0)
    # BN-39: categories of overtime.
    overtime_day_minutes = models.PositiveIntegerField(default=0)
    overtime_night_minutes = models.PositiveIntegerField(default=0)
    overtime_rest_day_minutes = models.PositiveIntegerField(default=0)
    overtime_holiday_minutes = models.PositiveIntegerField(default=0)
    # BN-40: approval of the overtime by the line manager.
    overtime_status = models.CharField(
        max_length=20, choices=OVERTIME_STATUSES, default="NONE"
    )
    overtime_decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    # BN-41: qualification of absences.
    absence_justified = models.BooleanField(default=False)
    absence_justification = models.CharField(max_length=255, blank=True)
    open_clocking = models.BooleanField(
        default=False, help_text="An entry without exit (forgotten clocking)."
    )
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("employee", "date")
        ordering = ["date"]

    @property
    def overtime_minutes(self):
        return (
            self.overtime_day_minutes
            + self.overtime_night_minutes
            + self.overtime_rest_day_minutes
            + self.overtime_holiday_minutes
        )

    @property
    def is_unjustified_absence(self):
        return self.status == "ABSENT" and not self.absence_justified


class AttendancePeriod(models.Model):
    """BN-45: monthly consolidation, locked once the payroll is validated."""

    STATUSES = (
        ("OPEN", "Open"),
        ("CONSOLIDATED", "Consolidated"),
        ("LOCKED", "Locked"),
    )

    year = models.PositiveSmallIntegerField()
    month = models.PositiveSmallIntegerField()
    status = models.CharField(max_length=20, choices=STATUSES, default="OPEN")
    consolidated_at = models.DateTimeField(null=True, blank=True)
    locked_at = models.DateTimeField(null=True, blank=True)
    summary = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ("year", "month")
        ordering = ["-year", "-month"]

    def __str__(self):
        return f"{self.month:02d}/{self.year}"
