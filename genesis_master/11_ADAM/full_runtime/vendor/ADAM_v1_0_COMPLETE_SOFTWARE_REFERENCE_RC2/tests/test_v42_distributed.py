from __future__ import annotations

import os
from pathlib import Path

import pytest

from adam_v41.reactions import ReactionIntent
from adam_v42.distributed import ConsensusError, DistributedUniverseCluster, SovereignErasureStore, QuorumCertificate, Vote
from adam_v42.erasure import ReedSolomonCodec


def test_majority_commit_failover_recovery_and_stale_term(tmp_path: Path):
    cluster = DistributedUniverseCluster(tmp_path / "cluster", 3)
    ids = cluster.leader.ids
    initial_term = cluster.term
    cert1 = cluster.apply(ReactionIntent("ASSIGN_EQUIPMENT", {"equipment": ids["equipment"], "project": ids["project"], "actor": ids["actor"]}))
    assert len(cert1.votes) == 3
    old_leader = cluster.leader_id
    cluster.stop_node(old_leader)
    assert cluster.term > initial_term and cluster.leader_id != old_leader
    with pytest.raises(ConsensusError):
        cluster.apply(ReactionIntent("RELEASE_EQUIPMENT", {"equipment": ids["equipment"], "project": ids["project"], "actor": ids["actor"]}, {"location": "YARD"}), expected_term=initial_term)
    cert2 = cluster.apply(ReactionIntent("RELEASE_EQUIPMENT", {"equipment": ids["equipment"], "project": ids["project"], "actor": ids["actor"]}, {"location": "YARD"}))
    assert len(cert2.votes) >= cluster.quorum
    cluster.start_node(old_leader)
    assert len({n.state_digest() for n in cluster.nodes.values()}) == 1


def test_quorum_unavailable_rejects_without_commit(tmp_path: Path):
    cluster = DistributedUniverseCluster(tmp_path / "cluster", 3)
    ids = cluster.leader.ids
    cluster.stop_node("n1")
    cluster.stop_node("n2")
    before = cluster.index
    with pytest.raises(ConsensusError):
        cluster.apply(ReactionIntent("ASSIGN_EQUIPMENT", {"equipment": ids["equipment"], "project": ids["project"], "actor": ids["actor"]}))
    assert cluster.index == before


def test_reed_solomon_reconstructs_after_any_two_losses():
    data = os.urandom(32771)
    codec = ReedSolomonCodec(3, 2)
    fragments = codec.encode(data)
    for a in range(5):
        for b in range(a + 1, 5):
            remaining = [f for f in fragments if f.index not in {a, b}]
            assert codec.reconstruct(remaining) == data


def test_sovereignty_placement_and_owner_loss(tmp_path: Path):
    nodes = [(f"ca{i}", "CA") for i in range(5)] + [("us1", "US"), ("eu1", "EU")]
    store = SovereignErasureStore(tmp_path / "store", nodes, 3, 2)
    data = os.urandom(8192)
    object_id = store.put(data, allowed_jurisdictions={"CA"})
    placements = store.manifest[object_id]["placements"]
    assert all(p["jurisdiction"] == "CA" for p in placements)
    assert store.reconstruct(object_id, unavailable_nodes={placements[0]["node_id"], placements[1]["node_id"]}) == data


def test_quorum_certificate_tamper_rejected(tmp_path: Path):
    cluster = DistributedUniverseCluster(tmp_path / "cluster", 3)
    ids = cluster.leader.ids
    cert = cluster.apply(ReactionIntent("ASSIGN_EQUIPMENT", {"equipment": ids["equipment"], "project": ids["project"], "actor": ids["actor"]}))
    assert cluster.verify_certificate(cert)
    first = cert.votes[0]
    bad_vote = Vote(first.node_id, first.authority_id, first.public_key_hex, "00" * 64)
    tampered = QuorumCertificate(cert.term, cert.index, cert.proposal_digest, cert.state_digest_before, (bad_vote, *cert.votes[1:]), cert.hlc)
    assert not cluster.verify_certificate(tampered)
