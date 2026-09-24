from __future__ import annotations
import hashlib, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
PATH = ROOT / "ENTITY_V3_GLOBAL_INFRASTRUCTURE_MANIFEST.json"
manifest = json.loads(PATH.read_text(encoding="utf-8-sig"))
errors = []
for entry in manifest.get("files", []):
    path = ROOT / entry["path"]
    if not path.is_file():
        errors.append(f"missing:{entry['path']}")
        continue
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != entry["sha256"]:
        errors.append(f"hash:{entry['path']}:{actual}")
material = "\n".join(
    f"{x['path']}|{x['sha256']}" for x in sorted(manifest.get("files", []), key=lambda x: x["path"])
).encode()
root = hashlib.sha256(material).hexdigest()
if root != manifest.get("snapshot_sha256"):
    errors.append(f"snapshot:{root}")
result = {"valid": not errors, "files": len(manifest.get("files", [])),
          "snapshot_sha256": root, "errors": errors}
print(json.dumps(result, indent=2, sort_keys=True))
sys.exit(0 if not errors else 2)
