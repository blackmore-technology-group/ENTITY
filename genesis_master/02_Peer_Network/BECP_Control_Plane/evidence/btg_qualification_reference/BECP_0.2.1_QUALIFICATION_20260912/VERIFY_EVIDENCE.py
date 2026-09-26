from __future__ import annotations
import hashlib, hmac, json, sys
from pathlib import Path
root = Path(__file__).resolve().parent
manifest_path = root / "QA_MANIFEST.json"
seal_path = root / "QA_SEAL.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
seal = json.loads(seal_path.read_text(encoding="utf-8"))
errors = []
for item in manifest["artifacts"]:
    path = root / item["path"]
    if not path.exists():
        errors.append(f"missing: {item['path']}")
        continue
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != item["sha256"]:
        errors.append(f"hash mismatch: {item['path']}")
manifest_hash = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
if manifest_hash != seal["manifest_sha256"]:
    errors.append("QA_MANIFEST hash mismatch")
if len(sys.argv) > 1:
    key = Path(sys.argv[1]).read_bytes()
    expected = hmac.new(key, manifest_hash.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, seal["manifest_hmac_sha256"]):
        errors.append("QA manifest HMAC mismatch")
print(json.dumps({"ok": not errors, "errors": errors}, indent=2))
raise SystemExit(0 if not errors else 2)
