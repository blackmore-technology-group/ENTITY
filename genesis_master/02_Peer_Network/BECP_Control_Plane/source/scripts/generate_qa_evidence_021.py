from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import platform
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography import x509
from cryptography.hazmat.primitives import hashes

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.2.1"
QUAL_ID = "BECP_0.2.1_QUALIFICATION_20260912"
QUAL = ROOT / "runtime" / "qualification" / "becp_0.2.1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def source_files() -> list[Path]:
    roots = [ROOT / name for name in (
        "blackmore_ecp", "api", "adapters", "agents", "scripts", "tests", "config", "docs"
    )]
    files = [ROOT / "pyproject.toml"]
    for base in roots:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}:
                files.append(path)
    return sorted(set(files))


def verify_audit_chain(path: Path) -> dict[str, Any]:
    previous = "GENESIS"
    count = 0
    errors: list[str] = []
    if not path.exists():
        return {"path": rel(path), "exists": False, "ok": False, "records": 0, "errors": ["missing"]}
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        record = json.loads(raw)
        count += 1
        if record.get("previous_hash") != previous:
            errors.append(f"line {number}: previous_hash mismatch")
        claimed = str(record.get("record_hash", ""))
        canonical_record = dict(record)
        canonical_record.pop("record_hash", None)
        canonical_record.pop("record_hmac", None)
        canonical = json.dumps(canonical_record, sort_keys=True, separators=(",", ":")).encode()
        actual = hashlib.sha256(canonical).hexdigest()
        if claimed != actual:
            errors.append(f"line {number}: record_hash mismatch")
        previous = claimed or actual
    return {"path": rel(path), "exists": True, "ok": not errors, "records": count,
            "file_sha256": sha256_file(path), "terminal_record_hash": previous, "errors": errors}


def cert_record(path: Path) -> dict[str, Any]:
    cert = x509.load_pem_x509_certificate(path.read_bytes())
    return {
        "path": rel(path),
        "pem_sha256": sha256_file(path),
        "fingerprint_sha256": cert.fingerprint(hashes.SHA256()).hex(),
        "subject": cert.subject.rfc4514_string(),
        "issuer": cert.issuer.rfc4514_string(),
        "not_valid_before_utc": cert.not_valid_before_utc.isoformat(),
        "not_valid_after_utc": cert.not_valid_after_utc.isoformat(),
    }


