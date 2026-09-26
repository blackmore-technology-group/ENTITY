from __future__ import annotations

import os
from pathlib import Path

import pytest

from adam_v41 import AtomicBrain, AtomicUniverse, ConflictError, Constructor, ExactCodec
from adam_v41.query import AtomicQueryEngine
from adam_v41.semantic import SemanticCodec


def test_exact_and_semantic_roundtrip(tmp_path: Path):
    u = AtomicUniverse(tmp_path / "u")
    exact = ExactCodec(u)
    data = os.urandom(10000)
    obj = exact.ingest(data)
    assert exact.reconstruct(obj.object_id) == data
    sem = SemanticCodec(u)
    value = {"a": [1, 2, {"x": True}], "b": None}
    root = sem.ingest(value)
    assert sem.reconstruct(root) == value


def test_rebond_history_mvcc_and_construction(tmp_path: Path):
    u = AtomicUniverse(tmp_path / "u")
    entity, v1 = u.assert_entity("project", "P1", {"location": "Grand Forks", "budget": 10, "cost": 5})
    old_seq = u.sequence
    _, v2 = u.assert_entity("project", "P1", {"location": "Boundary", "budget": 10, "cost": 12}, expected_version=v1)
    assert u.entity_view(entity)["location"] == "Boundary"
    assert u.entity_view(entity, at_seq=old_seq)["location"] == "Grand Forks"
    assert AtomicQueryEngine(u).over_budget()[0]["_key"] == "P1"
    assert "Boundary" in Constructor(u).entity_markdown(entity)
    with pytest.raises(ConflictError):
        u.assert_entity("project", "P1", {"cost": 1}, expected_version=v1)
    assert v2 == 2


def test_learning_and_restart(tmp_path: Path):
    root = tmp_path / "u"
    u = AtomicUniverse(root)
    brain = AtomicBrain(u)
    records = [{"id": str(i), "location": "Grand Forks", "status": "active", "cost": i} for i in range(20)]
    ids = brain.ingest_records(records, entity_type="project", id_field="id")
    proposals = brain.discover_compounds(records, min_support=5)
    assert any(p.accepted for p in proposals)
    root_hash = u.root_hash
    assert u.verify()["pass"]
    u.compact_authority()
    del u
    r = AtomicUniverse(root)
    assert r.root_hash == root_hash
    assert r.entity_view(ids[-1])["cost"] == 19
