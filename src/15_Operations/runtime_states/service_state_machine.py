from __future__ import annotations
from pathlib import Path
from contextlib import contextmanager
from threading import RLock
import json, sqlite3, time, uuid

STATES={"NORMAL","DEGRADED","OFFLINE","DEPENDENCY_UNAVAILABLE","MALICIOUS_INPUT","CONFLICTING_STATE","RECOVERY","QUARANTINED"}
HIGH_IMPACT={"AUTHORITY_MUTATE","RIGHTS_MUTATE","EXCLUSIVE_LICENSE_ACTIVATE","SETTLEMENT_EXECUTE","CAPABILITY_GRANT","KEY_ROTATE","CREDENTIAL_ISSUE"}
READ_ONLY={"READ","READ_LOCAL","VERIFY","VERIFY_LOCAL","EXPORT","BACKUP","STATUS","FORENSICS"}
RECOVERY_OPS={"RECOVERY_BEGIN","RESTORE","MIGRATE","DISPUTE","QUARANTINE"}
NORMAL_OPS=READ_ONLY|RECOVERY_OPS|HIGH_IMPACT|{"ASSET_REGISTER","POLICY_EVALUATE","CONSENT_GRANT","LICENSE_OFFER","LICENSE_ACCEPT","USAGE_RECORD","PROVENANCE_APPEND","CREDENTIAL_VERIFY","CONNECTOR_READ"}

def _now(): return int(time.time()*1000)

def _policy(state:str)->dict:
    state=str(state).upper()
    if state=="NORMAL": allowed=NORMAL_OPS
    elif state=="DEGRADED": allowed=READ_ONLY|{"RECOVERY_BEGIN","DISPUTE"}
    elif state=="OFFLINE": allowed={"READ_LOCAL","VERIFY_LOCAL","EXPORT","BACKUP","STATUS","RECOVERY_BEGIN"}
    elif state=="DEPENDENCY_UNAVAILABLE": allowed=READ_ONLY|{"RECOVERY_BEGIN","MIGRATE"}
    elif state=="MALICIOUS_INPUT": allowed={"STATUS","VERIFY","FORENSICS","QUARANTINE","RECOVERY_BEGIN"}
    elif state=="CONFLICTING_STATE": allowed={"STATUS","READ","VERIFY","DISPUTE","RECOVERY_BEGIN"}
    elif state=="RECOVERY": allowed={"STATUS","VERIFY","VERIFY_LOCAL","RESTORE","MIGRATE","BACKUP","FORENSICS"}
    elif state=="QUARANTINED": allowed={"STATUS","VERIFY","FORENSICS","RECOVERY_BEGIN"}
    else: allowed=set()
    return {"state":state,"allowed_operations":allowed,"fail_closed_high_impact":state!="NORMAL"}

TRANSITIONS={
 "NORMAL":{"DEGRADED","OFFLINE","DEPENDENCY_UNAVAILABLE","MALICIOUS_INPUT","CONFLICTING_STATE","RECOVERY"},
 "DEGRADED":{"NORMAL","OFFLINE","DEPENDENCY_UNAVAILABLE","MALICIOUS_INPUT","CONFLICTING_STATE","RECOVERY"},
 "OFFLINE":{"NORMAL","DEGRADED","RECOVERY"},
 "DEPENDENCY_UNAVAILABLE":{"NORMAL","DEGRADED","OFFLINE","RECOVERY"},
 "MALICIOUS_INPUT":{"NORMAL","QUARANTINED","RECOVERY"},
 "CONFLICTING_STATE":{"NORMAL","QUARANTINED","RECOVERY"},
 "RECOVERY":{"NORMAL","DEGRADED","OFFLINE","QUARANTINED"},
 "QUARANTINED":{"NORMAL","RECOVERY"},
}

