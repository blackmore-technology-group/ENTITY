"""Top-level regression orchestrator for ADAM v1.

The inherited R4 suite uses the already-qualified Bash/PowerShell file-isolation
runner. v0.51 and v1 tests are then executed as fresh processes. No pytest
process is reused across test files.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "v1_qualification" / "regression_packaged"
RESULT_RE = re.compile(r"ADAM_PYTEST_RESULT passed=(\d+) failed=(\d+) skipped=(\d+) exit=(\d+)")


def run_isolated(test_file: Path) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    relative = test_file.relative_to(ROOT)
    log = OUT / (str(relative).replace(os.sep, "__").replace(".", "_") + ".log")
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    command = [sys.executable, str(ROOT / "tools" / "isolated_pytest_file.py"), str(relative)]
    if os.name == "posix":
        command = ["timeout", "--kill-after=5", "180", *command]
    with log.open("wb") as handle:
        completed = subprocess.run(command, cwd=ROOT, env=env, stdout=handle, stderr=subprocess.STDOUT, check=False)
    text = log.read_text("utf-8", errors="replace")
    matches = RESULT_RE.findall(text)
    if not matches:
        raise RuntimeError(f"no deterministic pytest result for {relative}; exit={completed.returncode}")
    passed, failed, skipped, exit_code = map(int, matches[-1])
    if failed or skipped or exit_code or completed.returncode:
        raise RuntimeError(f"test file failed: {relative}")
    print(f"PASS {relative}: {passed}")
    return passed


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    total = 0
    if os.name == "posix":
        inherited = subprocess.run(["bash", str(ROOT / "tools" / "run_regression_files.sh")], cwd=ROOT, check=False)
        if inherited.returncode:
            return inherited.returncode
        inherited_result = json.loads((ROOT / "artifacts" / "v501_source_audit_qualification" / "ADAM_V0501_REGRESSION_RESULTS.json").read_text("utf-8"))
        total += int(inherited_result.get("tests_passed", inherited_result.get("passed", 0)))
    else:
        manifest = json.loads((ROOT / "tools" / "regression_manifest.json").read_text("utf-8"))
        for group in manifest["groups"]:
            for filename in group["files"]:
                total += run_isolated(ROOT / filename)

    total += run_isolated(ROOT / "tests_v051" / "test_v051_source_candidate.py")
    for test_file in sorted((ROOT / "tests_v1").glob("test_*.py")):
        total += run_isolated(test_file)
    expected = 148
    result = {"format": "ADAM-v1-rc2-packaged-regression", "tests_passed": total, "expected": expected, "passed": total == expected}
    (OUT / "ADAM_V1_PACKAGED_REGRESSION.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", "utf-8")
    print(json.dumps(result, indent=2))
    return 0 if total == expected else 1


if __name__ == "__main__":
    raise SystemExit(main())
