from __future__ import annotations

from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "ENTITY_V3_RELEASE_MANIFEST.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8-sig"))
    entries = list(manifest.get("files") or [])
    failures: list[str] = []
    seen: set[str] = set()
    for entry in entries:
        rel = str(entry.get("path") or "")
        if not rel or rel in seen:
            failures.append(f"invalid or duplicate path: {rel!r}")
            continue
        seen.add(rel)
        path = ROOT / rel
        if not path.is_file():
            failures.append(f"missing: {rel}")
            continue
        actual = sha256(path)
        expected = str(entry.get("sha256") or "").lower()
        if actual != expected:
            failures.append(f"hash mismatch: {rel}: {actual} != {expected}")

    snapshot = hashlib.sha256(
        json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    expected_snapshot = str(manifest.get("release_snapshot_sha256") or "").lower()
    if snapshot != expected_snapshot:
        failures.append(f"snapshot mismatch: {snapshot} != {expected_snapshot}")
    if manifest.get("version") != "3.0.0":
        failures.append("manifest version is not 3.0.0")
    if manifest.get("status") != "BTG_INTERNAL_QUALIFIED_RELEASE":
        failures.append("manifest status is not BTG_INTERNAL_QUALIFIED_RELEASE")
    result = {
        "schema": "entity-v3-release-manifest-verification-v1",
        "valid": not failures,
        "file_count": len(entries),
        "release_snapshot_sha256": snapshot,
        "version": manifest.get("version"),
        "status": manifest.get("status"),
        "failures": failures,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
