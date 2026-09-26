from __future__ import annotations

import compileall
import hashlib
import json
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from adam_v1 import ArtificialLivingUniverseV1Candidate
from adam_v41.canonical import canonical_json_bytes
from adam_v52 import EncryptedSoftwareCustodyProvider
from adam_v53 import NetworkAuthorityCluster
from adam_v54 import CommandRequest, DeviceCapabilityContract, DevicePilot, ParameterRule
from adam_v55 import NearestCentroidOrgan, synthetic_sensor_dataset
from adam_v56 import CandidateFreezer, MetricSample, QualificationRecorder, SLOThresholds
from adam_v57 import DailyWitness, RealTimeQualificationController, WallClockQualificationError
from adam_v58 import AssuranceCase, AssessorReceipt, AssessorRegistry, ExternalGate, TrustedAssessor

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "artifacts" / "v1_qualification"
OUT.mkdir(parents=True, exist_ok=True)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def gate(name: str, fn: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    started = time.time()
    try:
        details = fn()
        return {"name": name, "passed": True, "duration_seconds": round(time.time() - started, 3), "details": details}
    except Exception as exc:  # qualification boundary records all failures
        return {
            "name": name,
            "passed": False,
            "duration_seconds": round(time.time() - started, 3),
            "error": type(exc).__name__,
            "message": str(exc),
        }


def parent_lineage_gate() -> dict[str, Any]:
    parent_zip = ROOT / "lineage" / "v051" / "ADAM_v0_51_RUST_AUTHORITY_KERNEL_SOURCE_QUALIFICATION_CANDIDATE_FULL_BUILD.zip"
    checksum_file = parent_zip.with_suffix(parent_zip.suffix + ".sha256")
    expected = checksum_file.read_text("utf-8").split()[0]
    actual = sha256(parent_zip)
    if actual != expected:
        raise RuntimeError("v0.51 parent checksum mismatch")
    return {"parent_sha256": actual, "parent_bytes": parent_zip.stat().st_size}


def compile_gate() -> dict[str, Any]:
    packages = [f"adam_v{version}" for version in (52, 53, 54, 55, 56, 57, 58)] + ["adam_v1"]
    ok = all(compileall.compile_dir(str(ROOT / package), quiet=1, force=True) for package in packages)
    if not ok:
        raise RuntimeError("production layer compilation failed")
    return {"packages": packages, "python": os.sys.version.split()[0]}


def custody_gate() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="adam-v52-") as directory:
        provider = EncryptedSoftwareCustodyProvider(directory, b"q" * 32)
        handle = provider.create_key(key_id="reaction", purpose="REACTION_SIGNING", jurisdiction="CA-BC")
        receipt = provider.sign(handle, b"reaction", purpose="REACTION_SIGNING", context={"root": "r1"})
        if not provider.verify_receipt(receipt, b"reaction") or provider.verify_receipt(receipt, b"tampered"):
            raise RuntimeError("custody receipt integrity failed")
        return {"receipt_id": receipt.receipt_id, "hardware_backed": False, "production_hsm_gate": "OPEN"}


def restart_gate() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="adam-v1-restart-") as directory:
        with ArtificialLivingUniverseV1Candidate.create(directory) as first:
            handle = first.key_hierarchy.require("CA-BC", "REACTION_SIGNING")
            public = first.custody.get_public_key(handle)
            release = first.release_public_key
        with ArtificialLivingUniverseV1Candidate.create(directory) as second:
            reopened = second.key_hierarchy.require("CA-BC", "REACTION_SIGNING")
            if reopened != handle or second.custody.get_public_key(reopened) != public or second.release_public_key != release:
                raise RuntimeError("persistent runtime identity changed across restart")
            receipt = second.custody.sign(reopened, b"restart", purpose="REACTION_SIGNING", context={})
            if not second.custody.verify_receipt(receipt, b"restart"):
                raise RuntimeError("reopened custody could not sign")
        return {"restart_safe": True, "key_handle": handle.handle_id}


