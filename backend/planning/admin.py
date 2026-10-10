from django.contrib import admin

from .models import (
    Shift,
    ShiftSwapRequest,
    Timetable,
    TimetableEntry,
)

admin.site.register(Shift)
admin.site.register(ShiftSwapRequest)
admin.site.register(Timetable)
admin.site.register(TimetableEntry)
