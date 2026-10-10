import re

from django.core.exceptions import ValidationError


class ComplexityValidator:
    """
    BN-174: the password must mix upper case, lower case, digits and a symbol.
    """

    def validate(self, password, user=None):
        rules = [
            (r"[A-Z]", "an upper-case letter"),
            (r"[a-z]", "a lower-case letter"),
            (r"\d", "a digit"),
            (r"[^A-Za-z0-9]", "a symbol"),
        ]
        missing = [
            label for pattern, label in rules if not re.search(pattern, password)
        ]
        if missing:
            raise ValidationError(
                "The password must contain " + ", ".join(missing) + ".",
                code="password_too_simple",
            )

    def get_help_text(self):
        return "Your password must contain upper and lower case letters, a digit and a symbol."