def network_gate() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="adam-v53-") as directory:
        with NetworkAuthorityCluster(directory) as cluster:
            first = cluster.apply({"reaction": "CREATE_PROJECT", "project": "204"})
            cluster.partition(["net-2"])
            second = cluster.apply({"reaction": "ASSIGN_EQUIPMENT", "equipment": "12", "project": "204"})
            cluster.heal(["net-2"])
            cluster.stop_node("net-1")
            third = cluster.apply({"reaction": "ADVANCE_PROJECT", "project": "204"})
            cluster.recover_node("net-1")
            roots = {(row["root"], row["sequence"]) for row in cluster.health().values() if row.get("ok")}
            if roots != {(third.new_root, 3)}:
                raise RuntimeError("network authority did not converge after recovery")
            if not cluster.verify_certificate(second, {"reaction": "ASSIGN_EQUIPMENT", "equipment": "12", "project": "204"}):
                raise RuntimeError("durable certificate failed verification")
            if len(second.commit_votes) < second.quorum:
                raise RuntimeError("certificate lacks durable commit quorum")
            return {"commits": 3, "final_root": third.new_root, "durable_commit_votes": len(second.commit_votes)}


def device_gate() -> dict[str, Any]:
    contract = DeviceCapabilityContract(
        device_id="bounded-device",
        device_class="SIMULATED_LOW_ENERGY",
        jurisdiction="CA-BC",
        sensors=("pressure",),
        actuators=("output",),
        commands={"SET_OUTPUT": (ParameterRule("percent", 0.0, 25.0),)},
        safe_state={"output": 0.0},
        command_ttl_seconds=5,
        human_override_required=True,
        emergency_stop_required=True,
        maximum_command_rate_hz=1.0,
    )
    pilot = DevicePilot(contract)
    request = CommandRequest(contract.device_id, "SET_OUTPUT", {"percent": 10.0}, 100, 104, "operator", "goal", pilot.twin.root, "approved")
    receipt = pilot.evaluate(request, now=101, authority_allowed=True, safety_laws_passed=True, shadow_prediction_safe=True)
    if not receipt.accepted or receipt.hardware_execution:
        raise RuntimeError("bounded device reference produced invalid execution classification")
    pilot.emergency_stop()
    return {"receipt_id": receipt.receipt_id, "hardware_executed": receipt.hardware_execution, "emergency_stop": True}


def training_gate() -> dict[str, Any]:
    dataset = synthetic_sensor_dataset()
    organ = NearestCentroidOrgan("bounded-sensor")
    receipt = organ.train(dataset, validation_groups=("site-e",), test_groups=("site-f",), authorized_capability="SHADOW_ONLY", approved_by="independent-model-promotion-role")
    if receipt.test_accuracy != 1.0 or not organ.predict((1000.0, -1000.0, 500.0)).abstained:
        raise RuntimeError("bounded specialist organ failed accuracy or OOD gate")
    return {"dataset_root": receipt.dataset_root, "model_id": receipt.model_id, "ood_abstention": True}


