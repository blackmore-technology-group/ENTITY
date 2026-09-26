from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping, Sequence

from adam_v41.canonical import digest


@dataclass(frozen=True)
class ChemistryVersion:
    version: str
    parent: str | None
    atom_rules: Mapping[str, Any]
    bond_rules: Mapping[str, Any]
    compound_rules: Mapping[str, Any]
    reaction_rules: Mapping[str, Any]
    construction_rules: Mapping[str, Any]
    security_rules: Mapping[str, Any]
    approved_by: tuple[str, ...] = ()

    @property
    def chemistry_id(self) -> str:
        return digest("ADAM49:CHEMISTRY_VERSION", {
            "version": self.version,
            "parent": self.parent,
            "atom_rules": dict(self.atom_rules),
            "bond_rules": dict(self.bond_rules),
            "compound_rules": dict(self.compound_rules),
            "reaction_rules": dict(self.reaction_rules),
            "construction_rules": dict(self.construction_rules),
            "security_rules": dict(self.security_rules),
            "approved_by": list(self.approved_by),
        })


@dataclass(frozen=True)
class ChemistryProposal:
    proposal_type: str
    proposer: str
    parent_chemistry: str
    candidate: ChemistryVersion
    hypothesis: str
    expected_benefits: Mapping[str, float]
    evidence_ids: tuple[str, ...]

    @property
    def proposal_id(self) -> str:
        return digest("ADAM49:CHEMISTRY_PROPOSAL", {
            "proposal_type": self.proposal_type,
            "proposer": self.proposer,
            "parent_chemistry": self.parent_chemistry,
            "candidate": self.candidate.chemistry_id,
            "hypothesis": self.hypothesis,
            "expected_benefits": dict(self.expected_benefits),
            "evidence_ids": list(self.evidence_ids),
        })


@dataclass(frozen=True)
class ReplayCase:
    case_id: str
    exact_input: bytes
    historical_queries: Mapping[str, Any]
    authority_expectation: str
    security_expectation: str
    cost_baseline: float


@dataclass(frozen=True)
class ReplayResult:
    case_id: str
    exact_reconstruction: bool
    query_equivalent: bool
    security_equivalent: bool
    authority_equivalent: bool
    old_cost: float
    new_cost: float
    details: tuple[str, ...] = ()


@dataclass(frozen=True)
class PromotionDecision:
    proposal_id: str
    approved: bool
    approvers: tuple[str, ...]
    replay_root: str
    reasons: tuple[str, ...]


class HistoricalReplayLaboratory:
    """Runs candidate chemistry in a shadow universe using supplied deterministic adapters."""

    def __init__(self, transformer: Callable[[ChemistryVersion, ReplayCase], tuple[bytes, Mapping[str, Any], str, str, float]]) -> None:
        self.transformer = transformer

    def replay(self, chemistry: ChemistryVersion, cases: Sequence[ReplayCase]) -> list[ReplayResult]:
        results: list[ReplayResult] = []
        for case in cases:
            reconstructed, queries, authority, security, cost = self.transformer(chemistry, case)
            results.append(ReplayResult(
                case_id=case.case_id,
                exact_reconstruction=reconstructed == case.exact_input,
                query_equivalent=dict(queries) == dict(case.historical_queries),
                security_equivalent=security == case.security_expectation,
                authority_equivalent=authority == case.authority_expectation,
                old_cost=case.cost_baseline,
                new_cost=float(cost),
            ))
        return results

    @staticmethod
    def result_root(results: Sequence[ReplayResult]) -> str:
        return digest("ADAM49:REPLAY_RESULTS", [r.__dict__ for r in results])


class IndependentPromotionCouncil:
    def __init__(self, members: Iterable[str], threshold: int) -> None:
        self.members = set(members)
        self.threshold = threshold
        if threshold < 1 or threshold > len(self.members):
            raise ValueError("invalid promotion threshold")

    def decide(self, proposal: ChemistryProposal, results: Sequence[ReplayResult], approvals: Iterable[str]) -> PromotionDecision:
        approvers = tuple(sorted(set(approvals)))
        reasons: list[str] = []
        if proposal.proposer in approvers:
            reasons.append("proposer may not approve its own chemistry")
        unknown = set(approvers) - self.members
        if unknown:
            reasons.append(f"unknown approvers: {sorted(unknown)}")
        if len(set(approvers) & self.members) < self.threshold:
            reasons.append("approval threshold not met")
        for result in results:
            if not result.exact_reconstruction:
                reasons.append(f"{result.case_id}: exact reconstruction failed")
            if not result.query_equivalent:
                reasons.append(f"{result.case_id}: query equivalence failed")
            if not result.security_equivalent:
                reasons.append(f"{result.case_id}: security equivalence failed")
            if not result.authority_equivalent:
                reasons.append(f"{result.case_id}: authority equivalence failed")
            if result.new_cost > result.old_cost * 1.25:
                reasons.append(f"{result.case_id}: cost regression exceeds 25%")
        return PromotionDecision(
            proposal.proposal_id,
            not reasons,
            approvers,
            HistoricalReplayLaboratory.result_root(results),
            tuple(reasons),
        )


