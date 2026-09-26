from __future__ import annotations

import pytest

from adam_v44 import (
    BondAlgebra, BondFamily, ConfidenceClass, FirstClassBond, HyperBond, HyperRole,
    PhysicsError, ReactionIntent, TimeScope, ValenceConstraint,
)


def make_intent(kernel, *, proposer="planner", approvers=("HUMAN_APPROVER",)):
    return ReactionIntent(
        "ASSIGN_EQUIPMENT",
        {"equipment": "EX12", "location": "YARD", "project": "P204", "actor": "SHAWN",
         "work_order": "WO88", "approver": "SUPERVISOR", "evidence": "EVIDENCE1"},
        actor="SHAWN", authority="OPS", capabilities=("ASSIGN_EQUIPMENT",),
        expected_root=kernel.root, proposer=proposer, approvers=approvers,
    )


def test_first_class_bond_contains_full_algebra_and_is_deterministic():
    bond = FirstClassBond(
        "A", "SUPPORTED_BY", "E", BondFamily.EVIDENTIARY,
        direction="forward", order=2, time=TimeScope(1, None, 1), causal_parents=("C",),
        authority="AUTH", provenance=("P",), confidence=0.81,
        confidence_class=ConfidenceClass.SUPPORTED_HYPOTHESIS,
        security_scope="PRIVATE", chemistry_version="v44.1", reaction_origin="R",
        supporting_evidence=("E",), metadata={"note": "bounded"},
    )
    assert bond.bond_id == FirstClassBond(**bond.__dict__).bond_id
    assert bond.as_atomic_node()["bond"]["security_scope"] == "PRIVATE"


def test_bond_can_become_node_in_higher_order_bond():
    algebra = BondAlgebra()
    algebra.declare_entity("A", "ENTITY")
    algebra.declare_entity("B", "ENTITY")
    algebra.declare_entity("C", "ENTITY")
    base = FirstClassBond("A", "RELATED_TO", "B", authority="AUTH")
    algebra.add_bond(base)
    higher = FirstClassBond(base.bond_id, "EXPLAINED_BY", "C", BondFamily.COGNITIVE, authority="AUTH")
    algebra.add_bond(higher)
    assert algebra._node_type(base.bond_id) == "BOND"
    assert {base.bond_id, higher.bond_id, "A", "B", "C"} <= algebra.closure([higher.bond_id])


def test_hyperbond_preserves_multi_participant_event():
    algebra = BondAlgebra()
    for node, typ in [("SHAWN", "PERSON"), ("EX12", "EQUIPMENT"), ("P204", "PROJECT"), ("WO88", "WORK_ORDER")]:
        algebra.declare_entity(node, typ)
    hb = HyperBond("ASSIGNMENT_EVENT", (
        HyperRole("ACTOR", "SHAWN"), HyperRole("EQUIPMENT", "EX12"),
        HyperRole("DESTINATION", "P204"), HyperRole("AUTHORITY", "WO88"),
    ), authority="OPS")
    hid = algebra.add_hyperbond(hb)
    assert algebra.hyperbonds[hid].as_atomic_node()["kind"] == "hyperbond_atom"


def test_valence_rejects_invalid_target_and_cardinality():
    algebra = BondAlgebra()
    algebra.declare_entity("E", "EQUIPMENT")
    algebra.declare_entity("P1", "PROJECT")
    algebra.declare_entity("P2", "PROJECT")
    algebra.register_constraint(ValenceConstraint("ASSIGNED_TO", ("EQUIPMENT",), ("PROJECT",), maximum=1))
    algebra.add_bond(FirstClassBond("E", "ASSIGNED_TO", "P1", authority="OPS"))
    with pytest.raises(ValueError):
        algebra.add_bond(FirstClassBond("E", "ASSIGNED_TO", "P2", authority="OPS"))


def test_reaction_creates_proof_hyperbond_and_worldlines(assignment_kernel):
    old_root = assignment_kernel.root
    proof = assignment_kernel.commit(make_intent(assignment_kernel))
    assert proof.previous_root == old_root
    assert proof.new_root == assignment_kernel.root
    assert proof.hyperbond_id in assignment_kernel.algebra.hyperbonds
    assert assignment_kernel.worldlines["EX12"].states[-1][2] == proof.reaction_id
    assert any(b.predicate == "ASSIGNED_TO" and b.time.valid_until is None for b in assignment_kernel.algebra.bonds.values())


