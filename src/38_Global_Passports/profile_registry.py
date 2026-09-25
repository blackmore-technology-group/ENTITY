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
            db.execute("""CREATE TABLE IF NOT EXISTS profile_variants(
            profile_ref TEXT NOT NULL, body_sha256 TEXT NOT NULL, profile_id TEXT NOT NULL, version TEXT NOT NULL,
            kind TEXT NOT NULL, body_json TEXT NOT NULL, issuer_entity_id TEXT NOT NULL,
            signature_json TEXT NOT NULL, created_at_ms INTEGER NOT NULL, active_canonical INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(profile_ref,body_sha256))""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_profile_variants_ref ON profile_variants(profile_ref)")
            db.execute("""INSERT OR IGNORE INTO profile_variants(
            profile_ref,body_sha256,profile_id,version,kind,body_json,issuer_entity_id,signature_json,created_at_ms,active_canonical)
            SELECT profile_ref,body_sha256,profile_id,version,kind,body_json,issuer_entity_id,signature_json,created_at_ms,1 FROM profiles""")

    @staticmethod
    def _body(record:dict)->dict:
        return {k:v for k,v in record.items() if k not in {"body_sha256","issuer_entity_id","signature"}}

    @classmethod
    def _semantic_body(cls,record:dict)->dict:
        body=cls._body(record); body.pop("created_at_ms",None); return body

    @staticmethod
    def _row_record(row)->dict:
        body=json.loads(row["body_json"])
        return dict(body,body_sha256=row["body_sha256"],issuer_entity_id=row["issuer_entity_id"],signature=json.loads(row["signature_json"]))

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
                db.execute("INSERT INTO profile_variants VALUES(?,?,?,?,?,?,?,?,?,1)",(ref,body_sha,body["profile_id"],body["version"],kind,json.dumps(body,sort_keys=True),issuer_entity_id,json.dumps(sig,sort_keys=True),body["created_at_ms"]))
        except sqlite3.IntegrityError as exc: raise ValueError("immutable profile version already exists") from exc
        return dict(body,body_sha256=body_sha,issuer_entity_id=issuer_entity_id,signature=sig)
    def import_signed(self,profile:dict,*,allow_semantic_rebind:bool=False)->dict:
        record=dict(profile or {}); check=self.verify(record)
        if not check.get("valid"): raise ValueError("invalid signed profile: "+str(check.get("reason","unknown")))
        body=self._body(record); ref=body["profile_ref"]
        with sqlite3.connect(self.path) as db:
            db.row_factory=sqlite3.Row; prior=db.execute("SELECT * FROM profiles WHERE profile_ref=?",(ref,)).fetchone()
            if prior:
                old=self._row_record(prior)
                db.execute("INSERT OR IGNORE INTO profile_variants VALUES(?,?,?,?,?,?,?,?,?,0)",(ref,old["body_sha256"],old["profile_id"],old["version"],old["kind"],json.dumps(self._body(old),sort_keys=True),old["issuer_entity_id"],json.dumps(old["signature"],sort_keys=True),old["created_at_ms"]))
                if old["body_sha256"]==record["body_sha256"]: return old
                if not allow_semantic_rebind or self._semantic_body(old)!=self._semantic_body(record): raise ValueError("signed profile conflict")
                db.execute("UPDATE profile_variants SET active_canonical=0 WHERE profile_ref=?",(ref,))
                db.execute("INSERT OR REPLACE INTO profile_variants VALUES(?,?,?,?,?,?,?,?,?,1)",(ref,record["body_sha256"],body["profile_id"],body["version"],body["kind"],json.dumps(body,sort_keys=True),record["issuer_entity_id"],json.dumps(record["signature"],sort_keys=True),body["created_at_ms"]))
                db.execute("UPDATE profiles SET profile_id=?,version=?,kind=?,body_sha256=?,body_json=?,issuer_entity_id=?,signature_json=?,created_at_ms=? WHERE profile_ref=?",(body["profile_id"],body["version"],body["kind"],record["body_sha256"],json.dumps(body,sort_keys=True),record["issuer_entity_id"],json.dumps(record["signature"],sort_keys=True),body["created_at_ms"],ref))
            else:
                db.execute("INSERT INTO profiles VALUES(?,?,?,?,?,?,?,?,?)",(ref,body["profile_id"],body["version"],body["kind"],record["body_sha256"],json.dumps(body,sort_keys=True),record["issuer_entity_id"],json.dumps(record["signature"],sort_keys=True),body["created_at_ms"]))
                db.execute("INSERT INTO profile_variants VALUES(?,?,?,?,?,?,?,?,?,1)",(ref,record["body_sha256"],body["profile_id"],body["version"],body["kind"],json.dumps(body,sort_keys=True),record["issuer_entity_id"],json.dumps(record["signature"],sort_keys=True),body["created_at_ms"]))
        return self.get(ref)

    def get(self,profile_ref:str,body_sha256:str|None=None)->dict:
        with sqlite3.connect(self.path) as db:
            db.row_factory=sqlite3.Row
            row=(db.execute("SELECT * FROM profiles WHERE profile_ref=?",(str(profile_ref),)).fetchone() if body_sha256 is None else db.execute("SELECT * FROM profile_variants WHERE profile_ref=? AND body_sha256=?",(str(profile_ref),str(body_sha256))).fetchone())
        if not row: raise KeyError("profile missing")
        return self._row_record(row)

    def list_variants(self,profile_ref:str)->list[dict]:
        with sqlite3.connect(self.path) as db:
            db.row_factory=sqlite3.Row; rows=db.execute("SELECT * FROM profile_variants WHERE profile_ref=? ORDER BY created_at_ms,body_sha256",(str(profile_ref),)).fetchall()
        return [self._row_record(row) for row in rows]

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

    def resolve_stack(self,profile_refs:list[str],profile_hashes:list[str]|None=None)->dict:
        if profile_hashes is not None and len(profile_refs)!=len(profile_hashes): raise ValueError("profile stack refs/hashes length mismatch")
        refs=[]; seen=set()
        for i,ref in enumerate(profile_refs):
            if ref in seen: continue
            profile=self.get(ref,profile_hashes[i] if profile_hashes is not None else None); refs.append(profile); seen.add(ref)
        if not refs: raise ValueError("profile stack required")
        if not any(p["kind"]=="GLOBAL" for p in refs): raise ValueError("global profile required")
        missing=sorted({parent for p in refs for parent in p.get("parent_refs",[]) if parent not in seen})
        if missing: raise ValueError("profile stack missing parents: "+",".join(missing))
        return {"schema":"entity-v3-profile-stack-resolution-v1","profile_refs":[p["profile_ref"] for p in refs],
                "profile_hashes":[p["body_sha256"] for p in refs],"fail_closed":True,
                "profile_composition_does_not_create_authority":True,"standards_mapping_is_not_normative_equivalence":True}
