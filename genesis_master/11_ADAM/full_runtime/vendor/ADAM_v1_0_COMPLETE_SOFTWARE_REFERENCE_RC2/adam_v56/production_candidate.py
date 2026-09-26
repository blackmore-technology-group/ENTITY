from __future__ import annotations

import json
import math
import os
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from adam_v41.canonical import canonical_json_bytes, digest, sha256_bytes


class CandidateFreezeError(RuntimeError):
    """Raised when a frozen production candidate is mutated or misrepresented."""


@dataclass(frozen=True)
class SLOThresholds:
    availability_min: float
    commit_latency_p95_ms_max: float
    reconstruction_latency_p95_ms_max: float
    failover_seconds_max: float
    root_convergence_seconds_max: float
    exact_recreation_success_min: float
    unauthorized_commits_max: int = 0
    invariant_failures_max: int = 0
    data_loss_events_max: int = 0

    def validate(self) -> None:
        if not 0.0 <= self.availability_min <= 1.0:
            raise ValueError("availability_min must be in [0,1]")
        if not 0.0 <= self.exact_recreation_success_min <= 1.0:
            raise ValueError("exact_recreation_success_min must be in [0,1]")
        for name in (
            "commit_latency_p95_ms_max",
            "reconstruction_latency_p95_ms_max",
            "failover_seconds_max",
            "root_convergence_seconds_max",
        ):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")


@dataclass(frozen=True)
class ProductionCandidateManifest:
    candidate_id: str
    version: str
    source_manifest_hash: str
    dependency_lock_hash: str
    rust_binary_hashes: Mapping[str, str]
    deployment_digest: str
    thresholds: SLOThresholds
    created_at: int
    operator: str
    release_signer_id: str
    qualification_duration_seconds: int
    external_gate_evidence: Mapping[str, str]

    @property
    def manifest_hash(self) -> str:
        return digest(
            "ADAM56:PRODUCTION_CANDIDATE",
            {
                **asdict(self),
                "thresholds": asdict(self.thresholds),
                "rust_binary_hashes": dict(sorted(self.rust_binary_hashes.items())),
                "external_gate_evidence": dict(sorted(self.external_gate_evidence.items())),
            },
        )


@dataclass(frozen=True)
class MetricSample:
    name: str
    value: float
    observed_at: int
    labels: Mapping[str, str]


@dataclass(frozen=True)
class FaultEvent:
    kind: str
    started_at: int
    recovered_at: int | None
    expected: bool
    evidence_hash: str


@dataclass(frozen=True)
class QualificationCycle:
    cycle_index: int
    observed_at: int
    universe_root: str
    authority_chain_valid: bool
    witness_count: int
    metrics: tuple[MetricSample, ...]
    faults: tuple[FaultEvent, ...]
    software_version: str
    deployment_digest: str
    previous_cycle: str | None
    signature: bytes

    def unsigned(self) -> dict[str, Any]:
        return {
            "cycle_index": self.cycle_index,
            "observed_at": self.observed_at,
            "universe_root": self.universe_root,
            "authority_chain_valid": self.authority_chain_valid,
            "witness_count": self.witness_count,
            "metrics": [asdict(item) for item in self.metrics],
            "faults": [asdict(item) for item in self.faults],
            "software_version": self.software_version,
            "deployment_digest": self.deployment_digest,
            "previous_cycle": self.previous_cycle,
        }

    @property
    def cycle_id(self) -> str:
        return digest("ADAM56:QUALIFICATION_CYCLE", {**self.unsigned(), "signature": self.signature})


@dataclass
class SLOEvaluation:
    passed: bool
    measurements: Mapping[str, Any]
    failures: tuple[str, ...]


def _public_key_bytes(value: bytes | Ed25519PublicKey) -> bytes:
    if isinstance(value, Ed25519PublicKey):
        return value.public_bytes_raw()
    if not isinstance(value, bytes) or len(value) != 32:
        raise ValueError("trusted signer public keys must be 32-byte Ed25519 keys")
    return value


