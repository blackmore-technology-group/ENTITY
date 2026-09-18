from __future__ import annotations
from pathlib import Path
from contextlib import contextmanager
import json, secrets, sqlite3, time


def _now(): return int(time.time()*1000)
def _id(prefix): return f"{prefix}-"+secrets.token_hex(20)


class AuthorityCapabilityStore:
    """Least-privilege agent delegation and approval evidence; fail closed on expiry/revocation/scope mismatch."""
    def __init__(self,state_dir: str|Path,identity):
        self.root=Path(state_dir)/"authority"; self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/"capabilities.sqlite"; self.identity=identity; self._init_db()

    @contextmanager
    def _connect(self):
        db=sqlite3.connect(self.path,timeout=30); db.row_factory=sqlite3.Row
        try: yield db; db.commit()
        except Exception: db.rollback(); raise
        finally: db.close()

    def _init_db(self):
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("CREATE TABLE IF NOT EXISTS capabilities(capability_id TEXT PRIMARY KEY,grantor_entity_id TEXT NOT NULL,agent_id TEXT NOT NULL,operations_json TEXT NOT NULL,asset_scope_json TEXT NOT NULL,counterparty_scope_json TEXT NOT NULL,financial_limit REAL,expires_at_ms INTEGER,approval_required INTEGER NOT NULL,delegation_allowed INTEGER NOT NULL,status TEXT NOT NULL,signature_json TEXT NOT NULL,created_at_ms INTEGER NOT NULL,revoked_at_ms INTEGER)")
            db.execute("CREATE TABLE IF NOT EXISTS approvals(approval_id TEXT PRIMARY KEY,capability_id TEXT NOT NULL,approver_entity_id TEXT NOT NULL,operation TEXT NOT NULL,object_ref TEXT,signature_json TEXT NOT NULL,created_at_ms INTEGER NOT NULL)")
    def grant(self,grantor_entity_id: str,agent_id: str,*,operations: list[str],asset_scope: list[str]|None=None,counterparty_scope: list[str]|None=None,financial_limit: float|None=None,expires_at_ms: int|None=None,approval_required: bool=False,delegation_allowed: bool=False) -> dict:
        ops=sorted({str(x).strip().upper() for x in operations if str(x).strip()})
        if not ops: raise ValueError("at least one operation required")
        capability_id=_id("cap1"); now=_now(); assets=sorted({str(x) for x in (asset_scope or [])}); parties=sorted({str(x) for x in (counterparty_scope or [])})
        body={"schema":"entity-agent-capability-v1","capability_id":capability_id,"grantor_entity_id":grantor_entity_id,"agent_id":str(agent_id),"operations":ops,"asset_scope":assets,"counterparty_scope":parties,"financial_limit":financial_limit,"expires_at_ms":expires_at_ms,"approval_required":bool(approval_required),"delegation_allowed":bool(delegation_allowed),"status":"ACTIVE","created_at_ms":now}
        sig=self.identity.sign(grantor_entity_id,body)
        with self._connect() as db: db.execute("INSERT INTO capabilities VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(capability_id,grantor_entity_id,str(agent_id),json.dumps(ops),json.dumps(assets),json.dumps(parties),financial_limit,expires_at_ms,int(approval_required),int(delegation_allowed),"ACTIVE",json.dumps(sig,sort_keys=True),now,None))
        return dict(body,signature=sig)

    def revoke(self,grantor_entity_id: str,capability_id: str) -> dict:
        with self._connect() as db: row=db.execute("SELECT * FROM capabilities WHERE capability_id=?",(capability_id,)).fetchone()
        if not row: raise KeyError("capability not found")
        if row["grantor_entity_id"]!=grantor_entity_id: raise PermissionError("capability grantor mismatch")
        now=_now()
        with self._connect() as db: db.execute("UPDATE capabilities SET status='REVOKED',revoked_at_ms=? WHERE capability_id=?",(now,capability_id))
        return {"capability_id":capability_id,"status":"REVOKED","revoked_at_ms":now}

    def approve(self,approver_entity_id: str,capability_id: str,operation: str,object_ref: str|None=None) -> dict:
        approval_id=_id("apr1"); now=_now(); body={"schema":"entity-approval-v1","approval_id":approval_id,"capability_id":capability_id,"approver_entity_id":approver_entity_id,"operation":str(operation).upper(),"object_ref":object_ref,"created_at_ms":now}
        sig=self.identity.sign(approver_entity_id,body)
        with self._connect() as db: db.execute("INSERT INTO approvals VALUES(?,?,?,?,?,?,?)",(approval_id,capability_id,approver_entity_id,body["operation"],object_ref,json.dumps(sig,sort_keys=True),now))
        return dict(body,signature=sig)

    def authorize(self,capability_id: str,agent_id: str,operation: str,*,asset_id: str|None=None,counterparty_id: str|None=None,amount: float|None=None,object_ref: str|None=None) -> dict:
        with self._connect() as db: row=db.execute("SELECT * FROM capabilities WHERE capability_id=?",(capability_id,)).fetchone()
        if not row: return {"allowed":False,"reason":"capability_not_found"}
        if row["status"]!="ACTIVE": return {"allowed":False,"reason":"capability_not_active"}
        if row["agent_id"]!=str(agent_id): return {"allowed":False,"reason":"agent_mismatch"}
        if row["expires_at_ms"] is not None and int(row["expires_at_ms"])<_now(): return {"allowed":False,"reason":"capability_expired"}
        op=str(operation).upper(); ops=set(json.loads(row["operations_json"]))
        if op not in ops: return {"allowed":False,"reason":"operation_not_granted"}
        assets=set(json.loads(row["asset_scope_json"])); parties=set(json.loads(row["counterparty_scope_json"]))
        if assets and asset_id not in assets: return {"allowed":False,"reason":"asset_out_of_scope"}
        if parties and counterparty_id not in parties: return {"allowed":False,"reason":"counterparty_out_of_scope"}
        if amount is not None and row["financial_limit"] is not None and float(amount)>float(row["financial_limit"]): return {"allowed":False,"reason":"financial_limit_exceeded"}
        if bool(row["approval_required"]):
            with self._connect() as db: approval=db.execute("SELECT 1 FROM approvals WHERE capability_id=? AND operation=? AND (? IS NULL OR object_ref=?) ORDER BY created_at_ms DESC LIMIT 1",(capability_id,op,object_ref,object_ref)).fetchone()
            if not approval: return {"allowed":False,"reason":"approval_required"}
        return {"allowed":True,"capability_id":capability_id,"grantor_entity_id":row["grantor_entity_id"],"agent_id":row["agent_id"],"operation":op}

    def status(self) -> dict:
        with self._connect() as db:
            active=db.execute("SELECT COUNT(*) FROM capabilities WHERE status='ACTIVE'").fetchone()[0]
            approvals=db.execute("SELECT COUNT(*) FROM approvals").fetchone()[0]
        return {"ready":True,"least_privilege":True,"fail_closed":True,"active_capabilities":int(active),"approvals":int(approvals),"database":str(self.path)}

class ThresholdAuthorityStore:
    """Machine-enforced M-of-N approval for high-impact organization authority changes."""
    def __init__(self,state_dir: str|Path,identity):
        self.root=Path(state_dir)/"authority"; self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/"threshold_authority.sqlite"; self.identity=identity; self._init_db()

    @contextmanager
    def _connect(self):
        db=sqlite3.connect(self.path,timeout=30); db.row_factory=sqlite3.Row
        try: yield db; db.commit()
        except Exception: db.rollback(); raise
        finally: db.close()

    def _init_db(self):
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("CREATE TABLE IF NOT EXISTS threshold_policies(policy_id TEXT PRIMARY KEY,controller_entity_id TEXT NOT NULL,operation TEXT NOT NULL,approvers_json TEXT NOT NULL,threshold_n INTEGER NOT NULL,status TEXT NOT NULL,signature_json TEXT NOT NULL,created_at_ms INTEGER NOT NULL,revoked_at_ms INTEGER)")
            db.execute("CREATE TABLE IF NOT EXISTS threshold_votes(vote_id TEXT PRIMARY KEY,policy_id TEXT NOT NULL,request_id TEXT NOT NULL,approver_entity_id TEXT NOT NULL,object_ref TEXT,signature_json TEXT NOT NULL,created_at_ms INTEGER NOT NULL,UNIQUE(policy_id,request_id,approver_entity_id))")
    def create_policy(self,controller_entity_id: str,operation: str,approvers: list[str],threshold: int) -> dict:
        members=sorted({str(x).strip() for x in approvers if str(x).strip()})
        if not members: raise ValueError("at least one approver required")
        threshold=int(threshold)
        if threshold<1 or threshold>len(members): raise ValueError("threshold must be between 1 and approver count")
        policy_id=_id("thr1"); now=_now(); op=str(operation or "").upper().strip()
        if not op: raise ValueError("operation required")
        body={"schema":"entity-threshold-authority-v1","policy_id":policy_id,"controller_entity_id":controller_entity_id,"operation":op,"approvers":members,"threshold":threshold,"status":"ACTIVE","created_at_ms":now}
        sig=self.identity.sign(controller_entity_id,body)
        with self._connect() as db:
            db.execute("INSERT INTO threshold_policies VALUES(?,?,?,?,?,?,?,?,?)",(policy_id,controller_entity_id,op,json.dumps(members),threshold,"ACTIVE",json.dumps(sig,sort_keys=True),now,None))
        return dict(body,signature=sig)

    def revoke_policy(self,controller_entity_id: str,policy_id: str) -> dict:
        with self._connect() as db: row=db.execute("SELECT * FROM threshold_policies WHERE policy_id=?",(policy_id,)).fetchone()
        if not row: raise KeyError("threshold policy not found")
        if row["controller_entity_id"]!=controller_entity_id: raise PermissionError("threshold policy controller mismatch")
        now=_now()
        with self._connect() as db: db.execute("UPDATE threshold_policies SET status='REVOKED',revoked_at_ms=? WHERE policy_id=?",(now,policy_id))
        return {"policy_id":policy_id,"status":"REVOKED","revoked_at_ms":now}
    def approve(self,policy_id: str,request_id: str,approver_entity_id: str,object_ref: str|None=None) -> dict:
        with self._connect() as db: row=db.execute("SELECT * FROM threshold_policies WHERE policy_id=?",(policy_id,)).fetchone()
        if not row: raise KeyError("threshold policy not found")
        if row["status"]!="ACTIVE": raise PermissionError("threshold policy not active")
        members=set(json.loads(row["approvers_json"]))
        if approver_entity_id not in members: raise PermissionError("approver is outside threshold authority")
        vote_id=_id("vote1"); now=_now(); body={"schema":"entity-threshold-vote-v1","vote_id":vote_id,"policy_id":policy_id,"request_id":str(request_id),"approver_entity_id":approver_entity_id,"operation":row["operation"],"object_ref":object_ref,"created_at_ms":now}
        sig=self.identity.sign(approver_entity_id,body)
        try:
            with self._connect() as db: db.execute("INSERT INTO threshold_votes VALUES(?,?,?,?,?,?,?)",(vote_id,policy_id,str(request_id),approver_entity_id,object_ref,json.dumps(sig,sort_keys=True),now))
        except sqlite3.IntegrityError as exc: raise ValueError("duplicate threshold approval") from exc
        return dict(body,signature=sig)

    def authorize(self,policy_id: str,request_id: str,operation: str,object_ref: str|None=None) -> dict:
        with self._connect() as db: row=db.execute("SELECT * FROM threshold_policies WHERE policy_id=?",(policy_id,)).fetchone()
        if not row: return {"allowed":False,"reason":"threshold_policy_not_found"}
        if row["status"]!="ACTIVE": return {"allowed":False,"reason":"threshold_policy_not_active"}
        if str(operation).upper()!=row["operation"]: return {"allowed":False,"reason":"operation_mismatch"}
        with self._connect() as db:
            votes=db.execute("SELECT DISTINCT approver_entity_id,object_ref FROM threshold_votes WHERE policy_id=? AND request_id=?",(policy_id,str(request_id))).fetchall()
        matching=[v for v in votes if object_ref is None or v["object_ref"]==object_ref]
        count=len(matching); threshold=int(row["threshold_n"])
        return {"allowed":count>=threshold,"reason":"threshold_met" if count>=threshold else "threshold_not_met","approvals":count,"threshold":threshold,"policy_id":policy_id,"request_id":str(request_id)}
