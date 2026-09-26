from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUST = ROOT / "rust_v051"
ARTIFACTS = ROOT / "artifacts" / "v051_source_qualification"
JSON_OUT = ARTIFACTS / "ADAM_V051_SOURCE_QUALIFICATION.json"
MD_OUT = ARTIFACTS / "ADAM_V051_SOURCE_QUALIFICATION.md"
EXPECTED_R4_SHA256 = "3c406f50710d3aad86952bf87b42ac27b5260a77f357461e21122054cb6812c4"
EXPECTED_VECTOR_SHA256 = "bd371c85d27a2eda7dccf36795a5c6775670371c5b2942c6e1611b488b78e402"
EXPECTED_FUZZ = {
    "canonical_decoder",
    "atom_parser",
    "bond_parser",
    "hyperbond_parser",
    "reaction_parser",
    "proof_verifier",
    "quorum_certificate_verifier",
    "witness_chain_verifier",
    "event_log_replay",
    "checkpoint_restoration",
    "application_manifest_parser",
    "inference_authorization_parser",
    "novelty_closure_exchange",
    "truncated_journal_records",
    "corrupted_authority_records",
}
EXPECTED_BINS = {
    "adam-v051-authority-service",
    "adam-v051-conformance",
    "adam-v051-replay",
    "adam-v051-checkpoint",
    "adam-v051-proof-verify",
}


@dataclass
class Finding:
    severity: str
    category: str
    path: str
    line: int
    message: str


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def strip_cfg_test(text: str) -> str:
    marker = "#[cfg(test)]"
    index = text.find(marker)
    return text if index < 0 else text[:index]


def scan_markers(path: Path, text: str, findings: list[Finding]) -> None:
    relative = str(path.relative_to(ROOT))
    operational = strip_cfg_test(text) if "/src/" in relative.replace("\\", "/") else text
    patterns = [
        (r"\b(?:TODO|FIXME|TBD|HACK)\b", "development marker"),
        (r"\b(?:todo|unimplemented|unreachable)\s*!\s*\(", "stub macro"),
        (r"\bunsafe\b", "unsafe Rust"),
        (r"\.unwrap\s*\(", "runtime unwrap"),
        (r"\.expect\s*\(", "runtime expect"),
        (r"\bpanic\s*!\s*\(", "runtime panic"),
    ]
    for pattern, label in patterns:
        for match in re.finditer(pattern, operational):
            line = operational.count("\n", 0, match.start()) + 1
            findings.append(Finding("BLOCKER", "source_marker", relative, line, label))


def delimiter_errors(path: Path, text: str) -> list[Finding]:
    """Conservative delimiter scanner that ignores Rust comments and string literals."""
    findings: list[Finding] = []
    relative = str(path.relative_to(ROOT))
    stack: list[tuple[str, int]] = []
    pairs = {')': '(', ']': '[', '}': '{'}
    line = 1
    i = 0
    state = "normal"
    block_depth = 0
    raw_hashes = 0
    while i < len(text):
        c = text[i]
        n = text[i + 1] if i + 1 < len(text) else ""
        if c == "\n":
            line += 1
        if state == "line_comment":
            if c == "\n":
                state = "normal"
            i += 1
            continue
        if state == "block_comment":
            if c == "/" and n == "*":
                block_depth += 1
                i += 2
                continue
            if c == "*" and n == "/":
                block_depth -= 1
                i += 2
                if block_depth == 0:
                    state = "normal"
                continue
            i += 1
            continue
        if state == "string":
            if c == "\\":
                i += 2
                continue
            if c == '"':
                state = "normal"
            i += 1
            continue
        if state == "char":
            if c == "\\":
                i += 2
                continue
            if c == "'":
                state = "normal"
            i += 1
            continue
        if state == "raw":
            if c == '"' and text.startswith("#" * raw_hashes, i + 1):
                i += 1 + raw_hashes
                state = "normal"
            i += 1
            continue

        if c == "/" and n == "/":
            state = "line_comment"
            i += 2
            continue
        if c == "/" and n == "*":
            state = "block_comment"
            block_depth = 1
            i += 2
            continue
        if c == '"':
            state = "string"
            i += 1
            continue
        if c == "r":
            j = i + 1
            while j < len(text) and text[j] == "#":
                j += 1
            if j < len(text) and text[j] == '"':
                raw_hashes = j - (i + 1)
                state = "raw"
                i = j + 1
                continue
        if c == "'":
            # A lifetime such as 'a is not a character literal. Treat as char only
            # when a closing quote appears within a small literal window.
            window = text[i + 1:i + 8]
            closing = window.find("'")
            if closing >= 0 and "\n" not in window[:closing]:
                state = "char"
                i += 1
                continue
        if c in "([{":
            stack.append((c, line))
        elif c in pairs:
            if not stack or stack[-1][0] != pairs[c]:
                findings.append(Finding("BLOCKER", "syntax_balance", relative, line, f"unmatched {c}"))
                return findings
            stack.pop()
        i += 1
    if state in {"block_comment", "string", "char", "raw"}:
        findings.append(Finding("BLOCKER", "syntax_balance", relative, line, f"unterminated {state}"))
    for delimiter, opened_line in stack:
        findings.append(Finding("BLOCKER", "syntax_balance", relative, opened_line, f"unclosed {delimiter}"))
    return findings


