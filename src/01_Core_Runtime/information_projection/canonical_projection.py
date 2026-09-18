from __future__ import annotations
from pathlib import Path
from threading import RLock
from contextlib import contextmanager
import hashlib, json, sqlite3, time, uuid

CLASSIFICATIONS={"PUBLIC","INTERNAL","PRIVATE","RESTRICTED","NON_TRANSFERABLE","LICENSABLE"}
OUTCOMES={"DENY","ALLOW","REDACT","AGGREGATE","PSEUDONYMIZE","DERIVED_ANSWER","REVIEW_REQUIRED"}
SENSITIVE_KEYS={"password","secret","token","private_key","cookie","session","authorization","credential","recovery_key"}


def _now(): return int(time.time()*1000)
def _hash(value) -> str:
    raw=json.dumps(value,sort_keys=True,separators=(",",":"),default=str).encode()
    return hashlib.sha256(raw).hexdigest()


class InformationProjectionEngine:
    """Minimum-disclosure control path for sensitive cross-subsystem information movement."""
    def __init__(self,state_dir: str|Path):
        self.root=Path(state_dir)/"information_projection"; self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/"projection.sqlite"; self._lock=RLock(); self._init_db()

    @contextmanager
    def _connect(self):
        db=sqlite3.connect(self.path,timeout=30); db.row_factory=sqlite3.Row
        try: yield db; db.commit()
        except Exception: db.rollback(); raise
        finally: db.close()

    def _init_db(self):
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("CREATE TABLE IF NOT EXISTS disclosures(disclosure_id TEXT PRIMARY KEY,requesting_subsystem TEXT NOT NULL,actor TEXT,purpose TEXT NOT NULL,target TEXT NOT NULL,classification TEXT NOT NULL,outcome TEXT NOT NULL,disclosed_fields_json TEXT NOT NULL,authority_refs_json TEXT NOT NULL,request_sha256 TEXT NOT NULL,projection_sha256 TEXT,created_at_ms INTEGER NOT NULL)")

    @staticmethod
    def _sanitize_fields(fields) -> list[str]:
        out=[]
        for field in fields or []:
            key=str(field).strip()
            if key and key.lower() not in SENSITIVE_KEYS: out.append(key)
        return sorted(set(out))

    @staticmethod
    def _projection(data: dict, fields: list[str], redactions: set[str]) -> dict:
        out={}
        for key in fields:
            if key not in data: continue
            if key.lower() in SENSITIVE_KEYS or key in redactions:
                out[key]="REDACTED"
            else: out[key]=data[key]
        return out

    def decide(self,request: dict,data: dict) -> dict:
        subsystem=str(request.get("requesting_subsystem") or "UNKNOWN").upper()
        purpose=str(request.get("purpose") or "").strip(); target=str(request.get("target") or "").strip()
        classification=str(request.get("classification") or "PRIVATE").upper()
        if classification not in CLASSIFICATIONS: return self._record(request,{},"REVIEW_REQUIRED",[],"unknown_classification")
        if not purpose or not target: return self._record(request,{},"DENY",[],"purpose_and_target_required")
        capability=dict(request.get("capability") or {}); policy=dict(request.get("policy") or {})
        requested=self._sanitize_fields(request.get("requested_fields") or data.keys())
        minimum=self._sanitize_fields(request.get("minimum_fields") or requested)
        fields=sorted(set(requested).intersection(minimum))
        external=bool(request.get("external_transmission",False))
        content_requested=bool(request.get("content_requested",False))
        metadata_allowed=bool(capability.get("metadata_read",False))
        content_allowed=bool(capability.get("content_read",False))
        external_allowed=bool(policy.get("external_disclosure_allowed",False))
        rights_ok=policy.get("rights_authorized") is True and policy.get("consent_authorized") is not False
        if not metadata_allowed and not content_allowed:
            return self._record(request,{},"DENY",[],"no_read_capability")
        if content_requested and not content_allowed:
            return self._record(request,{},"DENY",[],"metadata_permission_does_not_grant_content")
        if external and not external_allowed:
            return self._record(request,{},"DENY",[],"external_disclosure_not_authorized")
        if classification in {"RESTRICTED","NON_TRANSFERABLE"} and external:
            return self._record(request,{},"DENY",[],"classification_blocks_external_disclosure")
        if classification != "PUBLIC" and policy.get("rights_authorized") is None:
            return self._record(request,{},"REVIEW_REQUIRED",[],"rights_state_unknown")
        if not rights_ok and classification != "PUBLIC":
            return self._record(request,{},"DENY",[],"rights_or_consent_denied")
        redactions={str(x) for x in request.get("redact_fields") or []}
        projection=self._projection(dict(data),fields,redactions)
        outcome="REDACT" if any(v=="REDACTED" for v in projection.values()) else "ALLOW"
        mode=str(request.get("projection_mode") or "MINIMUM").upper()
        if mode in {"AGGREGATE","PSEUDONYMIZE","DERIVED_ANSWER"}: outcome=mode
        return self._record(request,projection,outcome,list(projection),"authorized_minimum_projection")

    def _record(self,request: dict,projection: dict,outcome: str,fields: list[str],reason: str) -> dict:
        if outcome not in OUTCOMES: raise ValueError("unsupported projection outcome")
        disclosure_id="disc1-"+uuid.uuid4().hex; now=_now()
        authority_refs=[str(x) for x in request.get("authority_refs") or []]
        evidence={
            "schema":"entity-disclosure-evidence-v1","disclosure_id":disclosure_id,
            "requesting_subsystem":str(request.get("requesting_subsystem") or "UNKNOWN").upper(),
            "actor":request.get("actor"),"purpose":str(request.get("purpose") or ""),
            "target":str(request.get("target") or ""),"classification":str(request.get("classification") or "PRIVATE").upper(),
            "outcome":outcome,"reason":reason,"disclosed_fields":sorted(set(fields)),
            "authority_refs":authority_refs,"request_sha256":_hash(request),
            "projection_sha256":_hash(projection) if projection else None,"created_at_ms":now,
            "raw_sensitive_content_logged":False,
        }
        with self._lock,self._connect() as db:
            db.execute("INSERT INTO disclosures VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(
                disclosure_id,evidence["requesting_subsystem"],evidence["actor"],evidence["purpose"],evidence["target"],
                evidence["classification"],outcome,json.dumps(evidence["disclosed_fields"]),json.dumps(authority_refs),
                evidence["request_sha256"],evidence["projection_sha256"],now))
        return {"decision":evidence,"projection":projection if outcome not in {"DENY","REVIEW_REQUIRED"} else {}}

    def status(self) -> dict:
        with self._connect() as db: count=db.execute("SELECT COUNT(*) FROM disclosures").fetchone()[0]
        return {"ready":True,"schema":"entity-information-projection-v1","minimum_disclosure":True,
                "metadata_content_separation":True,"external_disclosure_fail_closed":True,"disclosure_events":int(count)}
