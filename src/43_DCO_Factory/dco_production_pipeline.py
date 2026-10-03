from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
from typing import Any
import hashlib, json, sqlite3, time

PIPELINE_SCHEMA="entity-dco-production-pipeline-v1"
PIPELINE_VERSION="1.0.0"

STAGES=(
    "ASSET_BUILT",
    "ASSET_QUALIFIED",
    "PROVENANCE_SEALED",
    "DCO_REGISTERED",
    "RIGHTS_PASSPORT_ISSUED",
    "GLOBAL_PASSPORT_ISSUED",
    "PROFILE_BTDU_BOUND",
    "ECONOMIC_INSTRUMENTS_ISSUED",
    "PUBLIC_SAFE_EVIDENCE_PUBLISHED",
)
OPTIONAL_STAGES=("BRIDGE_EXPOSURE_BOUND",)
DEPENDENCY={
    "ASSET_BUILT":None,
    "ASSET_QUALIFIED":"ASSET_BUILT",
    "PROVENANCE_SEALED":"ASSET_QUALIFIED",
    "DCO_REGISTERED":"PROVENANCE_SEALED",
    "RIGHTS_PASSPORT_ISSUED":"DCO_REGISTERED",
    "GLOBAL_PASSPORT_ISSUED":"RIGHTS_PASSPORT_ISSUED",
    "PROFILE_BTDU_BOUND":"GLOBAL_PASSPORT_ISSUED",
    "ECONOMIC_INSTRUMENTS_ISSUED":"PROFILE_BTDU_BOUND",
    "BRIDGE_EXPOSURE_BOUND":"ECONOMIC_INSTRUMENTS_ISSUED",
    "PUBLIC_SAFE_EVIDENCE_PUBLISHED":"ECONOMIC_INSTRUMENTS_ISSUED",
}
FORBIDDEN_PUBLIC_KEYS={
    "object_id","instrument_id","instrument_ids","venue_id","wallet_id","wallet_ids",
    "treasury_id","treasury_entity_id","runtime_path","runtime_database","private_key",
    "credentials","payment_credentials","settlement_details","customer_entitlements",
    "private_licence_terms","rollback_directory",
}
PUBLIC_MANIFEST_FIELDS=(
    "dco_id","name","asset_class","content_sha256","controller","originator","version",
    "public_rights_summary","rights_passport_sha256","global_passport_sha256",
    "qualification_sha256","benchmark_summary","public_provenance_refs","economic_state",
)

def now_ms()->int: return int(time.time()*1000)
def canon(v:Any)->bytes: return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()
def digest(v:Any)->str: return hashlib.sha256(v if isinstance(v,(bytes,bytearray)) else canon(v)).hexdigest()
def sha256_hex(v:str,name:str)->str:
    s=str(v or "").lower()
    if len(s)!=64 or any(c not in "0123456789abcdef" for c in s):
        raise ValueError(f"{name} must be lowercase SHA-256")
    return s