def main() -> int:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    findings: list[Finding] = []

    wrapper = ROOT / "lineage" / "v0501_r4" / "ADAM_V0501_R4.zip"
    wrapper_sha = sha256(wrapper) if wrapper.exists() else None
    if wrapper_sha != EXPECTED_R4_SHA256:
        findings.append(Finding("BLOCKER", "lineage", str(wrapper.relative_to(ROOT)), 1, "R4 wrapper checksum mismatch"))

    vector_path = RUST / "conformance" / "ADAM_V051_GOLDEN_VECTORS.json"
    vector_sha = sha256(vector_path) if vector_path.exists() else None
    if vector_sha != EXPECTED_VECTOR_SHA256:
        findings.append(Finding("BLOCKER", "conformance", str(vector_path.relative_to(ROOT)), 1, "golden vector checksum mismatch"))
    vectors = json.loads(vector_path.read_text(encoding="utf-8")) if vector_path.exists() else {}
    if len(vectors.get("primitive_vectors", [])) != 24 or len(vectors.get("transitions", [])) != 20:
        findings.append(Finding("BLOCKER", "conformance", str(vector_path.relative_to(ROOT)), 1, "unexpected vector inventory"))
    if not vectors.get("final", {}).get("bond_key_integrity"):
        findings.append(Finding("BLOCKER", "conformance", str(vector_path.relative_to(ROOT)), 1, "R4 oracle bond integrity is false"))

    workspace = tomllib.loads((RUST / "Cargo.toml").read_text(encoding="utf-8"))
    crate = tomllib.loads((RUST / "crates" / "adam-v051-kernel" / "Cargo.toml").read_text(encoding="utf-8"))
    fuzz = tomllib.loads((RUST / "fuzz" / "Cargo.toml").read_text(encoding="utf-8"))
    bins = {entry["name"] for entry in crate.get("bin", [])}
    fuzz_bins = {entry["name"] for entry in fuzz.get("bin", [])}
    if bins != EXPECTED_BINS:
        findings.append(Finding("BLOCKER", "target_inventory", "rust_v051/crates/adam-v051-kernel/Cargo.toml", 1, f"binary targets differ: {sorted(bins)}"))
    if fuzz_bins != EXPECTED_FUZZ:
        findings.append(Finding("BLOCKER", "fuzz_inventory", "rust_v051/fuzz/Cargo.toml", 1, f"fuzz targets differ: {sorted(fuzz_bins)}"))
    if workspace.get("workspace", {}).get("resolver") != "2":
        findings.append(Finding("BLOCKER", "manifest", "rust_v051/Cargo.toml", 1, "workspace resolver must be 2"))

    rust_files = sorted(RUST.rglob("*.rs"))
    production_files = sorted((RUST / "crates" / "adam-v051-kernel" / "src").rglob("*.rs"))
    for path in rust_files:
        text = path.read_text(encoding="utf-8")
        findings.extend(delimiter_errors(path, text))
        if path in production_files:
            scan_markers(path, text, findings)

    required_fragments = {
        "rust_v051/crates/adam-v051-kernel/src/lib.rs": ["#![forbid(unsafe_code)]", "pub mod physics", "pub mod journal", "pub mod distributed"],
        "rust_v051/crates/adam-v051-kernel/src/canonical.rs": ["pub fn unpack", "non-canonical MessagePack representation"],
        "rust_v051/crates/adam-v051-kernel/src/runtime.rs": ["reaction replay proof divergence", "checkpoint diverges from genesis replay"],
        "rust_v051/crates/adam-v051-kernel/src/journal.rs": ["frame checksum mismatch", "expected_key_id", "lock_exclusive"],
        "rust_v051/crates/adam-v051-kernel/src/checkpoint.rs": ["checkpoint root/state mismatch", "load_latest"],
        "rust_v051/crates/adam-v051-kernel/src/distributed.rs": ["certificate quorum is below majority", "duplicate certificate signer", "witness chain linkage mismatch"],
    }
    for relative, fragments in required_fragments.items():
        path = ROOT / relative
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        for fragment in fragments:
            if fragment not in text:
                findings.append(Finding("BLOCKER", "required_logic", relative, 1, f"missing required source fragment: {fragment}"))

    workflow_path = ROOT / ".github" / "workflows" / "adam-v051-rust.yml"
    workflow = workflow_path.read_text(encoding="utf-8") if workflow_path.exists() else ""
    for fragment in ["windows-latest", "ubuntu-latest", "miri test", "fuzz build", "cargo deny", "aarch64-unknown-linux-gnu"]:
        if fragment not in workflow:
            findings.append(Finding("BLOCKER", "ci", str(workflow_path.relative_to(ROOT)), 1, f"missing CI gate: {fragment}"))

    cargo = shutil.which("cargo")
    rustc = shutil.which("rustc")
    cargo_lock = RUST / "Cargo.lock"
    external_gates = []
    if not cargo or not rustc:
        external_gates.append("Rust compiler and Cargo unavailable in this execution environment")
    if not cargo_lock.exists():
        external_gates.append("Cargo.lock must be generated and sealed by the first successful Cargo build")
    external_gates.extend([
        "Linux and Windows debug/release compilation",
        "Miri execution on a pinned nightly toolchain",
        "AddressSanitizer, ThreadSanitizer and leak qualification",
        "long-running coverage-guided fuzzing with corpus retention",
        "reproducible binary comparison across clean builders",
        "independent Rust security review",
    ])

    blockers = [finding for finding in findings if finding.severity == "BLOCKER"]
    result = {
        "format": "ADAM-v0.51-source-qualification-v1",
        "version": "0.51.0-dev1",
        "classification": "RUST_AUTHORITY_SOURCE_QUALIFICATION_CANDIDATE",
        "source_status": "PASS" if not blockers else "FAIL",
        "compiled_status": "NOT_RUN_TOOLCHAIN_UNAVAILABLE" if not cargo or not rustc else "READY_TO_RUN",
        "r4_wrapper_sha256": wrapper_sha,
        "r4_wrapper_verified": wrapper_sha == EXPECTED_R4_SHA256,
        "golden_vectors_sha256": vector_sha,
        "golden_vectors_verified": vector_sha == EXPECTED_VECTOR_SHA256,
        "primitive_vectors": len(vectors.get("primitive_vectors", [])),
        "reaction_transitions": len(vectors.get("transitions", [])),
        "final_oracle_root": vectors.get("final", {}).get("root"),
        "rust_files_scanned": len(rust_files),
        "production_rust_files_scanned": len(production_files),
        "rust_source_lines": sum(path.read_text(encoding="utf-8").count("\n") + 1 for path in rust_files),
        "binary_targets": sorted(bins),
        "fuzz_targets": sorted(fuzz_bins),
        "cargo_available": bool(cargo),
        "rustc_available": bool(rustc),
        "cargo_lock_present": cargo_lock.exists(),
        "blocking_findings": len(blockers),
        "findings": [asdict(finding) for finding in findings],
        "external_execution_gates": external_gates,
    }
    JSON_OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# ADAM v0.51 Rust Authority Source Qualification",
        "",
        f"- Source status: **{result['source_status']}**",
        f"- Compiled status: **{result['compiled_status']}**",
        f"- R4 wrapper verified: **{result['r4_wrapper_verified']}**",
        f"- Golden vectors verified: **{result['golden_vectors_verified']}**",
        f"- Rust files scanned: **{result['rust_files_scanned']}**",
        f"- Rust source lines: **{result['rust_source_lines']}**",
        f"- Binary targets: **{len(result['binary_targets'])}**",
        f"- Fuzz targets: **{len(result['fuzz_targets'])}**",
        f"- Blocking findings: **{result['blocking_findings']}**",
        "",
        "## Claim boundary",
        "",
        "This report qualifies source inventory, canonical oracle preservation, static trust-boundary requirements and CI completeness. It does not claim that Rust was compiled, executed under Miri or sanitizers, fuzzed, or independently reviewed in this environment.",
        "",
        "## External execution gates",
        "",
    ]
    lines.extend(f"- {gate}" for gate in external_gates)
    if findings:
        lines.extend(["", "## Findings", ""])
        lines.extend(
            f"- **{finding.severity}** `{finding.path}:{finding.line}` — {finding.message}"
            for finding in findings
        )
    MD_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not blockers else 1


if __name__ == "__main__":
    raise SystemExit(main())
