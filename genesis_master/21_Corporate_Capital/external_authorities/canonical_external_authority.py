from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
import base64, json, sqlite3, time
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

SCHEMA="entity-external-authority-evidence-v1"
AUTHORITY_TYPES={"CORPORATE_REGISTER","TRANSFER_AGENT","REGISTRAR","AUDITOR","ACCOUNTING_SYSTEM","MARKET_DATA_PROVIDER","PAYMENT_PROVIDER","REGULATOR","LEGAL_ATTESTOR"}

def _b64d(value: str) -> bytes:
    return base64.urlsafe_b64decode(str(value)+"="*(-len(str(value))%4))

def _canon(value) -> bytes:
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")

def _now() -> int: return int(time.time()*1000)

class ExternalAuthorityRegistry:
    """Trust registry and signature verifier for externally authoritative capital evidence."""
    def __init__(self,state_dir: str|Path):
        self.root=Path(state_dir)/"external_authorities"; self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/"authorities.sqlite"; self._init_db()

    @contextmanager
    def _connect(self):
        db=sqlite3.connect(self.path,timeout=30); db.row_factory=sqlite3.Row
        try: yield db; db.commit()
        except Exception: db.rollback(); raise
        finally: db.close()
    def _init_db(self):
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("CREATE TABLE IF NOT EXISTS authorities(authority_id TEXT PRIMARY KEY,authority_type TEXT NOT NULL,public_key_b64 TEXT NOT NULL,jurisdictions_json TEXT NOT NULL,evidence_types_json TEXT NOT NULL,status TEXT NOT NULL,created_at_ms INTEGER NOT NULL)")

    def trust_authority(self,authority_id: str,authority_type: str,public_key_b64: str,*,jurisdictions: list[str],evidence_types: list[str],status: str="ACTIVE") -> dict:
        aid=str(authority_id or "").strip(); kind=str(authority_type or "").upper(); key=str(public_key_b64 or "").strip(); state=str(status or "").upper()
        if not aid or kind not in AUTHORITY_TYPES or not key: raise ValueError("invalid external authority")
        raw=_b64d(key)
        if len(raw)!=32: raise ValueError("Ed25519 public key must be 32 bytes")
        js=sorted({str(x).upper() for x in jurisdictions if str(x).strip()})
        types=sorted({str(x).upper() for x in evidence_types if str(x).strip()})
        if not js or not types: raise ValueError("jurisdictions and evidence_types required")
        with self._connect() as db:
            db.execute("INSERT OR REPLACE INTO authorities VALUES(?,?,?,?,?,?,?)",(aid,kind,key,json.dumps(js),json.dumps(types),state,_now()))
        return {"authority_id":aid,"authority_type":kind,"jurisdictions":js,"evidence_types":types,"status":state}

    def revoke_authority(self,authority_id: str) -> None:
        with self._connect() as db:
            cur=db.execute("UPDATE authorities SET status='REVOKED' WHERE authority_id=?",(str(authority_id),))
            if cur.rowcount!=1: raise KeyError("external authority not found")
    def authority(self,authority_id: str) -> dict:
        with self._connect() as db: row=db.execute("SELECT * FROM authorities WHERE authority_id=?",(str(authority_id),)).fetchone()
        if not row: raise KeyError("external authority not found")
        out=dict(row); out["jurisdictions"]=json.loads(out.pop("jurisdictions_json")); out["evidence_types"]=json.loads(out.pop("evidence_types_json")); return out

    def verify(self,evidence: dict,*,expected_subject: str|None=None,allowed_evidence_types: set[str]|None=None) -> bool:
        try:
            package=dict(evidence or {}); signature=str(package.pop("signature","") or "")
            if package.get("schema")!=SCHEMA or not signature: return False
            aid=str(package.get("authority_id") or ""); trusted=self.authority(aid)
            if trusted["status"]!="ACTIVE": return False
            if str(package.get("authority_type") or "").upper()!=trusted["authority_type"]: return False
            jurisdiction=str(package.get("jurisdiction") or "").upper(); etype=str(package.get("evidence_type") or "").upper()
            if jurisdiction not in set(trusted["jurisdictions"]): return False
            if etype not in set(trusted["evidence_types"]): return False
            if allowed_evidence_types and etype not in {str(x).upper() for x in allowed_evidence_types}: return False
            if expected_subject is not None and str(package.get("subject_entity_id") or "")!=str(expected_subject): return False
            if not str(package.get("external_authority_ref") or "").strip(): return False
            issued=int(package.get("issued_at_ms",0)); effective=int(package.get("effective_at_ms",0))
            if issued<=0 or effective<=0 or issued>_now()+300000: return False
            if not str(package.get("nonce") or "").strip(): return False
            pub=Ed25519PublicKey.from_public_bytes(_b64d(trusted["public_key_b64"]))
            pub.verify(_b64d(signature),_canon(package)); return True
        except Exception:
            return False

    def __call__(self,evidence: dict) -> bool:
        return self.verify(evidence)