class DCOProductionPipeline:
    """Factory-side issuance gate for real DCO assets.

    This is an application-layer state machine. It does not replace canonical ENTITY
    object, passport, BTDU, EEP, wallet or settlement state.
    """
    def __init__(self,state_dir:str|Path):
        self.root=Path(state_dir)/"dco_factory"
        self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/"entity_dco_production_pipeline.sqlite"
        self._init()

    @contextmanager
    def _db(self,write:bool=False):
        db=sqlite3.connect(self.path,timeout=30.0); db.row_factory=sqlite3.Row
        db.execute("PRAGMA busy_timeout=30000")
        try:
            yield db
            if write: db.commit()
        except Exception:
            if write: db.rollback()
            raise
        finally:
            db.close()

    def _init(self):
        with self._db(True) as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
            CREATE TABLE IF NOT EXISTS stages(
              dco_id TEXT NOT NULL,stage TEXT NOT NULL,evidence_sha256 TEXT NOT NULL,
              details_json TEXT NOT NULL,created_at_ms INTEGER NOT NULL,
              PRIMARY KEY(dco_id,stage));
            CREATE TABLE IF NOT EXISTS public_manifests(
              dco_id TEXT PRIMARY KEY,manifest_sha256 TEXT NOT NULL,
              manifest_json TEXT NOT NULL,created_at_ms INTEGER NOT NULL);
            """)

    def completed(self,dco_id:str)->set[str]:
        with self._db() as db:
            return {r["stage"] for r in db.execute("SELECT stage FROM stages WHERE dco_id=?",(str(dco_id),))}

    def record_stage(self,dco_id:str,stage:str,evidence_sha256:str,details:dict|None=None)->dict:
        dco_id=str(dco_id); stage=str(stage).upper()
        if stage not in set(STAGES)|set(OPTIONAL_STAGES): raise ValueError("unsupported DCO production stage")
        evidence_sha256=sha256_hex(evidence_sha256,"evidence_sha256")
        done=self.completed(dco_id)
        dep=DEPENDENCY[stage]
        if dep and dep not in done:
            raise ValueError(f"{stage} requires {dep}")
        body={"schema":"entity-dco-production-stage-v1","dco_id":dco_id,"stage":stage,
              "evidence_sha256":evidence_sha256,"details":dict(details or {}),"created_at_ms":now_ms()}
        with self._db(True) as db:
            prior=db.execute("SELECT evidence_sha256,details_json FROM stages WHERE dco_id=? AND stage=?",(dco_id,stage)).fetchone()
            if prior:
                if prior["evidence_sha256"]!=evidence_sha256 or json.loads(prior["details_json"])!=body["details"]:
                    raise ValueError("immutable production stage already recorded with different evidence")
                return body
            db.execute("INSERT INTO stages VALUES(?,?,?,?,?)",
                       (dco_id,stage,evidence_sha256,json.dumps(body["details"],sort_keys=True),body["created_at_ms"]))
        return body

    def status(self,dco_id:str)->dict:
        with self._db() as db:
            rows=[dict(r) for r in db.execute("SELECT * FROM stages WHERE dco_id=? ORDER BY created_at_ms,stage",(str(dco_id),))]
        done={r["stage"] for r in rows}
        next_required=next((s for s in STAGES if s not in done),None)
        return {"schema":"entity-dco-production-status-v1","dco_id":str(dco_id),
                "completed_stages":[r["stage"] for r in rows],
                "bridge_bound":"BRIDGE_EXPOSURE_BOUND" in done,
                "next_required_stage":next_required,
                "ready_for_economic_issuance":"PROFILE_BTDU_BOUND" in done,
                "economic_instruments_issued":"ECONOMIC_INSTRUMENTS_ISSUED" in done,
                "public_evidence_published":"PUBLIC_SAFE_EVIDENCE_PUBLISHED" in done}

    @staticmethod
    def build_public_safe_manifest(record:dict)->dict:
        raw=dict(record or {})
        leaked=sorted(k for k in raw if k in FORBIDDEN_PUBLIC_KEYS)
        if leaked: raise ValueError("public manifest contains forbidden operational keys: "+",".join(leaked))
        missing=[k for k in PUBLIC_MANIFEST_FIELDS if k not in raw]
        if missing: raise ValueError("public manifest missing fields: "+",".join(missing))
        content_sha=sha256_hex(raw["content_sha256"],"content_sha256")
        rp=sha256_hex(raw["rights_passport_sha256"],"rights_passport_sha256")
        gp=sha256_hex(raw["global_passport_sha256"],"global_passport_sha256")
        qh=sha256_hex(raw["qualification_sha256"],"qualification_sha256")
        econ=dict(raw["economic_state"] or {})
        state=str(econ.get("state") or "")
        if state not in {"POTENTIAL","OFFER","CONTRACTED","ACCRUED","SETTLED","REALIZED"}:
            raise ValueError("invalid economic_state")
        if int(econ.get("amount_units",0))<0: raise ValueError("negative economic amount")
        econ["market_observation_is_not_accounting_fair_value"]=True
        out={"schema":"entity-public-safe-dco-manifest-v1","dco_id":str(raw["dco_id"]),
             "name":str(raw["name"]),"asset_class":str(raw["asset_class"]),
             "content_sha256":content_sha,"controller":str(raw["controller"]),
             "originator":str(raw["originator"]),"version":str(raw["version"]),
             "public_rights_summary":dict(raw["public_rights_summary"]),
             "rights_passport_sha256":rp,"global_passport_sha256":gp,
             "qualification_sha256":qh,"benchmark_summary":dict(raw["benchmark_summary"]),
             "public_provenance_refs":sorted({str(x) for x in raw["public_provenance_refs"]}),
             "economic_state":econ,"live_operational_state_included":False,
             "customer_data_included":False,"credentials_included":False}
        out["manifest_sha256"]=digest(out)
        return out

    def publish_public_manifest_record(self,manifest:dict)->dict:
        body=dict(manifest)
        if body.get("schema")!="entity-public-safe-dco-manifest-v1": raise ValueError("public manifest schema")
        dco_id=str(body["dco_id"]); msha=str(body["manifest_sha256"])
        check=dict(body); check.pop("manifest_sha256",None)
        if digest(check)!=msha: raise ValueError("public manifest hash")
        self.record_stage(dco_id,"PUBLIC_SAFE_EVIDENCE_PUBLISHED",msha,
                          {"live_operational_state_included":False,"manifest_schema":body["schema"]})
        with self._db(True) as db:
            db.execute("INSERT OR REPLACE INTO public_manifests VALUES(?,?,?,?)",
                       (dco_id,msha,json.dumps(body,sort_keys=True),now_ms()))
        return body
