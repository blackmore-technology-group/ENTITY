from __future__ import annotations
from pathlib import Path
import ast, hashlib, importlib.metadata as md, json, sys, time

SCHEMA="entity-release-attestation-v1"

def sha(path: Path)->str: return hashlib.sha256(path.read_bytes()).hexdigest()
def dump(path:Path,data:dict)->dict:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return {"path":str(path),"sha256":sha(path),"bytes":path.stat().st_size}

def source_files(root:Path, roots:list[str]|None=None)->list[Path]:
    selected=[]; root=root.resolve(); roots=roots or ["00_Governance","01_Core_Runtime","04_Entity_Registry","16_Test_Qualification","17_Release"]
    excluded={"__pycache__",".pytest_cache","build","dist","node_modules",".git"}
    for rel in roots:
        base=root/rel
        if not base.exists(): continue
        for p in base.rglob("*.py"):
            if excluded.intersection(set(p.parts)): continue
            selected.append(p)
    return sorted(set(selected))

def imported_modules(files:list[Path])->set[str]:
    out=set()
    for path in files:
        try: tree=ast.parse(path.read_text(encoding="utf-8",errors="ignore"))
        except Exception: continue
        for node in ast.walk(tree):
            if isinstance(node,ast.Import): out.update(x.name.split(".")[0] for x in node.names)
            elif isinstance(node,ast.ImportFrom) and node.module: out.add(node.module.split(".")[0])
    return out

def dependency_inventory(files:list[Path])->list[dict]:
    mapping=md.packages_distributions(); stdlib=set(getattr(sys,"stdlib_module_names",set())); components=[]
    for module in sorted(imported_modules(files)):
        if module in stdlib: continue
        distributions=mapping.get(module) or []
        if not distributions:
            continue
        for dist_name in sorted(set(distributions)):
            try:
                dist=md.distribution(dist_name); meta=dist.metadata
                components.append({"name":dist.metadata.get("Name") or dist_name,"version":dist.version,
                    "module":module,"declared_license":meta.get("License") or "UNKNOWN",
                    "homepage":meta.get("Home-page") or "UNKNOWN","metadata_source":"installed_distribution_metadata"})
            except Exception:
                components.append({"name":dist_name,"version":"UNKNOWN","module":module,"declared_license":"UNKNOWN",
                    "homepage":"UNKNOWN","metadata_source":"unavailable"})
    unique={f"{x['name']}@{x['version']}":x for x in components}
    return [unique[k] for k in sorted(unique)]

def build_sbom(root:Path, files:list[Path])->dict:
    return {"schema":"entity-sbom-v1","generated_at_ms":int(time.time()*1000),"format":"BTG_JSON_SBOM",
            "components":dependency_inventory(files),"source_file_count":len(files),
            "source_inventory_sha256":hashlib.sha256("\n".join(f"{p.relative_to(root)}:{sha(p)}" for p in files).encode()).hexdigest()}

def build_rbom(sbom:dict)->dict:
    components=[]
    for item in sbom["components"]:
        license_value=str(item.get("declared_license") or "UNKNOWN").strip() or "UNKNOWN"
        components.append({"component":item["name"],"version":item["version"],"declared_license":license_value,
                           "rights_status":"METADATA_DECLARED" if license_value!="UNKNOWN" else "UNKNOWN",
                           "commercial_rights":"NOT_INFERRED","redistribution_rights":"NOT_INFERRED",
                           "review_required":license_value=="UNKNOWN"})
    return {"schema":"entity-rbom-v1","generated_at_ms":int(time.time()*1000),"components":components,
            "local_code_rights_status":"UNREVIEWED_ORGANIZATION_CLAIM","authorship_percentages_inferred":False,
            "unknowns_explicit":True}

def build_pbom(root:Path, files:list[Path], evidence_dir:Path)->dict:
    sources=[{"path":str(p.relative_to(root)),"sha256":sha(p)} for p in files]
    evidence=[]
    for p in sorted(evidence_dir.glob("ENTITY_*_CURRENT.json")):
        evidence.append({"path":str(p.relative_to(root)),"sha256":sha(p)})
    adrs=[]
    adr_root=root/"00_Governance"/"adr"
    if adr_root.exists():
        adrs=[{"path":str(p.relative_to(root)),"sha256":sha(p)} for p in sorted(adr_root.glob("ADR-*.md"))]
    return {"schema":"entity-pbom-v1","generated_at_ms":int(time.time()*1000),"source_files":sources,
            "architecture_decisions":adrs,"qualification_evidence":evidence,
            "ai_assistance":"KNOWN_AT_PROGRAM_LEVEL_NOT_ATTRIBUTED_PER_FILE",
            "hidden_model_reasoning_included":False,"unknown_provenance_explicit":True,
            "authorship_percentages_inferred":False}

def create_release_attestation(root:str|Path, output_dir:str|Path, release_id:str, signer=None, signer_entity_id:str|None=None,
                               source_roots:list[str]|None=None)->dict:
    root=Path(root).resolve(); out=Path(output_dir).resolve(); out.mkdir(parents=True,exist_ok=True)
    files=source_files(root,source_roots); evidence_dir=root/"16_Test_Qualification"/"evidence"
    sbom=build_sbom(root,files); rbom=build_rbom(sbom); pbom=build_pbom(root,files,evidence_dir)
    sbom_ref=dump(out/"SBOM.json",sbom); rbom_ref=dump(out/"RBOM.json",rbom); pbom_ref=dump(out/"PBOM.json",pbom)
    refs=[sbom_ref,rbom_ref,pbom_ref]
    for candidate in [root/"16_Test_Qualification"/"traceability"/"MASTER_RTM.json",
                      root/"17_Release"/"manifests"/"ENTITY_10_10_RELEASE_GATE_CURRENT.json"]:
        if candidate.is_file(): refs.append({"path":str(candidate),"sha256":sha(candidate),"bytes":candidate.stat().st_size})
    manifest={"schema":SCHEMA,"release_id":str(release_id),"generated_at_ms":int(time.time()*1000),
              "artifacts":refs,"missing_evidence_is_pass":False,"signed":False}
    if signer is not None and signer_entity_id:
        manifest["release_signer_entity_id"]=signer_entity_id; manifest["signed"]=True
        manifest["signature"]=signer.sign(signer_entity_id,dict(manifest))
    manifest_ref=dump(out/"RELEASE_EVIDENCE_MANIFEST.json",manifest)
    return {"manifest":manifest,"manifest_ref":manifest_ref,"sbom":sbom,"rbom":rbom,"pbom":pbom}
