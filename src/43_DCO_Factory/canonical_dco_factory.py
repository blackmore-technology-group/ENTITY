from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
import hashlib, json, sqlite3, time

FACTORY_PROFILE="ENTITY_DCO_FACTORY"
FACTORY_VERSION="0.1.0"
EEP_CLASSES={"SPOT_LICENSE","SUBSCRIPTION","COMPUTE_TO_DATA","PROCUREMENT","CONTRIBUTION","SECONDARY_LICENSE"}
SCARCITY_CLASSES={"OPEN_CAPACITY","CONTROLLED_CAPACITY","FIXED_CAP","UNIQUE"}
PROFILE_LIMITS={"STANDARD":(3,5),"ADVANCED":(6,8),"STRATEGIC":(9,12)}
LIFECYCLE={"ACTIVE","ACTIVE_PRELAUNCH","PAUSED","SUPERSEDED","REVOKED","EXPIRED","RETIRED"}

def now_ms(): return int(time.time()*1000)
def canon(v): return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str)
def sha(v): return hashlib.sha256((v if isinstance(v,(bytes,bytearray)) else canon(v).encode())).hexdigest()
def require_sha256(v,name):
    s=str(v or "").lower()
    if len(s)!=64 or any(c not in "0123456789abcdef" for c in s): raise ValueError(f"{name} must be SHA-256 hex")
    return s

