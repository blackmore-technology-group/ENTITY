from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUST = ROOT / "rust_v051"


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_frozen_r4_wrapper_is_unchanged():
    path = ROOT / "lineage" / "v0501_r4" / "ADAM_V0501_R4.zip"
    assert file_hash(path) == "3c406f50710d3aad86952bf87b42ac27b5260a77f357461e21122054cb6812c4"


def test_python_oracle_regenerates_identical_vectors(tmp_path):
    path = RUST / "conformance" / "ADAM_V051_GOLDEN_VECTORS.json"
    before = path.read_bytes()
    subprocess.run(
        [sys.executable, str(ROOT / "tools_v051" / "generate_conformance_vectors.py")],
        cwd=ROOT,
        env={"PYTHONPATH": str(ROOT)},
        check=True,
        capture_output=True,
        text=True,
    )
    assert path.read_bytes() == before
    assert file_hash(path) == "bd371c85d27a2eda7dccf36795a5c6775670371c5b2942c6e1611b488b78e402"


def test_conformance_inventory_and_final_root():
    data = json.loads((RUST / "conformance" / "ADAM_V051_GOLDEN_VECTORS.json").read_text())
    assert len(data["primitive_vectors"]) == 24
    assert len(data["transitions"]) == 20
    assert data["final"]["root"] == "107a151ccc502420c650b69f6d98a41949fa2305bd39c0b8480f6a2676e11868"
    assert data["final"]["bond_key_integrity"] is True
    assert all(item["simulated_root_matches"] for item in data["transitions"])


def test_rust_target_and_fuzz_inventory_is_complete():
    crate = tomllib.loads((RUST / "crates" / "adam-v051-kernel" / "Cargo.toml").read_text())
    fuzz = tomllib.loads((RUST / "fuzz" / "Cargo.toml").read_text())
    assert {item["name"] for item in crate["bin"]} == {
        "adam-v051-authority-service",
        "adam-v051-conformance",
        "adam-v051-replay",
        "adam-v051-checkpoint",
        "adam-v051-proof-verify",
    }
    assert len(fuzz["bin"]) == 15


def test_static_source_qualification_has_no_blockers():
    subprocess.run(
        [sys.executable, str(ROOT / "tools_v051" / "audit_v051_source.py")],
        cwd=ROOT,
        env={"PYTHONPATH": str(ROOT)},
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(
        (ROOT / "artifacts" / "v051_source_qualification" / "ADAM_V051_SOURCE_QUALIFICATION.json").read_text()
    )
    assert data["source_status"] == "PASS"
    assert data["blocking_findings"] == 0
    assert data["r4_wrapper_verified"] is True
    assert data["golden_vectors_verified"] is True
    assert data["compiled_status"] != "PASS"


def test_production_rust_forbids_unsafe_and_runtime_shortcuts():
    source = RUST / "crates" / "adam-v051-kernel" / "src"
    combined = "\n".join(path.read_text() for path in source.rglob("*.rs"))
    assert "#![forbid(unsafe_code)]" in combined
    for marker in ["todo!", "unimplemented!", "NotImplemented", "TODO", "FIXME"]:
        assert marker not in combined
    assert "pub fn unpack" in combined
    assert "checkpoint diverges from genesis replay" in combined
    assert "certificate quorum is below majority" in combined


def test_ci_contains_cross_platform_memory_safety_and_fuzz_gates():
    workflow = (ROOT / ".github" / "workflows" / "adam-v051-rust.yml").read_text()
    for marker in [
        "ubuntu-latest",
        "windows-latest",
        "cargo fmt",
        "cargo clippy",
        "miri test",
        "sanitizer",
        "fuzz build",
        "cargo deny",
        "aarch64-unknown-linux-gnu",
    ]:
        assert marker in workflow


def test_cargo_lock_is_never_fabricated_without_cargo():
    audit = json.loads(
        (ROOT / "artifacts" / "v051_source_qualification" / "ADAM_V051_SOURCE_QUALIFICATION.json").read_text()
    )
    lock = RUST / "Cargo.lock"
    if not audit["cargo_available"]:
        assert not lock.exists()
        assert audit["cargo_lock_present"] is False
