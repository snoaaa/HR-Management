import datetime

from django.db import migrations

# Fixed-date public holidays of Cameroon (movable religious holidays such as
# Good Friday, Ascension or Eid are added each year by HR).
HOLIDAYS = [
    ("New Year's Day", 1, 1),
    ("Youth Day", 2, 11),
    ("Labour Day", 5, 1),
    ("National Day", 5, 20),
    ("Assumption Day", 8, 15),
    ("Christmas Day", 12, 25),
]


def seed(apps, schema_editor):
    Calendar = apps.get_model("attendance", "WorkingCalendar")
    Holiday = apps.get_model("attendance", "PublicHoliday")
    Schedule = apps.get_model("attendance", "WorkSchedule")
    Day = apps.get_model("attendance", "WorkScheduleDay")
    Assignment = apps.get_model("attendance", "ScheduleAssignment")

    Calendar.objects.get_or_create(
        site=None, defaults={"name": "Default calendar", "rest_days": [5, 6]}
    )
    for name, month, day in HOLIDAYS:
        Holiday.objects.get_or_create(
            name=name,
            defaults={"date": datetime.date(2026, month, day), "recurring": True},
        )
    schedule, created = Schedule.objects.get_or_create(
        code="STD-40",
        defaults={
            "name": "Standard 40 h (Mon–Fri 08:00–17:00)",
            "schedule_type": "FIXED",
        },
    )
    if created:
        for weekday in range(5):
            Day.objects.create(
                schedule=schedule,
                weekday=weekday,
                start_time=datetime.time(8, 0),
                end_time=datetime.time(17, 0),
                break_minutes=60,
            )
        Assignment.objects.create(
            schedule=schedule, effective_from=datetime.date(2020, 1, 1)
        )


class Migration(migrations.Migration):

    dependencies = [("attendance", "0001_initial")]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
