from pathlib import Path
import shutil, hashlib, json
ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
DST=ROOT/"16_Test_Qualification"/"interoperability"/"external_domain_kit"
(DST/"valid_vectors").mkdir(parents=True,exist_ok=True)
(DST/"invalid_vectors").mkdir(parents=True,exist_ok=True)
(DST/"submissions").mkdir(parents=True,exist_ok=True)
shutil.copy2(ROOT/"22_Sovereign_Domain"/"protocols"/"ENTITY_DOMAIN_PROTOCOLS_v1.md",DST/"ENTITY_DOMAIN_PROTOCOLS_v1.md")
shutil.copy2(ROOT/"22_Sovereign_Domain"/"SERS-ENTITY-DOMAIN-001_v1.0.md",DST/"SERS-ENTITY-DOMAIN-001_v1.0.md")
for src_dir,name in ((ROOT/"16_Test_Qualification"/"evidence"/"ENTITY_DOMAIN_VALID_VECTORS","valid_vectors"),(ROOT/"16_Test_Qualification"/"evidence"/"ENTITY_DOMAIN_INVALID_VECTORS","invalid_vectors")):
    for p in src_dir.glob("*.json"):
        shutil.copy2(p,DST/name/p.name)
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
manifest={"schema":"entity-external-domain-conformance-kit-v1","files":{}}
for p in sorted(DST.rglob("*")):
    if p.is_file() and p.name!="KIT_MANIFEST.json": manifest["files"][str(p.relative_to(DST))]=sha(p)
manifest["kit_sha256"]=hashlib.sha256(json.dumps(manifest["files"],sort_keys=True,separators=(",",":")).encode()).hexdigest()
(DST/"KIT_MANIFEST.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps({"files":len(manifest["files"]),"kit_sha256":manifest["kit_sha256"],"path":str(DST)},indent=2))
