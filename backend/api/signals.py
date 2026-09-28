"""
BN-173: automatically records create/update/delete of sensitive data.
Also records login success/failure/logout and enforces account lockout
after repeated failures (part of BN-174's "individual account" protection).
"""

import json

from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import AuditLog, Module, SalaryRecord, User, UserRole
from .request_context import get_client_ip, get_client_machine, get_current_request
from .services import record_audit

# Models whose changes are always written to the audit trail, and which
# module they are considered part of.
AUDITED_MODELS = {
    SalaryRecord: Module.PAYROLL,
    UserRole: Module.ADMIN,
}

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


def _to_dict(instance):
    data = {}
    for field in instance._meta.fields:
        value = getattr(instance, field.name)
        try:
            json.dumps(value, cls=DjangoJSONEncoder)
        except TypeError:
            value = str(value)
        data[field.name] = value
    return data


@receiver(pre_save)
def _capture_previous_value(sender, instance, **kwargs):
    if sender not in AUDITED_MODELS:
        return
    if not instance.pk:
        instance._audit_previous = None
        return
    try:
        previous = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        instance._audit_previous = None
    else:
        instance._audit_previous = _to_dict(previous)


@receiver(post_save)
def _audit_create_update(sender, instance, created, **kwargs):
    if sender not in AUDITED_MODELS:
        return
    module = AUDITED_MODELS[sender]
    previous = getattr(instance, "_audit_previous", None)
    record_audit(
        action="create" if created else "update",
        module=module,
        obj=instance,
        previous_value=previous,
        new_value=_to_dict(instance),
    )


@receiver(post_delete)
def _audit_delete(sender, instance, **kwargs):
    if sender not in AUDITED_MODELS:
        return
    module = AUDITED_MODELS[sender]
    record_audit(
        action="delete",
        module=module,
        obj=instance,
        previous_value=_to_dict(instance),
        new_value=None,
    )


@receiver(user_logged_in)
def _on_login_success(sender, request, user, **kwargs):
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_activity = timezone.now()
    user.save(update_fields=["failed_login_attempts", "locked_until", "last_activity"])
    AuditLog.objects.create(
        user=user,
        action="login_success",
        module=Module.ADMIN,
        object_type="User",
        object_id=str(user.pk),
        object_repr=str(user),
        ip_address=get_client_ip(request) or None,
        machine=get_client_machine(request),
        session_key=getattr(getattr(request, "session", None), "session_key", "") or "",
    )


@receiver(user_logged_out)
def _on_logout(sender, request, user, **kwargs):
    if user is None:
        return
    AuditLog.objects.create(
        user=user,
        action="logout",
        module=Module.ADMIN,
        object_type="User",
        object_id=str(user.pk),
        object_repr=str(user),
        ip_address=get_client_ip(request) or None,
        machine=get_client_machine(request),
    )


@receiver(user_login_failed)
def _on_login_failed(sender, credentials, request=None, **kwargs):
    username = credentials.get("username", "")
    AuditLog.objects.create(
        user=None,
        username_snapshot=username,
        action="login_failure",
        module=Module.ADMIN,
        object_type="User",
        object_repr=username,
        ip_address=get_client_ip(request) or None,
        machine=get_client_machine(request),
    )

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return

    user.failed_login_attempts += 1
    if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
        user.locked_until = timezone.now() + timezone.timedelta(minutes=LOCKOUT_MINUTES)
    user.save(update_fields=["failed_login_attempts", "locked_until"])
