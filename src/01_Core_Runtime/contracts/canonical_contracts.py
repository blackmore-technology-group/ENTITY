from __future__ import annotations
from pathlib import Path
from contextlib import contextmanager
from threading import RLock
import json, re, secrets, sqlite3, time

ENTITY_ID_RE=re.compile(r"^(?:ent1|ent2)-[a-z2-7]{52}$")
LICENCE_STATES={"DRAFT","OFFERED","COUNTERED","ACCEPTED","ACTIVE","SUSPENDED","REVOKED_FOR_FUTURE_USE","EXPIRED","TERMINATED","DISPUTED","CLOSED"}
TERMINAL_STATES={"EXPIRED","TERMINATED","CLOSED"}

def _now(): return int(time.time()*1000)
def _id(prefix): return f"{prefix}-"+secrets.token_hex(20)

class ContractLicensingEngine:
    """Signed bilateral licence state machine bound to recorded licensing authority."""
    def __init__(self,state_dir: str|Path,identity,rights_graph,event_ledger=None,local_controller_check=None):
        self.root=Path(state_dir)/"contracts"; self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/"licensing.sqlite"; self.identity=identity; self.rights=rights_graph
        self.ledger=event_ledger; self.local_controller_check=local_controller_check or self._default_local
        self._lock=RLock(); self._init_db()
    def _default_local(self,entity_id: str) -> bool:
        try: self.identity.load_manifest(entity_id); return True
        except Exception: return False
    def _require_id(self,entity_id: str):
        if not ENTITY_ID_RE.fullmatch(str(entity_id or "")): raise ValueError("invalid Entity ID")
    def _require_local(self,entity_id: str):
        self._require_id(entity_id)
        if not self.local_controller_check(entity_id): raise PermissionError("operation requires locally controlled Entity")
    @contextmanager
    def _connect(self):
        db=sqlite3.connect(self.path,timeout=30); db.row_factory=sqlite3.Row
        try: yield db; db.commit()
        except Exception: db.rollback(); raise
        finally: db.close()
    def _init_db(self):
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=FULL")
            db.execute("CREATE TABLE IF NOT EXISTS licences(licence_id TEXT PRIMARY KEY,grantor_entity_id TEXT NOT NULL,licensee_entity_id TEXT NOT NULL,terms_json TEXT NOT NULL,terms_version INTEGER NOT NULL,state TEXT NOT NULL,authority_basis_json TEXT NOT NULL,created_at_ms INTEGER NOT NULL,updated_at_ms INTEGER NOT NULL,expires_at_ms INTEGER)")
            db.execute("CREATE TABLE IF NOT EXISTS licence_events(event_id TEXT PRIMARY KEY,licence_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_entity_id TEXT NOT NULL,from_state TEXT,to_state TEXT,terms_version INTEGER NOT NULL,payload_json TEXT NOT NULL,signature_json TEXT NOT NULL,created_at_ms INTEGER NOT NULL)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_licence_parties ON licences(grantor_entity_id,licensee_entity_id,state)")
    @staticmethod
    def _normalize_terms(terms: dict) -> dict:
        t=dict(terms or {})
        required=("assets","rights","purpose","scope","territory","duration","consideration","usage_requirements","reporting_requirements","retention_requirements","derivative_rules","revocation_rules","termination_rules")
        missing=[k for k in required if k not in t]
        if missing: raise ValueError(f"licence terms missing required fields: {missing}")
        t["assets"]=sorted({str(x) for x in (t.get("assets") or []) if str(x)})
        t["rights"]=sorted({str(x).upper() for x in (t.get("rights") or []) if str(x)})
        if not t["assets"] or not t["rights"]: raise ValueError("licence requires assets and rights")
        return t
    def _authority_basis(self,grantor: str,terms: dict) -> list[str]:
        claim_ids=[]
        for asset_id in terms["assets"]:
            decision=self.rights.can_license(grantor,asset_id)
            if not decision.get("allowed"): raise PermissionError(f"recorded licensing authority unavailable for asset {asset_id}")
            claim_ids.extend(str(c["claim_id"]) for c in decision.get("eligible_claims") or [])
        return sorted(set(claim_ids))
    def _event(self,db,licence_id,event_type,actor,from_state,to_state,version,payload):
        event_id=_id("lev2"); created=_now()
        body={"schema":"entity-licence-event-v2","event_id":event_id,"licence_id":licence_id,"event_type":event_type,
              "actor_entity_id":actor,"from_state":from_state,"to_state":to_state,"terms_version":int(version),
              "payload":dict(payload or {}),"created_at_ms":created}
        sig=self.identity.sign(actor,body)
        db.execute("INSERT INTO licence_events VALUES(?,?,?,?,?,?,?,?,?,?)",(event_id,licence_id,event_type,actor,from_state,to_state,int(version),json.dumps(body["payload"],sort_keys=True),json.dumps(sig,sort_keys=True),created))
        return dict(body,signature=sig)
    def _audit(self,actor: str,event_type: str,payload: dict):
        if self.ledger is not None:
            self.ledger.append(actor,event_type,subject_ids=[str(payload.get("licence_id") or "")],object_ids=list(payload.get("assets") or []),payload=payload,evidence_origin="DIRECT_OBSERVATION",confidence=1.0)
    def create_draft(self,grantor_entity_id: str,licensee_entity_id: str,terms: dict,*,expires_at_ms: int|None=None) -> dict:
        self._require_local(grantor_entity_id); self._require_id(licensee_entity_id)
        normalized=self._normalize_terms(terms); licence_id=_id("lic2"); now=_now()
        with self._lock,self._connect() as db:
            db.execute("INSERT INTO licences VALUES(?,?,?,?,?,?,?,?,?,?)",(licence_id,grantor_entity_id,licensee_entity_id,json.dumps(normalized,sort_keys=True),1,"DRAFT","[]",now,now,expires_at_ms))
            event=self._event(db,licence_id,"LICENCE_DRAFT_CREATED",grantor_entity_id,None,"DRAFT",1,{"terms":normalized,"expires_at_ms":expires_at_ms})
        self._audit(grantor_entity_id,"licence.draft_created",{"licence_id":licence_id,"assets":normalized["assets"]})
        return {"licence_id":licence_id,"state":"DRAFT","terms_version":1,"event":event}
    def _load(self,licence_id: str):
        with self._connect() as db: row=db.execute("SELECT * FROM licences WHERE licence_id=?",(licence_id,)).fetchone()
        if not row: raise KeyError("licence not found")
        return row
    def _transition(self,row,actor: str,to_state: str,event_type: str,payload: dict|None=None,authority_basis: list[str]|None=None) -> dict:
        from_state=str(row["state"]); version=int(row["terms_version"]); now=_now()
        if to_state not in LICENCE_STATES: raise ValueError("unsupported licence state")
        if from_state in TERMINAL_STATES: raise ValueError("terminal licence state cannot transition")
        basis=json.loads(row["authority_basis_json"] or "[]") if authority_basis is None else list(authority_basis)
        with self._lock,self._connect() as db:
            current=db.execute("SELECT state,terms_version FROM licences WHERE licence_id=?",(row["licence_id"],)).fetchone()
            if not current or current["state"]!=from_state or int(current["terms_version"])!=version: raise RuntimeError("licence state changed concurrently")
            db.execute("UPDATE licences SET state=?,authority_basis_json=?,updated_at_ms=? WHERE licence_id=?",(to_state,json.dumps(basis,sort_keys=True),now,row["licence_id"]))
            event=self._event(db,row["licence_id"],event_type,actor,from_state,to_state,version,dict(payload or {}))
        self._audit(actor,event_type.lower().replace("_","."),{"licence_id":row["licence_id"],"assets":json.loads(row["terms_json"])["assets"],"to_state":to_state})
        return {"licence_id":row["licence_id"],"state":to_state,"terms_version":version,"authority_basis_claim_ids":basis,"event":event}
    def offer(self,grantor_entity_id: str,licence_id: str) -> dict:
        row=self._load(licence_id); self._require_local(grantor_entity_id)
        if row["grantor_entity_id"]!=grantor_entity_id: raise PermissionError("only grantor may offer")
        if row["state"] not in {"DRAFT","COUNTERED"}: raise ValueError("invalid transition to OFFERED")
        terms=json.loads(row["terms_json"]); basis=self._authority_basis(grantor_entity_id,terms)
        return self._transition(row,grantor_entity_id,"OFFERED","LICENCE_OFFERED",{"authority_basis_claim_ids":basis},basis)
    def counter(self,licensee_entity_id: str,licence_id: str,terms: dict) -> dict:
        row=self._load(licence_id); self._require_local(licensee_entity_id)
        if row["licensee_entity_id"]!=licensee_entity_id: raise PermissionError("only licensee may counter")
        if row["state"]!="OFFERED": raise ValueError("only an offered licence may be countered")
        normalized=self._normalize_terms(terms); version=int(row["terms_version"])+1; now=_now()
        with self._lock,self._connect() as db:
            db.execute("UPDATE licences SET terms_json=?,terms_version=?,state='COUNTERED',authority_basis_json='[]',updated_at_ms=? WHERE licence_id=?",(json.dumps(normalized,sort_keys=True),version,now,licence_id))
            event=self._event(db,licence_id,"LICENCE_COUNTERED",licensee_entity_id,"OFFERED","COUNTERED",version,{"terms":normalized})
        self._audit(licensee_entity_id,"licence.countered",{"licence_id":licence_id,"assets":normalized["assets"]})
        return {"licence_id":licence_id,"state":"COUNTERED","terms_version":version,"event":event}
    def accept(self,actor_entity_id: str,licence_id: str) -> dict:
        row=self._load(licence_id); state=str(row["state"])
        expected=row["licensee_entity_id"] if state=="OFFERED" else row["grantor_entity_id"] if state=="COUNTERED" else None
        if not expected: raise ValueError("licence is not in an acceptable state")
        if actor_entity_id!=expected: raise PermissionError("wrong party for licence acceptance")
        self._require_local(actor_entity_id)
        basis=None
        if state=="COUNTERED":
            terms=json.loads(row["terms_json"]); basis=self._authority_basis(actor_entity_id,terms)
        return self._transition(row,actor_entity_id,"ACCEPTED","LICENCE_ACCEPTED",authority_basis=basis)
    def activate(self,grantor_entity_id: str,licence_id: str) -> dict:
        row=self._load(licence_id); self._require_local(grantor_entity_id)
        if row["grantor_entity_id"]!=grantor_entity_id: raise PermissionError("only grantor may activate")
        if row["state"]!="ACCEPTED": raise ValueError("licence must be ACCEPTED before activation")
        terms=json.loads(row["terms_json"]); basis=self._authority_basis(grantor_entity_id,terms)
        return self._transition(row,grantor_entity_id,"ACTIVE","LICENCE_ACTIVATED",{"authority_rechecked":True},basis)
    def future_revoke(self,grantor_entity_id: str,licence_id: str,reason: str="") -> dict:
        row=self._load(licence_id); self._require_local(grantor_entity_id)
        if row["grantor_entity_id"]!=grantor_entity_id: raise PermissionError("only grantor may revoke future use")
        if row["state"] not in {"ACTIVE","SUSPENDED","DISPUTED"}: raise ValueError("licence is not revocable for future use")
        return self._transition(row,grantor_entity_id,"REVOKED_FOR_FUTURE_USE","LICENCE_FUTURE_USE_REVOKED",{"reason":str(reason)[:1024],"historical_authorized_use_preserved":True})
    def terminate(self,actor_entity_id: str,licence_id: str,reason: str="") -> dict:
        row=self._load(licence_id); self._require_local(actor_entity_id)
        if actor_entity_id not in {row["grantor_entity_id"],row["licensee_entity_id"]}: raise PermissionError("party required")
        if row["state"] in TERMINAL_STATES: raise ValueError("licence already terminal")
        return self._transition(row,actor_entity_id,"TERMINATED","LICENCE_TERMINATED",{"reason":str(reason)[:1024]})
    def get(self,licence_id: str) -> dict:
        row=self._load(licence_id); out=dict(row)
        out["terms"]=json.loads(out.pop("terms_json")); out["authority_basis_claim_ids"]=json.loads(out.pop("authority_basis_json") or "[]")
        with self._connect() as db:
            events=db.execute("SELECT * FROM licence_events WHERE licence_id=? ORDER BY created_at_ms,event_id",(licence_id,)).fetchall()
        out["events"]=[]
        for raw in events:
            e=dict(raw); e["payload"]=json.loads(e.pop("payload_json")); e["signature"]=json.loads(e.pop("signature_json")); out["events"].append(e)
        return out
    def verify_history(self,licence_id: str) -> dict:
        item=self.get(licence_id); failures=[]
        for event in item["events"]:
            body={"schema":"entity-licence-event-v2","event_id":event["event_id"],"licence_id":event["licence_id"],"event_type":event["event_type"],
                  "actor_entity_id":event["actor_entity_id"],"from_state":event["from_state"],"to_state":event["to_state"],
                  "terms_version":event["terms_version"],"payload":event["payload"],"created_at_ms":event["created_at_ms"]}
            try:
                manifest=self.identity.load_manifest(event["actor_entity_id"])
                if not self.identity.verify_signature(manifest,body,event["signature"]): failures.append(event["event_id"])
            except Exception: failures.append(event["event_id"])
        return {"pass":not failures,"licence_id":licence_id,"events":len(item["events"]),"failed_event_ids":failures}
    def status(self) -> dict:
        with self._connect() as db:
            total=int(db.execute("SELECT COUNT(*) FROM licences").fetchone()[0]); active=int(db.execute("SELECT COUNT(*) FROM licences WHERE state='ACTIVE'").fetchone()[0])
        return {"ready":True,"schema":"entity-contract-licensing-v2","bilateral_signed_state_machine":True,"rights_authority_rechecked_on_activation":True,
                "offers_are_not_active":True,"future_revocation_preserves_history":True,"licences":total,"active":active,"database":str(self.path)}
