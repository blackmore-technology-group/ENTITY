from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
import hashlib, json, secrets, sqlite3, time

RELATIONSHIP_TYPES={"POSSESSION","CUSTODY","STORAGE_CONTROL","PROCESSING_AUTHORITY","SOVEREIGN_AUTHORITY","AUTHORSHIP","CREATORSHIP","LEGAL_RIGHTS","CONSENT_AUTHORITY","LICENSING_AUTHORITY","AUTHORIZED_USAGE","ECONOMIC_PARTICIPATION","GOVERNANCE_AUTHORITY","PAYMENT_AUTHORITY"}
EVIDENCE_ORIGINS={"DIRECT_OBSERVATION","ENTITY_ASSERTION","COUNTERPARTY_ATTESTATION","EXTERNAL_AUTHORITATIVE_RECORD","DERIVED_INFERENCE","UNKNOWN"}
AUTHORITY_ACTIONS={"SET_POLICY":"SOVEREIGN_AUTHORITY","GRANT_LICENCE":"LICENSING_AUTHORITY","GRANT_CONSENT":"CONSENT_AUTHORITY","AUTHORIZE_USAGE":"AUTHORIZED_USAGE","GOVERN_ENTITY":"GOVERNANCE_AUTHORITY","AUTHORIZE_PAYMENT":"PAYMENT_AUTHORITY"}

def _now(): return int(time.time()*1000)
def _id(prefix): return f"{prefix}-"+secrets.token_hex(20)
def _canon(v): return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
def _sha(v): return hashlib.sha256(v if isinstance(v,(bytes,bytearray)) else _canon(v)).hexdigest()