class CandidateFreezer:
    """Create candidate envelopes verified only through an explicit trust registry.

    The prior implementation embedded its own public key and then trusted that
    same key during verification.  RC2 removes that self-authentication path:
    verification requires a caller-supplied signer registry whose trust anchor
    is managed outside the candidate envelope.
    """

    def __init__(
        self,
        output_dir: str | os.PathLike[str],
        private_key: Ed25519PrivateKey | None = None,
        *,
        signer_id: str = "UNTRUSTED_EPHEMERAL_DEVELOPMENT_SIGNER",
    ) -> None:
        if not signer_id:
            raise ValueError("signer_id is required")
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._private = private_key or Ed25519PrivateKey.generate()
        self.public_key = self._private.public_key()
        self.signer_id = signer_id

    def freeze(
        self,
        *,
        version: str,
        source_manifest: bytes,
        dependency_lock: bytes,
        rust_binary_hashes: Mapping[str, str],
        deployment: Mapping[str, Any],
        thresholds: SLOThresholds,
        operator: str,
        qualification_duration_seconds: int,
        external_gate_evidence: Mapping[str, str],
    ) -> ProductionCandidateManifest:
        thresholds.validate()
        if qualification_duration_seconds <= 0:
            raise ValueError("qualification duration must be positive")
        common = {
            "version": version,
            "source_manifest_hash": sha256_bytes(source_manifest),
            "dependency_lock_hash": sha256_bytes(dependency_lock),
            "rust_binary_hashes": dict(sorted(rust_binary_hashes.items())),
            "deployment_digest": digest("ADAM56:DEPLOYMENT", dict(deployment)),
            "created_at": int(time.time()),
            "operator": operator,
            "release_signer_id": self.signer_id,
            "qualification_duration_seconds": qualification_duration_seconds,
            "external_gate_evidence": dict(sorted(external_gate_evidence.items())),
        }
        material = {**common, "thresholds": asdict(thresholds)}
        candidate_id = digest("ADAM56:CANDIDATE_ID", material)
        manifest = ProductionCandidateManifest(candidate_id=candidate_id, thresholds=thresholds, **common)
        manifest_object = {**asdict(manifest), "thresholds": asdict(thresholds)}
        payload = canonical_json_bytes(manifest_object)
        signature = self._private.sign(payload)
        public_raw = self.public_key.public_bytes_raw()
        envelope = {
            "format": "ADAM56_TRUSTED_CANDIDATE_ENVELOPE_V2",
            "manifest": manifest_object,
            "signer_id": self.signer_id,
            "signer_public_key_sha256": sha256_bytes(public_raw),
            "signature": signature.hex(),
        }
        path = self.output_dir / f"{candidate_id}.candidate.json"
        temporary = path.with_suffix(".tmp")
        with temporary.open("wb") as handle:
            handle.write(canonical_json_bytes(envelope))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        return manifest

    @staticmethod
    def verify(
        path: str | os.PathLike[str],
        trusted_signers: Mapping[str, bytes | Ed25519PublicKey] | None = None,
    ) -> bool:
        if not trusted_signers:
            return False
        try:
            envelope = json.loads(Path(path).read_text("utf-8"))
            if envelope.get("format") != "ADAM56_TRUSTED_CANDIDATE_ENVELOPE_V2":
                return False
            manifest = envelope["manifest"]
            signer_id = str(envelope["signer_id"])
            trusted = _public_key_bytes(trusted_signers[signer_id])
            if envelope.get("signer_public_key_sha256") != sha256_bytes(trusted):
                return False
            Ed25519PublicKey.from_public_bytes(trusted).verify(
                bytes.fromhex(envelope["signature"]), canonical_json_bytes(manifest)
            )
            if manifest.get("release_signer_id") != signer_id:
                return False
            candidate_id = manifest.get("candidate_id")
            material = {key: value for key, value in manifest.items() if key != "candidate_id"}
            return candidate_id == digest("ADAM56:CANDIDATE_ID", material)
        except (InvalidSignature, ValueError, KeyError, TypeError, json.JSONDecodeError, OSError):
            return False


