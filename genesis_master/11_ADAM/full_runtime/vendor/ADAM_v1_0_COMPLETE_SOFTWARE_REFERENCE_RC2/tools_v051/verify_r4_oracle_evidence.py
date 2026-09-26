from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORACLE = ROOT / "artifacts" / "v051_r4_oracle" / "ADAM_V051_R4_ORACLE_REGRESSION.json"
OUT = ROOT / "artifacts" / "v051_local_qualification" / "ADAM_V051_R4_EVIDENCE_VERIFICATION.json"
EXPECTED_WRAPPER = "3c406f50710d3aad86952bf87b42ac27b5260a77f357461e21122054cb6812c4"
MARKER = re.compile(r"ADAM_PYTEST_RESULT passed=(\d+) failed=(\d+) skipped=(\d+) exit=(\d+)")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    failures: list[str] = []
    wrapper = ROOT / "lineage" / "v0501_r4" / "ADAM_V0501_R4.zip"
    wrapper_hash = sha256(wrapper) if wrapper.exists() else None
    if wrapper_hash != EXPECTED_WRAPPER:
        failures.append("frozen R4 wrapper checksum mismatch")

    payload = json.loads(ORACLE.read_text(encoding="utf-8"))
    passed = failed = skipped = 0
    verified_logs = 0
    for record in payload["files"]:
        log = ROOT / record["log"]
        if not log.exists():
            failures.append(f"missing log: {record['log']}")
            continue
        actual_hash = sha256(log)
        if actual_hash != record["log_sha256"]:
            failures.append(f"log hash mismatch: {record['log']}")
            continue
        matches = MARKER.findall(log.read_text(encoding="utf-8", errors="replace"))
        if not matches:
            failures.append(f"missing deterministic result marker: {record['log']}")
            continue
        values = tuple(map(int, matches[-1]))
        expected = (record["passed"], record["failed"], record["skipped"], record["reported_exit"])
        if values != expected:
            failures.append(f"result marker mismatch: {record['log']}")
            continue
        verified_logs += 1
        passed += values[0]
        failed += values[1]
        skipped += values[2]

    if payload.get("status") != "PASS" or payload.get("expected") != 117:
        failures.append("oracle summary is not the frozen 117-test PASS record")
    if (passed, failed, skipped) != (117, 0, 0):
        failures.append(f"verified totals were {(passed, failed, skipped)}, expected (117, 0, 0)")

    result = {
        "format": "ADAM-v0.51-r4-evidence-verification-v1",
        "status": "PASS" if not failures else "FAIL",
        "wrapper_sha256": wrapper_hash,
        "verified_logs": verified_logs,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "failures": failures,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
