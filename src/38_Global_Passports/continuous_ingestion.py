from __future__ import annotations
from pathlib import Path
import hashlib, shutil

EXCLUDED_DIRS={".git","node_modules",".build","target","dist","bin","obj","__pycache__",".pytest_cache",".venv","venv"}
MODEL_EXT={".onnx",".pt",".pth",".safetensors",".gguf",".tflite"}
DATA_EXT={".csv",".jsonl",".parquet",".arrow",".avro"}
SOFTWARE_EXT={".py",".rs",".go",".java",".cs",".swift",".ts",".js",".kt",".cpp",".c",".h"}

def sha256_file(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def object_type_for(path:Path)->str:
    ext=path.suffix.lower()
    if ext in MODEL_EXT: return "MODEL"
    if ext in DATA_EXT: return "DATASET"
    if ext in SOFTWARE_EXT: return "SOFTWARE"
    if ext in {".md",".txt",".pdf",".docx",".xml",".yaml",".yml"}: return "DOCUMENT"
    return "OTHER"

class ContinuousProvenanceEngine:
    """Registers artifacts at creation time and stores recoverable content-addressed custody without making custody authoritative."""
    def __init__(self,state_root,identity,fabric,evidence_registry,rights_passports,global_passports):
        self.root=Path(state_root); self.vault=self.root/"content_vault"/"sha256"; self.vault.mkdir(parents=True,exist_ok=True)
        self.identity=identity; self.fabric=fabric; self.evidence=evidence_registry; self.rights=rights_passports; self.global_passports=global_passports
    def ingest_file(self,path,controller_entity_id:str,profile_refs:list[str],*,logical_path:str|None=None,
                    previous_object_id:str|None=None,rights_actions:list[str]|None=None,version:str="1.0")->dict:
        src=Path(path).resolve()
        if not src.is_file(): raise FileNotFoundError(src)
        content_sha=sha256_file(src); vault_path=self.vault/content_sha[:2]/content_sha
        vault_path.parent.mkdir(parents=True,exist_ok=True)
        if not vault_path.exists(): shutil.copy2(src,vault_path)
        if sha256_file(vault_path)!=content_sha: raise RuntimeError("content vault verification failed")
        descriptor={"logical_path":logical_path or src.name,"source_filename":src.name,"source_bytes":src.stat().st_size,
                    "content_addressed":True,"custody_provider":"BTG_LOCAL_CONTENT_VAULT","provider_is_authority":False}
        obj=self.fabric.register_object(controller_entity_id,object_type_for(src),src.name,descriptor=descriptor,content_sha256=content_sha)
        ev=self.evidence.issue_evidence(controller_entity_id,"DOCUMENT",obj["object_id"],content_sha,provenance_refs=[previous_object_id] if previous_object_id else [])
        actions=rights_actions or ["INSPECT","READ","COPY","DERIVE"]
        right=self.fabric.grant_right(obj["object_id"],controller_entity_id,controller_entity_id,actions,constraints={"purpose":"BTG_ENGINEERING"},economic_terms={"monetary_value_asserted":False})
        rp=self.rights.issue(controller_entity_id,obj["object_id"],[{"effect":"ALLOW","actions":actions}],version=version,
            custody=[{"provider":"BTG_LOCAL_CONTENT_VAULT","locator":f"sha256:{content_sha}","content_sha256":content_sha,"provider_is_authority":False,"credentials_included":False}],
            provenance_refs=[ev["evidence_id"]],economic_terms={"underlying_information_remains_nonrival":True})
        prov=[]
        if previous_object_id:
            prov.append(self.fabric.add_provenance(controller_entity_id,previous_object_id,obj["object_id"],"VERSION_DERIVED_FROM",contribution_bps=0,evidence={"evidence_id":ev["evidence_id"]}))
        gp=self.global_passports.issue(controller_entity_id,obj["object_id"],rp["passport_id"],profile_refs,version=version,
            evidence_refs=[ev["evidence_id"]],provenance_refs=[p["edge_id"] for p in prov],
            standards_mappings=[],economic_state={"state":"POTENTIAL","amount_units":0,"currency":"UNSPECIFIED"},
            industry_context={"continuous_ingestion":True,"logical_path":descriptor["logical_path"]})
        val=self.fabric.record_value(controller_entity_id,obj["object_id"],0,"UNSPECIFIED",state="POTENTIAL",
            basis_ref="v3.4-zero-value-baseline-no-market-or-accounting-value-asserted")
        return {"object":obj,"evidence":ev,"right":right,"rights_passport":rp,"global_passport":gp,
                "provenance":prov,"value":val,"vault_sha256":content_sha,"vault_path":str(vault_path),
                "continuous_provenance":True,"custody_is_not_authority":True}

    def ingest_directory(self,path,controller_entity_id:str,profile_refs:list[str],*,prefix:str="",rights_actions:list[str]|None=None)->dict:
        root=Path(path).resolve(); records=[]
        for src in sorted(root.rglob("*")):
            if not src.is_file() or any(part in EXCLUDED_DIRS for part in src.parts): continue
            rel=src.relative_to(root).as_posix(); logical=(prefix.rstrip("/")+"/"+rel).lstrip("/") if prefix else rel
            records.append(self.ingest_file(src,controller_entity_id,profile_refs,logical_path=logical,rights_actions=rights_actions))
        inventory=hashlib.sha256("\n".join(f"{r['object']['content_sha256']}  {r['object']['descriptor']['logical_path']}" for r in records).encode()).hexdigest()
        return {"schema":"entity-v3-continuous-ingest-result-v1","files":len(records),"inventory_sha256":inventory,
                "object_ids":[r["object"]["object_id"] for r in records],"global_passport_ids":[r["global_passport"]["passport_id"] for r in records],
                "content_addressed":True,"custody_is_not_authority":True,"economic_value_invented":False}
