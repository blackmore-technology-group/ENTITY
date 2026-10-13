"""Tests for examples/verify_receipt.py.

Covers the two acceptance paths from issue: the valid fixture exits 0 and
the tampered/malformed fixture exits non-zero. Also covers malformed input,
every required field's presence/type, and each value constraint the script
enforces.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
EXAMPLES = HERE.parent
SCRIPT = EXAMPLES / "verify_receipt.py"
FIXTURES = EXAMPLES / "fixtures"
VALID_FIXTURE = FIXTURES / "valid_usage_receipt.json"

ALL_STRING_FIELDS = (
    "schema",
    "receipt_id",
    "licence_id",
    "actor_entity_id",
    "asset_id",
    "use_type",
    "purpose",
    "assurance",
    "evidence_origin",
    "evidence_sha256",
    "nonce"
)
ALL_INT_FIELDS = ("quantity", "assurance_level", "created_at_ms")


def run(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(path)],
        capture_output=True,
        text=True
    )


def write_mutated(tmp_path: Path, **changes: object) -> Path:
    """Write the valid fixture with the given key/value changes applied."""
    receipt = json.loads(VALID_FIXTURE.read_text())
    receipt.update(changes)
    target = tmp_path / "receipt.json"
    target.write_text(json.dumps(receipt))
    return target


def write_without(tmp_path: Path, field: str) -> Path:
    """Write the valid fixture with one field removed."""
    receipt = json.loads(VALID_FIXTURE.read_text())
    del receipt[field]
    target = tmp_path / "receipt.json"
    target.write_text(json.dumps(receipt))
    return target


def assert_rejected(path: Path) -> None:
    """The script must exit non-zero and print a clean ``error:`` line.

    The stderr check matters: a raw Python traceback (e.g., an uncaught
    ``KeyError``) also exits non-zero, so checking the exit code alone would
    not distinguish a graceful rejection from a crash.
    """
    result = run(path)
    assert result.returncode != 0, result.stdout
    assert "error:" in result.stderr, result.stderr


# --------------------------------------------------------------------------- #
# Acceptance paths
# --------------------------------------------------------------------------- #
def test_valid_fixture_exits_zero() -> None:
    result = run(VALID_FIXTURE)
    assert result.returncode == 0, result.stderr
    assert "sha256:" in result.stdout
    assert "OK:" in result.stdout


def test_tampered_fixture_exits_one() -> None:
    result = run(FIXTURES / "tampered_usage_receipt.json")
    assert result.returncode == 1
    assert "error:" in result.stderr


def test_missing_file_exits_one() -> None:
    result = run(FIXTURES / "invalid_path.json")
    assert result.returncode == 1


def test_missing_argument_exits_two() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2


# --------------------------------------------------------------------------- #
# Malformed input
# --------------------------------------------------------------------------- #
def test_malformed_json_exits_nonzero(tmp_path: Path) -> None:
    path = tmp_path / "broken.json"
    path.write_text("{not valid json")
    result = run(path)
    assert result.returncode != 0
    assert "invalid JSON" in result.stderr


def test_non_object_json_exits_nonzero(tmp_path: Path) -> None:
    path = tmp_path / "list.json"
    path.write_text("[1, 2, 3]")
    result = run(path)
    assert result.returncode != 0
    assert "receipt must be a JSON object" in result.stderr


# --------------------------------------------------------------------------- #
# Field shape: presence and type
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("field", ALL_STRING_FIELDS)
def test_string_field_missing_rejected(tmp_path: Path, field: str) -> None:
    assert_rejected(write_without(tmp_path, field))


@pytest.mark.parametrize("field", ALL_STRING_FIELDS)
def test_string_field_wrong_type_rejected(tmp_path: Path, field: str) -> None:
    assert_rejected(write_mutated(tmp_path, **{field: 42}))


@pytest.mark.parametrize("field", ALL_STRING_FIELDS)
def test_string_field_empty_rejected(tmp_path: Path, field: str) -> None:
    assert_rejected(write_mutated(tmp_path, **{field: ""}))


@pytest.mark.parametrize("field", ALL_INT_FIELDS)
def test_int_field_missing_rejected(tmp_path: Path, field: str) -> None:
    assert_rejected(write_without(tmp_path, field))


@pytest.mark.parametrize("field", ALL_INT_FIELDS)
def test_int_field_wrong_type_rejected(tmp_path: Path, field: str) -> None:
    assert_rejected(write_mutated(tmp_path, **{field: "not-an-int"}))


@pytest.mark.parametrize("field", ALL_INT_FIELDS)
def test_int_field_boolean_rejected(tmp_path: Path, field: str) -> None:
    # bool is a subclass of int; the script must reject it explicitly.
    assert_rejected(write_mutated(tmp_path, **{field: True}))


# --------------------------------------------------------------------------- #
# Value constraints
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "schema",
    ["entity-usage-receipt-v1", "ENTITY-USAGE-RECEIPT-V2"]
)
def test_schema_must_match_exactly(tmp_path: Path, schema: str) -> None:
    assert_rejected(write_mutated(tmp_path, schema=schema))


@pytest.mark.parametrize(
    "assurance",
    ["UNKNOWN", "", "declared", "Declared"]
)
def test_assurance_must_be_documented_value(tmp_path: Path, assurance: str) -> None:
    assert_rejected(write_mutated(tmp_path, assurance=assurance))


@pytest.mark.parametrize(
    "evidence_origin",
    ["UNKNOWN", "", "direct_observation"]
)
def test_evidence_origin_must_be_documented_value(tmp_path: Path, evidence_origin: str) -> None:
    assert_rejected(write_mutated(tmp_path, evidence_origin=evidence_origin))


def test_assurance_level_must_match_assurance(tmp_path: Path) -> None:
    assert_rejected(write_mutated(tmp_path, assurance="DECLARED", assurance_level=4))


def test_quantity_must_be_non_negative(tmp_path: Path) -> None:
    assert_rejected(write_mutated(tmp_path, quantity=-1))


def test_created_at_ms_must_be_non_negative(tmp_path: Path) -> None:
    assert_rejected(write_mutated(tmp_path, created_at_ms=-1))


@pytest.mark.parametrize(
    "digest",
    ["not-a-hash", "abc", "z" * 64, "A" * 64, "0" * 63, "0" * 65]
)
def test_evidence_sha256_must_be_lowercase_hex(tmp_path: Path, digest: str) -> None:
    assert_rejected(write_mutated(tmp_path, evidence_sha256=digest))