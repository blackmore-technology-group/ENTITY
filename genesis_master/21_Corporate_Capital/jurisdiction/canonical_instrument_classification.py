from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
import json, sqlite3, time

ACTIONS={"RECORD_ISSUANCE","RECORD_TRANSFER","RECORD_REPURCHASE","RECORD_REDEMPTION","RECORD_CANCELLATION","RECORD_CONVERSION","RECORD_DIVIDEND","MARKET_OBSERVATION","DISCLOSURE"}
DECISIONS={"ALLOW_EVIDENCE_ONLY","REQUIRE_AUTHORIZED_REVIEW","DENY"}

def _now(): return int(time.time()*1000)

class InstrumentClassificationRegistry:
    """Versioned engineering policy boundary; never a substitute for legal classification."""
    def __init__(self,state_dir: str|Path):
        self.root=Path(state_dir)/"instrument_classification"; self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/"classification.sqlite"; self._init_db()

    @contextmanager
    def _connect(self):
        db=sqlite3.connect(self.path,timeout=30); db.row_factory=sqlite3.Row
        try: yield db; db.commit()
        except Exception: db.rollback(); raise
        finally: db.close()

    def _init_db(self):
        with self._connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS rules(rule_id TEXT PRIMARY KEY,jurisdiction TEXT NOT NULL,instrument_class TEXT NOT NULL,action TEXT NOT NULL,decision TEXT NOT NULL,version INTEGER NOT NULL,effective_at_ms INTEGER NOT NULL,expires_at_ms INTEGER,authority_ref TEXT NOT NULL,notes_json TEXT NOT NULL,UNIQUE(jurisdiction,instrument_class,action,version))")
    def register_rule(self,rule_id: str,*,jurisdiction: str,instrument_class: str,action: str,decision: str,version: int,effective_at_ms: int,authority_ref: str,expires_at_ms: int|None=None,notes: dict|None=None) -> dict:
        rid=str(rule_id or "").strip(); jur=str(jurisdiction or "").upper(); ic=str(instrument_class or "").upper(); act=str(action or "").upper(); dec=str(decision or "").upper()
        if not rid or not jur or not ic or act not in ACTIONS or dec not in DECISIONS: raise ValueError("invalid classification rule")
        if int(version)<=0 or int(effective_at_ms)<=0 or not str(authority_ref or "").strip(): raise ValueError("version, effective date and authority_ref required")
        if expires_at_ms is not None and int(expires_at_ms)<=int(effective_at_ms): raise ValueError("expiry must follow effective time")
        with self._connect() as db:
            db.execute("INSERT INTO rules VALUES(?,?,?,?,?,?,?,?,?,?)",(rid,jur,ic,act,dec,int(version),int(effective_at_ms),None if expires_at_ms is None else int(expires_at_ms),str(authority_ref),json.dumps(dict(notes or {}),sort_keys=True)))
        return {"rule_id":rid,"jurisdiction":jur,"instrument_class":ic,"action":act,"decision":dec,"version":int(version)}

    def evaluate(self,*,jurisdiction: str,instrument_class: str,action: str,at_ms: int|None=None) -> dict:
        jur=str(jurisdiction or "").upper(); ic=str(instrument_class or "").upper(); act=str(action or "").upper(); when=int(at_ms or _now())
        if act not in ACTIONS: return {"decision":"DENY","reason":"unsupported_action","legal_determination":False}
        with self._connect() as db:
            row=db.execute("SELECT * FROM rules WHERE jurisdiction=? AND instrument_class=? AND action=? AND effective_at_ms<=? AND (expires_at_ms IS NULL OR expires_at_ms>?) ORDER BY version DESC LIMIT 1",(jur,ic,act,when,when)).fetchone()
        if not row: return {"decision":"REQUIRE_AUTHORIZED_REVIEW","reason":"no_effective_rule","legal_determination":False,"jurisdiction":jur,"instrument_class":ic,"action":act}
        out=dict(row); out["notes"]=json.loads(out.pop("notes_json") or "{}"); out["legal_determination"]=False; return out

    def require_evidence_operation(self,**kwargs) -> dict:
        result=self.evaluate(**kwargs)
        if result["decision"]=="DENY": raise PermissionError("configured jurisdiction policy denies action")
        if result["decision"]=="REQUIRE_AUTHORIZED_REVIEW": raise PermissionError("authorized jurisdiction/compliance review required")
        return result