class DCOFactory:
    """Application-layer DCO catalog/factory above ENTITY v3.4.3.

    It standardizes templates, duplicate/version classification and master economic
    records. It does not replace the Universal Transaction Fabric, EEP, EOPP or Wallet.
    """
    def __init__(self,state_dir:str|Path):
        self.root=Path(state_dir)/"dco_factory"; self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/"entity_dco_factory.sqlite"; self._init()

    @contextmanager
    def _db(self,write=False):
        db=sqlite3.connect(self.path,timeout=30.0); db.row_factory=sqlite3.Row
        db.execute("PRAGMA busy_timeout=30000")
        try:
            yield db
            if write: db.commit()
        except Exception:
            if write: db.rollback()
            raise
        finally: db.close()

    def _init(self):
        with self._db(True) as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
            CREATE TABLE IF NOT EXISTS templates(
              template_id TEXT PRIMARY KEY,profile TEXT NOT NULL,template_sha256 TEXT NOT NULL,
              template_json TEXT NOT NULL,status TEXT NOT NULL,created_at_ms INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS dco_masters(
              dco_id TEXT PRIMARY KEY,template_id TEXT NOT NULL,family TEXT NOT NULL,
              source_sha256 TEXT NOT NULL,provenance_root TEXT,semantic_fingerprint TEXT,
              version TEXT NOT NULL,lifecycle TEXT NOT NULL,master_json TEXT NOT NULL,
              created_at_ms INTEGER NOT NULL);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_dco_source_hash ON dco_masters(source_sha256);
            CREATE INDEX IF NOT EXISTS idx_dco_prov ON dco_masters(provenance_root);
            CREATE INDEX IF NOT EXISTS idx_dco_sem ON dco_masters(semantic_fingerprint);
            CREATE TABLE IF NOT EXISTS relationships(
              parent_dco_id TEXT NOT NULL,child_dco_id TEXT NOT NULL,relation TEXT NOT NULL,
              created_at_ms INTEGER NOT NULL,PRIMARY KEY(parent_dco_id,child_dco_id,relation));
            CREATE TABLE IF NOT EXISTS issuance_runs(
              issuance_id TEXT PRIMARY KEY,dco_id TEXT NOT NULL,plan_sha256 TEXT NOT NULL,
              physical_instruments INTEGER NOT NULL,total_right_units INTEGER NOT NULL,
              status TEXT NOT NULL,created_at_ms INTEGER NOT NULL);
            """)

    @staticmethod
    def validate_template(template:dict)->dict:
        t=dict(template)
        tid=str(t.get("template_id") or "")
        profile=str(t.get("profile") or "").upper()
        if not tid: raise ValueError("template_id required")
        if profile not in PROFILE_LIMITS: raise ValueError("profile must be STANDARD, ADVANCED or STRATEGIC")
        products=list(t.get("products") or [])
        lo,hi=PROFILE_LIMITS[profile]
        if not lo<=len(products)<=hi: raise ValueError(f"{profile} profile requires {lo}-{hi} product archetypes")
        names=[]; normalized=[]
        for p in products:
            x=dict(p); a=str(x.get("archetype") or "").upper()
            if not a or a in names: raise ValueError("unique archetype required")
            names.append(a)
            cls=str(x.get("eep_class") or "").upper()
            if cls not in EEP_CLASSES: raise ValueError(f"unsupported EEP class for {a}")
            scarcity=str(x.get("scarcity_class") or "").upper()
            if scarcity not in SCARCITY_CLASSES: raise ValueError(f"invalid scarcity class for {a}")
            supply=int(x.get("initial_supply") or 0)
            if supply<1: raise ValueError(f"positive initial_supply required for {a}")
            variants=list(x.get("variants") or [])
            if scarcity=="UNIQUE" and variants and supply!=1:
                raise ValueError("UNIQUE variant archetypes must use one unit per physical variant")
            x.update({"archetype":a,"eep_class":cls,"scarcity_class":scarcity,"initial_supply":supply})
            normalized.append(x)
        t["profile"]=profile; t["products"]=normalized
        t.setdefault("schema","entity-dco-commercial-template-v1")
        t.setdefault("entity_display_version","3.4.3")
        t.setdefault("protocol_change_required",False)
        return t

    def register_template(self,template:dict)->dict:
        t=self.validate_template(template); raw=canon(t); digest=sha(raw); created=now_ms()
        with self._db(True) as db:
            db.execute("""INSERT INTO templates VALUES(?,?,?,?,?,?)
                          ON CONFLICT(template_id) DO UPDATE SET profile=excluded.profile,
                          template_sha256=excluded.template_sha256,template_json=excluded.template_json,
                          status='ACTIVE'""",
                       (t["template_id"],t["profile"],digest,raw,"ACTIVE",created))
        return {"template_id":t["template_id"],"profile":t["profile"],"template_sha256":digest,
                "archetype_count":len(t["products"]),"status":"ACTIVE"}

    def template(self,template_id:str)->dict:
        with self._db() as db: row=db.execute("SELECT * FROM templates WHERE template_id=? AND status='ACTIVE'",(template_id,)).fetchone()
        if not row: raise KeyError("template not found")
        return json.loads(row["template_json"])

    def classify_candidate(self,*,source_sha256:str,provenance_root:str|None=None,
                           semantic_fingerprint:str|None=None,version_of:str|None=None,
                           derivative_of:str|None=None)->dict:
        source=require_sha256(source_sha256,"source_sha256")
        with self._db() as db:
            exact=db.execute("SELECT dco_id FROM dco_masters WHERE source_sha256=?",(source,)).fetchone()
            if exact: return {"decision":"DUPLICATE_REJECT","existing_dco_id":exact["dco_id"],"basis":"SOURCE_HASH"}
            if semantic_fingerprint:
                sem=db.execute("SELECT dco_id FROM dco_masters WHERE semantic_fingerprint=?",(str(semantic_fingerprint),)).fetchone()
                if sem: return {"decision":"DUPLICATE_REJECT","existing_dco_id":sem["dco_id"],"basis":"SEMANTIC_FINGERPRINT"}
            if version_of:
                row=db.execute("SELECT dco_id FROM dco_masters WHERE dco_id=?",(version_of,)).fetchone()
                if not row: raise KeyError("version_of DCO not found")
                return {"decision":"NEW_VERSION","existing_dco_id":version_of,"basis":"EXPLICIT_VERSION_RELATION"}
            if derivative_of:
                row=db.execute("SELECT dco_id FROM dco_masters WHERE dco_id=?",(derivative_of,)).fetchone()
                if not row: raise KeyError("derivative_of DCO not found")
                return {"decision":"DERIVATIVE_OF_EXISTING_DCO","existing_dco_id":derivative_of,"basis":"EXPLICIT_DERIVATIVE_RELATION"}
            if provenance_root:
                prov=db.execute("SELECT dco_id FROM dco_masters WHERE provenance_root=? ORDER BY created_at_ms LIMIT 1",(str(provenance_root),)).fetchone()
                if prov: return {"decision":"REVIEW_EXISTING_LINEAGE","existing_dco_id":prov["dco_id"],"basis":"PROVENANCE_ROOT"}
        return {"decision":"NEW_DCO","existing_dco_id":None,"basis":"NO_DUPLICATE_SIGNAL"}

    def plan(self,template_id:str,*,dco_code:str,family:str,overrides:dict|None=None)->dict:
        t=self.template(template_id); overrides=dict(overrides or {})
        per=dict(overrides.get("products") or {})
        physical=[]; archetypes=[]
        for base in t["products"]:
            p={**base,**dict(per.get(base["archetype"]) or {})}
            variants=list(p.get("variants") or [None])
            if p["scarcity_class"]=="UNIQUE" and not variants: variants=[None]
            if not variants: variants=[None]
            records=[]
            for variant in variants:
                supply=1 if p["scarcity_class"]=="UNIQUE" and variant is not None else int(p["initial_supply"])
                rec={"archetype":p["archetype"],"eep_class":p["eep_class"],"scarcity_class":p["scarcity_class"],
                     "initial_supply":supply,"reserve_units":int(p.get("reserve_units") or 0),
                     "transferable":bool(p.get("transferable",False)),"duration_ms":p.get("duration_ms"),
                     "actions":list(p.get("actions") or []),"terms":dict(p.get("terms") or {})}
                if variant is not None: rec["variant"]=variant
                if rec["reserve_units"]<0 or rec["reserve_units"]>supply: raise ValueError("invalid reserve_units")
                records.append(rec); physical.append(rec)
            archetypes.append({"archetype":p["archetype"],"physical_instrument_count":len(records),
                               "total_supply":sum(x["initial_supply"] for x in records)})
        plan={"schema":"entity-dco-factory-plan-v1","factory_version":FACTORY_VERSION,
              "template_id":template_id,"profile":t["profile"],"dco_code":str(dco_code),
              "family":str(family).upper(),"archetype_count":len(archetypes),
              "physical_instrument_count":len(physical),
              "total_right_units":sum(x["initial_supply"] for x in physical),
              "treasury_reserve_units":sum(x["reserve_units"] for x in physical),
              "archetypes":archetypes,"physical_instruments":physical,
              "protocol_change_required":False}
        plan["plan_sha256"]=sha(plan)
        return plan

    def create_master(self,*,dco_id:str,template_id:str,family:str,source_sha256:str,
                      version:str="1.0",provenance_root:str|None=None,
                      semantic_fingerprint:str|None=None,lifecycle:str="ACTIVE_PRELAUNCH",
                      plan:dict|None=None,metadata:dict|None=None,version_of:str|None=None,
                      derivative_of:str|None=None)->dict:
        life=str(lifecycle).upper()
        if life not in LIFECYCLE: raise ValueError("invalid lifecycle")
        decision=self.classify_candidate(source_sha256=source_sha256,provenance_root=provenance_root,
                                         semantic_fingerprint=semantic_fingerprint,
                                         version_of=version_of,derivative_of=derivative_of)
        if decision["decision"]=="DUPLICATE_REJECT": raise ValueError("duplicate DCO rejected")
        if decision["decision"]=="REVIEW_EXISTING_LINEAGE": raise ValueError("existing lineage requires explicit version/derivative decision")
        master={"schema":"entity-dco-master-economic-record-v1","dco_id":str(dco_id),
                "template_id":template_id,"family":str(family).upper(),"source_sha256":require_sha256(source_sha256,"source_sha256"),
                "provenance_root":provenance_root,"semantic_fingerprint":semantic_fingerprint,
                "version":str(version),"lifecycle":life,"plan":dict(plan or {}),
                "metadata":dict(metadata or {}),"classification":decision,"created_at_ms":now_ms()}
        with self._db(True) as db:
            db.execute("INSERT INTO dco_masters VALUES(?,?,?,?,?,?,?,?,?,?)",
                       (master["dco_id"],template_id,master["family"],master["source_sha256"],
                        provenance_root,semantic_fingerprint,master["version"],life,canon(master),master["created_at_ms"]))
            if version_of:
                db.execute("INSERT INTO relationships VALUES(?,?,?,?)",(version_of,master["dco_id"],"VERSION_OF",master["created_at_ms"]))
            if derivative_of:
                db.execute("INSERT INTO relationships VALUES(?,?,?,?)",(derivative_of,master["dco_id"],"DERIVATIVE_OF",master["created_at_ms"]))
        return master

    def bulk_register_masters(self,records:list[dict])->int:
        rows=[]
        created=now_ms()
        for r in records:
            source=require_sha256(r["source_sha256"],"source_sha256")
            master={"schema":"entity-dco-master-economic-record-v1","dco_id":str(r["dco_id"]),
                    "template_id":str(r["template_id"]),"family":str(r["family"]).upper(),
                    "source_sha256":source,"provenance_root":r.get("provenance_root"),
                    "semantic_fingerprint":r.get("semantic_fingerprint"),"version":str(r.get("version","1.0")),
                    "lifecycle":str(r.get("lifecycle","ACTIVE_PRELAUNCH")).upper(),
                    "plan":dict(r.get("plan") or {}),"metadata":dict(r.get("metadata") or {}),
                    "created_at_ms":created}
            rows.append((master["dco_id"],master["template_id"],master["family"],source,
                         master["provenance_root"],master["semantic_fingerprint"],master["version"],
                         master["lifecycle"],canon(master),created))
        with self._db(True) as db:
            db.executemany("INSERT INTO dco_masters VALUES(?,?,?,?,?,?,?,?,?,?)",rows)
        return len(rows)

    def record_issuance(self,dco_id:str,plan:dict,status="QUALIFIED")->dict:
        issuance_id="issuance-"+sha({"dco_id":dco_id,"plan":plan,"at":now_ms()})[:24]
        body={"issuance_id":issuance_id,"dco_id":dco_id,"plan_sha256":str(plan["plan_sha256"]),
              "physical_instruments":int(plan["physical_instrument_count"]),
              "total_right_units":int(plan["total_right_units"]),"status":str(status).upper(),
              "created_at_ms":now_ms()}
        with self._db(True) as db:
            db.execute("INSERT INTO issuance_runs VALUES(?,?,?,?,?,?,?)",
                       (body["issuance_id"],body["dco_id"],body["plan_sha256"],body["physical_instruments"],
                        body["total_right_units"],body["status"],body["created_at_ms"]))
        return body

    def portfolio_summary(self)->dict:
        with self._db() as db:
            total=int(db.execute("SELECT COUNT(*) FROM dco_masters").fetchone()[0])
            active=int(db.execute("SELECT COUNT(*) FROM dco_masters WHERE lifecycle LIKE 'ACTIVE%'").fetchone()[0])
            families={r["family"]:int(r["n"]) for r in db.execute("SELECT family,COUNT(*) n FROM dco_masters GROUP BY family")}
            issued=db.execute("SELECT COALESCE(SUM(physical_instruments),0) i,COALESCE(SUM(total_right_units),0) u FROM issuance_runs WHERE status='QUALIFIED'").fetchone()
        return {"schema":"entity-dco-factory-portfolio-summary-v1","total_dcos":total,"active_dcos":active,
                "families":families,"qualified_physical_instruments":int(issued["i"]),
                "qualified_right_units":int(issued["u"]),"factory_version":FACTORY_VERSION,
                "target_design_capacity_dcos":10000,"protocol_change_required":False}