@dataclass
class ChemistryRegistry:
    versions: dict[str, ChemistryVersion] = field(default_factory=dict)
    active_id: str | None = None
    history: list[tuple[str, str, str]] = field(default_factory=list)

    def add_genesis(self, chemistry: ChemistryVersion) -> str:
        if self.active_id is not None:
            raise ValueError("genesis already exists")
        cid = chemistry.chemistry_id
        self.versions[cid] = chemistry
        self.active_id = cid
        self.history.append(("GENESIS", cid, "initial chemistry"))
        return cid

    def promote(self, proposal: ChemistryProposal, decision: PromotionDecision) -> str:
        if not decision.approved:
            raise PermissionError("chemistry promotion was not approved")
        if self.active_id != proposal.parent_chemistry:
            raise ValueError("proposal parent is not the active chemistry")
        candidate = ChemistryVersion(
            **{**proposal.candidate.__dict__, "approved_by": decision.approvers}
        )
        cid = candidate.chemistry_id
        self.versions[cid] = candidate
        self.active_id = cid
        self.history.append(("PROMOTE", cid, proposal.proposal_id))
        return cid

    def rollback(self, target_id: str, *, authority: str, reason: str) -> str:
        if target_id not in self.versions:
            raise KeyError("unknown chemistry")
        if not authority or not reason:
            raise PermissionError("authorized rollback reason required")
        self.active_id = target_id
        self.history.append(("ROLLBACK", target_id, f"{authority}:{reason}"))
        return target_id


class AdaptiveAtomicEconomy:
    """Chooses a representation strategy by total cost, not atom count alone."""

    WEIGHTS = {
        "storage": 1.0,
        "history": 0.8,
        "compute": 1.0,
        "latency": 1.2,
        "network": 1.0,
        "energy": 0.6,
        "verification": 1.1,
        "security_risk": 2.0,
        "reconstruction": 0.9,
    }

    def score(self, metrics: Mapping[str, float]) -> float:
        return sum(self.WEIGHTS.get(name, 1.0) * float(value) for name, value in metrics.items())

    def choose(self, candidates: Mapping[str, Mapping[str, float]]) -> tuple[str, float, dict[str, float]]:
        if not candidates:
            raise ValueError("at least one candidate strategy is required")
        scores = {name: self.score(metrics) for name, metrics in candidates.items()}
        best = min(scores, key=lambda name: (scores[name], name))
        return best, scores[best], scores

class ChemistryDiscoveryEngine:
    """Generates candidate chemistry from repeated structures without self-promoting it."""

    def propose_compound(
        self,
        *,
        proposer: str,
        parent: ChemistryVersion,
        signature: tuple[str, ...],
        occurrences: int,
        evidence_ids: Iterable[str],
        estimated_cost_reduction: float,
    ) -> ChemistryProposal:
        if occurrences < 2:
            raise ValueError("compound discovery requires repeated structure")
        compound_rules = dict(parent.compound_rules)
        compound_name = "COMPOUND::" + "::".join(signature)
        compound_rules[compound_name] = {
            "signature": list(signature),
            "minimum_support": occurrences,
            "reversible": True,
        }
        candidate = ChemistryVersion(
            version=f"{parent.version}+candidate-{digest('ADAM49:CANDIDATE_SUFFIX', signature)[:8]}",
            parent=parent.chemistry_id,
            atom_rules=parent.atom_rules,
            bond_rules=parent.bond_rules,
            compound_rules=compound_rules,
            reaction_rules=parent.reaction_rules,
            construction_rules=parent.construction_rules,
            security_rules=parent.security_rules,
        )
        return ChemistryProposal(
            "COMPOUND_DISCOVERY",
            proposer,
            parent.chemistry_id,
            candidate,
            f"Promote repeated bonded signature {signature}",
            {"estimated_cost_reduction": estimated_cost_reduction, "occurrences": float(occurrences)},
            tuple(sorted(set(evidence_ids))),
        )

    def propose_reaction(
        self,
        *,
        proposer: str,
        parent: ChemistryVersion,
        reaction_name: str,
        observed_transitions: Sequence[Mapping[str, Any]],
        evidence_ids: Iterable[str],
    ) -> ChemistryProposal:
        if len(observed_transitions) < 3:
            raise ValueError("reaction discovery requires at least three observations")
        signatures = {
            digest("ADAM49:TRANSITION_SIGNATURE", {
                "before": item.get("before"),
                "after": item.get("after"),
            })
            for item in observed_transitions
        }
        if len(signatures) != 1:
            raise ValueError("observed transitions are not stable enough for a reaction candidate")
        reaction_rules = dict(parent.reaction_rules)
        reaction_rules[reaction_name] = {
            "observations": len(observed_transitions),
            "transition_signature": next(iter(signatures)),
            "status": "CANDIDATE_ONLY",
        }
        candidate = ChemistryVersion(
            version=f"{parent.version}+reaction-{reaction_name.lower()}",
            parent=parent.chemistry_id,
            atom_rules=parent.atom_rules,
            bond_rules=parent.bond_rules,
            compound_rules=parent.compound_rules,
            reaction_rules=reaction_rules,
            construction_rules=parent.construction_rules,
            security_rules=parent.security_rules,
        )
        return ChemistryProposal(
            "REACTION_DISCOVERY", proposer, parent.chemistry_id, candidate,
            f"Observed stable transition for {reaction_name}",
            {"observations": float(len(observed_transitions))},
            tuple(sorted(set(evidence_ids))),
        )
