from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)
from django.dispatch import receiver

from .audit import audit
from .models import AuditLog


@receiver(user_logged_in)
def on_login(sender, request, user, **kw):
    audit(AuditLog.Action.LOGIN, request=request, actor=user)


@receiver(user_logged_out)
def on_logout(sender, request, user, **kw):
    audit(AuditLog.Action.LOGOUT, request=request, actor=user)


@receiver(user_login_failed)
def on_failed(sender, credentials, request=None, **kw):
    audit(
        AuditLog.Action.LOGIN_FAILED,
        request=request,
        changes={"identifier": credentials.get("email") or credentials.get("username", "")},
    )