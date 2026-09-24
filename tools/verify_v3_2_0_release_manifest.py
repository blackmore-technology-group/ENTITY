from __future__ import annotations
import hashlib, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
PATH = ROOT / "ENTITY_V3_2_0_RELEASE_MANIFEST.json"
BASE = ROOT / "ENTITY_V3_1_0_RELEASE_MANIFEST.json"
manifest = json.loads(PATH.read_text(encoding="utf-8"))
base = json.loads(BASE.read_text(encoding="utf-8-sig"))
errors = []

def sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

actual_base = sha(BASE)
if actual_base != manifest.get("base_release_manifest_sha256"):
    errors.append(f"base_manifest:{actual_base}")
if base.get("release_snapshot_sha256") != manifest.get("base_release_snapshot_sha256"):
    errors.append("base_snapshot")
for entry in manifest.get("overlay_files", []):
    path = ROOT / entry["path"]
    if not path.is_file():
        errors.append(f"missing:{entry['path']}")
        continue
    actual = sha(path)
    if actual != entry["sha256"]:
        errors.append(f"hash:{entry['path']}:{actual}")
material = "\n".join(
    f"{x['path']}|{x['sha256']}" for x in sorted(manifest.get("overlay_files", []), key=lambda x: x["path"])
).encode()
overlay_root = hashlib.sha256(material).hexdigest()
if overlay_root != manifest.get("overlay_snapshot_sha256"):
    errors.append(f"overlay_snapshot:{overlay_root}")
result = {
    "valid": not errors,
    "version": manifest.get("version"),
    "status": manifest.get("status"),
    "base_release_snapshot_sha256": manifest.get("base_release_snapshot_sha256"),
    "overlay_files": len(manifest.get("overlay_files", [])),
    "overlay_snapshot_sha256": overlay_root,
    "errors": errors,
}
print(json.dumps(result, indent=2, sort_keys=True))
sys.exit(0 if not errors else 2)
