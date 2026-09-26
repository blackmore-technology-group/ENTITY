from __future__ import annotations

import itertools
from dataclasses import asdict, dataclass
from typing import Any, Iterable

import sympy as sp

from adam_v41.canonical import digest
from adam_v42.safe_expression import SafeExpression, SafeExpressionError


class TheoremError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProofStep:
    rule: str
    conclusion: str
    premises: tuple[str, ...]


@dataclass(frozen=True)
class TheoremCertificate:
    theorem: str
    status: str
    method: str
    assumptions: tuple[str, ...]
    proof_steps: tuple[ProofStep, ...]
    counterexample: dict[str, Any] | None
    certificate_id: str


@dataclass(frozen=True)
class HornRule:
    premises: tuple[str, ...]
    conclusion: str
    name: str = "modus_ponens"


class HornProofEngine:
    """Proof-producing finite Horn-clause reasoner."""

    def prove(self, facts: Iterable[str], rules: Iterable[HornRule], goal: str) -> TheoremCertificate:
        known = set(facts)
        derivation: dict[str, ProofStep] = {fact: ProofStep("given", fact, ()) for fact in known}
        changed = True
        while changed and goal not in known:
            changed = False
            for rule in rules:
                if rule.conclusion in known:
                    continue
                if all(premise in known for premise in rule.premises):
                    known.add(rule.conclusion)
                    derivation[rule.conclusion] = ProofStep(rule.name, rule.conclusion, rule.premises)
                    changed = True
        if goal not in known:
            payload = {"goal": goal, "status": "UNPROVEN", "known": sorted(known)}
            return TheoremCertificate(goal, "UNPROVEN", "HORN_FORWARD_CHAINING", tuple(sorted(facts)), (), None, digest("ADAM43:THEOREM", payload))
        ordered: list[ProofStep] = []
        visited: set[str] = set()

        def visit(item: str) -> None:
            if item in visited:
                return
            visited.add(item)
            step = derivation[item]
            for premise in step.premises:
                visit(premise)
            ordered.append(step)

        visit(goal)
        payload = {"goal": goal, "status": "PROVEN", "steps": [asdict(step) for step in ordered]}
        return TheoremCertificate(goal, "PROVEN", "HORN_FORWARD_CHAINING", tuple(sorted(facts)), tuple(ordered), None, digest("ADAM43:THEOREM", payload))


class SymbolicTheoremProver:
    """Proof-producing symbolic algebra and conservation verifier using SymPy.

    It is much broader than bounded enumeration but is intentionally not described as
    a complete prover for arbitrary mathematics or undecidable first-order theories.
    """

    @staticmethod
    def prove_identity(lhs: str, rhs: str, *, symbols: Iterable[str], assumptions: Iterable[str] = ()) -> TheoremCertificate:
        symbol_map = {name: sp.Symbol(name) for name in symbols}
        try:
            left = sp.sympify(lhs, locals=symbol_map)
            right = sp.sympify(rhs, locals=symbol_map)
            difference = sp.simplify(left - right)
        except Exception as exc:
            raise TheoremError(f"unable to parse theorem: {exc}") from exc
        theorem = f"{lhs} = {rhs}"
        if difference == 0:
            steps = (
                ProofStep("normalize", f"({lhs}) - ({rhs})", ()),
                ProofStep("symbolic_simplification", "0", (f"({lhs}) - ({rhs})",)),
                ProofStep("equality_from_zero_difference", theorem, ("0",)),
            )
            payload = {"theorem": theorem, "status": "PROVEN", "method": "SYMPY_IDENTITY", "steps": [asdict(x) for x in steps]}
            return TheoremCertificate(theorem, "PROVEN", "SYMPY_IDENTITY", tuple(assumptions), steps, None, digest("ADAM43:THEOREM", payload))
        payload = {"theorem": theorem, "status": "NOT_IDENTITY", "residual": str(difference)}
        return TheoremCertificate(theorem, "NOT_PROVEN", "SYMPY_IDENTITY", tuple(assumptions), (), {"symbolic_residual": str(difference)}, digest("ADAM43:THEOREM", payload))

    @staticmethod
    def prove_conservation(before: dict[str, str], after: dict[str, str], *, symbols: Iterable[str]) -> TheoremCertificate:
        if set(before) != set(after):
            missing = sorted(set(before) ^ set(after))
            theorem = "conservation(" + ",".join(sorted(set(before) | set(after))) + ")"
            payload = {"theorem": theorem, "status": "REFUTED", "missing": missing}
            return TheoremCertificate(theorem, "REFUTED", "SYMBOLIC_CONSERVATION", (), (), {"mismatched_quantities": missing}, digest("ADAM43:THEOREM", payload))
        certificates = [
            SymbolicTheoremProver.prove_identity(before[name], after[name], symbols=symbols)
            for name in sorted(before)
        ]
        theorem = "conservation(" + ",".join(sorted(before)) + ")"
        failed = next((certificate for certificate in certificates if certificate.status != "PROVEN"), None)
        if failed:
            payload = {"theorem": theorem, "status": "REFUTED", "failed": failed.certificate_id}
            return TheoremCertificate(theorem, "REFUTED", "SYMBOLIC_CONSERVATION", (), (), failed.counterexample, digest("ADAM43:THEOREM", payload))
        steps = tuple(
            ProofStep("conserved_quantity", name, (certificate.theorem,))
            for name, certificate in zip(sorted(before), certificates)
        ) + (ProofStep("conjunction_introduction", theorem, tuple(sorted(before))),)
        payload = {"theorem": theorem, "status": "PROVEN", "components": [x.certificate_id for x in certificates]}
        return TheoremCertificate(theorem, "PROVEN", "SYMBOLIC_CONSERVATION", (), steps, None, digest("ADAM43:THEOREM", payload))

    @staticmethod
    def prove_by_exhaustion(expression: str, domains: dict[str, tuple[Any, ...]]) -> TheoremCertificate:
        try:
            safe_expression = SafeExpression.parse(expression)
        except SafeExpressionError as exc:
            raise TheoremError(str(exc)) from exc
        names = tuple(domains)
        cases = 0
        for values in itertools.product(*(domains[name] for name in names)):
            env = dict(zip(names, values))
            cases += 1
            try:
                result = safe_expression.evaluate(env)
            except SafeExpressionError as exc:
                raise TheoremError(str(exc)) from exc
            if not bool(result):
                payload = {"theorem": expression, "status": "REFUTED", "counterexample": env, "cases": cases}
                return TheoremCertificate(expression, "REFUTED", "FINITE_EXHAUSTION", (), (), env, digest("ADAM43:THEOREM", payload))
        step = ProofStep("finite_exhaustion", expression, (f"{cases} cases",))
        payload = {"theorem": expression, "status": "PROVEN_BOUNDED", "cases": cases}
        return TheoremCertificate(expression, "PROVEN_BOUNDED", "FINITE_EXHAUSTION", (), (step,), None, digest("ADAM43:THEOREM", payload))
