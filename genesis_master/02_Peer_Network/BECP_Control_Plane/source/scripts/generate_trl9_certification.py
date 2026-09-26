from __future__ import annotations
import hashlib, hmac, json, os, shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"<LOCAL_DRIVE>/Blackmore_Technology_Group\Software Development\BECP")
OUT = ROOT / "runtime" / "trl9" / "BECP_0.2.1_TRL9_20260912"
QA = ROOT / "qa_evidence" / "BECP_0.2.1_QUALIFICATION_20260912"
SEAL_KEY = ROOT / "runtime" / "secrets" / "qa_seal.key"
PRODUCT_ID = "BTG-PLAT-010"
VERSION = "0.2.1"

def sha256(path: Path) -> str:
    d = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            d.update(chunk)
    return d.hexdigest()
def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def file_entry(path: Path, base: Path = ROOT) -> dict:
    return {
        "path": str(path.relative_to(base)) if path.is_relative_to(base) else str(path),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }

checks: dict[str, bool] = {}
api = load_json(OUT / "PRODUCTION_API_SECURITY_RESULTS.json")
mcp = load_json(OUT / "PRODUCTION_MCP_RESULTS.json")
products = load_json(OUT / "PRODUCT_INTEGRATION_LIVE_RESULTS.json")
rdc = load_json(OUT / "RDC_DUAL_PATH_FINAL_RESULTS.json")
audits = load_json(OUT / "PRODUCTION_AUDIT_CHAIN_VERIFICATION.json")
gwrec = load_json(OUT / "GATEWAY_RESTART_RECOVERY.json")
agrec = load_json(OUT / "AGENT_RESTART_RECOVERY.json")
qa_status = load_json(QA / "QUALIFICATION_RELEASE_STATUS.json")
checks["production_api_security_26"] = api.get("status") == "PASS" and api.get("check_count") == 26
checks["production_mcp_8_tools"] = mcp.get("status") == "PASS" and mcp.get("tool_count") == 8
checks["product_integrations_live"] = products.get("status") == "PASS" and all(v.get("ok") for v in products.get("products", {}).values())
checks["rdc_dual_path"] = rdc.get("status") == "PASS" and rdc.get("bridge_terminal", {}).get("ok") is True
checks["production_audit_chains"] = audits.get("status") == "PASS" and all(v.get("ok") for v in audits.get("chains", {}).values())
checks["gateway_restart_recovery"] = gwrec.get("status") == "PASS"
checks["agent_restart_recovery"] = agrec.get("status") == "PASS"
checks["release_qa_qualified"] = qa_status.get("disposition") == "QUALIFIED_PASS"
reg_text = (OUT / "FINAL_REGRESSION_RESULTS.txt").read_text(encoding="utf-8-sig")
compile_text = (OUT / "FINAL_COMPILE_STATUS.txt").read_text(encoding="utf-8-sig")
checks["final_regression_8_of_8"] = "8 passed" in reg_text and "failed" not in reg_text.lower()
checks["final_compileall"] = "COMPILE_EXIT=0" in compile_text

expected_build = load_json(QA / "FINAL_BUILD_HASHES.json")
artifact_evidence = []
artifact_hashes_ok = True
for item in expected_build:
    path = ROOT / item["path"]
    actual = file_entry(path)
    actual["expected_sha256"] = item["sha256"].lower()
    actual["expected_bytes"] = int(item["bytes"])
    actual["match"] = actual["sha256"] == item["sha256"].lower() and actual["bytes"] == int(item["bytes"])
    artifact_hashes_ok &= actual["match"]
    artifact_evidence.append(actual)
checks["qualified_artifact_hashes"] = artifact_hashes_ok

release_manifest = load_json(ROOT / "build" / "BECP_0.2.1" / "release" / "RELEASE_PACKAGE_MANIFEST.json")
release_zip = Path(release_manifest["release_zip"])
release_zip_ok = sha256(release_zip) == release_manifest["release_zip_sha256"].lower() and release_zip.stat().st_size == int(release_manifest["release_zip_bytes"])
checks["qualified_release_zip"] = release_zip_ok and release_manifest.get("private_keys_included") is False
prod_verify = load_json(OUT / "FINAL_PRODUCTION_VERIFY.json")
deep_live = load_json(ROOT / "runtime" / "qualification" / "LIVE_RESULTS.json")
checks["production_runtime_final"] = prod_verify.get("status") == "PASS" and prod_verify.get("btg_online") is True and prod_verify.get("btg_agent_version") == VERSION
checks["deep_live_qualification"] = deep_live.get("status") == "PASS"

