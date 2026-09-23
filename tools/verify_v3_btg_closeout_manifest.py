from __future__ import annotations
import hashlib, json, pathlib, sys

REPO = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = REPO / "ENTITY_V3_BTG_INTERNAL_CLOSEOUT_MANIFEST.json"

def sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

m = json.loads(MANIFEST.read_text(encoding="utf-8-sig"))
errors = []
for item in m.get("files", []):
    path = REPO / item["path"]
    if not path.is_file():
        errors.append(f"missing:{item['path']}")
        continue
    actual = sha(path)
    if actual != item["sha256"]:
        errors.append(f"hash:{item['path']}:{actual}")
material = "\n".join(
    f"{x['path']}|{x['sha256']}" for x in sorted(m.get("files", []), key=lambda x: x["path"])
).encode()
root = hashlib.sha256(material).hexdigest()
if root != m.get("snapshot_sha256"):
    errors.append(f"snapshot:{root}")
result = {"valid": not errors, "files": len(m.get("files", [])), "snapshot_sha256": root, "errors": errors}
print(json.dumps(result, indent=2, sort_keys=True))
sys.exit(0 if not errors else 2)
