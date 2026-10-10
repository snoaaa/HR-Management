"""M-15 – personalised reports (BN-161) and scheduled sending (BN-162)."""

from django.conf import settings
from django.db import models


class SavedReport(models.Model):
    DATASETS = (
        ("EMPLOYEES", "Employees"),
        ("CONTRACTS", "Contracts"),
        ("LEAVE", "Leave requests"),
        ("ATTENDANCE", "Daily attendance"),
        ("PAYSLIPS", "Payslips"),
        ("CAREER", "Career acts"),
    )

    name = models.CharField(max_length=150)
    dataset = models.CharField(max_length=20, choices=DATASETS)
    fields = models.JSONField(default=list, help_text="Columns to show.")
    filters = models.JSONField(default=dict, blank=True, help_text="{field: value}.")
    group_by = models.CharField(max_length=60, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reports"
    )
    shared = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ReportSchedule(models.Model):
    FREQUENCIES = (
        ("DAILY", "Every day"),
        ("WEEKLY", "Every Monday"),
        ("MONTHLY", "First day of the month"),
    )
    FORMATS = (("xlsx", "Excel"), ("pdf", "PDF"), ("csv", "CSV"))

    report = models.ForeignKey(
        SavedReport, on_delete=models.CASCADE, related_name="schedules"
    )
    frequency = models.CharField(max_length=10, choices=FREQUENCIES)
    file_format = models.CharField(max_length=5, choices=FORMATS, default="xlsx")
    recipients = models.TextField(help_text="E-mail addresses separated by commas.")
    last_sent_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def is_due(self, today):
        if self.last_sent_at and self.last_sent_at.date() == today:
            return False
        if self.frequency == "WEEKLY":
            return today.weekday() == 0
        if self.frequency == "MONTHLY":
            return today.day == 1
        return True
