from django.contrib import admin

from .models import (
    EntitlementRule,
    LeaveAdjustment,
    LeaveRequest,
    LeaveType,
)

admin.site.register(EntitlementRule)
admin.site.register(LeaveAdjustment)
admin.site.register(LeaveRequest)
admin.site.register(LeaveType)
