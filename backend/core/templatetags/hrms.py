"""
Filters available in every document template (declared as builtins).

money: 300000 → "300 000" (BN-146 / NF-07: one single format for amounts).
"""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def money(value, decimals=0):
    if value in (None, ""):
        return ""
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return value
    decimals = int(decimals)
    quantum = Decimal(1).scaleb(-decimals)
    number = number.quantize(quantum, rounding=ROUND_HALF_UP)
    sign = "-" if number < 0 else ""
    integer, _, fraction = f"{abs(number):.{decimals}f}".partition(".")
    groups = []
    while integer:
        groups.insert(0, integer[-3:])
        integer = integer[:-3]
    text = " ".join(groups) or "0"
    return f"{sign}{text}{'.' + fraction if fraction else ''}"


@register.filter
def nonzero_money(value):
    """Empty cell for a zero amount."""
    try:
        if Decimal(str(value)) == 0:
            return ""
    except (InvalidOperation, ValueError):
        return value
    return money(value)
