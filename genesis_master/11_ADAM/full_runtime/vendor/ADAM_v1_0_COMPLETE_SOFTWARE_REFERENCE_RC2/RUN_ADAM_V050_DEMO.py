#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from adam_v44 import STANDARD_BOND_TABLE, assignment_intent, build_equipment_physics, release_intent
from adam_v45 import NeuralSymbolicCognitionFabric
from adam_v47 import IncrementalDependencyEngine, TemporalDynamicsOrgan, TransitionExample
from adam_v50 import (
    CapabilityAuthority, ClosureNode, DistributedPhysicsCluster, InferenceClosureAuthorizer,
    SecurityDomain, SovereignAtomStore, WitnessNode, WitnessQuorum,
)


def main() -> int:
    cluster = DistributedPhysicsCluster(build_equipment_physics, 3)
    for index in range(12):
        cluster.apply(assignment_intent(cluster.leader.kernel) if index % 2 == 0 else release_intent(cluster.leader.kernel))
        if index == 4:
            failed = cluster.leader_id
            cluster.stop(failed)
        if index == 8:
            cluster.recover(failed)

    cognition = NeuralSymbolicCognitionFabric()
    training = cognition.train(cluster.leader.kernel.algebra)

    dynamics = TemporalDynamicsOrgan()
    dynamics.train([
        TransitionExample(("AVAILABLE",), "ASSIGN_EQUIPMENT", ("NORMAL",), ("ASSIGNED",)),
        TransitionExample(("ASSIGNED",), "RELEASE_EQUIPMENT", ("NORMAL",), ("AVAILABLE",)),
    ] * 10)

    incremental = IncrementalDependencyEngine()
    incremental.set_base("cost", 120)
    incremental.set_base("budget", 100)
    incremental.add_derived("variance", ("cost", "budget"), lambda c: c["cost"] - c["budget"])

    store = SovereignAtomStore()
    store.register_domain(SecurityDomain("CA_SECRET", "SECRET", ("CA",), ("OPS",), "NO_DEDUPE"))
    atom_id = store.put(b"ADAM sovereign evidence", domain_id="CA_SECRET", jurisdiction="CA", authority="OPS")

    authority = CapabilityAuthority("ADAM_AUTH")
    capability = authority.issue(subject="SHAWN", purposes=("OPERATIONS",), scopes=("PUBLIC", "OPS"), predicates=("READ",), expires_at=100)
    closure = InferenceClosureAuthorizer()
    closure.add(ClosureNode("PUBLIC_FACT", "PUBLIC", "READ"))
    closure.add(ClosureNode("OPS_COMPOUND", "OPS", "READ", dependencies=("PUBLIC_FACT",)))
    authorized = closure.authorize(("OPS_COMPOUND",), capability, authority.public_key, now=1, purpose="OPERATIONS", subject="SHAWN")

    witness_quorum = WitnessQuorum((WitnessNode("W1"), WitnessNode("W2"), WitnessNode("W3")), 2)
    statements = witness_quorum.certify(cluster.leader.kernel.root)

    output = {
        "version": "0.50.0.dev1",
        "bond_families": 9,
        "standard_predicates": len(STANDARD_BOND_TABLE),
        "distributed_commits": cluster.index,
        "authority_term": cluster.term,
        "replica_roots": sorted(cluster.roots()),
        "last_certificate_valid": cluster.verify_certificate(cluster.certificates[-1]),
        "hyperbonds": len(cluster.leader.kernel.algebra.hyperbonds),
        "worldline_states": len(cluster.leader.kernel.worldlines["EX12"].states),
        "cognition_models": {name: run.run_id for name, run in training.items()},
        "dynamics_prediction": dynamics.predict(("AVAILABLE",), "ASSIGN_EQUIPMENT", ("NORMAL",)).next_signature,
        "incremental_variance": incremental.derived["variance"].value,
        "encrypted_atom": atom_id,
        "decryption_verified": store.get(atom_id, authority="OPS", jurisdiction="CA").decode(),
        "authorized_closure": sorted(authorized),
        "witness_quorum_verified": witness_quorum.verify(cluster.leader.kernel.root, statements),
        "claim_boundary": "Bounded development demonstration; not production certification.",
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
