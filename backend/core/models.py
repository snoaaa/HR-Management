from django.db import models, transaction

# Default values of the configurable settings (BN-178). They are copied into
# the Setting table by the seed command and can then be edited without code.
DEFAULT_SETTINGS = {
    "MATRICULATION_FORMAT": (
        "EMP-{year}-{seq:03d}",
        "Format of the matriculation number",
    ),
    "SESSION_INACTIVITY_MINUTES": ("15", "Automatic logout after inactivity (minutes)"),
    "CONTRACT_ALERT_DAYS": ("30", "Notice before end of fixed-term contract (days)"),
    "TRIAL_ALERT_DAYS": ("15", "Notice before end of trial period (days)"),
    "DOCUMENT_ALERT_DAYS": (
        "30",
        "Notice before expiry of an employee document (days)",
    ),
    "RETIREMENT_AGE": ("60", "Legal retirement age (years)"),
    "RETIREMENT_ALERT_DAYS": ("180", "Notice before retirement (days)"),
    "MAX_FIXED_TERM_RENEWALS": (
        "1",
        "Number of renewals allowed for a fixed-term contract",
    ),
    "LEAVE_TRACKING_START_YEAR": (
        "2026",
        "First year whose leave balances are computed",
    ),
    "LEAVE_OVERLAP_THRESHOLD": (
        "30",
        "Max share of a team on leave at the same time (%)",
    ),
    "MIN_REST_BETWEEN_SHIFTS_HOURS": ("11", "Minimum rest between two shifts (hours)"),
    "MAX_WEEKLY_HOURS": ("48", "Maximum planned hours per week"),
    "LATENESS_TOLERANCE_MINUTES": (
        "5",
        "Lateness tolerated before it is counted (minutes)",
    ),
    "NIGHT_START": ("22:00", "Start of night work"),
    "NIGHT_END": ("06:00", "End of night work"),
    "CURRENCY": ("XAF", "Currency of the country of establishment (BN-146)"),
    "ROUNDING_UNIT": ("1", "Rounding unit for amounts (BN-146)"),
    "PAYROLL_DUE_DAY": ("25", "Day of the month when the payroll must be validated"),
    "DECLARATION_DUE_DAY": (
        "15",
        "Day of the following month when declarations are due",
    ),
}


def sync_default_settings(SettingModel=None):
    """Create the settings that do not exist yet (keeps edited values)."""
    SettingModel = SettingModel or Setting
    for key, (value, description) in DEFAULT_SETTINGS.items():
        SettingModel.objects.get_or_create(
            key=key, defaults={"value": value, "description": description}
        )


class Setting(models.Model):
    """BN-178: reference parameters editable without development."""

    key = models.CharField(max_length=100, unique=True)
    value = models.CharField(max_length=255)
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["key"]

    def __str__(self):
        return f"{self.key}={self.value}"


def get_setting(key, default=None):
    row = Setting.objects.filter(key=key).only("value").first()
    if row is not None:
        return row.value
    if default is not None:
        return default
    return DEFAULT_SETTINGS.get(key, (None,))[0]


def get_int_setting(key, default=0):
    try:
        return int(get_setting(key, str(default)))
    except (TypeError, ValueError):
        return default


class Sequence(models.Model):
    """Monotonic counters (matriculation numbers, journal numbering...)."""

    name = models.CharField(max_length=100, unique=True)
    value = models.PositiveIntegerField(default=0)

    @classmethod
    def next_value(cls, name):
        with transaction.atomic():
            seq, _ = cls.objects.select_for_update().get_or_create(name=name)
            seq.value += 1
            seq.save(update_fields=["value"])
            return seq.value
