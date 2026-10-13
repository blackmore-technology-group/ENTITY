"""ENTITY DataChip execution host: EXECUTE does not mean EXPORT.

Proposed isolated adapter for EDCF v0.2. Verifies actual canonical formula data,
ENTITY-signed execute grants and signed revocation, license, and device identity.
Bounds reconstructed data in memory, permits one vetted deterministic opcode,
never writes content bytes out, never imports/executes code from a DataChip.
"""
from __future__ import annotations

import hashlib
import io
from pathlib import Path
from collections.abc import Callable, Mapping
from typing import Any
import zipfile

from .execution_rights import ExecutionDenied, verify_execution_right
from .formula_chip import (
    inspect_formula, verify_formula, _open, _verified_chunks,
)

MAX_RUNTIME_INPUT = 4096
MAX_ARCHIVE_BYTES = 2 * 1024 * 1024

def execute_verified_formula(*, path: str | Path,
    expected_archive_sha256: str, expected_assembly_sha256: str,
    grant: dict, revocations: dict,
    trusted_issuer_keys: Mapping[str, bytes],
    trusted_revocation_keys: Mapping[str, bytes],
    authenticated_subject: str, authenticated_audience: str,
    authenticated_device: str,
    licensed_entitlement: Callable[..., bool],
    device_attestation: Callable[..., bool],
    trusted_revocation_checkpoint: int, now: int,
    approved_operation: str = "ascii_uppercase") -> dict[str, Any]:
    """Run one pinned bounded operation; return a digest, never reconstructed bytes."""
    if approved_operation != "ascii_uppercase":
        raise ExecutionDenied("unapproved host operation")
    p = Path(path)
    if not p.is_file() or p.is_symlink():
        raise ExecutionDenied("unsafe or absent EDCF source")
    if p.stat().st_size > MAX_ARCHIVE_BYTES:
        raise ExecutionDenied("EDCF archive cap exceeded")
    with p.open("rb") as src:
        archive = src.read(MAX_ARCHIVE_BYTES + 1)
    if len(archive) > MAX_ARCHIVE_BYTES:
        raise ExecutionDenied("EDCF archive cap exceeded")
    archive_sha256 = hashlib.sha256(archive).hexdigest()
    if archive_sha256 != expected_archive_sha256:
        raise ExecutionDenied("EDCF archive pin mismatch")
    try:
        manifest = inspect_formula(p)
        receipt = verify_formula(p)
    except Exception as exc:
        raise ExecutionDenied("genuine ENTITY content integrity check failed") from exc
    if receipt.get("integrity_verified") is not True or receipt.get("formula_native") is not True:
        raise ExecutionDenied("ENTITY formula not verified")
    if manifest["content_bytes"] > MAX_RUNTIME_INPUT:
        raise ExecutionDenied("execution content exceeds memory limit")
    if (receipt["chip_id"] != manifest["chip_id"]
        or receipt["content_sha256"] != manifest["content_sha256"]
        or receipt["content_bytes"] != manifest["content_bytes"]):
        raise ExecutionDenied("verified content receipt mismatch")
    # Authorize usage, not ownership; private records and KMS never cross this boundary.
    auth = verify_execution_right(
        grant, revocations, pinned_issuer_keys=trusted_issuer_keys,
        pinned_revocation_keys=trusted_revocation_keys,
        subject=authenticated_subject, audience=authenticated_audience,
        device_id=authenticated_device,
        chip_id=manifest["chip_id"],
        content_sha256=manifest["content_sha256"],
        assembly_sha256=expected_assembly_sha256,
        license_entitlement=licensed_entitlement,
        device_identity=device_attestation,
        protected_min_sequence=trusted_revocation_checkpoint, now=now)
    if not auth["execution_right_verified"]:
        raise ExecutionDenied("execution not authorized")
    if p.read_bytes() != archive:
        raise ExecutionDenied("archive changed during authorization")
    try:
        with zipfile.ZipFile(io.BytesIO(archive)) as zf:
            doc = _open(zf)
            if (doc["chip_id"] != manifest["chip_id"] or
                doc["content_sha256"] != manifest["content_sha256"]):
                raise ExecutionDenied("in-memory manifest changed")
            chunks = []
            total = 0
            for part in _verified_chunks(zf, doc):
                total += len(part)
                if total > MAX_RUNTIME_INPUT:
                    raise ExecutionDenied("in-memory reconstruction exceeded budget")
                chunks.append(part)
            raw = b"".join(chunks)
    except ExecutionDenied:
        raise
    except Exception as exc:
        raise ExecutionDenied("bounded reconstruction failed") from exc
    if not raw or any(char > 127 for char in raw):
        raise ExecutionDenied("approved ASCII operation requires 7-bit input")
    output = raw.upper()
    return {
        "schema": "entity-edc-authorized-execution-result-v0.1",
        "chip_id": manifest["chip_id"],
        "input_sha256": manifest["content_sha256"],
        "output_sha256": hashlib.sha256(output).hexdigest(),
        "operation": approved_operation,
        "grant_id": auth["grant_id"],
        "passport_id": auth["passport_id"],
        "content_integrity_verified": True,
        "issuer_execute_right_verified": True,
        "revocation_verified": True,
        "license_entitlement_verified": True,
        "device_adapter_verified": True,
        "export_permission": False,
        "private_content_exported": False,
        "production_hardware_attested": False,
        "production_ready": False,
    }
