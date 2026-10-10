from django.contrib import admin

from .models import (
    ReportSchedule,
    SavedReport,
)

admin.site.register(ReportSchedule)
admin.site.register(SavedReport)
