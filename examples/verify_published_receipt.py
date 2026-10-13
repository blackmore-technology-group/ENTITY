#!/usr/bin/env python3
"""Verify a published ENTITY JSON receipt (stdlib only).

This example checks file integrity hashing and a minimal structural/self-hash
ruleset for supported public receipt schemas. It does not import ENTITY runtime
modules and does not prove external-world claims, legal ownership, or economic value.

Supported schemas (auto-selected from the ``schema`` field):

- ``entity-independent-node/receipt/v1`` — Independent Node Program transport receipt
  (see ``independent-node/README.md``). Verifies required fields and recomputes
  ``receipt_sha256`` using the same canonical JSON rules as ``independent-node/node.py``.

Example::

  python examples/verify_published_receipt.py examples/fixtures/independent_node_receipt_valid.json
  python examples/verify_published_receipt.py examples/fixtures/independent_node_receipt_tampered.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

HEX64 = re.compile(r"^[0-9a-f]{64}$")
RECEIPT_ID = re.compile(r"^inp-[0-9a-f]{32}$")
NODE_ID = re.compile(r"^ent-test-[0-9a-f]{16}$")

INP_RECEIPT_SCHEMA = "entity-independent-node/receipt/v1"
INP_EVENTS = ("RECEIVE", "REJECT")
INP_REQUIRED = (
    "schema",
    "receipt_id",
    "event",
    "timestamp",
    "receiver_node_id",
    "sender_node_id",
    "object_sha256",
    "origin_sha256",
    "lineage_depth",
    "result",
    "receipt_sha256",
)


def canon(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def content_sha256(value: Any) -> str:
    payload = value if isinstance(value, bytes) else canon(value)
    return hashlib.sha256(payload).hexdigest()


def load_receipt(path: Path) -> tuple[bytes, dict[str, Any]]:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"receipt is not UTF-8: {exc}") from exc
    try:
        doc = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc}") from exc
    if not isinstance(doc, dict):
        raise ValueError("receipt root must be a JSON object")
    return raw, doc


def verify_inp_receipt(doc: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if doc.get("schema") != INP_RECEIPT_SCHEMA:
        failures.append(f"schema must be {INP_RECEIPT_SCHEMA!r}")
        return failures
    for key in INP_REQUIRED:
        if key not in doc:
            failures.append(f"missing required field: {key}")
    if failures:
        return failures

    if not isinstance(doc["lineage_depth"], int) or isinstance(doc["lineage_depth"], bool) \
            or doc["lineage_depth"] < 0:
        failures.append("lineage_depth must be a non-negative integer (booleans are not integers)")
    for field in ("object_sha256", "origin_sha256", "receipt_sha256"):
        if not isinstance(doc[field], str) or not HEX64.match(doc[field]):
            failures.append(f"{field} must be a 64-character lowercase hex SHA-256 digest")
    if not isinstance(doc["receipt_id"], str) or not RECEIPT_ID.match(doc["receipt_id"]):
        failures.append("receipt_id must match 'inp-<32 lowercase hex>'")
    for field in ("receiver_node_id", "sender_node_id"):
        if not isinstance(doc[field], str) or not NODE_ID.match(doc[field]):
            failures.append(f"{field} must match 'ent-test-<16 lowercase hex>'")
    if doc["event"] not in INP_EVENTS:
        failures.append(f"event must be one of {INP_EVENTS}")
    if not isinstance(doc["timestamp"], str):
        failures.append("timestamp must be an ISO 8601 string")
    else:
        try:
            parsed = datetime.fromisoformat(doc["timestamp"])
        except ValueError:
            failures.append("timestamp must be a parseable ISO 8601 string")
        else:
            if parsed.tzinfo is None:
                failures.append("timestamp must carry a UTC offset")

    declared = doc.get("receipt_sha256")
    body = {k: v for k, v in doc.items() if k != "receipt_sha256"}
    expected = content_sha256(body)
    if declared != expected:
        failures.append("receipt_sha256 does not match canonical body hash (tampered or corrupt)")

    result = doc.get("result")
    if not isinstance(result, str) or not (result == "PASS" or result.startswith("FAIL:")):
        failures.append("result must be PASS or a FAIL: message from the harness")

    return failures


def verify_receipt(doc: dict[str, Any]) -> tuple[str, list[str]]:
    schema = doc.get("schema")
    if schema == INP_RECEIPT_SCHEMA:
        return schema, verify_inp_receipt(doc)
    return str(schema), [f"unsupported or missing receipt schema: {schema!r}"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify a published ENTITY JSON receipt (example tooling).")
    parser.add_argument("receipt", type=Path, help="path to published receipt JSON")
    args = parser.parse_args(argv)

    path = args.receipt.resolve()
    if not path.is_file():
        print(f"error: file not found: {path}", file=sys.stderr)
        return 2

    try:
        raw, doc = load_receipt(path)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    file_digest = hashlib.sha256(raw).hexdigest()
    schema, failures = verify_receipt(doc)

    print(f"file_sha256={file_digest}")
    print(f"schema={schema}")
    if failures:
        for item in failures:
            print(f"FAIL: {item}", file=sys.stderr)
        return 1

    print("PASS: structural and self-hash checks succeeded")
    print(
        "note: a matching self-hash only proves the file was not altered since it was written; "
        "anyone can recompute it. This tool does not verify signatures, runtime state, "
        "node identity, or external-world truth.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
