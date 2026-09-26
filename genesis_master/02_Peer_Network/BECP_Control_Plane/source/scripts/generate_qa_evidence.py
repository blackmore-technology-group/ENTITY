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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def read_text_auto(path: Path) -> str:
    raw = path.read_bytes()
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16")
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig")
    return raw.decode("utf-8", errors="replace")


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")
def source_files() -> list[Path]:
    roots = [
        ROOT / "blackmore_ecp",
        ROOT / "api",
        ROOT / "adapters",
        ROOT / "agents",
        ROOT / "scripts",
        ROOT / "tests",
        ROOT / "config",
        ROOT / "docs",
    ]
    files: list[Path] = [ROOT / "pyproject.toml"]
    for base in roots:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
                continue
            files.append(path)
    return sorted(set(files))
def verify_audit_chain(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": rel(path), "exists": False, "ok": False, "records": 0}
    previous = "GENESIS"
    count = 0
    errors: list[str] = []
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            record = json.loads(raw)
        except Exception as exc:
            errors.append(f"line {number}: invalid JSON: {exc}")
            continue
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
    return {
        "path": rel(path), "exists": True, "ok": not errors,
        "records": count, "file_sha256": sha256_file(path),
        "terminal_record_hash": previous, "errors": errors,
    }
def cert_info(path: Path) -> dict[str, Any]:
    cert = x509.load_pem_x509_certificate(path.read_bytes())
    return {
        "path": rel(path),
        "sha256": sha256_file(path),
        "fingerprint_sha256": cert.fingerprint(hashes.SHA256()).hex(),
        "subject": cert.subject.rfc4514_string(),
        "issuer": cert.issuer.rfc4514_string(),
        "serial_number": str(cert.serial_number),
        "not_valid_before_utc": cert.not_valid_before_utc.isoformat(),
        "not_valid_after_utc": cert.not_valid_after_utc.isoformat(),
    }


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def selected_versions() -> dict[str, str]:
    import importlib.metadata as metadata
    names = ["fastapi", "uvicorn", "pydantic", "cryptography", "websockets", "httpx", "mcp"]
    result: dict[str, str] = {}
    for name in names:
        try:
            result[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            result[name] = "NOT_INSTALLED"
    return result
def main() -> int:
    parser = argparse.ArgumentParser(description="Generate sealed BECP qualification evidence")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)

    live_src = ROOT / "runtime" / "qualification" / "LIVE_RESULTS.json"
    regression = output / "REGRESSION_RESULTS.txt"
    compileall = output / "COMPILEALL_RESULTS.txt"
    if not live_src.exists() or not regression.exists() or not compileall.exists():
        raise RuntimeError("required qualification inputs are missing")
    shutil.copy2(live_src, output / "LIVE_RESULTS.json")
    live = read_json(live_src)
    regression_text = read_text_auto(regression)
    compile_text = read_text_auto(compileall)
    regression_ok = "5 passed" in regression_text and "EXIT_CODE=0" in regression_text
    compile_ok = "EXIT_CODE=0" in compile_text
    live_ok = live.get("status") == "PASS"

    source_inventory = [
        {"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)}
        for path in source_files()
    ]
    write_json(output / "SOURCE_FILE_HASHES.json", source_inventory)

    registry_path = ROOT / "runtime" / "registry" / "devices.json"
    registry = read_json(registry_path)
    certificate_records: list[dict[str, Any]] = []
    cert_paths = [
        ROOT / "runtime" / "pki" / "ca" / "ca.cert.pem",
        ROOT / "runtime" / "pki" / "server" / "gateway.cert.pem",
    ]
    registered_fingerprint_match = True
    for device in registry.get("devices", []):
        raw_path = device.get("certificate_path")
        if raw_path:
            cert_paths.append(Path(raw_path))
    for path in sorted(set(cert_paths)):
        record = cert_info(path)
        matching = [d for d in registry.get("devices", []) if d.get("certificate_path") == str(path)]
        if matching:
            record["registered_device_ids"] = [d["device_id"] for d in matching]
            for device in matching:
                match = device.get("certificate_fingerprint") == record["fingerprint_sha256"]
                record.setdefault("registry_fingerprint_matches", {})[device["device_id"]] = match
                registered_fingerprint_match = registered_fingerprint_match and match
        certificate_records.append(record)
    write_json(output / "CERTIFICATE_EVIDENCE.json", certificate_records)
    audit_paths = sorted((ROOT / "runtime" / "audit").glob("*.jsonl"))
    audit_paths += sorted((ROOT / "runtime" / "qualification").glob("*.jsonl"))
    audit_evidence = [verify_audit_chain(path) for path in audit_paths]
    audit_ok = all(item.get("ok") for item in audit_evidence)
    write_json(output / "AUDIT_CHAIN_EVIDENCE.json", audit_evidence)

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

    environment = {
        "generated_utc": now.isoformat(),
        "hostname": platform.node(),
        "platform": platform.platform(),
        "python": sys.version,
        "dependencies": selected_versions(),
        "qualification_scope": "BECP local TLS/mTLS two-identity engineering-control qualification on BTG",
        "second_workstation_note": "ENG-SIM-01 is an independent BECP identity/certificate simulated on the same physical BTG computer.",
    }
    write_json(output / "ENVIRONMENT.json", environment)
    checks = live.get("checks", {})
    required_live_checks = {
        "two_agents_online": checks.get("two_agents_online", {}).get("online_devices") == 2,
        "new_chat_discovery": len(checks.get("new_chat_discovery", [])) == 2,
        "btg_remote_terminal": checks.get("btg_remote_terminal", {}).get("ok") is True,
        "terminal_ownership": checks.get("terminal_ownership", {}).get("blocked") is True and checks.get("terminal_ownership", {}).get("status") == 403,
        "second_workstation_routing": checks.get("second_workstation_routing", {}).get("ok") is True,
        "kill_switch": checks.get("kill_switch", {}).get("disconnect_enforced") is True and checks.get("kill_switch", {}).get("action_blocked") is True,
        "kill_switch_recovery": checks.get("kill_switch_recovery", {}).get("reconnected") is True and checks.get("kill_switch_recovery", {}).get("health_ok") is True,
        "mcp_v2": checks.get("mcp_v2", {}).get("tool_count", 0) >= 8 and checks.get("mcp_v2", {}).get("health_ok") is True and checks.get("mcp_v2", {}).get("session_closed") is True,
        "niki_adapter": checks.get("niki_adapter", {}).get("devices", 0) >= 2 and checks.get("niki_adapter", {}).get("terminal_ok") is True,
    }
    live_checks_ok = all(required_live_checks.values())
    registry_devices = registry.get("devices", [])
    registry_ok = (
        len(registry_devices) >= 2
        and all(not d.get("revoked", False) for d in registry_devices)
        and all(d.get("remote_access_enabled", False) for d in registry_devices)
    )
    overall_ok = all([
        compile_ok,
        regression_ok,
        live_ok,
        live_checks_ok,
        audit_ok,
        registered_fingerprint_match,
        registry_ok,
    ])
    disposition = "QUALIFIED_PASS" if overall_ok else "QUALIFICATION_FAIL"

    shutil.copy2(registry_path, output / "DEVICE_REGISTRY_SNAPSHOT.json")
    status = {
        "product": "Blackmore Engineering Control Plane",
        "product_id": "BTG-PLAT-010",
        "version": "0.2.0",
        "qualification_id": "BECP_0.2.0_QUALIFICATION_20260912",
        "generated_utc": now.isoformat(),
        "disposition": disposition,
        "compileall_pass": compile_ok,
        "regression_pass": regression_ok,
        "regression_summary": "5 passed" if regression_ok else "FAILED",
        "live_e2e_pass": live_ok and live_checks_ok,
        "live_checks": required_live_checks,
        "audit_hash_chains_pass": audit_ok,
        "registered_certificate_fingerprints_match": registered_fingerprint_match,
        "device_registry_pass": registry_ok,
        "physical_device_scope": "BTG only; second workstation is a separate logical BECP identity simulated on BTG",
    }
    write_json(output / "QUALIFICATION_RELEASE_STATUS.json", status)
    legacy_manifest_path = ROOT / "runtime" / "pki" / "PKI_MANIFEST.json"
    legacy_manifest = read_json(legacy_manifest_path) if legacy_manifest_path.exists() else {}
    current_btg = next((d for d in registry_devices if d.get("device_id") == "56d7ed92-c5b4-4cca-addd-02ab1384ca74"), None)
    pki_status = {
        "authoritative_source": "current certificate files plus BECP device registry",
        "legacy_pki_manifest_path": rel(legacy_manifest_path) if legacy_manifest_path.exists() else None,
        "legacy_pki_manifest_sha256": sha256_file(legacy_manifest_path) if legacy_manifest_path.exists() else None,
        "legacy_manifest_authoritative": False,
        "legacy_btg_fingerprint": legacy_manifest.get("device_certificate_fingerprint"),
        "current_btg_fingerprint": current_btg.get("certificate_fingerprint") if current_btg else None,
        "legacy_manifest_superseded": bool(current_btg and legacy_manifest.get("device_certificate_fingerprint") != current_btg.get("certificate_fingerprint")),
        "current_registered_certificates_verified": registered_fingerprint_match,
    }
    write_json(output / "PKI_ACTIVE_STATUS.json", pki_status)

    qa_key_path = ROOT / "runtime" / "secrets" / "qa_seal.key"
    if not qa_key_path.exists():
        qa_key_path.write_bytes(os.urandom(64))
    qa_key = qa_key_path.read_bytes()
    if len(qa_key) < 32:
        raise RuntimeError("QA seal key is too short")
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

    report_lines = [
        "# BECP 0.2.0 Qualification Report",
        "",
        f"Qualification ID: BECP_0.2.0_QUALIFICATION_20260912",
        f"Generated UTC: {now.isoformat()}",
        f"Disposition: {disposition}",
        "",
        "## Verified results",
        f"- Python compile-all: {'PASS' if compile_ok else 'FAIL'}",
        f"- Full pytest regression: {'PASS — 5/5 tests' if regression_ok else 'FAIL'}",
        f"- Live TLS/mTLS remote E2E: {'PASS' if live_ok and live_checks_ok else 'FAIL'}",
        f"- Audit hash-chain verification: {'PASS' if audit_ok else 'FAIL'}",
        f"- Current registered certificate fingerprint alignment: {'PASS' if registered_fingerprint_match else 'FAIL'}",
        "- Physical scope: one physical BTG workstation; ENG-SIM-01 is a separately enrolled logical workstation identity using its own certificate on the same physical BTG host.",
        "",
        "## Security scope",
        "Private keys and signing-secret contents are intentionally excluded from this evidence package.",
        "The package records public certificate fingerprints, secret presence, source/config/test hashes, audit-chain evidence, regression results, and live E2E results.",
        "The legacy PKI_MANIFEST.json is recorded as superseded where its BTG fingerprint differs from the currently registered certificate.",
    ]
    (output / "QUALIFICATION_REPORT.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")
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
    artifact_files = sorted(
        path for path in output.iterdir()
        if path.is_file() and path.name not in {"QA_MANIFEST.json", "QA_SEAL.json", "QA_SEAL.sha256", "QA_SEAL.hmac"}
    )
    artifacts = [
        {"path": path.name, "bytes": path.stat().st_size, "sha256": sha256_file(path)}
        for path in artifact_files
    ]
    manifest = {
        "schema_version": 1,
        "qualification_id": "BECP_0.2.0_QUALIFICATION_20260912",
        "product": "Blackmore Engineering Control Plane",
        "product_id": "BTG-PLAT-010",
        "version": "0.2.0",
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
    key_id = hashlib.sha256(qa_key).hexdigest()[:16]
    seal = {
        "schema_version": 1,
        "qualification_id": manifest["qualification_id"],
        "generated_utc": now.isoformat(),
        "disposition": disposition,
        "manifest_sha256": manifest_sha256,
        "manifest_hmac_sha256": manifest_hmac,
        "qa_seal_key_id_sha256_prefix": key_id,
        "hmac_key_location": "runtime/secrets/qa_seal.key (not included in evidence package)",
    }
    write_json(output / "QA_SEAL.json", seal)
    (output / "QA_SEAL.sha256").write_text(manifest_sha256 + "  QA_MANIFEST.json\n", encoding="utf-8")
    (output / "QA_SEAL.hmac").write_text(manifest_hmac + "  QA_MANIFEST.json\n", encoding="utf-8")

    active_pki_path = ROOT / "runtime" / "pki" / "PKI_ACTIVE_INVENTORY.json"
    write_json(active_pki_path, {
        "generated_utc": now.isoformat(),
        "authoritative": True,
        "certificates": certificate_records,
        "registry_sha256": sha256_file(registry_path),
        "legacy_manifest_superseded": pki_status["legacy_manifest_superseded"],
    })

    print(json.dumps({
        "disposition": disposition,
        "output": str(output),
        "manifest_sha256": manifest_sha256,
        "manifest_hmac_sha256": manifest_hmac,
        "artifact_count": len(artifacts),
        "source_file_count": len(source_inventory),
        "audit_chains_ok": audit_ok,
    }, indent=2))
    return 0 if overall_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
