from __future__ import annotations

import ast
import operator
from dataclasses import dataclass
from typing import Any, Mapping


class SafeExpressionError(ValueError):
    """Raised when a proof expression is outside the deterministic safe subset."""


_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
}
_UNARY_OPS = {ast.Not: operator.not_, ast.USub: operator.neg, ast.UAdd: operator.pos}
_COMPARE_OPS = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
}


@dataclass(frozen=True)
class SafeExpression:
    source: str
    tree: ast.Expression
    names: frozenset[str]

    @classmethod
    def parse(cls, source: str, *, max_length: int = 4096, max_nodes: int = 256) -> "SafeExpression":
        if not isinstance(source, str) or not source.strip():
            raise SafeExpressionError("expression must be non-empty text")
        if len(source) > max_length:
            raise SafeExpressionError("expression exceeds maximum length")
        try:
            parsed = ast.parse(source, mode="eval")
        except SyntaxError as exc:
            raise SafeExpressionError(f"invalid expression syntax: {exc.msg}") from exc
        nodes = list(ast.walk(parsed))
        if len(nodes) > max_nodes:
            raise SafeExpressionError("expression exceeds maximum node count")
        names: set[str] = set()
        allowed = (
            ast.Expression, ast.BoolOp, ast.BinOp, ast.UnaryOp, ast.Compare, ast.Name,
            ast.Load, ast.Constant, ast.And, ast.Or, ast.Not, ast.UAdd, ast.USub,
            ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod,
            ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.IfExp,
        )
        for node in nodes:
            if not isinstance(node, allowed):
                raise SafeExpressionError(f"unsupported expression node: {type(node).__name__}")
            if isinstance(node, ast.Name):
                if node.id.startswith("__"):
                    raise SafeExpressionError("dunder names are forbidden")
                names.add(node.id)
            if isinstance(node, ast.Constant) and not isinstance(node.value, (bool, int, float, str, type(None))):
                raise SafeExpressionError(f"unsupported constant type: {type(node.value).__name__}")
        return cls(source, parsed, frozenset(names))

    def evaluate(self, environment: Mapping[str, Any]) -> Any:
        missing = self.names - set(environment)
        if missing:
            raise SafeExpressionError(f"missing variables: {sorted(missing)}")
        extra_values = [name for name in self.names if not isinstance(environment[name], (bool, int, float, str, type(None)))]
        if extra_values:
            raise SafeExpressionError(f"unsupported variable value types: {sorted(extra_values)}")
        return self._eval(self.tree.body, environment)

    @classmethod
    def _eval(cls, node: ast.AST, env: Mapping[str, Any]) -> Any:
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            return env[node.id]
        if isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                result: Any = True
                for value in node.values:
                    result = cls._eval(value, env)
                    if not result:
                        return result
                return result
            result = False
            for value in node.values:
                result = cls._eval(value, env)
                if result:
                    return result
            return result
        if isinstance(node, ast.UnaryOp):
            return _UNARY_OPS[type(node.op)](cls._eval(node.operand, env))
        if isinstance(node, ast.BinOp):
            left = cls._eval(node.left, env)
            right = cls._eval(node.right, env)
            if isinstance(node.op, ast.Mult) and (
                isinstance(left, str) and isinstance(right, int)
                or isinstance(right, str) and isinstance(left, int)
            ):
                count = right if isinstance(right, int) else left
                if abs(count) > 100_000:
                    raise SafeExpressionError("string multiplication exceeds safe bound")
            return _BIN_OPS[type(node.op)](left, right)
        if isinstance(node, ast.Compare):
            left = cls._eval(node.left, env)
            for operation, comparator in zip(node.ops, node.comparators, strict=True):
                right = cls._eval(comparator, env)
                if not _COMPARE_OPS[type(operation)](left, right):
                    return False
                left = right
            return True
        if isinstance(node, ast.IfExp):
            branch = node.body if cls._eval(node.test, env) else node.orelse
            return cls._eval(branch, env)
        raise SafeExpressionError(f"unsupported expression node: {type(node).__name__}")