class SovereignAuthorityRegistry:
    """Explicit authority/custody/storage relationships. Infrastructure possession never escalates authority implicitly."""
    def __init__(self,state_dir:str|Path,identity):
        self.root=Path(state_dir)/"sovereign_authority"; self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/"sovereign_authority.sqlite"; self.identity=identity; self._init_db()
    @contextmanager
    def _connect(self):
        db=sqlite3.connect(self.path,timeout=30); db.row_factory=sqlite3.Row
        try: yield db; db.commit()
        except Exception: db.rollback(); raise
        finally: db.close()
    def _init_db(self):
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL"); db.execute("PRAGMA synchronous=FULL")
            db.execute("CREATE TABLE IF NOT EXISTS relationships(relationship_id TEXT PRIMARY KEY,entity_id TEXT NOT NULL,party_ref TEXT NOT NULL,relationship_type TEXT NOT NULL,scope_json TEXT NOT NULL,evidence_origin TEXT NOT NULL,evidence_json TEXT NOT NULL,status TEXT NOT NULL,effective_at_ms INTEGER NOT NULL,expires_at_ms INTEGER,created_at_ms INTEGER NOT NULL,revoked_at_ms INTEGER,signature_json TEXT NOT NULL)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_sovereign_rel_entity ON relationships(entity_id,relationship_type,status)")
            db.execute("CREATE TABLE IF NOT EXISTS storage_bindings(binding_id TEXT PRIMARY KEY,entity_id TEXT NOT NULL,provider_ref TEXT NOT NULL,storage_ref TEXT NOT NULL,relationship_id TEXT NOT NULL,status TEXT NOT NULL,created_at_ms INTEGER NOT NULL,retired_at_ms INTEGER,signature_json TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS economic_participation(participation_id TEXT PRIMARY KEY,entity_id TEXT NOT NULL,party_ref TEXT NOT NULL,basis_ref TEXT NOT NULL,participation_type TEXT NOT NULL,terms_json TEXT NOT NULL,status TEXT NOT NULL,created_at_ms INTEGER NOT NULL,revoked_at_ms INTEGER,signature_json TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS migrations(migration_id TEXT PRIMARY KEY,entity_id TEXT NOT NULL,from_provider_ref TEXT NOT NULL,to_provider_ref TEXT NOT NULL,from_binding_id TEXT NOT NULL,to_binding_id TEXT NOT NULL,pre_semantic_sha256 TEXT NOT NULL,post_semantic_sha256 TEXT NOT NULL,export_sha256 TEXT NOT NULL,status TEXT NOT NULL,created_at_ms INTEGER NOT NULL,signature_json TEXT NOT NULL)")
    def _require_entity(self,entity_id:str):
        self.identity.load_manifest(entity_id)
    def _signed(self,entity_id:str,body:dict)->dict:
        return self.identity.sign(entity_id,body)
    def grant_relationship(self,entity_id:str,party_ref:str,relationship_type:str,*,scope=None,evidence_origin="ENTITY_ASSERTION",evidence=None,effective_at_ms=None,expires_at_ms=None)->dict:
        self._require_entity(entity_id); rtype=str(relationship_type or "").upper(); origin=str(evidence_origin or "").upper(); party=str(party_ref or "").strip()
        if rtype not in RELATIONSHIP_TYPES or origin not in EVIDENCE_ORIGINS or not party: raise ValueError("invalid relationship")
        if expires_at_ms is not None and int(expires_at_ms)<=int(effective_at_ms or _now()): raise ValueError("expiry must follow effective time")
        rid=_id("srel1"); now=_now(); body={"schema":"entity-sovereign-relationship-v1","relationship_id":rid,"entity_id":entity_id,"party_ref":party,"relationship_type":rtype,"scope":dict(scope or {}),"evidence_origin":origin,"evidence":dict(evidence or {}),"status":"ACTIVE","effective_at_ms":int(effective_at_ms or now),"expires_at_ms":expires_at_ms,"created_at_ms":now}
        sig=self._signed(entity_id,body)
        with self._connect() as db: db.execute("INSERT INTO relationships VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",(rid,entity_id,party,rtype,json.dumps(body["scope"],sort_keys=True),origin,json.dumps(body["evidence"],sort_keys=True),"ACTIVE",body["effective_at_ms"],expires_at_ms,now,None,json.dumps(sig,sort_keys=True)))
        return dict(body,signature=sig)
    def revoke_relationship(self,entity_id:str,relationship_id:str,reason="owner_action")->dict:
        self._require_entity(entity_id); now=_now()
        with self._connect() as db:
            row=db.execute("SELECT * FROM relationships WHERE relationship_id=?",(relationship_id,)).fetchone()
            if not row: raise KeyError("relationship not found")
            if row["entity_id"]!=entity_id: raise PermissionError("entity mismatch")
            db.execute("UPDATE relationships SET status='REVOKED',revoked_at_ms=? WHERE relationship_id=?",(now,relationship_id))
        return {"relationship_id":relationship_id,"status":"REVOKED","revoked_at_ms":now,"reason":str(reason)}
    def active_relationships(self,entity_id:str,party_ref:str|None=None)->list[dict]:
        now=_now(); sql="SELECT * FROM relationships WHERE entity_id=? AND status='ACTIVE' AND effective_at_ms<=? AND (expires_at_ms IS NULL OR expires_at_ms>?)"; args=[entity_id,now,now]
        if party_ref is not None: sql+=" AND party_ref=?"; args.append(str(party_ref))
        sql+=" ORDER BY relationship_type,relationship_id"
        with self._connect() as db: rows=db.execute(sql,args).fetchall()
        out=[]
        for row in rows:
            x=dict(row); x["scope"]=json.loads(x.pop("scope_json") or "{}"); x["evidence"]=json.loads(x.pop("evidence_json") or "{}"); x["signature"]=json.loads(x.pop("signature_json") or "{}"); out.append(x)
        return out
    def authorize_relationship_action(self,entity_id:str,party_ref:str,action:str)->dict:
        required=AUTHORITY_ACTIONS.get(str(action or "").upper())
        if not required: return {"allowed":False,"reason":"unsupported_action"}
        active=self.active_relationships(entity_id,party_ref); types={x["relationship_type"] for x in active}
        if required not in types: return {"allowed":False,"reason":"required_authority_missing","required_relationship":required,"observed_relationships":sorted(types),"implicit_escalation_prohibited":True}
        return {"allowed":True,"required_relationship":required,"authority_relationship_ids":[x["relationship_id"] for x in active if x["relationship_type"]==required]}
    def bind_storage(self,entity_id:str,provider_ref:str,storage_ref:str,*,evidence=None)->dict:
        relationship=self.grant_relationship(entity_id,provider_ref,"STORAGE_CONTROL",scope={"storage_ref":storage_ref},evidence_origin="COUNTERPARTY_ATTESTATION" if evidence else "ENTITY_ASSERTION",evidence=evidence or {})
        bid=_id("sbind1"); now=_now(); body={"schema":"entity-storage-binding-v1","binding_id":bid,"entity_id":entity_id,"provider_ref":str(provider_ref),"storage_ref":str(storage_ref),"relationship_id":relationship["relationship_id"],"status":"ACTIVE","created_at_ms":now}; sig=self._signed(entity_id,body)
        with self._connect() as db: db.execute("INSERT INTO storage_bindings VALUES(?,?,?,?,?,?,?,?,?)",(bid,entity_id,str(provider_ref),str(storage_ref),relationship["relationship_id"],"ACTIVE",now,None,json.dumps(sig,sort_keys=True)))
        return dict(body,signature=sig,storage_does_not_imply_authority=True)
    def record_economic_participation(self,entity_id:str,party_ref:str,*,basis_ref:str,participation_type:str,terms:dict)->dict:
        self._require_entity(entity_id); party=str(party_ref or "").strip(); basis=str(basis_ref or "").strip(); ptype=str(participation_type or "").upper()
        if not party or not basis or not ptype: raise ValueError("party, basis and participation_type required")
        pid=_id("epart1"); now=_now(); body={"schema":"entity-economic-participation-v1","participation_id":pid,"entity_id":entity_id,"party_ref":party,"basis_ref":basis,"participation_type":ptype,"terms":dict(terms or {}),"status":"ACTIVE","created_at_ms":now}; sig=self._signed(entity_id,body)
        with self._connect() as db: db.execute("INSERT INTO economic_participation VALUES(?,?,?,?,?,?,?,?,?,?)",(pid,entity_id,party,basis,ptype,json.dumps(body["terms"],sort_keys=True),"ACTIVE",now,None,json.dumps(sig,sort_keys=True)))
        return dict(body,signature=sig)
    def semantic_snapshot(self,entity_id:str)->dict:
        relationships=self.active_relationships(entity_id)
        with self._connect() as db:
            bindings=[dict(r) for r in db.execute("SELECT binding_id,entity_id,provider_ref,storage_ref,relationship_id,status,created_at_ms,retired_at_ms FROM storage_bindings WHERE entity_id=? ORDER BY binding_id",(entity_id,))]
            parts=[dict(r) for r in db.execute("SELECT participation_id,entity_id,party_ref,basis_ref,participation_type,terms_json,status,created_at_ms,revoked_at_ms FROM economic_participation WHERE entity_id=? ORDER BY participation_id",(entity_id,))]
        for p in parts: p["terms"]=json.loads(p.pop("terms_json") or "{}")
        projection={"schema":"entity-sovereign-semantic-snapshot-v1","entity_id":entity_id,"relationships":[{k:v for k,v in r.items() if k not in {"signature","created_at_ms","revoked_at_ms"}} for r in relationships],"storage_bindings":[{k:v for k,v in b.items() if k not in {"created_at_ms","retired_at_ms"}} for b in bindings],"economic_participation":[{k:v for k,v in p.items() if k not in {"created_at_ms","revoked_at_ms"}} for p in parts]}
        projection["semantic_sha256"]=_sha(projection); return projection
    def export_manifest(self,entity_id:str)->dict:
        self._require_entity(entity_id); snapshot=self.semantic_snapshot(entity_id); now=_now(); body={"schema":"entity-sovereign-export-manifest-v1","entity_id":entity_id,"semantic_sha256":snapshot["semantic_sha256"],"relationship_count":len(snapshot["relationships"]),"storage_binding_count":len(snapshot["storage_bindings"]),"economic_participation_count":len(snapshot["economic_participation"]),"created_at_ms":now}; sig=self._signed(entity_id,body)
        return dict(body,signature=sig,snapshot=snapshot,provider_independent=True)
    def authority_semantic_hash(self,entity_id:str)->str:
        infrastructure={"POSSESSION","CUSTODY","STORAGE_CONTROL","PROCESSING_AUTHORITY"}
        relationships=[r for r in self.active_relationships(entity_id) if r["relationship_type"] not in infrastructure]
        with self._connect() as db: parts=[dict(r) for r in db.execute("SELECT party_ref,basis_ref,participation_type,terms_json,status FROM economic_participation WHERE entity_id=? AND status='ACTIVE' ORDER BY participation_id",(entity_id,))]
        for p in parts: p["terms"]=json.loads(p.pop("terms_json") or "{}")
        projection={"entity_id":entity_id,"authoritative_relationships":[{k:v for k,v in r.items() if k not in {"signature","created_at_ms","revoked_at_ms","relationship_id"}} for r in relationships],"economic_participation":parts}
        return _sha(projection)
    def migrate_storage_provider(self,entity_id:str,from_binding_id:str,to_provider_ref:str,to_storage_ref:str,*,export_sha256:str,evidence=None)->dict:
        self._require_entity(entity_id); digest=str(export_sha256 or "").lower()
        if len(digest)!=64 or any(c not in "0123456789abcdef" for c in digest): raise ValueError("export_sha256 required")
        with self._connect() as db: old=db.execute("SELECT * FROM storage_bindings WHERE binding_id=?",(from_binding_id,)).fetchone()
        if not old or old["entity_id"]!=entity_id or old["status"]!="ACTIVE": raise ValueError("active source storage binding required")
        before=self.authority_semantic_hash(entity_id); new=self.bind_storage(entity_id,to_provider_ref,to_storage_ref,evidence=evidence)
        now=_now()
        with self._connect() as db:
            db.execute("UPDATE storage_bindings SET status='RETIRED',retired_at_ms=? WHERE binding_id=?",(now,from_binding_id))
            db.execute("UPDATE relationships SET status='REVOKED',revoked_at_ms=? WHERE relationship_id=?",(now,old["relationship_id"]))
        after=self.authority_semantic_hash(entity_id)
        if before!=after: raise RuntimeError("provider migration changed sovereign authority semantics")
        mid=_id("pmig1"); body={"schema":"entity-provider-migration-v1","migration_id":mid,"entity_id":entity_id,"from_provider_ref":old["provider_ref"],"to_provider_ref":str(to_provider_ref),"from_binding_id":from_binding_id,"to_binding_id":new["binding_id"],"pre_semantic_sha256":before,"post_semantic_sha256":after,"export_sha256":digest,"status":"VERIFIED","created_at_ms":now}; sig=self._signed(entity_id,body)
        with self._connect() as db: db.execute("INSERT INTO migrations VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(mid,entity_id,old["provider_ref"],str(to_provider_ref),from_binding_id,new["binding_id"],before,after,digest,"VERIFIED",now,json.dumps(sig,sort_keys=True)))
        return dict(body,signature=sig,entity_root_unchanged=True,former_provider_authority_not_inferred=True)
    def status(self)->dict:
        with self._connect() as db:
            rel=db.execute("SELECT COUNT(*) FROM relationships").fetchone()[0]; mig=db.execute("SELECT COUNT(*) FROM migrations WHERE status='VERIFIED'").fetchone()[0]
        return {"ready":True,"schema":"entity-sovereign-authority-v1","relationships":int(rel),"verified_provider_migrations":int(mig),"custody_is_not_authority":True,"storage_is_not_ownership":True,"processing_is_not_consent":True,"access_is_not_licence":True}
