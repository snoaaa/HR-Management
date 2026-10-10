from django.contrib import admin

from .models import (
    AttendancePeriod,
    Clocking,
    ClockingRegularisation,
    DailyAttendance,
    Mission,
    PublicHoliday,
    ScheduleAssignment,
    ScheduleException,
    WorkSchedule,
    WorkScheduleDay,
    WorkingCalendar,
)

admin.site.register(AttendancePeriod)
admin.site.register(Clocking)
admin.site.register(ClockingRegularisation)
admin.site.register(DailyAttendance)
admin.site.register(Mission)
admin.site.register(PublicHoliday)
admin.site.register(ScheduleAssignment)
admin.site.register(ScheduleException)
admin.site.register(WorkSchedule)
admin.site.register(WorkScheduleDay)
admin.site.register(WorkingCalendar)
