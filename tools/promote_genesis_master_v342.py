from __future__ import annotations
from pathlib import Path
import hashlib, json, os, re, shutil, time

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(os.environ.get("ENTITY_GENESIS_MASTER_SOURCE", str(Path("D:/") / "Sovereign_Entity_Network")))
DEST = ROOT / "genesis_master"
TOP_RE = re.compile(r"^(?:0[0-9]|1[0-9]|2[0-3])_.+")
ALLOWED_SUFFIXES = {
    ".py", ".md", ".json", ".txt", ".yaml", ".yml", ".toml", ".ps1", ".csv", ".xml",
    ".rs", ".go", ".java", ".cs", ".swift", ".ts", ".js", ".kt", ".cpp", ".c", ".h",
}
EXCLUDED_DIRS = {
    ".git", "__pycache__", ".pytest_cache", ".venv", "venv", "node_modules", "target", "dist", "build",
    "bin", "obj", "runtime_state", "runtime_data", "secrets", "private", "backups", "encrypted_backups",
    "identity", "pairwise", "packages", "_implementation_backups", "compatibility_baseline", "sovereign_adapted", ".cxx", ".gradle",
}
EXCLUDED_SUFFIXES = {".sqlite", ".sqlite3", ".db", ".exe", ".dll", ".key", ".secret", ".pfx", ".p12", ".zip", ".7z", ".gz", ".entitybackup"}
ROOT_FILES = {"CANONICAL_STATE_CURRENT.json", "CANONICAL_STATE_CURRENT.json.sha256", "CANONICAL_AUTHORITY_HANDOFF_REQUIREMENTS.md", "CANONICAL_BINDING_COLLISION_REGISTER.md", "CROSS_CHAT_IMPLEMENTATION_COMPATIBILITY.md", "ENTITY_REQUIREMENTS_TRACEABILITY.md", "ROOT_MANIFEST.json", "README.md"}
def eligible(path: Path) -> bool:
    rel = path.relative_to(SOURCE)
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    if any(part.lower() in EXCLUDED_DIRS for part in rel.parts[:-1]):
        return False
    if len(rel.parts) == 1:
        return path.name in ROOT_FILES
    if not TOP_RE.fullmatch(rel.parts[0]):
        return False
    return path.suffix.lower() in ALLOWED_SUFFIXES

def main() -> int:
    if not SOURCE.is_dir():
        raise SystemExit(f"Genesis source not found: {SOURCE}")
    if DEST.exists():
        shutil.rmtree(DEST)
    DEST.mkdir(parents=True)
    records = []
    candidates = []
    for base, dirs, files in os.walk(SOURCE, topdown=True, onerror=lambda _exc: None):
        base_path = Path(base)
        dirs[:] = [d for d in dirs if d.lower() not in EXCLUDED_DIRS]
        for name in files:
            src = base_path / name
            try:
                if eligible(src):
                    candidates.append(src)
            except (OSError, ValueError):
                continue
    for src in sorted(candidates):
        try:
            raw = src.read_bytes()
        except OSError:
            continue
        source_sha = hashlib.sha256(raw).hexdigest()
        try:
            if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
                text = raw.decode("utf-16")
            else:
                text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            continue
        text = re.sub(r"(?i)\b[A-Z]:\\+", "<LOCAL_DRIVE>/", text)
        rel = src.relative_to(SOURCE)
        dst = DEST / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(text, encoding="utf-8", newline="\n")
        promoted_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        records.append({
            "path": rel.as_posix(),
            "source_sha256": source_sha,
            "promoted_sha256": promoted_sha,
            "bytes": len(text.encode("utf-8")),
            "public_normalization_applied": source_sha != promoted_sha,
        })
    inventory = hashlib.sha256("\n".join(f"{r['promoted_sha256']}  {r['path']}" for r in records).encode()).hexdigest()
    source_baseline = json.loads((SOURCE / "00_Governance" / "SERS_003_BASELINE.json").read_text(encoding="utf-8-sig"))
    manifest = {
        "schema": "entity-v3-4-2-genesis-master-promotion-v1",
        "version": "3.4.2",
        "generated_at_ms": int(time.time() * 1000),
        "source_root_label": "Sovereign_Entity_Network",
        "authoritative_baseline": source_baseline,
        "files": len(records),
        "inventory_sha256": inventory,
        "records": records,
        "public_safe_source_only": True,
        "runtime_state_included": False,
        "private_key_material_included": False,
        "databases_included": False,
        "compiled_binaries_included": False,
    }
    out = DEST / 'GENESIS_MASTER_PROMOTION_MANIFEST.json'
    out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps({'files': len(records), 'inventory_sha256': inventory, 'manifest': str(out)}, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