class QualificationRecorder:
    def __init__(
        self,
        manifest: ProductionCandidateManifest,
        output_dir: str | os.PathLike[str],
        private_key: Ed25519PrivateKey | None = None,
    ) -> None:
        self.manifest = manifest
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._private = private_key or Ed25519PrivateKey.generate()
        self.public_key = self._private.public_key()
        self.cycles: list[QualificationCycle] = []

    def record_cycle(
        self,
        *,
        universe_root: str,
        authority_chain_valid: bool,
        witness_count: int,
        metrics: Iterable[MetricSample],
        faults: Iterable[FaultEvent] = (),
        observed_at: int | None = None,
    ) -> QualificationCycle:
        observed_at = int(time.time()) if observed_at is None else observed_at
        unsigned = {
            "cycle_index": len(self.cycles) + 1,
            "observed_at": observed_at,
            "universe_root": universe_root,
            "authority_chain_valid": authority_chain_valid,
            "witness_count": witness_count,
            "metrics": tuple(metrics),
            "faults": tuple(faults),
            "software_version": self.manifest.version,
            "deployment_digest": self.manifest.deployment_digest,
            "previous_cycle": self.cycles[-1].cycle_id if self.cycles else None,
        }
        signature = self._private.sign(
            canonical_json_bytes(
                {
                    **unsigned,
                    "metrics": [asdict(item) for item in unsigned["metrics"]],
                    "faults": [asdict(item) for item in unsigned["faults"]],
                }
            )
        )
        cycle = QualificationCycle(**unsigned, signature=signature)
        self.cycles.append(cycle)
        with (self.output_dir / "cycles.jsonl").open("ab") as handle:
            handle.write(
                canonical_json_bytes(
                    {**cycle.unsigned(), "signature": signature.hex(), "cycle_id": cycle.cycle_id}
                )
                + b"\n"
            )
            handle.flush()
            os.fsync(handle.fileno())
        return cycle

    def verify_chain(self) -> bool:
        previous = None
        for index, cycle in enumerate(self.cycles, start=1):
            if cycle.cycle_index != index or cycle.previous_cycle != previous:
                return False
            try:
                self.public_key.verify(cycle.signature, canonical_json_bytes(cycle.unsigned()))
            except (InvalidSignature, ValueError):
                return False
            previous = cycle.cycle_id
        return True

    @staticmethod
    def _p95(values: list[float]) -> float:
        if not values:
            return math.inf
        ordered = sorted(values)
        index = min(len(ordered) - 1, max(0, int(round(0.95 * (len(ordered) - 1)))))
        return ordered[index]

    def evaluate(self) -> SLOEvaluation:
        thresholds = self.manifest.thresholds
        failures: list[str] = []
        metrics: dict[str, list[float]] = {}
        for cycle in self.cycles:
            for sample in cycle.metrics:
                metrics.setdefault(sample.name, []).append(sample.value)
        availability = sum(metrics.get("availability", [])) / max(1, len(metrics.get("availability", [])))
        exact_success = sum(metrics.get("exact_recreation_success", [])) / max(
            1, len(metrics.get("exact_recreation_success", []))
        )
        commit_p95 = self._p95(metrics.get("commit_latency_ms", []))
        reconstruction_p95 = self._p95(metrics.get("reconstruction_latency_ms", []))
        failover_max = max(metrics.get("failover_seconds", [0.0]))
        convergence_max = max(metrics.get("root_convergence_seconds", [0.0]))
        unauthorized = int(sum(metrics.get("unauthorized_commits", [])))
        invariant = int(sum(metrics.get("invariant_failures", [])))
        data_loss = int(sum(metrics.get("data_loss_events", [])))
        checks = {
            "availability": availability >= thresholds.availability_min,
            "commit_latency_p95_ms": commit_p95 <= thresholds.commit_latency_p95_ms_max,
            "reconstruction_latency_p95_ms": reconstruction_p95 <= thresholds.reconstruction_latency_p95_ms_max,
            "failover_seconds": failover_max <= thresholds.failover_seconds_max,
            "root_convergence_seconds": convergence_max <= thresholds.root_convergence_seconds_max,
            "exact_recreation_success": exact_success >= thresholds.exact_recreation_success_min,
            "unauthorized_commits": unauthorized <= thresholds.unauthorized_commits_max,
            "invariant_failures": invariant <= thresholds.invariant_failures_max,
            "data_loss_events": data_loss <= thresholds.data_loss_events_max,
            "authority_chain": all(cycle.authority_chain_valid for cycle in self.cycles),
            "cycle_chain": self.verify_chain(),
        }
        failures.extend(name for name, passed in checks.items() if not passed)
        return SLOEvaluation(
            passed=not failures,
            measurements={
                "availability": availability,
                "commit_latency_p95_ms": commit_p95,
                "reconstruction_latency_p95_ms": reconstruction_p95,
                "failover_seconds_max": failover_max,
                "root_convergence_seconds_max": convergence_max,
                "exact_recreation_success": exact_success,
                "unauthorized_commits": unauthorized,
                "invariant_failures": invariant,
                "data_loss_events": data_loss,
                "checks": checks,
            },
            failures=tuple(failures),
        )
