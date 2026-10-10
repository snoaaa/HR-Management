import datetime

from django.db import migrations

SHIFTS = [
    ("M", "Morning", datetime.time(6, 0), datetime.time(14, 0), 30, "#00A09D"),
    ("A", "Afternoon", datetime.time(14, 0), datetime.time(22, 0), 30, "#0096d6"),
    ("N", "Night", datetime.time(22, 0), datetime.time(6, 0), 30, "#4a2f42"),
    ("D", "Day duty", datetime.time(8, 0), datetime.time(17, 0), 60, "#714B67"),
]


def seed(apps, schema_editor):
    Shift = apps.get_model("planning", "Shift")
    for code, name, start, end, pause, color in SHIFTS:
        Shift.objects.get_or_create(
            code=code,
            defaults={
                "name": name,
                "start_time": start,
                "end_time": end,
                "break_minutes": pause,
                "color": color,
            },
        )


class Migration(migrations.Migration):

    dependencies = [("planning", "0001_initial")]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
