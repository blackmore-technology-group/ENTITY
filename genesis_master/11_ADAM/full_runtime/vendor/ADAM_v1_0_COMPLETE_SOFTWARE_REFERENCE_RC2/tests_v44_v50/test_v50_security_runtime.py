from __future__ import annotations

import pytest

from adam_v50 import (
    CapabilityAuthority, ClosureNode, InferenceClosureAuthorizer, SecurityDomain,
    SovereignArtificialUniverse, SovereignAtomStore, WitnessNode, WitnessQuorum,
)


def test_domain_encryption_sovereignty_and_crypto_erasure():
    store = SovereignAtomStore()
    domain = SecurityDomain("CA_SECRET", "SECRET", ("CA",), ("OPS",), "NO_DEDUPE")
    store.register_domain(domain)
    a1 = store.put(b"private", domain_id="CA_SECRET", jurisdiction="CA", authority="OPS")
    a2 = store.put(b"private", domain_id="CA_SECRET", jurisdiction="CA", authority="OPS")
    assert a1 != a2
    assert store.get(a1, authority="OPS", jurisdiction="CA") == b"private"
    with pytest.raises(PermissionError):
        store.get(a1, authority="OPS", jurisdiction="US")
    store.erase_domain("CA_SECRET", authority="OPS")
    with pytest.raises(KeyError):
        store.get(a1, authority="OPS", jurisdiction="CA")


def test_purpose_bound_inference_closure_authorization():
    authority = CapabilityAuthority("AUTH")
    cap = authority.issue(subject="SHAWN", purposes=("OPERATIONS",), scopes=("PUBLIC", "OPS"), predicates=("READ",), expires_at=100)
    closure = InferenceClosureAuthorizer()
    closure.add(ClosureNode("A", "PUBLIC", "READ"))
    closure.add(ClosureNode("B", "OPS", "READ", dependencies=("A",)))
    assert closure.authorize(("B",), cap, authority.public_key, now=1, purpose="OPERATIONS", subject="SHAWN") == {"A", "B"}
    closure.add(ClosureNode("C", "OPS", "READ", inferable_scopes=("SECRET",)))
    with pytest.raises(PermissionError, match="inference"):
        closure.authorize(("C",), cap, authority.public_key, now=1, purpose="OPERATIONS", subject="SHAWN")


def test_witness_quorum_certifies_and_detects_chain_tamper():
    witnesses = [WitnessNode("W1"), WitnessNode("W2"), WitnessNode("W3")]
    quorum = WitnessQuorum(witnesses, 2)
    statements = quorum.certify("ROOT1")
    assert quorum.verify("ROOT1", statements)
    witnesses[0].statements[0] = type(statements[0])(**{**statements[0].__dict__, "universe_root": "TAMPER"})
    assert not witnesses[0].verify_chain()


def test_integrated_v50_runtime_health_and_root_certification():
    quorum = WitnessQuorum((WitnessNode("W1"), WitnessNode("W2")), 2)
    runtime = SovereignArtificialUniverse.create(quorum)
    statements = runtime.certify_current_root()
    assert runtime.witnesses.verify(runtime.physics.root, statements)
    health = runtime.health()
    assert health["physics_root"] == runtime.physics.root
    assert health["witnesses"] == 2


def test_distributed_physics_quorum_failover_and_recovery():
    from adam_v50 import DistributedPhysicsCluster
    from test_v44_physics import make_intent
    # The fixture is a factory here so every replica has identical genesis and laws.
    from conftest import assignment_kernel as fixture_function
    # pytest fixtures are wrapped; use the original function for deterministic replica creation.
    factory = getattr(fixture_function, "__wrapped__", fixture_function)
    cluster = DistributedPhysicsCluster(factory, 3)
    intent = make_intent(cluster.leader.kernel)
    cert = cluster.apply(intent)
    assert cert.new_root == cluster.leader.kernel.root
    assert cluster.verify_certificate(cert)
    assert len(cluster.roots()) == 1
    old_leader = cluster.leader_id
    cluster.stop(old_leader)
    assert cluster.leader_id != old_leader
    cluster.recover(old_leader)
    assert len(cluster.roots()) == 1


def test_v50_wall_clock_controller_refuses_early_or_test_certification(tmp_path):
    from adam_v50 import ProductionQualification50, QualificationError
    now = [1_000_000_000]
    quorum = WitnessQuorum((WitnessNode("W1"), WitnessNode("W2")), 2)
    controller = ProductionQualification50(
        tmp_path, quorum,
        health_probe=lambda: {"physics_root": "ROOT"},
        cycle=lambda: {"committed": True},
        duration_days=1, interval_seconds=1,
        now_ns=lambda: now[0], test_only=True,
    )
    now[0] += 1_000_000_000
    assert controller.run_cycle()["success"]
    with pytest.raises(QualificationError, match="test-only"):
        controller.finalize()


def test_distributed_certificate_rejects_duplicate_or_shrunk_quorum():
    from dataclasses import replace
    from adam_v44 import build_equipment_physics, assignment_intent
    from adam_v50 import DistributedPhysicsCluster
    cluster = DistributedPhysicsCluster(build_equipment_physics, 3)
    certificate = cluster.apply(assignment_intent(cluster.leader.kernel))
    assert cluster.verify_certificate(certificate)
    duplicated = replace(certificate, votes=(certificate.votes[0], certificate.votes[0]))
    assert not cluster.verify_certificate(duplicated)
    shrunk = replace(certificate, membership=(certificate.membership[0],), quorum=1)
    proposal = dict(certificate.proposal_payload)
    proposal["membership"] = [list(certificate.membership[0])]
    proposal["quorum"] = 1
    assert not cluster.verify_certificate_with_proposal(shrunk, proposal)


def test_witness_quorum_validates_supplied_unique_statements():
    from dataclasses import replace
    from adam_v50 import WitnessNode, WitnessQuorum
    witnesses = (WitnessNode("W1"), WitnessNode("W2"), WitnessNode("W3"))
    quorum = WitnessQuorum(witnesses, 2)
    statements = quorum.certify("ROOT")
    assert quorum.verify("ROOT", statements)
    assert not quorum.verify("ROOT", (statements[0], statements[0]))
    forged = replace(statements[0], signature=b"x" * 64)
    assert not quorum.verify("ROOT", (forged, statements[1]))