def candidate_gate() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="adam-v56-") as directory:
        signer = Ed25519PrivateKey.generate()
        freezer = CandidateFreezer(directory, signer, signer_id="release-root")
        manifest = freezer.freeze(
            version="1.0.0-rc2",
            source_manifest=b"source",
            dependency_lock=b"lock",
            rust_binary_hashes={},
            deployment={"authority_nodes": 3, "physical_hosts": 1},
            thresholds=SLOThresholds(0.99, 100.0, 200.0, 10.0, 10.0, 1.0),
            operator="ADAM_DEVELOPMENT_OPERATOR",
            qualification_duration_seconds=30 * 24 * 60 * 60,
            external_gate_evidence={},
        )
        candidate_path = next(Path(directory).glob("*.candidate.json"))
        if CandidateFreezer.verify(candidate_path):
            raise RuntimeError("candidate self-authenticated without trust registry")
        if not CandidateFreezer.verify(candidate_path, {"release-root": signer.public_key().public_bytes_raw()}):
            raise RuntimeError("trusted candidate signature did not verify")
        recorder = QualificationRecorder(manifest, Path(directory) / "cycles")
        recorder.record_cycle(universe_root="root", authority_chain_valid=True, witness_count=3, metrics=(
            MetricSample("availability", 1.0, 1, {}),
            MetricSample("commit_latency_ms", 5.0, 1, {}),
            MetricSample("reconstruction_latency_ms", 10.0, 1, {}),
            MetricSample("failover_seconds", 1.0, 1, {}),
            MetricSample("root_convergence_seconds", 1.0, 1, {}),
            MetricSample("exact_recreation_success", 1.0, 1, {}),
            MetricSample("unauthorized_commits", 0.0, 1, {}),
            MetricSample("invariant_failures", 0.0, 1, {}),
            MetricSample("data_loss_events", 0.0, 1, {}),
        ), observed_at=1)
        if not recorder.evaluate().passed:
            raise RuntimeError("bounded SLO evaluation failed")
        return {"candidate_id": manifest.candidate_id, "trusted_release_signature": True}


def wall_clock_gate() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="adam-v57-") as directory:
        controller_key = Ed25519PrivateKey.generate()
        witness_key = Ed25519PrivateKey.generate()
        path = Path(directory) / "state.json"
        controller = RealTimeQualificationController(
            path,
            candidate_id="candidate",
            deployment_digest="deployment",
            required_seconds=24 * 60 * 60,
            minimum_witnesses=1,
            private_key=controller_key,
            trusted_witnesses={"independent-witness": witness_key.public_key().public_bytes_raw()},
        )
        if controller.certification_status()["certified"]:
            raise RuntimeError("wall-clock controller certified before real elapsed time")
        envelope = json.loads(path.read_text("utf-8"))
        envelope["payload"]["started_utc"] -= 86400 * 30
        path.write_text(json.dumps(envelope), "utf-8")
        try:
            RealTimeQualificationController(
                path,
                candidate_id="candidate",
                deployment_digest="deployment",
                required_seconds=24 * 60 * 60,
                minimum_witnesses=1,
                private_key=controller_key,
                trusted_witnesses={"independent-witness": witness_key.public_key().public_bytes_raw()},
            )
        except WallClockQualificationError:
            return {"early_certification_rejected": True, "state_tamper_rejected": True}
        raise RuntimeError("edited wall-clock state was accepted")


def assurance_gate() -> dict[str, Any]:
    trusted_private = Ed25519PrivateKey.generate()
    registry = AssessorRegistry({"assessor": TrustedAssessor("assessor", "Independent Lab", trusted_private.public_key().public_bytes_raw(), "key-1")})
    case = AssuranceCase(operator_id="operator", production_build_hash="build", assessor_registry=registry)
    for gate_id in case.REQUIRED_GATES:
        case.record_gate(ExternalGate(gate_id, gate_id, None, False, False))
    attacker = Ed25519PrivateKey.generate()
    unsigned = {
        "assessor_id": "assessor",
        "organization": "Independent Lab",
        "independent_of_operator": True,
        "production_build_hash": "build",
        "report_hash": "report",
        "issued_at": 1,
        "conclusion": "PASS",
        "public_key": attacker.public_key().public_bytes_raw(),
        "key_id": "key-1",
        "scope": ("SECURITY", "SAFETY", "OPERATIONS"),
    }
    provisional = AssessorReceipt(**unsigned, signature=b"")
    forged = AssessorReceipt(**unsigned, signature=attacker.sign(canonical_json_bytes(provisional.unsigned())))
    try:
        case.attach_assessor_receipt(forged)
    except PermissionError:
        pass
    else:
        raise RuntimeError("self-declared assessor bypassed registry")
    if case.promotion_status()["promotable_to_v1"]:
        raise RuntimeError("assurance case promoted without external evidence")
    return {"promotion_refused": True, "untrusted_assessor_rejected": True}


