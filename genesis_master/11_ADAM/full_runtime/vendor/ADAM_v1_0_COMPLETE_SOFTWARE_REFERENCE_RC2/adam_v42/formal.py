from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from adam_v41.canonical import digest
from .safe_expression import SafeExpression, SafeExpressionError


class ProofError(RuntimeError):
    pass


def _parse(expr: str) -> SafeExpression:
    try:
        return SafeExpression.parse(expr)
    except SafeExpressionError as exc:
        raise ProofError(str(exc)) from exc


@dataclass(frozen=True)
class Law:
    name: str
    expression: str
    variables: dict[str, tuple[Any, ...]]

    @property
    def law_id(self) -> str:
        return digest("ADAM42:LAW", {"name": self.name, "expression": self.expression, "variables": self.variables})


@dataclass(frozen=True)
class ProofCertificate:
    law_id: str
    status: str
    cases_checked: int
    counterexample: dict[str, Any] | None
    certificate_id: str


class BoundedProofChecker:
    """Machine-checks laws over explicitly finite domains.

    This is a real proof system for its bounded language; it is deliberately not
    described as a general theorem prover for unbounded mathematics.
    """

    @staticmethod
    def prove(law: Law) -> ProofCertificate:
        expression = _parse(law.expression)
        names = list(law.variables)
        cases = 0
        for values in itertools.product(*(law.variables[n] for n in names)):
            env = dict(zip(names, values))
            cases += 1
            try:
                result = expression.evaluate(env)
            except SafeExpressionError as exc:
                raise ProofError(str(exc)) from exc
            if not bool(result):
                payload = {"law_id": law.law_id, "status": "REFUTED", "cases": cases, "counterexample": env}
                return ProofCertificate(law.law_id, "REFUTED", cases, env, digest("ADAM42:PROOF", payload))
        payload = {"law_id": law.law_id, "status": "PROVEN_BOUNDED", "cases": cases, "counterexample": None}
        return ProofCertificate(law.law_id, "PROVEN_BOUNDED", cases, None, digest("ADAM42:PROOF", payload))

    @staticmethod
    def prove_transition(
        name: str,
        states: Iterable[Any],
        actions: Iterable[Any],
        transition: Callable[[Any, Any], Any | None],
        invariant: Callable[[Any, Any, Any], bool],
    ) -> ProofCertificate:
        cases = 0
        for state, action in itertools.product(states, actions):
            after = transition(state, action)
            if after is None:
                continue
            cases += 1
            if not invariant(state, action, after):
                counter = {"before": state, "action": action, "after": after}
                payload = {"name": name, "status": "REFUTED", "counterexample": counter, "cases": cases}
                return ProofCertificate(digest("ADAM42:TRANSITION_LAW", name), "REFUTED", cases, counter, digest("ADAM42:PROOF", payload))
        payload = {"name": name, "status": "PROVEN_BOUNDED", "cases": cases}
        return ProofCertificate(digest("ADAM42:TRANSITION_LAW", name), "PROVEN_BOUNDED", cases, None, digest("ADAM42:PROOF", payload))