class ServiceStateMachine:
    def __init__(self,state_dir:str|Path):
        self.root=Path(state_dir)/"service_states"; self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/"service_states.sqlite"; self._lock=RLock(); self._init_db()
    @contextmanager
    def _connect(self):
        db=sqlite3.connect(self.path,timeout=30); db.row_factory=sqlite3.Row
        try: yield db; db.commit()
        except Exception: db.rollback(); raise
        finally: db.close()
    def _init_db(self):
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("CREATE TABLE IF NOT EXISTS services(service_id TEXT PRIMARY KEY,state TEXT NOT NULL,reason TEXT NOT NULL,version INTEGER NOT NULL,updated_at_ms INTEGER NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS transitions(transition_id TEXT PRIMARY KEY,service_id TEXT NOT NULL,from_state TEXT,to_state TEXT NOT NULL,trigger TEXT NOT NULL,evidence_json TEXT NOT NULL,created_at_ms INTEGER NOT NULL)")
    def register(self,service_id:str)->dict:
        sid=str(service_id).strip()
        if not sid: raise ValueError("service_id required")
        now=_now()
        with self._connect() as db:
            db.execute("INSERT OR IGNORE INTO services VALUES(?,?,?,?,?)",(sid,"NORMAL","registered",1,now))
            row=db.execute("SELECT * FROM services WHERE service_id=?",(sid,)).fetchone()
        return dict(row)
    def get(self,service_id:str)->dict:
        with self._connect() as db: row=db.execute("SELECT * FROM services WHERE service_id=?",(service_id,)).fetchone()
        if not row: raise KeyError("service not registered")
        return dict(row)
    def transition(self,service_id:str,to_state:str,*,trigger:str,evidence:dict|None=None)->dict:
        target=str(to_state).upper()
        if target not in STATES: raise ValueError("invalid service state")
        with self._lock,self._connect() as db:
            db.execute("BEGIN IMMEDIATE"); row=db.execute("SELECT * FROM services WHERE service_id=?",(service_id,)).fetchone()
            if not row: raise KeyError("service not registered")
            current=str(row["state"])
            if target==current: raise ValueError("state transition must change state")
            if target not in TRANSITIONS[current]: raise PermissionError(f"invalid transition {current}->{target}")
            ev=dict(evidence or {})
            if target in {"MALICIOUS_INPUT","CONFLICTING_STATE","QUARANTINED"} and not ev: raise ValueError("security/conflict transition requires evidence")
            now=_now(); version=int(row["version"])+1; tid="sst1-"+uuid.uuid4().hex
            db.execute("UPDATE services SET state=?,reason=?,version=?,updated_at_ms=? WHERE service_id=?",(target,str(trigger)[:1024],version,now,service_id))
            db.execute("INSERT INTO transitions VALUES(?,?,?,?,?,?,?)",(tid,service_id,current,target,str(trigger)[:1024],json.dumps(ev,sort_keys=True),now))
        return {"transition_id":tid,"service_id":service_id,"from_state":current,"to_state":target,"version":version,"evidence":ev}
    def authorize_operation(self,service_id:str,operation:str)->dict:
        row=self.get(service_id); state=str(row["state"]); op=str(operation or "").upper(); policy=_policy(state)
        if not op: return {"allowed":False,"reason":"operation_required","state":state}
        if op in HIGH_IMPACT and state!="NORMAL": return {"allowed":False,"reason":"high_impact_fail_closed","state":state,"operation":op}
        allowed=op in policy["allowed_operations"]
        return {"allowed":bool(allowed),"reason":"allowed" if allowed else "operation_not_allowed_in_state","state":state,"operation":op}
    def describe(self,service_id:str)->dict:
        row=self.get(service_id); state=str(row["state"]); policy=_policy(state)
        status={"NORMAL":"operational","DEGRADED":"limited functionality","OFFLINE":"local/offline only","DEPENDENCY_UNAVAILABLE":"required dependency unavailable","MALICIOUS_INPUT":"malicious input detected","CONFLICTING_STATE":"conflicting authoritative state","RECOVERY":"recovery in progress","QUARANTINED":"service quarantined"}[state]
        recovery={"NORMAL":"none","DEGRADED":"restore dependency or enter recovery","OFFLINE":"restore connectivity/dependency or recover","DEPENDENCY_UNAVAILABLE":"restore dependency or migrate","MALICIOUS_INPUT":"quarantine evidence and recover","CONFLICTING_STATE":"resolve dispute/conflict before mutation","RECOVERY":"verify restored state before normal","QUARANTINED":"forensic review then recovery"}[state]
        return {**row,"user_visible_status":status,"audit_behavior":"record all transitions and denied high-impact operations","recovery_action":recovery,"fail_closed":state!="NORMAL","policy":policy}
    def history(self,service_id:str)->list[dict]:
        with self._connect() as db: rows=db.execute("SELECT * FROM transitions WHERE service_id=? ORDER BY created_at_ms,transition_id",(service_id,)).fetchall()
        out=[]
        for row in rows:
            item=dict(row); item["evidence"]=json.loads(item.pop("evidence_json")); out.append(item)
        return out
    def status(self)->dict:
        with self._connect() as db:
            rows=db.execute("SELECT state,COUNT(*) n FROM services GROUP BY state").fetchall()
        return {"ready":True,"schema":"entity-service-state-machine-v1","states":sorted(STATES),"high_impact_fail_closed":True,"service_counts":{r["state"]:int(r["n"]) for r in rows}}
