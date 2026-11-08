from django.contrib import admin

from .models import (
    ApprovalCircuit,
    ApprovalLevel,
    ApprovalTask,
    Notification,
    NotificationPreference,
)

admin.site.register(ApprovalCircuit)
admin.site.register(ApprovalLevel)
admin.site.register(ApprovalTask)
admin.site.register(Notification)
admin.site.register(NotificationPreference)
