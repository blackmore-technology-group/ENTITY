from __future__ import annotations

from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from adam_v41.canonical import canonical_json_bytes, digest, sha256_bytes


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFORMATIONAL = "INFORMATIONAL"


class FindingStatus(str, Enum):
    OPEN = "OPEN"
    REMEDIATED = "REMEDIATED"
    ACCEPTED = "ACCEPTED"
    RETESTED = "RETESTED"


@dataclass(frozen=True)
class AuditFinding:
    finding_id: str
    scope: str
    severity: Severity
    title: str
    description: str
    status: FindingStatus
    evidence_hashes: tuple[str, ...]
    treatment: str | None = None


@dataclass(frozen=True)
class TrustedAssessor:
    assessor_id: str
    organization: str
    public_key: bytes
    key_id: str
    authorized_scope: tuple[str, ...] = ("SECURITY", "SAFETY", "OPERATIONS")
    active: bool = True

    def __post_init__(self) -> None:
        if not self.assessor_id or not self.organization or not self.key_id:
            raise ValueError("assessor identity, organization and key_id are required")
        if len(self.public_key) != 32:
            raise ValueError("assessor public key must be a 32-byte Ed25519 key")

    @property
    def fingerprint(self) -> str:
        return sha256_bytes(self.public_key)


class AssessorRegistry:
    """Explicit trust registry managed outside assessor receipts."""

    def __init__(self, assessors: Mapping[str, TrustedAssessor] | None = None) -> None:
        self._assessors: dict[str, TrustedAssessor] = dict(assessors or {})

    def register(self, assessor: TrustedAssessor) -> None:
        existing = self._assessors.get(assessor.assessor_id)
        if existing is not None and existing != assessor:
            raise ValueError("conflicting assessor registration")
        self._assessors[assessor.assessor_id] = assessor

    def require(self, assessor_id: str) -> TrustedAssessor:
        try:
            assessor = self._assessors[assessor_id]
        except KeyError as exc:
            raise PermissionError("assessor is not enrolled in the trusted registry") from exc
        if not assessor.active:
            raise PermissionError("assessor registration is disabled")
        return assessor

    def snapshot(self) -> Mapping[str, Any]:
        return {
            assessor_id: {
                "organization": assessor.organization,
                "key_id": assessor.key_id,
                "public_key_sha256": assessor.fingerprint,
                "authorized_scope": list(assessor.authorized_scope),
                "active": assessor.active,
            }
            for assessor_id, assessor in sorted(self._assessors.items())
        }


@dataclass(frozen=True)
class AssessorReceipt:
    assessor_id: str
    organization: str
    independent_of_operator: bool
    production_build_hash: str
    report_hash: str
    issued_at: int
    conclusion: str
    public_key: bytes
    signature: bytes
    key_id: str = "default"
    scope: tuple[str, ...] = ("SECURITY", "SAFETY", "OPERATIONS")

    def unsigned(self) -> dict[str, Any]:
        return {
            "assessor_id": self.assessor_id,
            "organization": self.organization,
            "independent_of_operator": self.independent_of_operator,
            "production_build_hash": self.production_build_hash,
            "report_hash": self.report_hash,
            "issued_at": self.issued_at,
            "conclusion": self.conclusion,
            "public_key": self.public_key.hex(),
            "key_id": self.key_id,
            "scope": list(self.scope),
        }

    @property
    def receipt_id(self) -> str:
        return digest("ADAM58:ASSESSOR_RECEIPT", {**self.unsigned(), "signature": self.signature})


@dataclass(frozen=True)
class ExternalGate:
    gate_id: str
    description: str
    evidence_hash: str | None
    passed: bool
    independently_verified: bool


