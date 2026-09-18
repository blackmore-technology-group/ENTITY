from __future__ import annotations
from pathlib import Path
from threading import RLock
from contextlib import contextmanager
import json, secrets, sqlite3, time

ACTIONS={"VIEW","COPY","DOWNLOAD","PUBLIC_DISPLAY","COMMERCIAL_REUSE","DERIVATIVE_WORK","AI_TRAINING","AI_EVALUATION","AI_INFERENCE","MODEL_TUNING","EMBEDDING","INDEXING","SEARCH","AD_TARGETING","PROFILE_BUILDING","FACIAL_RECOGNITION","LOCATION_ANALYSIS","RESEARCH","SUBLICENSE","REDISTRIBUTE"}
DECISIONS={"PERMIT","PROHIBIT","LICENSE_REQUIRED","OWNER_ONLY"}


def _now(): return int(time.time()*1000)
def _id(prefix): return f"{prefix}-"+secrets.token_hex(20)


class PolicyConsentEngine:
    """Versioned ODRL-inspired policy and purpose-bound consent; unknown actions fail closed."""
    def __init__(self,state_dir: str|Path,identity):
        self.root=Path(state_dir)/"policy_consent"; self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/"policy_consent.sqlite"; self.identity=identity; self._lock=RLock(); self._init_db()

    @contextmanager
    def _connect(self):
        db=sqlite3.connect(self.path,timeout=30); db.row_factory=sqlite3.Row
        try: yield db; db.commit()
        except Exception: db.rollback(); raise
        finally: db.close()

    def _init_db(self):
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("CREATE TABLE IF NOT EXISTS policies(policy_id TEXT NOT NULL,version INTEGER NOT NULL,controller_entity_id TEXT NOT NULL,name TEXT NOT NULL,rules_json TEXT NOT NULL,jurisdiction TEXT,status TEXT NOT NULL,signature_json TEXT NOT NULL,created_at_ms INTEGER NOT NULL,PRIMARY KEY(policy_id,version))")
            db.execute("CREATE TABLE IF NOT EXISTS consents(consent_id TEXT PRIMARY KEY,policy_id TEXT NOT NULL,policy_version INTEGER NOT NULL,authorizing_entity_id TEXT NOT NULL,counterparty_entity_id TEXT,purpose TEXT NOT NULL,asset_scope_json TEXT NOT NULL,status TEXT NOT NULL,expires_at_ms INTEGER,signature_json TEXT NOT NULL,created_at_ms INTEGER NOT NULL,revoked_at_ms INTEGER)")
    @staticmethod
    def _normalize_rules(rules: dict|None) -> dict:
        out={}
        for action,raw in dict(rules or {}).items():
            key=str(action).upper()
            if key not in ACTIONS: raise ValueError(f"unknown policy action: {key}")
            item=dict(raw) if isinstance(raw,dict) else {"decision":str(raw)}
            decision=str(item.get("decision") or "PROHIBIT").upper()
            if decision not in DECISIONS: raise ValueError(f"invalid decision for {key}")
            out[key]={"decision":decision,"constraints":dict(item.get("constraints") or {}),"duties":list(item.get("duties") or [])}
        return out

    def create_policy(self,controller_entity_id: str,name: str,rules: dict|None=None,jurisdiction: str|None=None) -> dict:
        policy_id=_id("pol1"); version=1; now=_now(); normalized=self._normalize_rules(rules)
        body={"schema":"entity-policy-v1","policy_id":policy_id,"version":version,"controller_entity_id":controller_entity_id,"name":str(name)[:256],"rules":normalized,"jurisdiction":jurisdiction,"status":"ACTIVE","created_at_ms":now}
        sig=self.identity.sign(controller_entity_id,body)
        with self._connect() as db: db.execute("INSERT INTO policies VALUES(?,?,?,?,?,?,?,?,?)",(policy_id,version,controller_entity_id,body["name"],json.dumps(normalized,sort_keys=True),jurisdiction,"ACTIVE",json.dumps(sig,sort_keys=True),now))
        return dict(body,signature=sig)

    def revise_policy(self,controller_entity_id: str,policy_id: str,rules: dict|None=None,name: str|None=None,jurisdiction: str|None=None) -> dict:
        with self._connect() as db: prior=db.execute("SELECT * FROM policies WHERE policy_id=? ORDER BY version DESC LIMIT 1",(policy_id,)).fetchone()
        if not prior: raise KeyError("policy not found")
        if prior["controller_entity_id"]!=controller_entity_id: raise PermissionError("policy controller mismatch")
        version=int(prior["version"])+1; normalized=self._normalize_rules(rules if rules is not None else json.loads(prior["rules_json"])); now=_now()
        body={"schema":"entity-policy-v1","policy_id":policy_id,"version":version,"controller_entity_id":controller_entity_id,"name":str(name or prior["name"])[:256],"rules":normalized,"jurisdiction":jurisdiction if jurisdiction is not None else prior["jurisdiction"],"status":"ACTIVE","supersedes_version":int(prior["version"]),"created_at_ms":now}
        sig=self.identity.sign(controller_entity_id,body)
        with self._connect() as db: db.execute("INSERT INTO policies VALUES(?,?,?,?,?,?,?,?,?)",(policy_id,version,controller_entity_id,body["name"],json.dumps(normalized,sort_keys=True),body["jurisdiction"],"ACTIVE",json.dumps(sig,sort_keys=True),now))
        return dict(body,signature=sig)
    def evaluate(self,policy_id: str,action: str,*,version: int|None=None) -> dict:
        key=str(action or "").upper()
        if key not in ACTIONS: return {"allowed":False,"decision":"PROHIBIT","reason":"unknown_action_fail_closed"}
        with self._connect() as db:
            if version is None: row=db.execute("SELECT * FROM policies WHERE policy_id=? ORDER BY version DESC LIMIT 1",(policy_id,)).fetchone()
            else: row=db.execute("SELECT * FROM policies WHERE policy_id=? AND version=?",(policy_id,int(version))).fetchone()
        if not row: return {"allowed":False,"decision":"PROHIBIT","reason":"policy_not_found"}
        rule=json.loads(row["rules_json"]).get(key,{"decision":"PROHIBIT","constraints":{},"duties":[]})
        return {"allowed":rule["decision"]=="PERMIT","decision":rule["decision"],"constraints":rule.get("constraints",{}),"duties":rule.get("duties",[]),"policy_id":policy_id,"policy_version":int(row["version"])}

    def grant_consent(self,authorizing_entity_id: str,policy_id: str,*,purpose: str,asset_scope: list[str]|None=None,counterparty_entity_id: str|None=None,expires_at_ms: int|None=None) -> dict:
        with self._connect() as db: row=db.execute("SELECT * FROM policies WHERE policy_id=? ORDER BY version DESC LIMIT 1",(policy_id,)).fetchone()
        if not row: raise KeyError("policy not found")
        if row["controller_entity_id"]!=authorizing_entity_id: raise PermissionError("consent authorizer must control policy")
        purpose=str(purpose or "").strip()
        if not purpose: raise ValueError("purpose is required")
        consent_id=_id("con1"); now=_now(); scope=sorted({str(x) for x in (asset_scope or []) if str(x)})
        body={"schema":"entity-consent-v1","consent_id":consent_id,"policy_id":policy_id,"policy_version":int(row["version"]),"authorizing_entity_id":authorizing_entity_id,"counterparty_entity_id":counterparty_entity_id,"purpose":purpose,"asset_scope":scope,"status":"ACTIVE","expires_at_ms":expires_at_ms,"created_at_ms":now}
        sig=self.identity.sign(authorizing_entity_id,body)
        with self._connect() as db: db.execute("INSERT INTO consents VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(consent_id,policy_id,int(row["version"]),authorizing_entity_id,counterparty_entity_id,purpose,json.dumps(scope),"ACTIVE",expires_at_ms,json.dumps(sig,sort_keys=True),now,None))
        return dict(body,signature=sig)

    def authorize_consent(self,consent_id: str,*,counterparty_entity_id: str,purpose: str,asset_scope: list[str],action: str) -> dict:
        now=_now(); key=str(action or "").upper(); requested=sorted({str(x) for x in asset_scope if str(x)})
        if key not in ACTIONS: return {"allowed":False,"reason":"unknown_action_fail_closed"}
        with self._connect() as db: row=db.execute("SELECT * FROM consents WHERE consent_id=?",(str(consent_id),)).fetchone()
        if not row: return {"allowed":False,"reason":"consent_not_found"}
        if row["status"]!="ACTIVE": return {"allowed":False,"reason":"consent_not_active"}
        if row["expires_at_ms"] is not None and int(row["expires_at_ms"])<=now: return {"allowed":False,"reason":"consent_expired"}
        if row["counterparty_entity_id"] and row["counterparty_entity_id"]!=counterparty_entity_id: return {"allowed":False,"reason":"consent_counterparty_mismatch"}
        if str(row["purpose"])!=str(purpose): return {"allowed":False,"reason":"consent_purpose_mismatch"}
        scope=set(json.loads(row["asset_scope_json"]));
        if scope and not set(requested).issubset(scope): return {"allowed":False,"reason":"consent_asset_scope_mismatch"}
        policy=self.evaluate(row["policy_id"],key,version=int(row["policy_version"]))
        allowed=policy.get("decision") in {"PERMIT","LICENSE_REQUIRED"}
        return {"allowed":bool(allowed),"reason":"authorized" if allowed else "policy_prohibits_action","consent_id":consent_id,"policy":policy}

    def revoke_consent(self,authorizing_entity_id: str,consent_id: str) -> dict:
        with self._connect() as db: row=db.execute("SELECT * FROM consents WHERE consent_id=?",(consent_id,)).fetchone()
        if not row: raise KeyError("consent not found")
        if row["authorizing_entity_id"]!=authorizing_entity_id: raise PermissionError("consent authorizer mismatch")
        if row["status"]!="ACTIVE": raise ValueError("consent is not active")
        now=_now()
        with self._connect() as db: db.execute("UPDATE consents SET status='REVOKED',revoked_at_ms=? WHERE consent_id=?",(now,consent_id))
        return {"consent_id":consent_id,"status":"REVOKED","revoked_at_ms":now,"historical_policy_version":int(row["policy_version"])}

    def status(self) -> dict:
        with self._connect() as db: pc=db.execute("SELECT COUNT(*) FROM policies").fetchone()[0]; cc=db.execute("SELECT COUNT(*) FROM consents").fetchone()[0]
        return {"ready":True,"policy_model":"ODRL_INSPIRED_ENTITY_PROFILE_V1","unknown_actions_fail_closed":True,"versioned_consent":True,"policies":int(pc),"consents":int(cc),"database":str(self.path)}
