from __future__ import annotations

import json
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from adam_v41.cognition import UniverseCognition
from adam_v42.safe_expression import SafeExpression, SafeExpressionError
from adam_v50.sovereignty import EncryptedAtom, SecurityDomain, SovereignAtomStore
from native_authority_reference import prepare_reference_command

ROOT = Path(__file__).parents[1]


def test_safe_expression_rejects_runtime_escape_vectors():
    for expression in (
        "__import__('os').system('id')",
        "value.__class__",
        "value[0]",
        "open('x')",
        "(lambda: 1)()",
    ):
        with pytest.raises(SafeExpressionError):
            SafeExpression.parse(expression)
    parsed = SafeExpression.parse("amount >= 10 and active")
    assert parsed.evaluate({"amount": 10, "active": True}) is True


def test_cognition_rejects_legacy_pickle_and_roundtrips_safe_json(tmp_path: Path):
    cognition, report = UniverseCognition.train(output_dir=tmp_path, train_examples=1000, test_examples=300)
    assert report.test_accuracy == 1.0
    restored = UniverseCognition.load(report.model_path)
    assert restored.predict_features([1, 0, 1, 0, 1, 1, 0, 0, 1])[0] == "ASSIGNED"
    unsafe = tmp_path / "unsafe.pkl"
    unsafe.write_bytes(b"\x80\x04cos\nsystem\n.")
    with pytest.raises(ValueError, match="legacy pickle"):
        UniverseCognition.load(unsafe)


def test_native_reference_replays_stale_root_and_detects_tamper(tmp_path: Path):
    native_dir = ROOT / "native_authority_reference"
    command, _compiled = prepare_reference_command(native_dir)
    log = tmp_path / "native.log"
    first = subprocess.run([*command, str(log)], input="APPEND 616263\nROOT\nQUIT\n", check=True, capture_output=True, text=True)
    root_line = [line for line in first.stdout.splitlines() if line.startswith("OK 1 ")][0]
    root = root_line.split()[-1]
    restarted = subprocess.run([*command, str(log)], input="VERIFY\nAPPEND " + ("00" * 32) + " 64\nAPPEND " + root + " 64\nQUIT\n", check=True, capture_output=True, text=True)
    assert root_line in restarted.stdout
    assert "ERR STALE_ROOT" in restarted.stdout
    assert "OK 2 " in restarted.stdout
    data = bytearray(log.read_bytes())
    data[-1] ^= 0x01
    log.write_bytes(data)
    tampered = subprocess.run([*command, str(log)], capture_output=True, text=True)
    assert tampered.returncode == 65
    assert "integrity failure" in tampered.stderr


def test_sovereign_atom_metadata_is_identity_and_aad_bound():
    store = SovereignAtomStore()
    domain = SecurityDomain("OPS", "PRIVATE", ("CA",), ("AUTH",))
    store.register_domain(domain)
    first = store.put(b"same", domain_id="OPS", jurisdiction="CA", authority="AUTH", metadata={"purpose": "a"})
    second = store.put(b"same", domain_id="OPS", jurisdiction="CA", authority="AUTH", metadata={"purpose": "b"})
    assert first != second
    atom = store.atoms[first]
    store.atoms[first] = replace(atom, metadata={"purpose": "tampered"})
    with pytest.raises(Exception):
        store.get(first, authority="AUTH", jurisdiction="CA")


def test_mechanical_source_audit_artifact_has_no_blocking_open_findings():
    # The mechanical audit is a separate top-level qualification gate.  This
    # test validates its signed release artifact without recursively launching
    # a compiler/subprocess tree from inside pytest, which can deadlock after
    # fork-heavy distributed tests on some platforms.
    path = ROOT / "artifacts/source_audit/ADAM_V1_RC2_SOURCE_AUDIT_RESULTS.json"
    assert path.exists(), "run tools/audit_source_tree.py before regression qualification"
    payload = json.loads(path.read_text())
    assert payload["version"] == "1.0.0-rc2"
    assert payload["summary"]["blocking_open_findings"] == 0
    assert payload["compileall_passed"] is True
    assert payload["native_reference"]["restart_verified"] is True
    assert payload["secret_file_audit"]["passed"] is True


def test_rust_targets_are_explicitly_uncompiled_but_static_hardened():
    payload = json.loads((ROOT / "artifacts/source_audit/ADAM_V1_RC2_SOURCE_AUDIT_RESULTS.json").read_text())
    assert len(payload["rust_targets"]) == 2
    for target in payload["rust_targets"]:
        assert all(target["static_gates"].values())
        if not target["cargo_available"]:
            assert target["compiled"] is False


def test_rust_audit_is_lockfile_aware_and_external_by_default():
    audit_source = (ROOT / "tools/audit_source_tree.py").read_text(encoding="utf-8")
    assert 'if (check_dir / "Cargo.lock").exists()' in audit_source
    assert 'command.append("--locked")' in audit_source
    assert 'rust_compile_external_review' in audit_source
    assert 'ADAM_REQUIRE_RUST' in audit_source

    for relative in ("rust_authority_kernel/src/main.rs", "rust_authority_kernel_v44/src/main.rs"):
        rust_source = (ROOT / relative).read_text(encoding="utf-8")
        assert "Response<serde_json::Value>" in rust_source
        assert "serde_json::to_value(value)" in rust_source
