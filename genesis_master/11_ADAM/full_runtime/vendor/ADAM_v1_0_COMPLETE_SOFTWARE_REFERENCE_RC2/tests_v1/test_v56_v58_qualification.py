from __future__ import annotations

import json
from dataclasses import replace

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from adam_v41.canonical import canonical_json_bytes
from adam_v56 import CandidateFreezer, MetricSample, QualificationRecorder, SLOThresholds
from adam_v57 import DailyWitness, RealTimeQualificationController, WallClockQualificationError
from adam_v58 import (
    AssuranceCase,
    AssessorReceipt,
    AssessorRegistry,
    AuditFinding,
    ExternalGate,
    FindingStatus,
    Severity,
    TrustedAssessor,
)


def thresholds() -> SLOThresholds:
    return SLOThresholds(0.99, 100.0, 200.0, 10.0, 10.0, 1.0)


def test_candidate_freeze_requires_explicit_trust_anchor_and_slo_evaluation(tmp_path):
    signer = Ed25519PrivateKey.generate()
    freezer = CandidateFreezer(tmp_path / "candidate", signer, signer_id="release-root")
    manifest = freezer.freeze(
        version="1.0.0-rc2",
        source_manifest=b"manifest",
        dependency_lock=b"lock",
        rust_binary_hashes={"kernel": "abc"},
        deployment={"nodes": 3},
        thresholds=thresholds(),
        operator="operator",
        qualification_duration_seconds=86400,
        external_gate_evidence={},
    )
    candidate_path = next((tmp_path / "candidate").glob("*.candidate.json"))
    assert not CandidateFreezer.verify(candidate_path)
    assert CandidateFreezer.verify(candidate_path, {"release-root": signer.public_key().public_bytes_raw()})
    assert not CandidateFreezer.verify(candidate_path, {"release-root": Ed25519PrivateKey.generate().public_key().public_bytes_raw()})

    recorder = QualificationRecorder(manifest, tmp_path / "cycles")
    for index in range(5):
        recorder.record_cycle(universe_root=f"root-{index}", authority_chain_valid=True, witness_count=3, metrics=(
            MetricSample("availability", 1.0, index, {}),
            MetricSample("commit_latency_ms", 10.0 + index, index, {}),
            MetricSample("reconstruction_latency_ms", 20.0, index, {}),
            MetricSample("failover_seconds", 2.0, index, {}),
            MetricSample("root_convergence_seconds", 1.0, index, {}),
            MetricSample("exact_recreation_success", 1.0, index, {}),
            MetricSample("unauthorized_commits", 0.0, index, {}),
            MetricSample("invariant_failures", 0.0, index, {}),
            MetricSample("data_loss_events", 0.0, index, {}),
        ), observed_at=index)
    result = recorder.evaluate()
    assert result.passed
    assert recorder.verify_chain()


def _controller(tmp_path):
    controller_key = Ed25519PrivateKey.generate()
    witness_key = Ed25519PrivateKey.generate()
    controller = RealTimeQualificationController(
        tmp_path / "wall.json",
        candidate_id="candidate",
        deployment_digest="deploy",
        required_seconds=86400,
        minimum_witnesses=1,
        private_key=controller_key,
        trusted_witnesses={"external-w1": witness_key.public_key().public_bytes_raw()},
    )
    return controller, controller_key, witness_key


def test_wall_clock_refuses_early_certification_and_untrusted_witness(tmp_path):
    controller, _, witness_key = _controller(tmp_path)
    status = controller.certification_status()
    assert not status["certified"]
    assert "required real elapsed time has not completed" in status["blockers"]
    template = controller.witness_template(universe_root="root", metrics={"availability": 1.0}, witness_id="external-w1")
    witness = DailyWitness.issue(private_key=witness_key, **template)
    controller.submit_daily_witness(witness)
    with pytest.raises(WallClockQualificationError):
        controller.submit_daily_witness(witness)
    forged = replace(witness, witness_id="unknown")
    with pytest.raises(WallClockQualificationError):
        controller.submit_daily_witness(forged)


def test_wall_clock_signed_state_rejects_policy_and_time_edit(tmp_path):
    controller, controller_key, witness_key = _controller(tmp_path)
    state_path = tmp_path / "wall.json"
    envelope = json.loads(state_path.read_text("utf-8"))
    envelope["payload"]["started_utc"] -= 10 * 86400
    envelope["payload"]["required_seconds"] = 1
    envelope["payload"]["minimum_witnesses"] = 0
    state_path.write_text(json.dumps(envelope), encoding="utf-8")
    with pytest.raises(WallClockQualificationError):
        RealTimeQualificationController(
            state_path,
            candidate_id="candidate",
            deployment_digest="deploy",
            required_seconds=86400,
            minimum_witnesses=1,
            private_key=controller_key,
            trusted_witnesses={"external-w1": witness_key.public_key().public_bytes_raw()},
        )


def test_assurance_case_blocks_until_external_independent_gates():
    case = AssuranceCase(operator_id="operator", production_build_hash="build", assessor_registry=AssessorRegistry())
    for gate_id in case.REQUIRED_GATES:
        case.record_gate(ExternalGate(gate_id, gate_id, None, False, False))
    case.add_finding(AuditFinding("F-1", "kernel", Severity.HIGH, "high", "description", FindingStatus.OPEN, ()))
    status = case.promotion_status()
    assert not status["promotable_to_v1"]
    assert any("F-1" in blocker for blocker in status["blockers"])


def test_assessor_receipt_must_match_pinned_trusted_registry():
    trusted_private = Ed25519PrivateKey.generate()
    registry = AssessorRegistry({
        "external-assessor": TrustedAssessor(
            "external-assessor",
            "Independent Labs",
            trusted_private.public_key().public_bytes_raw(),
            "key-2026",
        )
    })
    unsigned = {
        "assessor_id": "external-assessor",
        "organization": "Independent Labs",
        "independent_of_operator": True,
        "production_build_hash": "build",
        "report_hash": "report",
        "issued_at": 1,
        "conclusion": "PASS",
        "public_key": trusted_private.public_key().public_bytes_raw(),
        "key_id": "key-2026",
        "scope": ("SECURITY", "SAFETY", "OPERATIONS"),
    }
    provisional = AssessorReceipt(**unsigned, signature=b"")
    receipt = AssessorReceipt(**unsigned, signature=trusted_private.sign(canonical_json_bytes(provisional.unsigned())))
    case = AssuranceCase(operator_id="operator", production_build_hash="build", assessor_registry=registry)
    case.attach_assessor_receipt(receipt)
    assert case.assessor_receipt == receipt

    attacker = Ed25519PrivateKey.generate()
    forged_unsigned = {**unsigned, "public_key": attacker.public_key().public_bytes_raw()}
    forged_provisional = AssessorReceipt(**forged_unsigned, signature=b"")
    forged = AssessorReceipt(**forged_unsigned, signature=attacker.sign(canonical_json_bytes(forged_provisional.unsigned())))
    other = AssuranceCase(operator_id="operator", production_build_hash="build", assessor_registry=registry)
    with pytest.raises(PermissionError):
        other.attach_assessor_receipt(forged)