required_docs = [
    ROOT / "docs" / "OPERATIONS_AND_USER_GUIDE.md",
    ROOT / "docs" / "SECURITY_ADMINISTRATION_GUIDE.md",
    ROOT / "docs" / "MAINTENANCE_RECOVERY_ROLLBACK_GUIDE.md",
    ROOT / "docs" / "OPERATOR_TRAINING_GUIDE.md",
    ROOT / "docs" / "SUSTAINING_ENGINEERING_PLAN.md",
    ROOT / "docs" / "TRL9_CERTIFICATION_BASIS.md",
]
required_scripts = [
    ROOT / "scripts" / "START_BECP_PRODUCTION_GATEWAY_021.ps1",
    ROOT / "scripts" / "START_BECP_PRODUCTION_AGENT_021.ps1",
    ROOT / "scripts" / "STOP_BECP_PRODUCTION_021.ps1",
    ROOT / "scripts" / "VERIFY_BECP_PRODUCTION_021.ps1",
]
required_configs = [
    ROOT / "config" / "GATEWAY_LOCAL_QUALIFICATION.json",
    ROOT / "config" / "BTG_ENGINEERING_WORKSTATION.json",
    ROOT / "config" / "RDC_BECP_BRIDGE.json",
]
checks["operations_documentation_complete"] = all(p.exists() and p.stat().st_size > 0 for p in required_docs)
checks["operations_scripts_complete"] = all(p.exists() and p.stat().st_size > 0 for p in required_scripts)
checks["production_configs_present"] = all(p.exists() and p.stat().st_size > 0 for p in required_configs)
product_configs = [
    Path(r"<LOCAL_DRIVE>/Blackmore_Technology_Group\NIKI\Blackmore_Central_Intelligence_Advanced_NIKI_ADAM_BSIE_v0.6.1_AR_INTELLIGENCE_COMPLETE\integrations\becp\configuration.json"),
    Path(r"<LOCAL_DRIVE>/Blackmore_Technology_Group\Software Development\HIKE_AR\HikeAR_v0.1.0\integrations\becp\configuration.json"),
    Path(r"<LOCAL_DRIVE>/Blackmore_Technology_Group\Software Development\HUNT_AR\HuntAR_v4.3.0\integrations\becp\configuration.json"),
    Path(r"<LOCAL_DRIVE>/Blackmore_Technology_Group\Software Development\SAR\SearchAR_v0.12.0\integrations\becp\configuration.json"),
]
checks["product_integration_configs_0_2_1"] = all(load_json(p).get("integration_version") == VERSION for p in product_configs)

evidence_paths = [
    OUT / "FINAL_REGRESSION_RESULTS.txt", OUT / "FINAL_COMPILE_STATUS.txt",
    OUT / "PRODUCTION_API_SECURITY_RESULTS.json", OUT / "PRODUCTION_MCP_RESULTS.json",
    OUT / "PRODUCT_INTEGRATION_LIVE_RESULTS.json", OUT / "RDC_DUAL_PATH_FINAL_RESULTS.json",
    OUT / "PRODUCTION_AUDIT_CHAIN_VERIFICATION.json", OUT / "GATEWAY_RESTART_RECOVERY.json",
    OUT / "AGENT_RESTART_RECOVERY.json", OUT / "AUDIT_LOG_ROTATION_MANIFEST.json",
    OUT / "FINAL_PRODUCTION_VERIFY.json", ROOT / "runtime" / "qualification" / "LIVE_RESULTS.json",
    QA / "QA_MANIFEST.json", QA / "QA_SEAL.json", QA / "QUALIFICATION_RELEASE_STATUS.json",
]
checks["required_evidence_present"] = all(p.exists() and p.stat().st_size > 0 for p in evidence_paths)

inventory = {
    "qualified_artifacts": artifact_evidence,
    "release_zip": file_entry(release_zip),
    "production_configs": [file_entry(p) for p in required_configs],
    "operations_documents": [file_entry(p) for p in required_docs],
    "operations_scripts": [file_entry(p) for p in required_scripts],
    "product_integration_configs": [file_entry(p, Path(p.anchor)) for p in product_configs],
    "evidence_files": [file_entry(p) for p in evidence_paths],
}
disposition = "TRL9_CERTIFIED_PASS" if all(checks.values()) else "TRL9_CERTIFICATION_FAIL"
now = datetime.now(timezone.utc).isoformat()
manifest = {
    "product": "Blackmore Engineering Control Plane",
    "product_id": PRODUCT_ID,
    "version": VERSION,
    "certification_scope": "Internal Blackmore Technology Group software technology-readiness certification",
    "certification_basis": "Software TRL-9 operational criteria: final integrated system operated successfully in its operational environment, documentation completed, sustaining support established, and operational results documented.",
    "external_accreditation": False,
    "generated_utc": now,
    "disposition": disposition,
    "checks": checks,
    "inventory": inventory,
}
manifest_path = OUT / "TRL9_EVIDENCE_MANIFEST.json"
manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
manifest_sha = sha256(manifest_path)

key = SEAL_KEY.read_bytes().strip()
manifest_hmac = hmac.new(key, manifest_path.read_bytes(), hashlib.sha256).hexdigest()
(OUT / "TRL9_EVIDENCE_MANIFEST.sha256").write_text(manifest_sha + "\n", encoding="utf-8")
(OUT / "TRL9_EVIDENCE_MANIFEST.hmac").write_text(manifest_hmac + "\n", encoding="utf-8")
seal = {"algorithm": "HMAC-SHA256", "manifest": manifest_path.name, "manifest_sha256": manifest_sha, "manifest_hmac_sha256": manifest_hmac, "generated_utc": now}
(OUT / "TRL9_SEAL.json").write_text(json.dumps(seal, indent=2), encoding="utf-8")
