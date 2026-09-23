from __future__ import annotations

from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "ENTITY_V3_DEVELOPMENT_MANIFEST.json"

def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8-sig"))
    entries = list(manifest.get("files") or [])
    seen: set[str] = set()
    failures: list[str] = []

    for entry in entries:
        rel = str(entry.get("path") or "")
        expected = str(entry.get("sha256") or "").lower()
        if not rel or rel in seen:
            failures.append(f"invalid or duplicate path: {rel!r}")
            continue
        seen.add(rel)
        target = ROOT / Path(rel)
        if not target.is_file():
            failures.append(f"missing: {rel}")
            continue
        actual = file_sha256(target)
        if actual != expected:
            failures.append(f"hash mismatch: {rel}: {actual} != {expected}")

    snapshot = hashlib.sha256(
        json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    expected_snapshot = str(manifest.get("development_snapshot_sha256") or "").lower()
    if snapshot != expected_snapshot:
        failures.append(
            f"snapshot mismatch: {snapshot} != {expected_snapshot}"
        )

    result = {
        "schema": "entity-v3-development-manifest-verification-v1",
        "valid": not failures,
        "file_count": len(entries),
        "snapshot_sha256": snapshot,
        "status": manifest.get("status"),
        "failures": failures,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["valid"] else 1

if __name__ == "__main__":
    sys.exit(main())