"""
Safe evaluation of the payroll formulas (BN-88).

Only numbers, variables, + - * / // %, comparisons, and / or / not and the
functions below are accepted; anything else is refused. Every computation is
done with Decimal so that no floating-point rounding difference appears
between the payroll and the accounting (BN-146).

Functions: min, max, abs, round(x, n), floor, ceil, if_(condition, a, b).
"""

import ast
import math
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation


class FormulaError(Exception):
    pass


def _round(value, digits=0):
    quantum = Decimal(1).scaleb(-int(digits))
    return Decimal(value).quantize(quantum, rounding=ROUND_HALF_UP)


FUNCTIONS = {
    "min": lambda *a: min(a),
    "max": lambda *a: max(a),
    "abs": lambda a: abs(a),
    "round": _round,
    "floor": lambda a: Decimal(math.floor(a)),
    "ceil": lambda a: Decimal(math.ceil(a)),
    "if_": lambda c, a, b: a if c else b,
}

_BINARY = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b if b else Decimal(0),
    ast.FloorDiv: lambda a, b: a // b if b else Decimal(0),
    ast.Mod: lambda a, b: a % b if b else Decimal(0),
}
_COMPARE = {
    ast.Gt: lambda a, b: a > b,
    ast.GtE: lambda a, b: a >= b,
    ast.Lt: lambda a, b: a < b,
    ast.LtE: lambda a, b: a <= b,
    ast.Eq: lambda a, b: a == b,
    ast.NotEq: lambda a, b: a != b,
}


def _to_decimal(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise FormulaError(f"Not a number: {value!r}")


def _eval(node, variables):
    if isinstance(node, ast.Expression):
        return _eval(node.body, variables)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return Decimal(str(node.value))
    if isinstance(node, ast.Name):
        if node.id not in variables:
            raise FormulaError(f"Unknown variable '{node.id}'.")
        return _to_decimal(variables[node.id])
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
        return _BINARY[type(node.op)](
            _eval(node.left, variables), _eval(node.right, variables)
        )
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_eval(node.operand, variables)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return not _eval(node.operand, variables)
    if isinstance(node, ast.BoolOp):
        values = [_eval(v, variables) for v in node.values]
        return all(values) if isinstance(node.op, ast.And) else any(values)
    if (
        isinstance(node, ast.Compare)
        and len(node.ops) == 1
        and type(node.ops[0]) in _COMPARE
    ):
        return _COMPARE[type(node.ops[0])](
            _eval(node.left, variables), _eval(node.comparators[0], variables)
        )
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in FUNCTIONS
        and not node.keywords
    ):
        args = [_eval(arg, variables) for arg in node.args]
        return FUNCTIONS[node.func.id](*args)
    raise FormulaError(f"Forbidden expression: {ast.dump(node)[:80]}")


def evaluate(formula, variables):
    """Evaluate a formula; an empty formula gives 0."""
    formula = (formula or "").strip()
    if not formula:
        return Decimal(0)
    try:
        tree = ast.parse(formula, mode="eval")
    except SyntaxError as exc:
        raise FormulaError(f"Syntax error in '{formula}': {exc.msg}")
    result = _eval(tree, variables)
    if isinstance(result, bool):
        return Decimal(1) if result else Decimal(0)
    return result


def check(formula, known_names):
    """Validate a formula when it is saved: syntax and variable names."""
    try:
        tree = ast.parse((formula or "0").strip() or "0", mode="eval")
    except SyntaxError as exc:
        raise FormulaError(f"Syntax error: {exc.msg}")
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Name)
            and node.id not in known_names
            and node.id not in FUNCTIONS
        ):
            raise FormulaError(f"Unknown variable '{node.id}'.")
    _eval(tree, {name: Decimal(1) for name in known_names})
