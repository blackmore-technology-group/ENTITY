from __future__ import annotations
from pathlib import Path
from typing import Any
import hashlib, json, secrets, sqlite3, time

PROFILE_KINDS={"GLOBAL","JURISDICTION","INDUSTRY","DOMAIN","PRIVACY","TRUST","DISCLOSURE"}
CONFLICT_POLICIES={"FAIL_CLOSED","MOST_RESTRICTIVE"}

def now_ms()->int: return int(time.time()*1000)
def canon(v:Any)->bytes: return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()
def digest(v:Any)->str: return hashlib.sha256(v if isinstance(v,(bytes,bytearray)) else canon(v)).hexdigest()
def rid(prefix:str)->str: return prefix+"-"+secrets.token_hex(12)
def sha256_hex(v:str)->str:
    v=str(v).lower()
    if len(v)!=64 or any(c not in "0123456789abcdef" for c in v): raise ValueError("expected lowercase SHA-256")
    return v

class GlobalProfileRegistry:
    """Versioned composable profiles. Profiles constrain interpretation; they do not create sovereign authority."""
    def __init__(self,root:str|Path,identity):
        self.path=Path(root)/"entity_v3_4_global_profiles.sqlite"; self.path.parent.mkdir(parents=True,exist_ok=True); self.identity=identity
        with sqlite3.connect(self.path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS profiles(
            profile_ref TEXT PRIMARY KEY, profile_id TEXT NOT NULL, version TEXT NOT NULL, kind TEXT NOT NULL,
            body_sha256 TEXT NOT NULL, body_json TEXT NOT NULL, issuer_entity_id TEXT NOT NULL,
            signature_json TEXT NOT NULL, created_at_ms INTEGER NOT NULL, UNIQUE(profile_id,version))""")
    def register(self,issuer_entity_id:str,profile_id:str,version:str,kind:str,*,
                 schema_sha256:str,standards:list[dict]|None=None,parent_refs:list[str]|None=None,
                 object_types:list[str]|None=None,required_evidence_types:list[str]|None=None,
                 policy:dict|None=None,conflict_policy:str="FAIL_CLOSED",public_unclassified:bool=True)->dict:
        self.identity.load_manifest(issuer_entity_id); kind=str(kind).upper(); conflict_policy=str(conflict_policy).upper()
        if kind not in PROFILE_KINDS: raise ValueError("unsupported profile kind")
        if conflict_policy not in CONFLICT_POLICIES: raise ValueError("unsupported conflict policy")
        if kind=="INDUSTRY" and "DEFENCE" in str(profile_id).upper() and not public_unclassified:
            raise ValueError("public defence profile must remain unclassified")
        ref=f"{profile_id}@{version}"; body={
            "schema":"entity-v3-global-profile-v1","profile_ref":ref,"profile_id":str(profile_id),"version":str(version),
            "kind":kind,"schema_sha256":sha256_hex(schema_sha256),"standards":sorted(list(standards or []),key=lambda x:json.dumps(x,sort_keys=True)),
            "parent_refs":sorted({str(x) for x in (parent_refs or [])}),"object_types":sorted({str(x).upper() for x in (object_types or [])}),
            "required_evidence_types":sorted({str(x).upper() for x in (required_evidence_types or [])}),"policy":dict(policy or {}),
            "conflict_policy":conflict_policy,"public_unclassified":bool(public_unclassified),"profile_is_not_authority":True,
            "standards_mapping_is_not_normative_equivalence":True,"created_at_ms":now_ms()}
        body_sha=digest(body); sig=self.identity.sign(issuer_entity_id,body)
        try:
            with sqlite3.connect(self.path) as db:
                db.execute("INSERT INTO profiles VALUES(?,?,?,?,?,?,?,?,?)",(ref,body["profile_id"],body["version"],kind,body_sha,json.dumps(body,sort_keys=True),issuer_entity_id,json.dumps(sig,sort_keys=True),body["created_at_ms"]))
        except sqlite3.IntegrityError as exc: raise ValueError("immutable profile version already exists") from exc
        return dict(body,body_sha256=body_sha,issuer_entity_id=issuer_entity_id,signature=sig)
    def get(self,profile_ref:str)->dict:
        with sqlite3.connect(self.path) as db:
            db.row_factory=sqlite3.Row; row=db.execute("SELECT * FROM profiles WHERE profile_ref=?",(str(profile_ref),)).fetchone()
        if not row: raise KeyError("profile missing")
        body=json.loads(row["body_json"])
        return dict(body,body_sha256=row["body_sha256"],issuer_entity_id=row["issuer_entity_id"],signature=json.loads(row["signature_json"]))

    def verify(self,profile:dict)->dict:
        try:
            body={k:v for k,v in profile.items() if k not in {"body_sha256","issuer_entity_id","signature"}}
            if body.get("schema")!="entity-v3-global-profile-v1": raise ValueError("schema")
            if body.get("kind") not in PROFILE_KINDS or body.get("conflict_policy") not in CONFLICT_POLICIES: raise ValueError("profile semantics")
            if body.get("profile_is_not_authority") is not True or body.get("standards_mapping_is_not_normative_equivalence") is not True: raise ValueError("authority boundary")
            sha256_hex(body.get("schema_sha256")); expected=digest(body)
            if profile.get("body_sha256")!=expected: raise ValueError("hash")
            manifest=self.identity.load_manifest(profile["issuer_entity_id"])
            if not self.identity.verify_signature(manifest,body,dict(profile.get("signature") or {})): raise ValueError("signature")
            return {"valid":True,"profile_ref":body["profile_ref"],"body_sha256":expected}
        except Exception as exc: return {"valid":False,"reason":type(exc).__name__}

    def resolve_stack(self,profile_refs:list[str])->dict:
        refs=[]; seen=set()
        for ref in profile_refs:
            if ref in seen: continue
            profile=self.get(ref); refs.append(profile); seen.add(ref)
        if not refs: raise ValueError("profile stack required")
        if not any(p["kind"]=="GLOBAL" for p in refs): raise ValueError("global profile required")
        missing=sorted({parent for p in refs for parent in p.get("parent_refs",[]) if parent not in seen})
        if missing: raise ValueError("profile stack missing parents: "+",".join(missing))
        return {"schema":"entity-v3-profile-stack-resolution-v1","profile_refs":[p["profile_ref"] for p in refs],
                "profile_hashes":[p["body_sha256"] for p in refs],"fail_closed":True,
                "profile_composition_does_not_create_authority":True,"standards_mapping_is_not_normative_equivalence":True}
