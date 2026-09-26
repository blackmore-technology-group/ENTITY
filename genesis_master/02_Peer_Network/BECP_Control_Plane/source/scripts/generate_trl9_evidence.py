from __future__ import annotations

import hashlib
import hmac
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"<LOCAL_DRIVE>/Blackmore_Technology_Group\Software Development\BECP")
OUT = ROOT / "qa_evidence" / "BECP_0.2.1_TRL9_CERTIFICATION_20260913"
TRL9 = ROOT / "runtime" / "trl9" / "BECP_0.2.1_TRL9_20260912"
QUAL = ROOT / "runtime" / "qualification" / "becp_0.2.1"
AUDIT = ROOT / "runtime" / "audit"
DEVICE = "56d7ed92-c5b4-4cca-addd-02ab1384ca74"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def run(cmd: list[str], cwd: Path = ROOT) -> dict:
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
    return {"returncode": p.returncode, "stdout": p.stdout, "stderr": p.stderr}


def verify_audit(path: Path) -> dict:
    previous = "GENESIS"
    count = 0
    errors: list[str] = []
    if not path.exists():
        return {"ok": False, "records": 0, "errors": ["missing audit file"]}
    for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        count += 1
        record = json.loads(line)
        stored = str(record.get("record_hash", ""))
        if record.get("previous_hash") != previous:
            errors.append(f"record {idx}: previous_hash mismatch")
        canonical = dict(record)
        canonical.pop("record_hash", None)
        canonical.pop("record_hmac", None)
        calc = hashlib.sha256(
            json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        if calc != stored:
            errors.append(f"record {idx}: record_hash mismatch")
        previous = stored
    return {
        "ok": not errors and count > 0,
        "records": count,
        "final_hash": previous,
        "sha256": sha256(path),
        "errors": errors,
    }


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    core = run([os.fspath(Path(os.sys.executable)), "-m", "pytest", "-q"])
    compile_result = run([
        os.fspath(Path(os.sys.executable)), "-m", "compileall", "-q",
        "blackmore_ecp", "api", "adapters", "agents", "scripts"
    ])
    product_roots = {
        "NIKI": Path(r"<LOCAL_DRIVE>/Blackmore_Technology_Group\NIKI\Blackmore_Central_Intelligence_Advanced_NIKI_ADAM_BSIE_v0.6.1_AR_INTELLIGENCE_COMPLETE"),
        "HIKEAR": Path(r"<LOCAL_DRIVE>/Blackmore_Technology_Group\Software Development\HIKE_AR\HikeAR_v0.1.0"),
        "HUNTAR": Path(r"<LOCAL_DRIVE>/Blackmore_Technology_Group\Software Development\HUNT_AR\HuntAR_v4.3.0"),
        "SEARCHAR": Path(r"<LOCAL_DRIVE>/Blackmore_Technology_Group\Software Development\SAR\SearchAR_v0.12.0"),
    }
    product_tests = {
        name: run([os.fspath(Path(os.sys.executable)), "-m", "pytest", "integrations/becp/tests", "-q"], root)
        for name, root in product_roots.items()
    }
    write_json(OUT / "FINAL_REGRESSION_RESULTS.json", {
        "core": core, "compileall": compile_result, "product_integrations": product_tests
    })
    expected_artifacts = load_json(QUAL / "FINAL_BUILD_HASHES.json")
    artifact_results = []
    for item in expected_artifacts:
        path = ROOT / item["path"]
        actual = {
            "path": item["path"],
            "exists": path.exists(),
            "expected_bytes": item["bytes"],
            "expected_sha256": item["sha256"],
        }
        if path.exists():
            actual.update({
                "actual_bytes": path.stat().st_size,
                "actual_sha256": sha256(path),
            })
            actual["ok"] = (
                actual["actual_bytes"] == item["bytes"]
                and actual["actual_sha256"] == item["sha256"]
            )
        else:
            actual["ok"] = False
        artifact_results.append(actual)
    write_json(OUT / "DEPLOYED_ARTIFACT_HASHES.json", artifact_results)
    support_files = [
        ROOT / "config" / "GATEWAY_LOCAL_QUALIFICATION.json",
        ROOT / "config" / "BTG_ENGINEERING_WORKSTATION.json",
        ROOT / "scripts" / "START_BECP_PRODUCTION_GATEWAY_021.ps1",
        ROOT / "scripts" / "START_BECP_PRODUCTION_AGENT_021.ps1",
        ROOT / "scripts" / "STOP_BECP_PRODUCTION_021.ps1",
        ROOT / "scripts" / "VERIFY_BECP_PRODUCTION_021.ps1",
        ROOT / "docs" / "OPERATIONS_AND_USER_GUIDE.md",
        ROOT / "docs" / "SECURITY_ADMINISTRATION_GUIDE.md",
        ROOT / "docs" / "MAINTENANCE_RECOVERY_ROLLBACK_GUIDE.md",
        ROOT / "docs" / "OPERATOR_TRAINING_GUIDE.md",
        ROOT / "docs" / "SUSTAINING_ENGINEERING_PLAN.md",
        ROOT / "docs" / "TRL9_CERTIFICATION_BASIS.md",
    ]
    support_hashes = []
    for path in support_files:
        support_hashes.append({
            "path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size,
            "sha256": sha256(path), "exists": path.exists()
        })
    write_json(OUT / "DEPLOYMENT_SUPPORT_HASHES.json", support_hashes)
