"""
Safe Expression Parser and Evaluator.
Evaluates user-configurable resource filtering expressions using Python's AST
without using unsafe eval().
"""

from __future__ import annotations
import ast
import operator
from typing import Dict, Any, Union


# Allowed operators mapping
OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.And: lambda a, b: a and b,
    ast.Or: lambda a, b: a or b,
    ast.Not: operator.not_,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


class ExpressionEvaluator:
    """Safely compiles and evaluates arithmetic & boolean expressions against a variables dict."""

    def __init__(self, expression_str: str):
        self.raw_expression = expression_str
        self.compiled_ast = self._compile(expression_str)

    def _compile(self, expression_str: str) -> ast.Expression:
        # Preprocess: normalize boolean keywords (case-insensitive)
        cleaned = expression_str.replace(" OR ", " or ").replace(" Or ", " or ")
        cleaned = cleaned.replace(" AND ", " and ").replace(" And ", " and ")
        cleaned = cleaned.replace(" NOT ", " not ").replace(" Not ", " not ")
        # Also handle starting or trailing keywords if any
        if cleaned.startswith("NOT ") or cleaned.startswith("Not "):
            cleaned = "not " + cleaned[4:]

        try:
            parsed = ast.parse(cleaned, mode="eval")
            return parsed
        except SyntaxError as e:
            raise ValueError(f"Invalid target expression syntax '{expression_str}': {e}")

    def evaluate(self, context: Dict[str, Union[int, float]]) -> bool:
        """Evaluates the expression with the given variable mapping."""
        # Normalize keys in context to lowercase
        norm_context = {k.lower(): v for k, v in context.items()}
        result = self._eval_node(self.compiled_ast.body, norm_context)
        return bool(result)

    def _eval_node(self, node: ast.AST, context: Dict[str, Any]) -> Any:
        if isinstance(node, ast.Constant):  # Python 3.8+ numbers/bools
            return node.value

        elif isinstance(node, ast.Name):
            var_name = node.id.lower()
            if var_name in context:
                return context[var_name]
            raise KeyError(f"Unknown variable '{node.id}' in target expression. Allowed: {list(context.keys())}")

        elif isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type in OPERATORS:
                operand = self._eval_node(node.operand, context)
                return OPERATORS[op_type](operand)
            raise ValueError(f"Unsupported unary operator: {op_type}")

        elif isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type in OPERATORS:
                left = self._eval_node(node.left, context)
                right = self._eval_node(node.right, context)
                return OPERATORS[op_type](left, right)
            raise ValueError(f"Unsupported binary operator: {op_type}")

        elif isinstance(node, ast.Compare):
            left = self._eval_node(node.left, context)
            for op, comparator in zip(node.ops, node.comparators):
                op_type = type(op)
                if op_type not in OPERATORS:
                    raise ValueError(f"Unsupported comparison operator: {op_type}")
                right = self._eval_node(comparator, context)
                if not OPERATORS[op_type](left, right):
                    return False
                left = right
            return True

        elif isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                for val_node in node.values:
                    if not self._eval_node(val_node, context):
                        return False
                return True
            elif isinstance(node.op, ast.Or):
                for val_node in node.values:
                    if self._eval_node(val_node, context):
                        return True
                return False
            raise ValueError(f"Unsupported boolean operator: {type(node.op)}")

        raise ValueError(f"Unsupported AST node in expression: {type(node).__name__}")
