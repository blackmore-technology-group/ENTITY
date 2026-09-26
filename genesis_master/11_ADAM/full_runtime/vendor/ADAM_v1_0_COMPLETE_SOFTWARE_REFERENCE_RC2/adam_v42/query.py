from __future__ import annotations

import operator
import re
from dataclasses import dataclass
from typing import Any, Iterable


class QueryError(RuntimeError):
    pass


@dataclass(frozen=True)
class QueryPlan:
    entity_type: str
    predicate: str | None
    operator: str | None
    value: Any
    return_fields: tuple[str, ...]
    shards: tuple[str, ...]
    estimated_rows: int
    strategy: str


_PATTERN = re.compile(
    r"^MATCH\s+(?P<type>\"[^\"]+\"|[\w: -]+?)"
    r"(?:\s+WHERE\s+(?P<field>[\w_]+)\s*(?P<op>==|!=|>=|<=|>|<|CONTAINS)\s*(?P<value>.+?))?"
    r"\s+RETURN\s+(?P<returns>[\w_, *]+)$",
    re.IGNORECASE,
)


class DistributedAQL:
    """Small declarative planner with shard pruning and sequence-aware result caching."""

    OPS = {"==": operator.eq, "!=": operator.ne, ">": operator.gt, "<": operator.lt, ">=": operator.ge, "<=": operator.le}

    def __init__(self, records: Iterable[tuple[str, dict[str, Any]]], sequence_provider=lambda: 0):
        self.shards: dict[str, list[dict[str, Any]]] = {}
        for entity_type, record in records:
            self.shards.setdefault(entity_type, []).append(record)
        self.sequence_provider = sequence_provider
        self.cache: dict[str, tuple[int, list[dict[str, Any]]]] = {}

    @staticmethod
    def _parse_value(value: str | None) -> Any:
        if value is None:
            return None
        value = value.strip()
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            return value[1:-1]
        if value.casefold() in ("true", "false"):
            return value.casefold() == "true"
        try:
            return float(value) if "." in value else int(value)
        except ValueError:
            return value

    def plan(self, query: str) -> QueryPlan:
        match = _PATTERN.match(query.strip())
        if not match:
            raise QueryError("Unsupported AQL syntax")
        entity_type = match.group("type").strip().strip('"')
        shards = (entity_type,) if entity_type in self.shards else tuple(sorted(self.shards)) if entity_type == "*" else ()
        if not shards:
            raise QueryError(f"No shard for {entity_type!r}")
        estimated = sum(len(self.shards[s]) for s in shards)
        strategy = "SHARD_PRUNED_SCAN" if len(shards) == 1 else "DISTRIBUTED_PARALLEL_SCAN"
        return QueryPlan(
            entity_type, match.group("field"), match.group("op"), self._parse_value(match.group("value")),
            tuple(x.strip() for x in match.group("returns").split(",")), shards, estimated, strategy,
        )

    def execute(self, query: str) -> tuple[QueryPlan, list[dict[str, Any]]]:
        seq = int(self.sequence_provider())
        cached = self.cache.get(query)
        if cached and cached[0] == seq:
            return self.plan(query), [dict(row) for row in cached[1]]
        plan = self.plan(query)
        result = []
        for shard in plan.shards:
            for row in self.shards[shard]:
                if plan.predicate:
                    actual = row.get(plan.predicate)
                    if plan.operator == "CONTAINS":
                        passed = str(plan.value).casefold() in str(actual).casefold()
                    else:
                        try:
                            passed = self.OPS[plan.operator](actual, plan.value)
                        except (TypeError, KeyError):
                            passed = False
                    if not passed:
                        continue
                if plan.return_fields == ("*",):
                    result.append(dict(row))
                else:
                    result.append({field: row.get(field) for field in plan.return_fields})
        self.cache[query] = (seq, [dict(row) for row in result])
        return plan, result

    def update_shard(self, entity_type: str, records: list[dict[str, Any]]) -> None:
        self.shards[entity_type] = records
        self.cache.clear()
