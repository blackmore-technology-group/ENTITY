#!/usr/bin/env python3
"""Standalone ENTITY receipt verifier.

Verifies a published ENTITY Transaction Evidence Bundle (TEB) v1 receipt
without requiring the full ENTITY runtime. Uses Python standard library only.

Usage:
    python3 examples/verify_receipt.py <path-to-receipt.json>
    python3 examples/verify_receipt.py examples/valid_receipt.json
    python3 examples/verify_receipt.py examples/tampered_receipt.json

Exit codes:
    0 — receipt passed all checks
    1 — receipt failed validation (malformed JSON, missing fields, hash mismatch)
    2 — usage error (wrong arguments)

What this script verifies:
    1. The file is valid JSON.
    2. The JSON matches the entity-transaction-evidence-bundle-v1 schema fields.
    3. The transaction_root_sha256 matches SHA-256(canonical_json(evidence)).
    4. All required evidence sections are present.
    5. The signature field is present and well-formed.

What this script does NOT prove:
    - The receipt has not been modified since issuance (only an independently
      trusted expected digest can prove that; a freshly computed hash proves
      only that the file hasn't changed since you last computed it).
    - The signature is cryptographically valid (requires the issuer's public key
      and signature verification logic, not included in this minimal example).
    - The signing entity is trusted (trust-anchor acceptance is a deployment
      decision, per §5 of the TEB spec).
    - The underlying real-world assertions are true (a valid receipt proves
      structural integrity, not factual truth).
"""
import hashlib
import json
import sys
from pathlib import Path


# Required top-level fields per ENTITY_TRANSACTION_EVIDENCE_BUNDLE_v1 §3
REQUIRED_TOP_LEVEL = {
    "schema",
    "transaction_id",
    "issuer_entity_id",
    "transaction_root_sha256",
    "generated_at_ms",
    "evidence",
    "signature",
    "evidence_boundary",
}

# Required evidence sections per §4
REQUIRED_EVIDENCE_SECTIONS = {
    "transaction_record",
    "manifests",
    "asset_provenance",
    "rights",
    "licence",
    "usage_receipt",
    "license_settlement",
    "value_record",
    "digital_commodity",
    "corporate_authorization",
    "capital",
    "share_settlement",
    "event_ledger",
    "external_trust_anchors",
}

SCHEMA_EXPECTED = "entity-transaction-evidence-bundle-v1"


def canonical_json(obj) -> str:
    """Produce canonical JSON per §3: UTF-8, sorted keys, no whitespace, `,` and `:` separators."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def compute_transaction_root(evidence: dict) -> str:
    """SHA-256(canonical_json(evidence)) per §3."""
    canonical = canonical_json(evidence)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify_receipt(path: Path) -> list[str]:
    """Verify a receipt file. Returns list of errors (empty = valid)."""
    errors = []

    # 1. Read and parse JSON
    try:
        raw = path.read_bytes()
    except OSError as e:
        return [f"cannot read file: {e}"]

    try:
        receipt = json.loads(raw)
    except json.JSONDecodeError as e:
        return [f"invalid JSON: {e}"]

    if not isinstance(receipt, dict):
        return ["top-level JSON is not an object"]

    # 2. Print file SHA-256 (informational, not proof of integrity)
    file_sha256 = hashlib.sha256(raw).hexdigest()
    print(f"File SHA-256: {file_sha256}")
    print(f"  (note: this hash proves only that the file hasn't changed since")
    print(f"   you computed it. An independently trusted expected digest is")
    print(f"   needed to prove the file hasn't been modified since issuance.)")
    print()

    # 3. Check schema field
    schema = receipt.get("schema", "")
    if schema != SCHEMA_EXPECTED:
        errors.append(
            f"schema mismatch: expected '{SCHEMA_EXPECTED}', got '{schema}'"
        )
        # If schema is wrong, remaining checks may not apply
        if not schema:
            return errors

    # 4. Check required top-level fields
    missing_top = REQUIRED_TOP_LEVEL - set(receipt.keys())
    if missing_top:
        errors.append(
            f"missing required top-level fields: {sorted(missing_top)}"
        )

    # 5. Compute and verify transaction_root_sha256
    evidence = receipt.get("evidence")
    declared_root = receipt.get("transaction_root_sha256", "")
    if evidence is None:
        if "evidence" not in receipt:
            errors.append("'evidence' field is missing — cannot compute transaction root")
        else:
            errors.append("'evidence' field is null")
    elif not isinstance(evidence, dict):
        errors.append(f"'evidence' must be an object, got {type(evidence).__name__}")
    else:
        computed_root = compute_transaction_root(evidence)
        print(f"Declared transaction_root_sha256: {declared_root}")
        print(f"Computed transaction_root_sha256: {computed_root}")
        print()
        if computed_root != declared_root:
            errors.append(
                f"transaction_root_sha256 mismatch: "
                f"declared '{declared_root}' does not match "
                f"computed '{computed_root}' — evidence has been modified"
            )

    # 6. Check required evidence sections
    if isinstance(evidence, dict):
        missing_sections = REQUIRED_EVIDENCE_SECTIONS - set(evidence.keys())
        if missing_sections:
            errors.append(
                f"missing required evidence sections: {sorted(missing_sections)}"
            )

    # 7. Check signature field is present and well-formed
    signature = receipt.get("signature")
    if signature is None:
        errors.append("'signature' field is missing")
    elif not isinstance(signature, dict):
        errors.append(f"'signature' must be an object, got {type(signature).__name__}")
    else:
        # Per §5: ENTITY-native signatures use an explicitly identified
        # signature record and key version
        sig_fields = {"algorithm", "value", "key_id", "signed_at"}
        missing_sig = sig_fields - set(signature.keys())
        if missing_sig:
            errors.append(
                f"signature missing fields: {sorted(missing_sig)}"
            )

    return errors


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <path-to-receipt.json>", file=sys.stderr)
        print(f"  Example: {sys.argv[0]} examples/valid_receipt.json", file=sys.stderr)
        sys.exit(2)

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"Error: file not found: {path}", file=sys.stderr)
        sys.exit(1)

    print(f"Verifying: {path}")
    print()

    errors = verify_receipt(path)

    if errors:
        print(f"❌ FAILED — {len(errors)} error(s):")
        for e in errors:
            print(f"  • {e}")
        print()
        print("This receipt did NOT pass verification. Do not trust it.")
        sys.exit(1)
    else:
        print("✅ PASSED — all structural checks succeeded.")
        print()
        print("What was verified:")
        print("  ✓ Valid JSON")
        print("  ✓ Schema field matches entity-transaction-evidence-bundle-v1")
        print("  ✓ All required top-level fields present")
        print("  ✓ transaction_root_sha256 matches computed SHA-256 of evidence")
        print("  ✓ All 14 required evidence sections present")
        print("  ✓ Signature field is present and well-formed")
        print()
        print("What was NOT verified (requires additional context):")
        print("  ✗ Cryptographic signature validity (needs issuer public key)")
        print("  ✗ Trust anchor acceptance (deployment decision)")
        print("  ✗ Factual truth of underlying assertions")
        sys.exit(0)


if __name__ == "__main__":
    main()
