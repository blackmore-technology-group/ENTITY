from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "v501_source_audit_qualification"
MANIFEST = json.loads((ROOT / "tools/regression_manifest.json").read_text(encoding="utf-8"))


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        raise SystemExit("usage: summarize_regression.py <results.tsv>")
    result_file = Path(argv[1])
    rows = []
    for raw in result_file.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        group, file_name, passed_text, elapsed_text, log_name = raw.split("\t")
        log_path = ROOT / log_name
        rows.append({
            "group": group,
            "path": file_name,
            "passed": int(passed_text),
            "elapsed_seconds": float(elapsed_text),
            "log": log_name,
            "log_sha256": hashlib.sha256(log_path.read_bytes()).hexdigest(),
        })

    groups = []
    total = 0
    for spec in MANIFEST["groups"]:
        files = [row for row in rows if row["group"] == spec["name"]]
        passed = sum(row["passed"] for row in files)
        expected_files = set(spec["files"])
        actual_files = {row["path"] for row in files}
        if actual_files != expected_files:
            raise RuntimeError(f"{spec['name']} file mismatch: expected={expected_files}, actual={actual_files}")
        if passed != spec["expected"]:
            raise RuntimeError(f"{spec['name']}: expected {spec['expected']}, got {passed}")
        groups.append({"name": spec["name"], "status": "PASS", "passed": passed,
                       "expected": spec["expected"], "files": files})
        total += passed
    if total != MANIFEST["total_expected"]:
        raise RuntimeError(f"expected {MANIFEST['total_expected']} total tests, got {total}")

    source_audit = ROOT / "artifacts/source_audit/ADAM_V1_RC2_SOURCE_AUDIT_RESULTS.json"
    source_payload = json.loads(source_audit.read_text(encoding="utf-8"))
    if source_payload["summary"]["blocking_open_findings"] != 0:
        raise RuntimeError("blocking source findings remain")
    integrated_path = OUT / "ADAM_V0501_INTEGRATED_LOGIC_AUDIT_RESULTS.json"
    integrated = json.loads(integrated_path.read_text(encoding="utf-8"))
    if integrated.get("failed") != 0:
        raise RuntimeError("integrated logic audit contains failures")

    regression = {
        "format": "ADAM-v0.50.1-regression-qualification",
        "version": "0.50.1.dev4",
        "passed": total,
        "failed": 0,
        "groups": groups,
        "compileall_passed": True,
        "source_audit_sha256": hashlib.sha256(source_audit.read_bytes()).hexdigest(),
    }
    regression_path = OUT / "ADAM_V0501_REGRESSION_RESULTS.json"
    regression_path.write_text(json.dumps(regression, indent=2, sort_keys=True), encoding="utf-8")

    wheel_path = OUT / "ADAM_V0501_WHEEL_QUALIFICATION.json"
    if not wheel_path.exists():
        raise RuntimeError("wheel qualification artifact missing")
    wheel = json.loads(wheel_path.read_text(encoding="utf-8"))
    if wheel.get("build") != "PASS" or wheel.get("import_smoke") != "PASS":
        raise RuntimeError("wheel qualification failed")

    combined = {
        "format": "ADAM-v0.50.1-source-audited-combined-qualification",
        "version": "0.50.1.dev4",
        "status": "PASS",
        "regression_tests": {"passed": total, "failed": 0, "groups": groups},
        "integrated_logic_audit": {
            "passed": integrated.get("passed"), "failed": integrated.get("failed"),
            "artifact": str(integrated_path.relative_to(ROOT)),
            "sha256": hashlib.sha256(integrated_path.read_bytes()).hexdigest(),
        },
        "mechanical_source_audit": {
            "blocking_open_findings": 0,
            "artifact": str(source_audit.relative_to(ROOT)),
            "sha256": hashlib.sha256(source_audit.read_bytes()).hexdigest(),
        },
        "wheel_qualification": {
            "build": wheel["build"],
            "isolated_install": wheel["install_to_isolated_target"],
            "import_smoke": wheel["import_smoke"],
            "wheel": wheel["wheel"],
            "wheel_sha256": wheel["sha256"],
            "artifact_sha256": hashlib.sha256(wheel_path.read_bytes()).hexdigest(),
        },
        "claim_boundary": integrated.get("claim_boundary", {}),
    }
    combined_path = ROOT / "ADAM_V0501_COMBINED_QUALIFICATION.json"
    combined_path.write_text(json.dumps(combined, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"status": "PASS", "tests": total, "integrated_gates": integrated.get("passed"),
                      "combined": str(combined_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
