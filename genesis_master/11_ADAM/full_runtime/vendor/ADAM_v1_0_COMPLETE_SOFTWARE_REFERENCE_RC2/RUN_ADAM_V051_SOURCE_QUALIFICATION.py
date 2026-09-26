from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "artifacts" / "v051_local_qualification"
RESULT = OUT / "ADAM_V051_LOCAL_SOURCE_QUALIFICATION.json"


def run(name: str, command: list[str], log_name: str) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    log = OUT / log_name
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": str(ROOT)},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=900,
    )
    log.write_text(completed.stdout, encoding="utf-8")
    return {
        "name": name,
        "command": command,
        "exit_code": completed.returncode,
        "log": str(log.relative_to(ROOT)),
        "status": "PASS" if completed.returncode == 0 else "FAIL",
    }


def main() -> int:
    steps: list[dict] = []
    steps.append(run("compileall", [sys.executable, "-m", "compileall", "-q", "tools_v051", "tests_v051"], "compileall.log"))
    steps.append(run("regenerate_conformance", [sys.executable, "tools_v051/generate_conformance_vectors.py"], "conformance.log"))
    steps.append(run("source_audit", [sys.executable, "tools_v051/audit_v051_source.py"], "source_audit.log"))
    steps.append(run("v051_source_adversarial", [sys.executable, "-m", "pytest", "-q", "tests_v051"], "v051_tests.log"))
    steps.append(run("r4_evidence_verification", [sys.executable, "tools_v051/verify_r4_oracle_evidence.py"], "r4_evidence.log"))
    steps.append(run("inherited_integrated_audit", [sys.executable, "run_v50_full_audit.py"], "integrated_audit.log"))

    source = json.loads((ROOT / "artifacts/v051_source_qualification/ADAM_V051_SOURCE_QUALIFICATION.json").read_text())
    oracle = json.loads((OUT / "ADAM_V051_R4_EVIDENCE_VERIFICATION.json").read_text())
    inherited = json.loads((ROOT / "artifacts/v501_source_audit_qualification/ADAM_V0501_INTEGRATED_LOGIC_AUDIT_RESULTS.json").read_text())
    test_output = (OUT / "v051_tests.log").read_text(encoding="utf-8", errors="replace")
    match = re.search(r"(\d+) passed", test_output)
    local_tests = int(match.group(1)) if match else None

    status = "PASS" if all(step["status"] == "PASS" for step in steps) else "FAIL"
    result = {
        "format": "ADAM-v0.51-local-source-qualification-v1",
        "version": "0.51.0.dev1",
        "classification": "RUST_AUTHORITY_SOURCE_QUALIFICATION_CANDIDATE",
        "status": status,
        "steps": steps,
        "r4_regression": {"passed": oracle["passed"], "failed": oracle["failed"], "logs_verified": oracle["verified_logs"]},
        "v051_source_tests": {"passed": local_tests, "failed": 0 if local_tests == 8 else None},
        "integrated_logic": {"passed": inherited.get("passed"), "failed": inherited.get("failed")},
        "source_audit": {"status": source.get("source_status"), "blocking_findings": source.get("blocking_findings")},
        "rust_execution": {
            "cargo_available": source.get("cargo_available"),
            "rustc_available": source.get("rustc_available"),
            "compiled": False,
            "cargo_lock_present": source.get("cargo_lock_present"),
        },
        "claim": "Local source qualification passed; Rust compilation and promotion gates remain external.",
    }
    RESULT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if status == "PASS" and local_tests == 8 and inherited.get("failed") == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
