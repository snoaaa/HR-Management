"""
BN-174 - Password policy.

Complements the stock Django validators already configured in settings
(minimum length, similarity to user attributes, common-password list,
not-fully-numeric) with:

  - PasswordComplexityValidator: requires upper/lower case, a digit and a
    special character.
  - PasswordHistoryValidator: forbids re-using one of the user's last N
    passwords (the hash history is kept on User.password_history, updated
    in api/services.py::set_user_password).
"""

import re

from django.contrib.auth.hashers import check_password
from django.core.exceptions import ValidationError


class PasswordComplexityValidator:
    def __init__(self, min_upper=1, min_lower=1, min_digit=1, min_special=1):
        self.min_upper = min_upper
        self.min_lower = min_lower
        self.min_digit = min_digit
        self.min_special = min_special

    def validate(self, password, user=None):
        errors = []
        if len(re.findall(r"[A-Z]", password)) < self.min_upper:
            errors.append("The password must contain at least one uppercase letter.")
        if len(re.findall(r"[a-z]", password)) < self.min_lower:
            errors.append("The password must contain at least one lowercase letter.")
        if len(re.findall(r"[0-9]", password)) < self.min_digit:
            errors.append("The password must contain at least one digit.")
        if len(re.findall(r"[^A-Za-z0-9]", password)) < self.min_special:
            errors.append("The password must contain at least one special character.")
        if errors:
            raise ValidationError(errors)

    def get_help_text(self):
        return "Your password must contain uppercase, lowercase, a digit and a special character."


class PasswordHistoryValidator:
    """Rejects a password that matches one of the user's last `history_size` passwords."""

    def __init__(self, history_size=5):
        self.history_size = history_size

    def validate(self, password, user=None):
        if user is None or not getattr(user, "pk", None):
            return
        history = list(getattr(user, "password_history", []) or [])
        for old_hash in history[-self.history_size :]:
            if check_password(password, old_hash):
                raise ValidationError(
                    f"You cannot reuse one of your last {self.history_size} passwords."
                )

    def get_help_text(self):
        return f"Your password may not match any of your last {self.history_size} passwords."
