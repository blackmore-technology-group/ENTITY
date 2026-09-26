from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from adam_v41.reactions import ReactionEngine, ReactionError, ReactionIntent, ReactionReceipt
from .time_model import ValidInterval


@dataclass(frozen=True)
class AdvancedCondition:
    role: str
    predicate: str
    operator: str
    expected: Any = None


@dataclass(frozen=True)
class ComputedArgument:
    name: str
    role: str
    predicate: str
    operation: str
    operand_arg: str | None = None
    operand_literal: float | None = None


@dataclass(frozen=True)
class AdvancedPolicy:
    reaction: str
    conditions: tuple[AdvancedCondition, ...] = ()
    computed_arguments: tuple[ComputedArgument, ...] = ()


class AdvancedReactionEngine:
    """Adds aggregate, quantified, temporal and arithmetic guards to v0.41 reactions."""

    def __init__(self, base: ReactionEngine):
        self.base = base
        self.policies: dict[str, AdvancedPolicy] = {}

    def register_policy(self, policy: AdvancedPolicy) -> None:
        self.policies[policy.reaction] = policy

    def _values(self, entity_id: str, predicate: str) -> list[Any]:
        state = self.base._state_refs(entity_id)
        return self.base._values(state, predicate)

    def _check(self, condition: AdvancedCondition, intent: ReactionIntent) -> bool:
        entity_id = intent.bindings[condition.role]
        values = self._values(entity_id, condition.predicate)
        if condition.operator == "count_gte": return len(values) >= int(condition.expected)
        if condition.operator == "count_lte": return len(values) <= int(condition.expected)
        if condition.operator == "sum_gte": return sum(float(v) for v in values) >= float(condition.expected)
        if condition.operator == "sum_lte": return sum(float(v) for v in values) <= float(condition.expected)
        if condition.operator == "sum_plus_arg_lte":
            spec = dict(condition.expected)
            other_values = self._values(intent.bindings[spec.get("role", condition.role)], spec["predicate"])
            return len(values) == 1 and len(other_values) == 1 and float(values[0]) + float(intent.args[spec["arg"]]) <= float(other_values[0])
        if condition.operator == "all_equal": return bool(values) and all(v == condition.expected for v in values)
        if condition.operator == "any_equal": return any(v == condition.expected for v in values)
        if condition.operator == "valid_at":
            at_ns = int(intent.args["at_ns"])
            return any(isinstance(v, dict) and ValidInterval(int(v["start_ns"]), v.get("end_ns")).contains(at_ns) for v in values)
        raise ReactionError(f"Unsupported advanced operator {condition.operator!r}")

    def _computed_intent(self, intent: ReactionIntent, policy: AdvancedPolicy) -> ReactionIntent:
        args = dict(intent.args)
        for rule in policy.computed_arguments:
            values = self._values(intent.bindings[rule.role], rule.predicate)
            if len(values) != 1 or not isinstance(values[0], (int, float)):
                raise ReactionError(f"Computed argument {rule.name} requires one numeric value")
            operand = args[rule.operand_arg] if rule.operand_arg else rule.operand_literal
            if rule.operation == "add": value = float(values[0]) + float(operand)
            elif rule.operation == "subtract": value = float(values[0]) - float(operand)
            elif rule.operation == "multiply": value = float(values[0]) * float(operand)
            else: raise ReactionError(f"Unsupported arithmetic operation {rule.operation!r}")
            args[rule.name] = value
        return ReactionIntent(intent.reaction, dict(intent.bindings), args)

    def simulate(self, intent: ReactionIntent) -> ReactionReceipt:
        policy = self.policies.get(intent.reaction)
        if policy:
            failures = [c for c in policy.conditions if not self._check(c, intent)]
            if failures:
                raise ReactionError("Advanced reaction conditions failed", violations=[str(x) for x in failures])
            intent = self._computed_intent(intent, policy)
        return self.base.simulate(intent)

    def apply(self, intent: ReactionIntent) -> ReactionReceipt:
        policy = self.policies.get(intent.reaction)
        if policy:
            failures = [c for c in policy.conditions if not self._check(c, intent)]
            if failures:
                raise ReactionError("Advanced reaction conditions failed", violations=[str(x) for x in failures])
            intent = self._computed_intent(intent, policy)
        return self.base.apply(intent)