def source_gate() -> dict[str, Any]:
    operational = [ROOT / f"adam_v{version}" for version in (52, 53, 54, 55, 56, 57, 58)] + [ROOT / "adam_v1"]
    patterns = {
        "markers": re.compile(r"\b(?:" + "|".join(("TO" + "DO", "FIX" + "ME", "T" + "BD", "HA" + "CK")) + r")\b"),
        "unsafe_deserialization": re.compile(r"pickle\.(?:load|loads)\s*\("),
        "dynamic_execution": re.compile(r"\b(?:eval|exec)\s*\("),
        "runtime_stub": re.compile(r"NotImplementedError"),
    }
    findings: list[dict[str, Any]] = []
    file_count = 0
    line_count = 0
    for directory in operational:
        for path in directory.rglob("*.py"):
            file_count += 1
            text = path.read_text("utf-8")
            line_count += len(text.splitlines())
            for category, pattern in patterns.items():
                for match in pattern.finditer(text):
                    findings.append({"category": category, "path": str(path.relative_to(ROOT)), "match": match.group(0)})
    if findings:
        raise RuntimeError(f"blocking source findings: {findings}")
    return {"python_files": file_count, "source_lines": line_count, "blocking_findings": 0}


def runtime_gate() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="adam-v1-runtime-") as directory:
        with ArtificialLivingUniverseV1Candidate.create(directory) as runtime:
            training = runtime.train_bounded_sensor_organ()
            status = runtime.local_status()
            if status["promotion"]["promotable_to_v1"]:
                raise RuntimeError("software reference incorrectly reported external certification")
            return {"classification": status["classification"], "model_id": training["model_id"], "external_blockers": len(status["promotion"]["blockers"])}


def main() -> int:
    gates = [
        gate("frozen_v051_lineage", parent_lineage_gate),
        gate("python_source_compilation", compile_gate),
        gate("v052_custody_reference", custody_gate),
        gate("v1_restart_safe_persistent_identity", restart_gate),
        gate("v053_durable_commit_certificate", network_gate),
        gate("v054_bounded_device_pilot", device_gate),
        gate("v055_governed_training", training_gate),
        gate("v056_trusted_candidate_and_slo", candidate_gate),
        gate("v057_signed_wall_clock_and_independent_witness_policy", wall_clock_gate),
        gate("v058_trusted_assessor_registry", assurance_gate),
        gate("v1_source_hygiene", source_gate),
        gate("v1_integrated_software_reference_runtime", runtime_gate),
    ]
    failed = [item for item in gates if not item["passed"]]
    result = {
        "format": "ADAM-v1-rc2-local-software-qualification",
        "version": "1.0.0-rc2",
        "classification": "COMPLETE_SOFTWARE_REFERENCE_EXTERNAL_CERTIFICATION_REQUIRED",
        "generated_at": int(time.time()),
        "local_gates_passed": len(gates) - len(failed),
        "local_gates_failed": len(failed),
        "gates": gates,
        "external_certification_gates": {
            "hardware_hsm_kms_pkcs11": "OPEN",
            "physically_independent_multi_host_wan": "OPEN",
            "certified_physical_device_pilot": "OPEN",
            "large_licensed_real_world_training": "OPEN",
            "thirty_actual_wall_clock_days": "OPEN",
            "independent_security_safety_operational_audit": "OPEN",
        },
        "software_complete": not failed,
        "production_certified": False,
    }
    output = OUT / "ADAM_V1_RC2_LOCAL_QUALIFICATION_RESULTS.json"
    output.write_bytes(canonical_json_bytes(result))
    print(json.dumps(result, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
