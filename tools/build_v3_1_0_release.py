from __future__ import annotations
import hashlib, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
base_manifest_path = ROOT / 'ENTITY_V3_0_1_RELEASE_MANIFEST.json'
base_manifest = json.loads(base_manifest_path.read_text(encoding='utf-8-sig'))
files = {x['path'] for x in base_manifest['files']}
files.add('ENTITY_V3_0_1_RELEASE_MANIFEST.json')
overlay = {
    'ENTITY_V3_GLOBAL_INFRASTRUCTURE_MANIFEST.json',
    'RELEASE_NOTES_v3.1.0.md',
    'docs/qualification/ENTITY_V3_1_0_RELEASE_QUALIFICATION_2026-09-24.json',
    'docs/qualification/ENTITY_V3_1_0_RELEASE_QUALIFICATION_2026-09-24.md',
    'src/35_Global_Infrastructure/institutional_semantics.py',
    'src/35_Global_Infrastructure/privacy_provenance.py',
    'src/35_Global_Infrastructure/topology_crypto.py',
    'src/35_Global_Infrastructure/data_economic_sovereignty.py',
    'protocol/v3/ENTITY_GLOBAL_INFRASTRUCTURE_PROFILE.md',
    'protocol/v3/ENTITY_GLOBAL_INFRASTRUCTURE_GAP_CLOSURE.md',
    'protocol/v3/ENTITY_GLOBAL_INFRASTRUCTURE.schema.json',
    'protocol/v3/ENTITY_DATA_ECONOMIC_SOVEREIGNTY_DOCTRINE.md',
    'protocol/v3/ENTITY_GLOBAL_CLEANROOM_PROFILE.json',
}
files.update(overlay)
files.update({
    'tests/test_v3_global_infrastructure.py',
    'tests/test_v3_global_conformance.py',
    'tests/test_v3_data_economic_sovereignty.py',
    'tools/build_v3_global_conformance.py',
    'tools/build_v3_global_cleanroom_profile.py',
    'tools/seal_v3_global_infrastructure.py',
    'tools/verify_v3_global_infrastructure_manifest.py',
    'tools/build_v3_1_0_release.py',
    'tools/verify_v3_1_0_release_manifest.py',
    'tools/run_v3_1_0_release_gate.ps1',
})
vector_dir = ROOT / 'protocol' / 'v3' / 'global_vectors'
for path in vector_dir.glob('*'):
    if path.is_file():
        files.add(path.relative_to(ROOT).as_posix())
missing = [rel for rel in sorted(files) if not (ROOT / rel).is_file()]
if missing:
    raise SystemExit('missing release-critical files: ' + ', '.join(missing))
def sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
entries = [{'path': rel, 'sha256': sha(ROOT / rel)} for rel in sorted(files)]
material = '\n'.join(f"{x['path']}|{x['sha256']}" for x in entries).encode()
feature = json.loads((ROOT / 'ENTITY_V3_GLOBAL_INFRASTRUCTURE_MANIFEST.json').read_text(encoding='utf-8-sig'))
qualification = json.loads((ROOT / 'docs/qualification/ENTITY_V3_1_0_RELEASE_QUALIFICATION_2026-09-24.json').read_text(encoding='utf-8-sig'))
manifest = {
    'schema': 'entity-v3-1-0-release-manifest-v1',
    'version': '3.1.0',
    'status': 'BTG_INTERNAL_QUALIFIED_FEATURE_RELEASE',
    'release_date': '2026-09-24',
    'repository': 'blackmore-technology-group/ENTITY',
    'supersedes': 'v3.0.1',
    'base_commit': 'a977b013cb29504f04953c4fce33d2372e91097b',
    'base_release_manifest_sha256': sha(base_manifest_path),
    'base_release_snapshot_sha256': base_manifest['release_snapshot_sha256'],
    'feature_manifest_snapshot_sha256': feature['snapshot_sha256'],
    'qualification': qualification,
    'external_remaining': qualification['external_remaining'],
    'permanent_truth_boundaries': qualification['permanent_truth_boundaries'],
    'files': entries,
    'release_snapshot_sha256': hashlib.sha256(material).hexdigest(),
}
out = ROOT / 'ENTITY_V3_1_0_RELEASE_MANIFEST.json'
out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8')
print(json.dumps({
    'version': manifest['version'], 'status': manifest['status'],
    'files': len(entries), 'release_snapshot_sha256': manifest['release_snapshot_sha256'],
    'base_release_snapshot_sha256': manifest['base_release_snapshot_sha256'],
    'feature_manifest_snapshot_sha256': manifest['feature_manifest_snapshot_sha256'],
}, indent=2))