@dataclass
class AssuranceCase:
    operator_id: str
    production_build_hash: str
    assessor_registry: AssessorRegistry | None = None
    findings: list[AuditFinding] = field(default_factory=list)
    gates: dict[str, ExternalGate] = field(default_factory=dict)
    assessor_receipt: AssessorReceipt | None = None

    REQUIRED_GATES = (
        "RUST_COMPILED_QUALIFIED",
        "HSM_HARDWARE_CUSTODY",
        "PHYSICAL_MULTI_HOST",
        "CERTIFIED_DEVICE_PILOT",
        "REAL_WORLD_TRAINING",
        "THIRTY_DAY_WALL_CLOCK",
        "INDEPENDENT_SECURITY_AUDIT",
    )

    def add_finding(self, finding: AuditFinding) -> None:
        if any(existing.finding_id == finding.finding_id for existing in self.findings):
            raise ValueError("duplicate finding id")
        self.findings.append(finding)

    def record_gate(self, gate: ExternalGate) -> None:
        if gate.gate_id not in self.REQUIRED_GATES:
            raise ValueError("unknown external gate")
        if gate.passed and not gate.evidence_hash:
            raise ValueError("passed external gates require immutable evidence")
        self.gates[gate.gate_id] = gate

    def attach_assessor_receipt(self, receipt: AssessorReceipt) -> None:
        if self.assessor_registry is None:
            raise PermissionError("no trusted assessor registry configured")
        trusted = self.assessor_registry.require(receipt.assessor_id)
        if not receipt.independent_of_operator or receipt.assessor_id == self.operator_id:
            raise PermissionError("assessor is not independent of the operator")
        if receipt.production_build_hash != self.production_build_hash:
            raise ValueError("assessor receipt is for another build")
        if receipt.organization != trusted.organization or receipt.key_id != trusted.key_id:
            raise PermissionError("assessor identity does not match trusted registration")
        if receipt.public_key != trusted.public_key:
            raise PermissionError("assessor public key is not the pinned trusted key")
        if not set(receipt.scope).issubset(set(trusted.authorized_scope)):
            raise PermissionError("assessor receipt exceeds its authorized scope")
        if receipt.conclusion not in {"PASS", "FAIL", "CONDITIONAL"}:
            raise ValueError("unsupported assessor conclusion")
        try:
            Ed25519PublicKey.from_public_bytes(trusted.public_key).verify(
                receipt.signature, canonical_json_bytes(receipt.unsigned())
            )
        except (InvalidSignature, ValueError) as exc:
            raise ValueError("assessor receipt signature is invalid") from exc
        self.assessor_receipt = receipt
        self.record_gate(
            ExternalGate(
                "INDEPENDENT_SECURITY_AUDIT",
                "independent security, safety and operational review",
                receipt.report_hash,
                receipt.conclusion == "PASS",
                True,
            )
        )

    def unresolved_findings(self) -> tuple[AuditFinding, ...]:
        return tuple(
            finding
            for finding in self.findings
            if finding.status not in {FindingStatus.RETESTED, FindingStatus.ACCEPTED}
        )

    def promotion_status(self) -> Mapping[str, Any]:
        blockers: list[str] = []
        independent_required = {
            "HSM_HARDWARE_CUSTODY",
            "PHYSICAL_MULTI_HOST",
            "CERTIFIED_DEVICE_PILOT",
            "THIRTY_DAY_WALL_CLOCK",
            "INDEPENDENT_SECURITY_AUDIT",
        }
        for gate_id in self.REQUIRED_GATES:
            gate = self.gates.get(gate_id)
            if gate is None or not gate.passed:
                blockers.append(f"external gate not passed: {gate_id}")
            elif not gate.evidence_hash:
                blockers.append(f"external gate lacks evidence: {gate_id}")
            elif not gate.independently_verified and gate_id in independent_required:
                blockers.append(f"external gate lacks independent verification: {gate_id}")
        for finding in self.unresolved_findings():
            if finding.severity in {Severity.CRITICAL, Severity.HIGH}:
                blockers.append(f"unresolved {finding.severity.value} finding: {finding.finding_id}")
        if self.assessor_receipt is None:
            blockers.append("no trusted independent assessor receipt")
        elif self.assessor_receipt.conclusion != "PASS":
            blockers.append("independent assessor conclusion is not PASS")
        return {
            "production_build_hash": self.production_build_hash,
            "promotable_to_v1": not blockers,
            "blockers": blockers,
            "gates": {key: asdict(value) for key, value in sorted(self.gates.items())},
            "findings": [asdict(finding) for finding in self.findings],
            "assessor_receipt": self.assessor_receipt.receipt_id if self.assessor_receipt else None,
            "assessor_registry": self.assessor_registry.snapshot() if self.assessor_registry else {},
        }
