"""
Helper functions used by views/signals to write audit entries (BN-173),
to change a user's password while maintaining history + forced-change state
(BN-174), and to issue/verify TOTP second-factor codes (BN-176).
"""

import pyotp
from django.conf import settings
from django.contrib.auth.password_validation import (
    validate_password as run_password_validators,
)
from django.utils import timezone

from .models import AuditLog
from .request_context import get_client_ip, get_client_machine, get_current_request

PASSWORD_HISTORY_SIZE = 5


def record_audit(
    *,
    action,
    module="",
    obj=None,
    object_type="",
    object_id="",
    previous_value=None,
    new_value=None,
    user=None,
    notes="",
):
    """
    Writes one immutable AuditLog row (BN-173). `user` defaults to the
    currently authenticated request user, if any (thread-local set by
    AuditContextMiddleware).
    """
    request = get_current_request()

    if user is None and request is not None:
        request_user = getattr(request, "user", None)
        if request_user is not None and getattr(
            request_user, "is_authenticated", False
        ):
            user = request_user

    if obj is not None:
        object_type = object_type or obj.__class__.__name__
        object_id = object_id or str(getattr(obj, "pk", ""))

    AuditLog.objects.create(
        user=user,
        action=action,
        module=module,
        object_type=object_type,
        object_id=str(object_id),
        object_repr=str(obj)[:255] if obj is not None else "",
        previous_value=previous_value,
        new_value=new_value,
        ip_address=get_client_ip(request) or None,
        machine=get_client_machine(request),
        session_key=getattr(getattr(request, "session", None), "session_key", "") or "",
        notes=notes,
    )


def set_user_password(user, raw_password, *, forced=False):
    """
    Validates and applies a new password (BN-174): runs the full validator
    chain (length, complexity, similarity, history...), then updates
    password_history, password_changed_at and clears must_change_password.
    """
    run_password_validators(raw_password, user=user)

    history = list(user.password_history or [])
    history.append(user.password)  # previous hash, before overwriting
    user.password_history = history[-PASSWORD_HISTORY_SIZE:]

    user.set_password(raw_password)
    user.must_change_password = False
    user.password_changed_at = timezone.now()
    user.failed_login_attempts = 0
    user.locked_until = None
    user.save(
        update_fields=[
            "password",
            "password_history",
            "must_change_password",
            "password_changed_at",
            "failed_login_attempts",
            "locked_until",
        ]
    )

    record_audit(
        action="password_change",
        module="admin",
        obj=user,
        notes="Forced/first-login change" if forced else "Voluntary password change",
    )
    return user


# -- BN-176 - second authentication factor for payroll profiles -------------


def generate_two_factor_secret() -> str:
    """A fresh base32 TOTP secret, to be shown to the user once as a QR code."""
    return pyotp.random_base32()


def get_two_factor_provisioning_uri(user, secret: str) -> str:
    """otpauth:// URI an authenticator app (Google Authenticator, etc.) can scan."""
    issuer = getattr(settings, "OTP_ISSUER_NAME", "HR Management")
    return pyotp.totp.TOTP(secret).provisioning_uri(
        name=user.username, issuer_name=issuer
    )


def verify_two_factor_code(secret: str, code: str) -> bool:
    """Checks a 6-digit TOTP code against `secret`, allowing 1 step of drift."""
    if not secret or not code:
        return False
    return pyotp.totp.TOTP(secret).verify(code, valid_window=1)
