from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / "tools" / "regression_manifest.json").read_text())
OUT = ROOT / "artifacts" / "v051_r4_oracle"
RESULT = OUT / "ADAM_V051_R4_ORACLE_REGRESSION.json"
MARKER = re.compile(r"ADAM_PYTEST_RESULT passed=(\d+) failed=(\d+) skipped=(\d+) exit=(\d+)")


def run_file(group: str, relative: str) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    safe = relative.replace("/", "_").removesuffix(".py")
    log = OUT / f"{group}__{safe}.log"
    command = [sys.executable, str(ROOT / "tools" / "isolated_pytest_file.py"), relative]
    started = time.monotonic()
    with log.open("w", encoding="utf-8") as stream:
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": str(ROOT)},
            stdout=stream,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )
        marker_seen = False
        deadline = time.monotonic() + 240
        while time.monotonic() < deadline:
            stream.flush()
            output = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
            if MARKER.search(output):
                marker_seen = True
                break
            if process.poll() is not None:
                break
            time.sleep(0.1)
        # A test result marker is authoritative for this isolated runner. Kill the
        # whole process group after it appears so inherited native-library helper
        # processes cannot block later files during interpreter teardown.
        if marker_seen:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                raise RuntimeError(f"unable to reap process group for {relative}")
        elif process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=10)
            raise RuntimeError(f"timeout in {relative}")
    output = log.read_text(encoding="utf-8", errors="replace")
    matches = MARKER.findall(output)
    if not matches:
        raise RuntimeError(f"missing deterministic result marker in {relative}")
    passed, failed, skipped, reported_exit = map(int, matches[-1])
    if reported_exit != 0 or failed or skipped:
        raise RuntimeError(
            f"qualification failure in {relative}: reported={reported_exit} "
            f"failed={failed} skipped={skipped}"
        )
    return {
        "group": group,
        "file": relative,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "reported_exit": reported_exit,
        "elapsed_seconds": round(time.monotonic() - started, 6),
        "log": str(log.relative_to(ROOT)),
    }


def main() -> int:
    records = []
    for group in MANIFEST["groups"]:
        # Each file receives a new interpreter and process group. The manifest is
        # deliberately processed in group order to preserve the R4 qualification.
        for relative in group["files"]:
            print(f"[R4] {group['name']} / {relative}", flush=True)
            records.append(run_file(group["name"], relative))
    total = sum(record["passed"] for record in records)
    expected = MANIFEST["total_expected"]
    group_totals = {
        group["name"]: sum(record["passed"] for record in records if record["group"] == group["name"])
        for group in MANIFEST["groups"]
    }
    expected_groups = {group["name"]: group["expected"] for group in MANIFEST["groups"]}
    status = "PASS" if total == expected and group_totals == expected_groups else "FAIL"
    payload = {
        "format": "ADAM-v0.51-r4-oracle-regression-v1",
        "r4_version": MANIFEST["version"],
        "status": status,
        "passed": total,
        "failed": sum(record["failed"] for record in records),
        "skipped": sum(record["skipped"] for record in records),
        "expected": expected,
        "group_totals": group_totals,
        "expected_group_totals": expected_groups,
        "files": records,
    }
    RESULT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "passed": total, "expected": expected, "groups": group_totals}, indent=2))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
