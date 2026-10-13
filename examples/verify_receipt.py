#!/usr/bin/env python3
"""
Verify a published ENTITY usage receipt (schema ``entity-usage-receipt-v2``).

Usage:
    python3 verify_receipt.py path/to/receipt.json

Exits 0 when the receipt is well-formed and satisfies the documented
minimum field set for ``entity-usage-receipt-v2``; exits non-zero otherwise.

Field set and enum values are taken from ``_receipt()`` in
``src/01_Core_Runtime/usage_control/canonical_usage_control.py``.
Items this script verifies:
    - the file parses as JSON
    - the file's SHA-256 digest
    - the receipt's ``schema`` is ``entity-usage-receipt-v2``
    - documented required fields are present with the expected types
    - the enum fields hold a documented value
    - ``assurance_level`` matches the level documented for the ``assurance`` value
    - ``evidence_sha256`` is 64 lowercase hex characters

Items this script does not verify:
    - that the receipt has not been modified. A SHA-256 computed from the file
      only detects modification if compared to an independently trusted expected
      digest, which this script does not have.
    - that the ``signature`` field, if present, is valid. Signature verification
      requires the signer's manifest, a runtime dependency.
    - that ``evidence_sha256`` matches any actual evidence payload.
    - any real-world assertion the receipt makes (that the usage occurred, that the
      actor is who the receipt claims, that the assurance level was actually reached,
      or that any descriptive field is true).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


SCHEMA = "entity-usage-receipt-v2"

ASSURANCE_TO_LEVEL = {
    "DECLARED": 1,
    "ENTITY_GATEWAY_OBSERVED": 2,
    "COUNTERPARTY_ATTESTED": 3,
    "ENVIRONMENT_ATTESTED": 4
}

ASSURANCE_VALUES = frozenset(ASSURANCE_TO_LEVEL)

EVIDENCE_ORIGIN_VALUES = frozenset({
    "DIRECT_OBSERVATION",
    "ENTITY_ASSERTION",
    "COUNTERPARTY_ATTESTATION",
    "EXTERNAL_AUTHORITATIVE_RECORD"
})

_STRING_FIELDS = (
    "receipt_id",
    "licence_id",
    "actor_entity_id",
    "asset_id",
    "use_type",
    "purpose",
    "nonce"
)
_INT_FIELDS = ("quantity", "assurance_level", "created_at_ms")

_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


def sha256_of_file(path: Path) -> str:
    """Returns the SHA-256 of the file on disk, as a lowercase hex value."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def validate(receipt: object) -> None:
    """Fail closed on any deviation from the documented schema."""
    if not isinstance(receipt, dict):
        _fail("receipt must be a JSON object")

    if receipt.get("schema") != SCHEMA:
        _fail(f"unexpected schema: {receipt.get('schema')!r} (expected {SCHEMA!r})")

    # Presence and type
    for name in _STRING_FIELDS:
        value = receipt.get(name)
        if not isinstance(value, str) or not value:
            _fail(f"field {name!r} must be a non-empty string")

    for name in _INT_FIELDS:
        value = receipt.get(name)
        if isinstance(value, bool) or not isinstance(value, int):
            _fail(f"field {name!r} must be an integer")

    # Value ranges
    if receipt["quantity"] < 0:
        _fail("field 'quantity' must be non-negative")
    if receipt["created_at_ms"] < 0:
        _fail("field 'created_at_ms' must be a non-negative epoch-millisecond value")

    # Enumerations
    assurance = receipt.get("assurance")
    if assurance not in ASSURANCE_VALUES:
        _fail(f"field 'assurance' must be one of {sorted(ASSURANCE_VALUES)}")

    if receipt.get("evidence_origin") not in EVIDENCE_ORIGIN_VALUES:
        _fail(f"field 'evidence_origin' must be one of {sorted(EVIDENCE_ORIGIN_VALUES)}")

    # Cross-field check
    expected_level = ASSURANCE_TO_LEVEL[assurance]
    if expected_level != receipt["assurance_level"]:
        _fail(f"field 'assurance_level' is {receipt['assurance_level']} but assurance {assurance!r} requires level {expected_level}")

    # Format
    digest = receipt.get("evidence_sha256")
    if not isinstance(digest, str) or not _HEX64.match(digest):
        _fail("field 'evidence_sha256' must be 64 lowercase hex characters")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify a published ENTITY usage receipt.")
    parser.add_argument("path", type=Path, help="path to the receipt JSON file")
    args = parser.parse_args(argv)

    if not args.path.is_file():
        _fail(f"not a file: {args.path}")

    print(f"sha256: {sha256_of_file(args.path)}")

    try:
        raw = args.path.read_text(encoding="utf-8")
    except OSError as e:
        _fail(f"cannot read file: {e}")

    try:
        receipt = json.loads(raw)
    except json.JSONDecodeError as e:
        _fail(f"invalid JSON: {e}")

    validate(receipt)
    print(f"OK: {receipt['receipt_id']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())