def test_shadow_branch_does_not_change_authoritative_root(assignment_kernel):
    root = assignment_kernel.root
    branch = assignment_kernel.branch()
    branch.commit(make_intent(branch))
    assert assignment_kernel.root == root
    assert branch.root != root


def test_model_cannot_approve_own_reaction(assignment_kernel):
    with pytest.raises(PhysicsError, match="own reaction"):
        assignment_kernel.commit(make_intent(assignment_kernel, proposer="MODEL8", approvers=("MODEL8",)))


def test_stale_root_and_missing_capability_are_rejected(assignment_kernel):
    intent = make_intent(assignment_kernel)
    bad = ReactionIntent(**{**intent.__dict__, "expected_root": "stale"})
    with pytest.raises(PhysicsError, match="stale"):
        assignment_kernel.commit(bad)
    bad2 = ReactionIntent(**{**intent.__dict__, "capabilities": ()})
    with pytest.raises(PhysicsError, match="capabilities"):
        assignment_kernel.commit(bad2)


def test_standard_bond_periodic_table_covers_all_families():
    from adam_v44 import STANDARD_BOND_TABLE
    families = {spec.family for spec in STANDARD_BOND_TABLE.values()}
    from adam_v44 import BondFamily
    assert families == set(BondFamily)
    assert STANDARD_BOND_TABLE["CAUSED"].requires_evidence
    assert STANDARD_BOND_TABLE["TRANSFORMS"].executable
    assert STANDARD_BOND_TABLE["LIKELY_CAUSES"].probabilistic


def test_isolated_authority_process_simulates_without_commit_and_commits_by_reaction_only():
    from adam_v44 import IsolatedPhysicsAuthority
    from conftest import assignment_kernel as fixture_function
    factory = getattr(fixture_function, "__wrapped__", fixture_function)
    with IsolatedPhysicsAuthority(factory) as service:
        initial = service.root()
        # Build the intent against the service-owned root; no mutable kernel object is exposed.
        from adam_v44 import ReactionIntent
        intent = ReactionIntent(
            "ASSIGN_EQUIPMENT",
            {"equipment": "EX12", "location": "YARD", "project": "P204", "actor": "SHAWN",
             "work_order": "WO88", "approver": "SUPERVISOR", "evidence": "EVIDENCE1"},
            actor="SHAWN", authority="OPS", capabilities=("ASSIGN_EQUIPMENT",),
            expected_root=initial["root"], proposer="PLANNER", approvers=("HUMAN",),
        )
        simulated = service.simulate(intent)
        assert not simulated["committed"]
        assert service.root() == initial
        committed = service.commit(intent)
        assert committed["committed"]
        assert service.root()["root"] == committed["proof"]["new_root"]


def test_repeated_reactions_keep_proof_root_equal_to_committed_root():
    from adam_v44 import build_equipment_physics, assignment_intent, release_intent
    kernel = build_equipment_physics()
    for index in range(20):
        proof = kernel.commit(assignment_intent(kernel) if index % 2 == 0 else release_intent(kernel))
        assert proof.new_root == kernel.root
    assert kernel.logical_time == 20


def test_content_addressed_bond_keys_remain_consistent_after_termination():
    from adam_v44 import build_equipment_physics, assignment_intent, release_intent
    kernel = build_equipment_physics()
    for index in range(12):
        kernel.commit(assignment_intent(kernel) if index % 2 == 0 else release_intent(kernel))
        assert not kernel.algebra.validate_state(kernel.logical_time)
        assert all(key == bond.bond_id for key, bond in kernel.algebra.bonds.items())
    assert kernel.algebra.superseded_by


def test_reaction_identity_commits_authorization_context(assignment_kernel):
    first = make_intent(assignment_kernel, proposer="PLANNER_A", approvers=("HUMAN",))
    _, proof_a = assignment_kernel.simulate(first)
    second = ReactionIntent(**{**first.__dict__, "proposer": "PLANNER_B"})
    _, proof_b = assignment_kernel.simulate(second)
    assert proof_a.reaction_id != proof_b.reaction_id


def test_minimum_valence_is_enforced():
    algebra = BondAlgebra()
    algebra.declare_entity("E", "EQUIPMENT")
    algebra.declare_entity("Y", "LOCATION")
    algebra.register_constraint(ValenceConstraint("AVAILABLE_AT", ("EQUIPMENT",), ("LOCATION",), minimum=1, maximum=1))
    assert algebra.validate_state(0)
    algebra.add_bond(FirstClassBond("E", "AVAILABLE_AT", "Y", authority="OPS"))
    assert algebra.validate_state(0) == []
