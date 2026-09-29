"""harness/env/calc.py — the `calculate` tool: arithmetic only.

Accepts numbers (with thousands separators), + - * / ( ) and unary minus. No names, no functions,
no rounding choices made for the model: the result is the exact float of the expression, rendered
with up to 12 significant digits. Anything else is an error the model sees.
"""
from __future__ import annotations
import ast
import math
import operator
import re

_ALLOWED_BIN = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}
_ALLOWED_UN = {ast.USub: operator.neg, ast.UAdd: operator.pos}
_CLEAN_RE = re.compile(r"^[\d\s.,+\-*/()]+$")


class CalcError(ValueError):
    pass


def _eval(node):
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return float(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BIN:
        left, right = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Div) and right == 0:
            raise CalcError("division by zero")
        return _ALLOWED_BIN[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UN:
        return _ALLOWED_UN[type(node.op)](_eval(node.operand))
    raise CalcError("only numbers, + - * / and parentheses are allowed")


def calculate(expression) -> float:
    s = str(expression or "").strip()
    if not s:
        raise CalcError("empty expression")
    if not _CLEAN_RE.match(s):
        raise CalcError("only numbers, + - * / and parentheses are allowed (no names, no %, no $)")
    s = re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", s)     # 119,018,767 -> 119018767
    if "," in s:
        raise CalcError("a comma that is not a thousands separator")
    try:
        tree = ast.parse(s, mode="eval")
    except SyntaxError as e:
        raise CalcError(f"cannot parse: {e.msg}") from None
    val = _eval(tree)
    if math.isnan(val) or math.isinf(val):
        raise CalcError("result is not finite")
    return val


def fmt(val: float) -> str:
    """12 significant digits, no trailing zeros, no rounding choice beyond float precision."""
    s = f"{val:.12g}"
    if "e" in s or "E" in s:
        s = f"{val:.12f}".rstrip("0").rstrip(".")
    return s
