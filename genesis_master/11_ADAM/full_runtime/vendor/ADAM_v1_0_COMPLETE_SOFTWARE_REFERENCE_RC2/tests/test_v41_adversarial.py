from __future__ import annotations

import os
from pathlib import Path

import pytest

from adam_v41 import AtomicUniverse, ExactCodec, ReactionEngine, ReactionError, ReactionIntent, TypeRegistry
from adam_v41.demo_domain import install_equipment_domain
from adam_v41.universe import IntegrityError


def test_exact_evidence_survives_universe_reactions(tmp_path: Path):
    u = AtomicUniverse(tmp_path / "u")
    payload = os.urandom(65536)
    exact = ExactCodec(u)
    obj = exact.ingest(payload, name="evidence.bin")
    engine = ReactionEngine(u, TypeRegistry())
    install_equipment_domain(engine)
    equipment, _ = engine.genesis_entity("equipment", "EQ", {"status": "AVAILABLE", "location": "YARD"})
    project, _ = engine.genesis_entity("project", "P", {"status": "ACTIVE"})
    actor, _ = engine.genesis_entity(
        "person", "A", {"name": "A", "grant::ASSIGN_EQUIPMENT": True, "grant::RELEASE_EQUIPMENT": True}
    )
    engine.apply(ReactionIntent("ASSIGN_EQUIPMENT", {"equipment": equipment, "project": project, "actor": actor}))
    assert exact.reconstruct(obj.object_id) == payload


def test_unknown_reaction_and_wrong_role_types_are_rejected(tmp_path: Path):
    u = AtomicUniverse(tmp_path / "u")
    engine = ReactionEngine(u, TypeRegistry())
    install_equipment_domain(engine)
    equipment, _ = engine.genesis_entity("equipment", "EQ", {"status": "AVAILABLE", "location": "YARD"})
    project, _ = engine.genesis_entity("project", "P", {"status": "ACTIVE"})
    actor, _ = engine.genesis_entity(
        "person", "A", {"name": "A", "grant::ASSIGN_EQUIPMENT": True, "grant::RELEASE_EQUIPMENT": True}
    )
    with pytest.raises(ReactionError):
        engine.apply(ReactionIntent("INVENT_REALITY", {"equipment": equipment, "project": project, "actor": actor}))
    with pytest.raises(ReactionError):
        engine.apply(ReactionIntent("ASSIGN_EQUIPMENT", {"equipment": project, "project": equipment, "actor": actor}))


def test_tail_corruption_recovery_and_non_tail_tamper_rejection(tmp_path: Path):
    root = tmp_path / "u"
    u = AtomicUniverse(root)
    u.assert_entity("x", "1", {"a": 1})
    u.assert_entity("x", "2", {"a": 2})
    log = root / "universe.a41log"
    original = log.read_bytes()
    log.write_bytes(original + b"torn-tail")
    recovered = AtomicUniverse(root)
    assert recovered.log.recovered_torn_bytes == len(b"torn-tail")
    data = bytearray(log.read_bytes())
    data[len(data) // 3] ^= 0x01
    log.write_bytes(bytes(data))
    with pytest.raises(IntegrityError):
        AtomicUniverse(root)