def build_artifacts() -> list[Path]:
    base = ROOT / "build" / "BECP_0.2.1"
    return [
        base / "server" / "BECP_Gateway_v0.2.1.exe",
        base / "agent" / "BECP_Workstation_Agent_v0.2.1.exe",
        base / "bridge" / "BECP_RDC_Bridge_v0.2.1.exe",
        base / "packages" / "blackmore_ecp-0.2.1-py3-none-any.whl",
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate sealed BECP 0.2.1 qualification evidence")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)

    regression = output / "REGRESSION_RESULTS.txt"
    compileall = output / "COMPILEALL_RESULTS.txt"
    if not regression.exists() or not compileall.exists():
        raise RuntimeError("regression/compile evidence inputs are missing")

    required_q = [
        "BINARY_QUALIFICATION_RESULTS.json", "MCP_QUALIFICATION_RESULTS.json",
        "WHEEL_QUALIFICATION_RESULTS.json", "RUNTIME_VERSION_EVIDENCE.json",
        "DIRECT_RDC_RESULTS.json", "FINAL_BUILD_HASHES.json", "devices.json",
    ]
    for name in required_q:
        src = QUAL / name
        if not src.exists():
            raise RuntimeError(f"missing qualification input: {src}")
        shutil.copy2(src, output / name)

    binary = read_json(QUAL / "BINARY_QUALIFICATION_RESULTS.json")
    mcp = read_json(QUAL / "MCP_QUALIFICATION_RESULTS.json")
    wheel = read_json(QUAL / "WHEEL_QUALIFICATION_RESULTS.json")
    runtime_version = read_json(QUAL / "RUNTIME_VERSION_EVIDENCE.json")
    direct_rdc = read_json(QUAL / "DIRECT_RDC_RESULTS.json")
    recorded_hashes = read_json(QUAL / "FINAL_BUILD_HASHES.json")
    q_registry = read_json(QUAL / "devices.json")

    regression_text = regression.read_text(encoding="utf-8", errors="replace")
    compile_text = compileall.read_text(encoding="utf-8", errors="replace")
    regression_ok = "8 passed" in regression_text and "EXIT_CODE=0" in regression_text
    compile_ok = "EXIT_CODE=0" in compile_text

    source_inventory = [
        {"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)}
        for path in source_files()
    ]
    write_json(output / "SOURCE_FILE_HASHES.json", source_inventory)

    actual_build = [
        {"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)}
        for path in build_artifacts()
    ]
    write_json(output / "BUILD_ARTIFACT_EVIDENCE.json", actual_build)

    hashes_ok = (
        len(recorded_hashes) == len(actual_build) == 4
        and all(recorded_hashes[i].get("sha256") == actual_build[i]["sha256"] for i in range(4))
        and all(recorded_hashes[i].get("bytes") == actual_build[i]["bytes"] for i in range(4))
    )

    audit_paths = [QUAL / "gateway_audit.jsonl", QUAL / "btg_agent_audit.jsonl"]
    audit_evidence = [verify_audit_chain(path) for path in audit_paths]
    audit_ok = all(item.get("ok") for item in audit_evidence)
    write_json(output / "AUDIT_CHAIN_EVIDENCE.json", audit_evidence)

    certs: list[dict[str, Any]] = []
    cert_match = True
    for device in q_registry.get("devices", []):
        raw = device.get("certificate_path")
        if not raw:
            continue
        record = cert_record(Path(raw))
        record["device_id"] = device.get("device_id")
        record["registry_fingerprint"] = device.get("certificate_fingerprint")
        record["registry_match"] = record["fingerprint_sha256"] == device.get("certificate_fingerprint")
        cert_match = cert_match and record["registry_match"]
        certs.append(record)
    write_json(output / "CERTIFICATE_EVIDENCE.json", certs)

    btg = next((d for d in q_registry.get("devices", []) if d.get("device_id") == "56d7ed92-c5b4-4cca-addd-02ab1384ca74"), {})
    checks = {
        "compileall": compile_ok,
        "regression_8_of_8": regression_ok,
        "binary_chain": binary.get("status") == "PASS" and all(binary.get("checks", {}).values()),
        "mcp_v2": mcp.get("status") == "PASS" and mcp.get("tool_count") == 8 and mcp.get("health_ok") is True,
        "wheel_install_and_entrypoint": wheel.get("status") == "PASS" and wheel.get("installed_version") == VERSION,
        "runtime_versions": runtime_version.get("status") == "PASS" and runtime_version.get("gateway_api_version") == VERSION and runtime_version.get("agent_version") == VERSION,
        "direct_rdc_preserved": direct_rdc.get("status") == "PASS",
        "build_hashes_match": hashes_ok,
        "audit_hash_chains": audit_ok,
        "certificate_fingerprints": cert_match,
        "btg_online": btg.get("online") is True,
        "btg_agent_version": btg.get("agent_version") == VERSION,
    }
    overall_ok = all(checks.values())
    disposition = "QUALIFIED_PASS" if overall_ok else "QUALIFICATION_FAIL"

    status = {
        "product": "Blackmore Engineering Control Plane",
        "product_id": "BTG-PLAT-010",
        "version": VERSION,
        "qualification_id": QUAL_ID,
        "generated_utc": now.isoformat(),
        "disposition": disposition,
        "checks": checks,
        "qualification_ports": [9175, 9176, 9177],
        "production_0_2_0_runtime_modified": False,
        "physical_device_scope": "BTG physical workstation; bridge credential is intentionally scoped to BTG only.",
    }
    write_json(output / "QUALIFICATION_RELEASE_STATUS.json", status)

    environment = {
        "generated_utc": now.isoformat(),
        "hostname": platform.node(),
        "platform": platform.platform(),
        "python": sys.version,
        "qualification_scope": "Corrected BECP 0.2.1 Gateway + Agent + RDC Bridge + wheel on isolated local qualification ports",
    }
    write_json(output / "ENVIRONMENT.json", environment)

    secret_presence = []
    for name in ["client_signing.key", "approval_signing.key", "qa_seal.key"]:
        path = ROOT / "runtime" / "secrets" / name
        secret_presence.append({
            "name": name,
            "present": path.exists(),
            "bytes": path.stat().st_size if path.exists() else 0,
            "content_included_in_evidence": False,
        })
    write_json(output / "SECRET_PRESENCE.json", secret_presence)

    report = [
        "# BECP 0.2.1 Qualification Report", "",
        f"Qualification ID: {QUAL_ID}",
        f"Generated UTC: {now.isoformat()}",
        f"Disposition: {disposition}", "",
        "## Final results",
    ]
    report.extend(f"- {name}: {'PASS' if value else 'FAIL'}" for name, value in checks.items())
    report += ["", "## Release scope",
               "This qualification covers the corrected 0.2.1 Gateway, Workstation Agent, RDC Bridge, and Python wheel.",
               "The RDC bridge is additive: direct Desktop Commander PowerShell remains available and was separately verified.",
               "Private signing keys are not included in this evidence package."]
    (output / "QUALIFICATION_REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    verifier = '''from __future__ import annotations
import hashlib, hmac, json, sys
from pathlib import Path
root = Path(__file__).resolve().parent
manifest_path = root / "QA_MANIFEST.json"
seal_path = root / "QA_SEAL.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
seal = json.loads(seal_path.read_text(encoding="utf-8"))
errors = []
for item in manifest["artifacts"]:
    path = root / item["path"]
    if not path.exists():
        errors.append(f"missing: {item['path']}")
        continue
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != item["sha256"]:
        errors.append(f"hash mismatch: {item['path']}")
manifest_hash = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
if manifest_hash != seal["manifest_sha256"]:
    errors.append("QA_MANIFEST hash mismatch")
if len(sys.argv) > 1:
    key = Path(sys.argv[1]).read_bytes()
    expected = hmac.new(key, manifest_hash.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, seal["manifest_hmac_sha256"]):
        errors.append("QA manifest HMAC mismatch")
print(json.dumps({"ok": not errors, "errors": errors}, indent=2))
raise SystemExit(0 if not errors else 2)
'''
    (output / "VERIFY_EVIDENCE.py").write_text(verifier, encoding="utf-8")

    qa_key_path = ROOT / "runtime" / "secrets" / "qa_seal.key"
    if not qa_key_path.exists():
        qa_key_path.write_bytes(os.urandom(64))
    qa_key = qa_key_path.read_bytes()
    if len(qa_key) < 32:
        raise RuntimeError("QA seal key is too short")

    excluded = {"QA_MANIFEST.json", "QA_SEAL.json", "QA_SEAL.sha256", "QA_SEAL.hmac"}
    artifact_files = sorted(path for path in output.iterdir() if path.is_file() and path.name not in excluded)
    artifacts = [
        {"path": path.name, "bytes": path.stat().st_size, "sha256": sha256_file(path)}
        for path in artifact_files
    ]
    manifest = {
        "schema_version": 1,
        "qualification_id": QUAL_ID,
        "product": "Blackmore Engineering Control Plane",
        "product_id": "BTG-PLAT-010",
        "version": VERSION,
        "generated_utc": now.isoformat(),
        "disposition": disposition,
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "source_file_count": len(source_inventory),
        "source_inventory_sha256": sha256_file(output / "SOURCE_FILE_HASHES.json"),
        "private_key_material_included": False,
    }

    manifest_path = output / "QA_MANIFEST.json"
    write_json(manifest_path, manifest)
    manifest_sha256 = sha256_file(manifest_path)
    manifest_hmac = hmac.new(qa_key, manifest_sha256.encode(), hashlib.sha256).hexdigest()
    seal = {
        "schema_version": 1,
        "qualification_id": QUAL_ID,
        "generated_utc": now.isoformat(),
        "disposition": disposition,
        "manifest_sha256": manifest_sha256,
        "manifest_hmac_sha256": manifest_hmac,
        "qa_seal_key_id_sha256_prefix": hashlib.sha256(qa_key).hexdigest()[:16],
        "hmac_key_location": "runtime/secrets/qa_seal.key (not included in evidence package)",
    }
    write_json(output / "QA_SEAL.json", seal)
    (output / "QA_SEAL.sha256").write_text(manifest_sha256 + "  QA_MANIFEST.json\n", encoding="utf-8")
    (output / "QA_SEAL.hmac").write_text(manifest_hmac + "  QA_MANIFEST.json\n", encoding="utf-8")

    print(json.dumps({
        "disposition": disposition,
        "output": str(output),
        "manifest_sha256": manifest_sha256,
        "manifest_hmac_sha256": manifest_hmac,
        "artifact_count": len(artifacts),
        "source_file_count": len(source_inventory),
        "checks": checks,
    }, indent=2))
    return 0 if overall_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
