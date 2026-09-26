from __future__ import annotations

from pathlib import Path

import pytest

from adam_v41 import AtomicUniverse, ReactionEngine, ReactionError, ReactionIntent, TypeRegistry, UniverseCognition
from adam_v41.demo_domain import install_equipment_domain


def build_domain(tmp_path: Path):
    universe = AtomicUniverse(tmp_path / "universe")
    engine = ReactionEngine(universe, TypeRegistry())
    install_equipment_domain(engine)
    equipment, _ = engine.genesis_entity("equipment", "EQ-1", {"status": "AVAILABLE", "location": "YARD"})
    active_project, _ = engine.genesis_entity("project", "P-1", {"status": "ACTIVE", "budget": 1000, "cost": 100})
    inactive_project, _ = engine.genesis_entity("project", "P-2", {"status": "INACTIVE"})
    actor, _ = engine.genesis_entity(
        "person",
        "U-1",
        {"name": "Authorized", "grant::ASSIGN_EQUIPMENT": True, "grant::RELEASE_EQUIPMENT": True},
    )
    outsider, _ = engine.genesis_entity(
        "person",
        "U-2",
        {"name": "Unauthorized", "grant::ASSIGN_EQUIPMENT": False, "grant::RELEASE_EQUIPMENT": False},
    )
    return universe, engine, equipment, active_project, inactive_project, actor, outsider


def test_shadow_simulation_is_non_authoritative(tmp_path: Path):
    universe, engine, equipment, project, _, actor, _ = build_domain(tmp_path)
    before_seq = universe.sequence
    before_root = universe.root_hash
    receipt = engine.simulate(
        ReactionIntent("ASSIGN_EQUIPMENT", {"equipment": equipment, "project": project, "actor": actor})
    )
    assert not receipt.committed
    assert universe.sequence == before_seq
    assert universe.root_hash == before_root
    assert receipt.projected_views["equipment"]["status"] == "ASSIGNED"
    assert universe.entity_view(equipment)["status"] == "AVAILABLE"


def test_valid_assignment_and_release_are_proof_carrying(tmp_path: Path):
    universe, engine, equipment, project, _, actor, _ = build_domain(tmp_path)
    before = universe.sequence
    assigned = engine.apply(
        ReactionIntent("ASSIGN_EQUIPMENT", {"equipment": equipment, "project": project, "actor": actor})
    )
    assert assigned.committed and assigned.sequence_after == before + 1
    view = universe.entity_view(equipment)
    assert view["status"] == "ASSIGNED"
    assert view["assigned_to"]["key"] == "P-1"
    assert "location" not in view
    assert assigned.proof_id in universe.atoms
    assert universe.atoms[assigned.proof_id].kind == "reaction_proof"

    released = engine.apply(
        ReactionIntent(
            "RELEASE_EQUIPMENT",
            {"equipment": equipment, "project": project, "actor": actor},
            {"location": "YARD"},
        )
    )
    assert released.committed
    view = universe.entity_view(equipment)
    assert view["status"] == "AVAILABLE"
    assert view["location"] == "YARD"
    assert "assigned_to" not in view


def test_authority_preconditions_and_valence_reject_invalid_worlds(tmp_path: Path):
    universe, engine, equipment, project, inactive, actor, outsider = build_domain(tmp_path)
    initial_root = universe.root_hash
    invalid = [
        ReactionIntent("ASSIGN_EQUIPMENT", {"equipment": equipment, "project": project, "actor": outsider}),
        ReactionIntent("ASSIGN_EQUIPMENT", {"equipment": equipment, "project": inactive, "actor": actor}),
        ReactionIntent(
            "RELEASE_EQUIPMENT",
            {"equipment": equipment, "project": project, "actor": actor},
            {"location": "YARD"},
        ),
    ]
    for intent in invalid:
        with pytest.raises(ReactionError):
            engine.apply(intent)
    assert universe.root_hash == initial_root
    assert universe.entity_view(equipment)["status"] == "AVAILABLE"


def test_genesis_is_precommit_validated(tmp_path: Path):
    universe = AtomicUniverse(tmp_path / "universe")
    engine = ReactionEngine(universe, TypeRegistry())
    install_equipment_domain(engine)
    root = universe.root_hash
    with pytest.raises(ReactionError):
        engine.genesis_entity("equipment", "BROKEN", {"status": "ASSIGNED", "location": "YARD"})
    assert universe.root_hash == root


def test_history_and_restart_preserve_worldline(tmp_path: Path):
    root = tmp_path / "universe"
    universe, engine, equipment, project, _, actor, _ = build_domain(tmp_path)
    old_seq = universe.sequence
    engine.apply(ReactionIntent("ASSIGN_EQUIPMENT", {"equipment": equipment, "project": project, "actor": actor}))
    assert universe.entity_view(equipment, at_seq=old_seq)["status"] == "AVAILABLE"
    root_hash = universe.root_hash
    del engine, universe
    restarted = AtomicUniverse(root)
    assert restarted.root_hash == root_hash
    assert restarted.entity_view(equipment)["status"] == "ASSIGNED"
    assert restarted.entity_view(equipment, at_seq=old_seq)["status"] == "AVAILABLE"


def test_trained_cognition_is_advisory_and_governance_contains_false_proposal(tmp_path: Path):
    cognition, report = UniverseCognition.train(output_dir=tmp_path / "model", epochs=80)
    assert report.test_accuracy >= 0.98
    universe, engine, equipment, project, inactive, actor, outsider = build_domain(tmp_path / "domain")
    valid = ReactionIntent("ASSIGN_EQUIPMENT", {"equipment": equipment, "project": project, "actor": actor})
    label, confidence, _ = cognition.predict_intent(engine, valid)
    assert label == "ASSIGNED"
    assert confidence > 0.5

    # A malicious or hallucinated proposal still crosses the deterministic gate.
    invalid = ReactionIntent("ASSIGN_EQUIPMENT", {"equipment": equipment, "project": inactive, "actor": outsider})
    root = universe.root_hash
    with pytest.raises(ReactionError):
        engine.apply(invalid)
    assert universe.root_hash == root


def test_guarded_kernel_blocks_raw_mutation(tmp_path: Path):
    from adam_v41 import AuthorityError, UniverseKernel
    from adam_v41.demo_domain import install_equipment_domain

    kernel = UniverseKernel(tmp_path / "guarded")
    install_equipment_domain(kernel.reactions)
    before = kernel.root_hash
    with pytest.raises(AuthorityError):
        kernel._universe.assert_entity("equipment", "BYPASS", {"status": "ASSIGNED", "location": "YARD"})
    assert kernel.root_hash == before
