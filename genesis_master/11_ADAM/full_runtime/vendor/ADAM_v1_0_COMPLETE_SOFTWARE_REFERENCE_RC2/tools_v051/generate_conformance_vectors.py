from __future__ import annotations
import json
from pathlib import Path
from adam_v41.canonical import pack, digest
from adam_v44 import (
    BondFamily, ConfidenceClass, FirstClassBond, HyperBond, HyperRole, TimeScope,
    build_equipment_physics, assignment_intent, release_intent,
)

OUT = Path(__file__).resolve().parents[1] / "rust_v051" / "conformance" / "ADAM_V051_GOLDEN_VECTORS.json"


def p(name, value):
    return {"name": name, "canonical_hex": pack(value).hex(), "sha256_test": digest("ADAM51:VECTOR", value)}

primitive = [
    p("null", None), p("false", False), p("true", True),
    p("uint_0", 0), p("uint_127", 127), p("uint_128", 128), p("uint_255", 255),
    p("uint_256", 256), p("uint_65535", 65535), p("uint_65536", 65536),
    p("uint_2_32", 2**32), p("neg_1", -1), p("neg_32", -32), p("neg_33", -33),
    p("neg_128", -128), p("neg_129", -129), p("float", 0.81), p("negative_zero", -0.0),
    p("empty_string", ""), p("short_string", "ADAM"), p("unicode", "Kootenay ⛰"),
    p("bytes", b"\x00\x01ADAM\xff"), p("array", [1, "A", None, True]),
    p("sorted_map", {"z": 1, "a": 2, "middle": [3, 4]}),
]

bond = FirstClassBond(
    "A", "SUPPORTED_BY", "E", BondFamily.EVIDENTIARY,
    direction="forward", order=2, time=TimeScope(1, None, 1), causal_parents=("C",),
    authority="AUTH", provenance=("P",), confidence=0.81,
    confidence_class=ConfidenceClass.SUPPORTED_HYPOTHESIS,
    security_scope="PRIVATE", chemistry_version="v44.1", reaction_origin="R",
    supporting_evidence=("E",), metadata={"note": "bounded", "ordinal": 7},
)
hyper = HyperBond(
    "ASSIGNMENT_EVENT",
    (HyperRole("ACTOR", "SHAWN"), HyperRole("DESTINATION", "P204"), HyperRole("EQUIPMENT", "EX12")),
    authority="OPS", time=TimeScope(4, None, 4), provenance=("SOURCE1",),
    security_scope="PUBLIC", chemistry_version="v44.1", causal_parents=(bond.bond_id,),
    confidence=1.0, metadata={"work_order": "WO88"},
)

kernel = build_equipment_physics()
initial = {
    "logical_time": kernel.logical_time,
    "root": kernel.root,
    "algebra_root": kernel.algebra.root(),
    "entities": dict(sorted(kernel.algebra.entity_types.items())),
    "constraints": sorted(kernel.algebra.constraints),
    "reaction_type_ids": {k: v.reaction_type_id for k, v in sorted(kernel.reactions.items())},
}
transitions = []
for i in range(20):
    intent = assignment_intent(kernel) if i % 2 == 0 else release_intent(kernel)
    before = kernel.root
    after_algebra, simulated = kernel.simulate(intent)
    proof = kernel.commit(intent)
    transitions.append({
        "index": i + 1,
        "reaction_name": intent.reaction_name,
        "intent": {
            "reaction_name": intent.reaction_name,
            "bindings": dict(intent.bindings),
            "actor": intent.actor,
            "authority": intent.authority,
            "capabilities": list(intent.capabilities),
            "expected_root": intent.expected_root,
            "proposer": intent.proposer,
            "approvers": list(intent.approvers),
        },
        "previous_root": before,
        "reaction_id": proof.reaction_id,
        "proof_id": proof.proof_id,
        "new_root": proof.new_root,
        "algebra_root": kernel.algebra.root(),
        "formed_bonds": list(proof.formed_bonds),
        "terminated_bonds": list(proof.terminated_bonds),
        "hyperbond_id": proof.hyperbond_id,
        "law_results": [list(x) for x in proof.law_results],
        "worldlines": {k: [list(x) for x in v.states] for k, v in sorted(kernel.worldlines.items()) if v.states},
        "simulated_root_matches": simulated.new_root == proof.new_root == kernel.root,
        "simulated_algebra_root": after_algebra.root(),
    })

payload = {
    "format": "ADAM-v0.51-python-rust-conformance-v1",
    "oracle": "ADAM v0.50.1 R4 Python canonical and v0.44 physics",
    "primitive_vectors": primitive,
    "bond": {"canonical": bond.canonical(), "canonical_hex": pack(bond.canonical()).hex(), "bond_id": bond.bond_id},
    "hyperbond": {"canonical": hyper.canonical(), "canonical_hex": pack(hyper.canonical()).hex(), "hyperbond_id": hyper.hyperbond_id},
    "initial_universe": initial,
    "transitions": transitions,
    "final": {
        "logical_time": kernel.logical_time,
        "root": kernel.root,
        "algebra_root": kernel.algebra.root(),
        "proof_ids": sorted(kernel.proofs),
        "reaction_ids": sorted(p.reaction_id for p in kernel.proofs.values()),
        "superseded_by": dict(sorted(kernel.algebra.superseded_by.items())),
        "bond_key_integrity": all(k == v.bond_id for k, v in kernel.algebra.bonds.items()),
    },
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(OUT)
print(json.dumps({"primitive": len(primitive), "transitions": len(transitions), "final_root": kernel.root}, indent=2))
