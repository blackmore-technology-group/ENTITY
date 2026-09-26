from __future__ import annotations

import pytest

from adam_v49 import (
    AdaptiveAtomicEconomy, ChemistryProposal, ChemistryRegistry, ChemistryVersion,
    HistoricalReplayLaboratory, IndependentPromotionCouncil, ReplayCase,
)


def chemistry(version, parent=None):
    return ChemistryVersion(version, parent, {"atom": 1}, {"bond": 1}, {"compound": 1},
                            {"reaction": 1}, {"construct": 1}, {"security": 1})


def transformer(candidate, case):
    factor = 0.8 if candidate.version == "v2" else 1.0
    return case.exact_input, case.historical_queries, case.authority_expectation, case.security_expectation, case.cost_baseline * factor


def test_historical_replay_and_independent_promotion():
    registry = ChemistryRegistry()
    parent = chemistry("v1")
    parent_id = registry.add_genesis(parent)
    candidate = chemistry("v2", parent_id)
    proposal = ChemistryProposal("BETTER_COMPOUND", "MODEL8", parent_id, candidate, "reduce cost", {"cost": 0.2}, ("E1",))
    cases = [ReplayCase("C1", b"exact", {"q": 1}, "AUTH", "SECURE", 10.0)]
    lab = HistoricalReplayLaboratory(transformer)
    results = lab.replay(candidate, cases)
    council = IndependentPromotionCouncil(("A", "B", "C"), 2)
    decision = council.decide(proposal, results, ("A", "B"))
    assert decision.approved
    promoted = registry.promote(proposal, decision)
    assert registry.active_id == promoted


def test_proposer_cannot_self_approve_and_failed_replay_blocks_promotion():
    parent = chemistry("v1")
    parent_id = parent.chemistry_id
    candidate = chemistry("v2", parent_id)
    proposal = ChemistryProposal("CHANGE", "A", parent_id, candidate, "test", {}, ())
    cases = [ReplayCase("C1", b"exact", {"q": 1}, "AUTH", "SECURE", 10)]
    bad_lab = HistoricalReplayLaboratory(lambda c, case: (b"wrong", {}, "WRONG", "WRONG", 30))
    decision = IndependentPromotionCouncil(("A", "B"), 1).decide(proposal, bad_lab.replay(candidate, cases), ("A",))
    assert not decision.approved
    assert any("own chemistry" in reason for reason in decision.reasons)


def test_safe_rollback_and_atomic_economy():
    registry = ChemistryRegistry()
    v1 = chemistry("v1")
    v1_id = registry.add_genesis(v1)
    assert registry.rollback(v1_id, authority="OPS", reason="qualification") == v1_id
    economy = AdaptiveAtomicEconomy()
    best, score, scores = economy.choose({
        "deep": {"storage": 2, "compute": 5, "security_risk": 1},
        "opaque": {"storage": 5, "compute": 1, "security_risk": 0.2},
    })
    assert best == min(scores, key=scores.get)


def test_autonomous_chemistry_discovery_proposes_but_cannot_promote_itself():
    from adam_v49 import ChemistryDiscoveryEngine
    parent = chemistry("v1")
    engine = ChemistryDiscoveryEngine()
    proposal = engine.propose_compound(
        proposer="MODEL8", parent=parent, signature=("INVOICE", "ISSUER", "RECIPIENT"),
        occurrences=100, evidence_ids=("E1", "E2"), estimated_cost_reduction=0.22,
    )
    assert proposal.candidate.parent == parent.chemistry_id
    decision = IndependentPromotionCouncil(("MODEL8", "HUMAN"), 1).decide(proposal, [], ("MODEL8",))
    assert not decision.approved


def test_reaction_discovery_requires_stable_repeated_transition():
    from adam_v49 import ChemistryDiscoveryEngine
    parent = chemistry("v1")
    engine = ChemistryDiscoveryEngine()
    transitions = [{"before": {"s": "A"}, "after": {"s": "B"}} for _ in range(3)]
    proposal = engine.propose_reaction(
        proposer="MODEL8", parent=parent, reaction_name="ADVANCE_STATE",
        observed_transitions=transitions, evidence_ids=("E1", "E2", "E3"),
    )
    assert proposal.candidate.reaction_rules["ADVANCE_STATE"]["status"] == "CANDIDATE_ONLY"
