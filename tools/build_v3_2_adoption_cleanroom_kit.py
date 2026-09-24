from __future__ import annotations
import hashlib, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
VECTORS = ROOT / "protocol" / "v3" / "adoption_vectors"
PROFILE_PATH = ROOT / "protocol" / "v3" / "ENTITY_ADOPTION_CLEANROOM_PROFILE.json"
OUT = ROOT / "protocol" / "v3" / "ENTITY_V3_2_ADOPTION_CLEANROOM_KIT.min.json"
EXPECTED_SHA256 = "44e7a00f910c89aced3b3c1b5e9cba486809ca313e9bfb4b7bc9266095c10c14"
EXPECTED_RESULT = "1eb59e09ab08da86bfd8584df4a64ba331f7bbbce3d236b9b94f351606c90e18"

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
manifest = json.loads((VECTORS / "VECTOR_MANIFEST.json").read_text(encoding="utf-8"))
if profile.get("expected_result_sha256") != EXPECTED_RESULT:
    raise SystemExit("unexpected v3.2 clean-room result hash")
rows = []
for entry in sorted(manifest["vectors"], key=lambda x: x["file"]):
    path = VECTORS / entry["file"]
    actual = sha(path.read_bytes())
    if actual != entry["sha256"]:
        raise SystemExit(f"vector hash mismatch: {entry['file']}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows.append({
        "name": pathlib.Path(entry["file"]).stem,
        "expect": entry["expect"],
        "sha256": entry["sha256"],
        "record": payload["record"],
    })
kit = {
    "schema": "entity-v3.2-adoption-cleanroom-kit-v1",
    "release_candidate": "v3.2.0",
    "base_release": "v3.1.0",
    "profile": profile,
    "schema_sha256": manifest["schema_sha256"],
    "vector_manifest_sha256": profile["vector_manifest_sha256"],
    "vectors": rows,
}
raw = (json.dumps(kit, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")
actual = sha(raw)
if actual != EXPECTED_SHA256:
    raise SystemExit(f"sealed compact kit hash changed: {actual} != {EXPECTED_SHA256}")
OUT.write_bytes(raw)
print(json.dumps({
    "valid": True,
    "vectors": len(rows),
    "kit_sha256": actual,
    "expected_result_sha256": EXPECTED_RESULT,
    "path": OUT.relative_to(ROOT).as_posix(),
}, indent=2, sort_keys=True))
