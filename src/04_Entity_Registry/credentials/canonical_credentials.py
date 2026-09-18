from __future__ import annotations
from pathlib import Path
from contextlib import contextmanager
import json, secrets, sqlite3, time

TRUST_ORDER=["SELF_CREATED","CONTACT_VERIFIED","DEVICE_ATTESTED","HUMAN_VERIFIED","ORGANIZATION_VERIFIED","PROFESSIONAL_CREDENTIAL_VERIFIED","AUTHORITY_ATTESTED"]
TRUST_LEVELS=set(TRUST_ORDER)
TRUST_RANK={name:i for i,name in enumerate(TRUST_ORDER)}

def _now(): return int(time.time()*1000)
def _id(prefix): return f"{prefix}-"+secrets.token_hex(20)


class CredentialTrustStore:
    """Selective-disclosure credential records; verification status is separate from identity existence."""
    def __init__(self,state_dir: str|Path,identity,world=None):
        self.root=Path(state_dir)/"credentials"; self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/"credentials.sqlite"; self.identity=identity; self.world=world; self._init_db()

    @contextmanager
    def _connect(self):
        db=sqlite3.connect(self.path,timeout=30); db.row_factory=sqlite3.Row
        try: yield db; db.commit()
        except Exception: db.rollback(); raise
        finally: db.close()

    def _init_db(self):
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("CREATE TABLE IF NOT EXISTS credentials(credential_id TEXT PRIMARY KEY,issuer_entity_id TEXT NOT NULL,subject_entity_id TEXT NOT NULL,credential_type TEXT NOT NULL,claims_json TEXT NOT NULL,trust_level TEXT NOT NULL,status TEXT NOT NULL,expires_at_ms INTEGER,signature_json TEXT NOT NULL,created_at_ms INTEGER NOT NULL,revoked_at_ms INTEGER)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_cred_subject ON credentials(subject_entity_id,status)")
    def _issuer_manifest(self,issuer_entity_id: str) -> dict|None:
        if self.world is not None:
            entity=self.world.get_entity(issuer_entity_id)
            if entity: return entity.get("manifest")
        try: return self.identity.load_manifest(issuer_entity_id)
        except Exception: return None

    @staticmethod
    def _body_from_row(row) -> dict:
        return {"schema":"entity-credential-v1","credential_id":row["credential_id"],"issuer_entity_id":row["issuer_entity_id"],"subject_entity_id":row["subject_entity_id"],"credential_type":row["credential_type"],"claims":json.loads(row["claims_json"]),"trust_level":row["trust_level"],"status":"ACTIVE","expires_at_ms":row["expires_at_ms"],"created_at_ms":row["created_at_ms"]}

    def issue(self,issuer_entity_id: str,subject_entity_id: str,credential_type: str,claims: dict,*,trust_level: str="SELF_CREATED",expires_at_ms: int|None=None) -> dict:
        trust=str(trust_level).upper()
        if trust not in TRUST_LEVELS: raise ValueError("unsupported trust level")
        credential_id=_id("cred1"); now=_now()
        body={"schema":"entity-credential-v1","credential_id":credential_id,"issuer_entity_id":issuer_entity_id,"subject_entity_id":subject_entity_id,"credential_type":str(credential_type)[:256],"claims":dict(claims or {}),"trust_level":trust,"status":"ACTIVE","expires_at_ms":expires_at_ms,"created_at_ms":now}
        sig=self.identity.sign(issuer_entity_id,body)
        with self._connect() as db: db.execute("INSERT INTO credentials VALUES(?,?,?,?,?,?,?,?,?,?,?)",(credential_id,issuer_entity_id,subject_entity_id,body["credential_type"],json.dumps(body["claims"],sort_keys=True),trust,"ACTIVE",expires_at_ms,json.dumps(sig,sort_keys=True),now,None))
        return dict(body,signature=sig)

    def ingest(self,credential: dict,signature: dict) -> dict:
        body=dict(credential or {})
        if body.get("schema")!="entity-credential-v1" or body.get("status")!="ACTIVE": raise ValueError("unsupported credential")
        trust=str(body.get("trust_level") or "").upper()
        if trust not in TRUST_LEVELS: raise ValueError("unsupported trust level")
        issuer=str(body.get("issuer_entity_id") or ""); subject=str(body.get("subject_entity_id") or "")
        manifest=self._issuer_manifest(issuer)
        if not manifest or not self.identity.verify_signature(manifest,body,signature): raise ValueError("credential signature invalid")
        expires=body.get("expires_at_ms"); created=int(body.get("created_at_ms") or 0)
        if not body.get("credential_id") or not issuer or not subject or created<=0: raise ValueError("credential identity fields required")
        with self._connect() as db:
            db.execute("INSERT OR REPLACE INTO credentials VALUES(?,?,?,?,?,?,?,?,?,?,?)",(body["credential_id"],issuer,subject,str(body.get("credential_type") or "")[:256],json.dumps(dict(body.get("claims") or {}),sort_keys=True),trust,"ACTIVE",expires,json.dumps(signature,sort_keys=True),created,None))
        return dict(body,signature=signature,verified=True)

    def verify(self,credential_id: str) -> dict:
        with self._connect() as db: row=db.execute("SELECT * FROM credentials WHERE credential_id=?",(credential_id,)).fetchone()
        if not row: raise KeyError("credential not found")
        manifest=self._issuer_manifest(row["issuer_entity_id"]); body=self._body_from_row(row); signature=json.loads(row["signature_json"])
        valid=bool(manifest and self.identity.verify_signature(manifest,body,signature)); expired=bool(row["expires_at_ms"] is not None and int(row["expires_at_ms"])<=_now())
        return {"credential_id":credential_id,"signature_valid":valid,"active":row["status"]=="ACTIVE" and not expired,"expired":expired,"trust_level":row["trust_level"],"credential_type":row["credential_type"],"issuer_entity_id":row["issuer_entity_id"],"subject_entity_id":row["subject_entity_id"]}

    def find_active(self,subject_entity_id: str,*,credential_type: str|None=None,minimum_trust_level: str|None=None,trusted_issuers: list[str]|None=None) -> list[dict]:
        minimum=str(minimum_trust_level or "SELF_CREATED").upper()
        if minimum not in TRUST_RANK: raise ValueError("unsupported minimum trust level")
        issuers=set(str(x) for x in (trusted_issuers or []) if str(x)); out=[]
        for item in self.subject_credentials(subject_entity_id):
            if credential_type and item["credential_type"]!=credential_type: continue
            if issuers and item["issuer_entity_id"] not in issuers: continue
            if TRUST_RANK.get(item["trust_level"],-1)<TRUST_RANK[minimum]: continue
            verified=self.verify(item["credential_id"])
            if verified["signature_valid"] and verified["active"]: out.append(dict(item,verification=verified))
        return out

    def revoke(self,issuer_entity_id: str,credential_id: str) -> dict:
        with self._connect() as db: row=db.execute("SELECT * FROM credentials WHERE credential_id=?",(credential_id,)).fetchone()
        if not row: raise KeyError("credential not found")
        if row["issuer_entity_id"]!=issuer_entity_id: raise PermissionError("credential issuer mismatch")
        now=_now()
        with self._connect() as db: db.execute("UPDATE credentials SET status='REVOKED',revoked_at_ms=? WHERE credential_id=?",(now,credential_id))
        return {"credential_id":credential_id,"status":"REVOKED","revoked_at_ms":now}

    def subject_credentials(self,subject_entity_id: str) -> list[dict]:
        with self._connect() as db: rows=db.execute("SELECT * FROM credentials WHERE subject_entity_id=? ORDER BY created_at_ms",(subject_entity_id,)).fetchall()
        out=[]
        for r in rows:
            item=dict(r); item["claims"]=json.loads(item.pop("claims_json")); item["signature"]=json.loads(item.pop("signature_json")); out.append(item)
        return out

    def selective_disclosure(self,credential_id: str,fields: list[str]) -> dict:
        with self._connect() as db: row=db.execute("SELECT * FROM credentials WHERE credential_id=?",(credential_id,)).fetchone()
        if not row: raise KeyError("credential not found")
        claims=json.loads(row["claims_json"]); selected={k:claims[k] for k in fields if k in claims}
        return {"credential_id":credential_id,"issuer_entity_id":row["issuer_entity_id"],"subject_entity_id":row["subject_entity_id"],"credential_type":row["credential_type"],"trust_level":row["trust_level"],"status":row["status"],"disclosed_claims":selected,"undisclosed_claim_count":max(0,len(claims)-len(selected))}

    def status(self) -> dict:
        with self._connect() as db: count=db.execute("SELECT COUNT(*) FROM credentials").fetchone()[0]
        return {"ready":True,"credential_schema":"entity-credential-v1","selective_disclosure":True,"verification_separate_from_identity":True,"credentials":int(count),"database":str(self.path)}
