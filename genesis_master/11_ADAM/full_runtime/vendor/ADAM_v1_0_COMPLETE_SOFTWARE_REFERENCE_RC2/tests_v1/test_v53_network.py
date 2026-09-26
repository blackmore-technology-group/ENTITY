from __future__ import annotations

from dataclasses import replace

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from adam_v41.canonical import canonical_json_bytes
from adam_v53 import GovernedMembership, MembershipApproval, NetworkAuthorityCluster, NetworkAuthorityError


def test_network_cluster_quorum_partition_restart_and_recovery(tmp_path):
    with NetworkAuthorityCluster(tmp_path / "cluster") as cluster:
        cert1 = cluster.apply({"reaction": "create", "entity": "project-1"})
        assert cluster.verify_certificate(cert1, {"reaction": "create", "entity": "project-1"})
        assert not cluster.verify_certificate(cert1, {"reaction": "tampered"})
        assert len(cert1.prepare_votes) >= cert1.quorum
        assert len(cert1.commit_votes) >= cert1.quorum
        assert all(vote.phase == "commit" for vote in cert1.commit_votes)

        cluster.partition(["net-2"])
        cert2 = cluster.apply({"reaction": "advance", "state": 2})
        assert cert2.sequence == 2
        cluster.heal(["net-2"])
        roots = {(row["root"], row["sequence"]) for row in cluster.health().values() if row.get("ok")}
        assert len(roots) == 1

        cluster.stop_node("net-1")
        cert3 = cluster.apply({"reaction": "advance", "state": 3})
        assert cert3.sequence == 3
        cluster.recover_node("net-1")
        roots = {(row["root"], row["sequence"]) for row in cluster.health().values() if row.get("ok")}
        assert roots == {(cert3.new_root, 3)}


def test_network_cluster_rejects_no_quorum(tmp_path):
    with NetworkAuthorityCluster(tmp_path / "cluster") as cluster:
        cluster.partition(["net-1", "net-2"])
        with pytest.raises(NetworkAuthorityError):
            cluster.apply({"reaction": "unsafe"})


def test_network_certificate_requires_durable_commit_votes_and_epoch(tmp_path):
    with NetworkAuthorityCluster(tmp_path / "cluster") as cluster:
        payload = {"reaction": "bind-votes"}
        cert = cluster.apply(payload)
        forged_vote = replace(cert.commit_votes[0], signature=b"0" * 64)
        assert cluster.verify_certificate(cert, payload)
        assert not cluster.verify_certificate(replace(cert, commit_votes=(forged_vote,)), payload)
        assert not cluster.verify_certificate(replace(cert, commit_votes=()), payload)
        assert not cluster.verify_certificate(replace(cert, membership_epoch=99), payload)
        assert not cluster.verify_certificate(replace(cert, membership_digest="0" * 64), payload)


def test_governed_membership_requires_signed_current_quorum():
    private = {name: Ed25519PrivateKey.generate() for name in ("a", "b", "c")}
    membership = GovernedMembership({name: key.public_key().public_bytes_raw() for name, key in private.items()})
    add_key = Ed25519PrivateKey.generate().public_key().public_bytes_raw()
    proposal = membership.proposal_hash(add={"d": add_key})

    def approval(name: str) -> MembershipApproval:
        signature = private[name].sign(canonical_json_bytes({"node_id": name, "proposal_hash": proposal}))
        return MembershipApproval(name, proposal, signature)

    with pytest.raises(PermissionError):
        membership.change(add={"d": add_key}, approvals=(approval("a"),))
    assert membership.change(add={"d": add_key}, approvals=(approval("a"), approval("b"))) == 2
    assert "d" in membership.members


def test_governed_membership_rejects_plain_or_forged_approvals():
    private = {name: Ed25519PrivateKey.generate() for name in ("a", "b", "c")}
    membership = GovernedMembership({name: key.public_key().public_bytes_raw() for name, key in private.items()})
    add_key = Ed25519PrivateKey.generate().public_key().public_bytes_raw()
    proposal = membership.proposal_hash(add={"d": add_key})
    forged = MembershipApproval("a", proposal, b"0" * 64)
    with pytest.raises(PermissionError):
        membership.change(add={"d": add_key}, approvals=(forged,))
