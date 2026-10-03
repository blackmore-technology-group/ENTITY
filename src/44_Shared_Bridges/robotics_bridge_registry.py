from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
import hashlib, json, sqlite3, time

BRIDGE_SCHEMA="entity-shared-bridge-registry-v1"
ROBOTICS_BRIDGE_ID="ENTITY_ROBOTICS_INTEGRATION"
ROBOTICS_INTERFACES=("ENTITY_API","ROS-2","OPEN-RMF","EXTERNAL_CUSTODY")
EXPOSURE_MODES={"NOT_EXPOSED","READ_ONLY","METERED","CONTROLLED_EXECUTION"}

def now_ms(): return int(time.time()*1000)
def canon(v): return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str)
def digest(v): return hashlib.sha256(canon(v).encode()).hexdigest()
def sha256_hex(v,name):
    s=str(v or "").lower()
    if len(s)!=64 or any(c not in "0123456789abcdef" for c in s): raise ValueError(f"{name} must be SHA-256")
    return s

class SharedBridgeRegistry:
    """Many DCOs bind to a small reusable bridge set; bridge bindings do not create rights."""
    def __init__(self,state_dir:str|Path):
        self.root=Path(state_dir)/"shared_bridges"; self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/"entity_shared_bridges.sqlite"; self._init()

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
            CREATE TABLE IF NOT EXISTS bridges(
              bridge_id TEXT PRIMARY KEY,version TEXT NOT NULL,interfaces_json TEXT NOT NULL,
              policy_json TEXT NOT NULL,bridge_sha256 TEXT NOT NULL,created_at_ms INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS bindings(
              dco_id TEXT NOT NULL,bridge_id TEXT NOT NULL,global_passport_sha256 TEXT NOT NULL,
              enabled_interfaces_json TEXT NOT NULL,exposure_mode TEXT NOT NULL,
              endpoint_ref TEXT,created_at_ms INTEGER NOT NULL,
              PRIMARY KEY(dco_id,bridge_id));
            """)
        self.register_bridge(
            ROBOTICS_BRIDGE_ID,"1.0",list(ROBOTICS_INTERFACES),
            {"shared_infrastructure":True,"one_bridge_per_dco":False,
             "mapping_is_not_normative_equivalence":True,
             "bridge_does_not_create_authority":True,
             "bridge_does_not_create_rights":True,
             "credentials_in_registry":False})

    def register_bridge(self,bridge_id,version,interfaces,policy):
        body={"schema":"entity-shared-bridge-definition-v1","bridge_id":str(bridge_id),"version":str(version),
              "interfaces":sorted({str(x) for x in interfaces}),"policy":dict(policy)}
        if not body["interfaces"]: raise ValueError("bridge interfaces required")
        if body["policy"].get("credentials_in_registry") is not False: raise ValueError("bridge registry cannot contain credentials")
        bsha=digest(body)
        with self._db(True) as db:
            prior=db.execute("SELECT bridge_sha256 FROM bridges WHERE bridge_id=?",(body["bridge_id"],)).fetchone()
            if prior and prior["bridge_sha256"]!=bsha: raise ValueError("immutable bridge definition conflict")
            db.execute("INSERT OR IGNORE INTO bridges VALUES(?,?,?,?,?,?)",
                       (body["bridge_id"],body["version"],json.dumps(body["interfaces"]),
                        json.dumps(body["policy"],sort_keys=True),bsha,now_ms()))
        return dict(body,bridge_sha256=bsha)

    def get_bridge(self,bridge_id):
        with self._db() as db:
            row=db.execute("SELECT * FROM bridges WHERE bridge_id=?",(str(bridge_id),)).fetchone()
        if not row: raise KeyError("bridge missing")
        return {"bridge_id":row["bridge_id"],"version":row["version"],
                "interfaces":json.loads(row["interfaces_json"]),"policy":json.loads(row["policy_json"]),
                "bridge_sha256":row["bridge_sha256"]}

    def bind(self,dco_id,global_passport_sha256,*,bridge_id=ROBOTICS_BRIDGE_ID,
             enabled_interfaces=None,exposure_mode="NOT_EXPOSED",endpoint_ref=None):
        bridge=self.get_bridge(bridge_id)
        gp=sha256_hex(global_passport_sha256,"global_passport_sha256")
        enabled=sorted({str(x) for x in (enabled_interfaces or [])})
        unknown=sorted(set(enabled)-set(bridge["interfaces"]))
        if unknown: raise ValueError("unsupported bridge interfaces: "+",".join(unknown))
        mode=str(exposure_mode).upper()
        if mode not in EXPOSURE_MODES: raise ValueError("invalid exposure mode")
        if mode=="NOT_EXPOSED" and endpoint_ref is not None: raise ValueError("non-exposed binding cannot publish endpoint")
        if endpoint_ref and any(x in str(endpoint_ref).lower() for x in ("token=","password=","secret=","apikey=","api_key=")):
            raise ValueError("credentials prohibited in bridge endpoint ref")
        body={"schema":"entity-dco-shared-bridge-binding-v1","dco_id":str(dco_id),
              "bridge_id":bridge["bridge_id"],"bridge_sha256":bridge["bridge_sha256"],
              "global_passport_sha256":gp,"enabled_interfaces":enabled,
              "exposure_mode":mode,"endpoint_ref":str(endpoint_ref) if endpoint_ref else None,
              "shared_bridge":True,"bridge_does_not_create_rights":True,
              "bridge_does_not_create_authority":True}
        with self._db(True) as db:
            prior=db.execute("SELECT * FROM bindings WHERE dco_id=? AND bridge_id=?",(body["dco_id"],body["bridge_id"])).fetchone()
            if prior:
                old={"global_passport_sha256":prior["global_passport_sha256"],
                     "enabled_interfaces":json.loads(prior["enabled_interfaces_json"]),
                     "exposure_mode":prior["exposure_mode"],"endpoint_ref":prior["endpoint_ref"]}
                new={k:body[k] for k in old}
                if old!=new: raise ValueError("immutable bridge binding already exists")
                return body
            db.execute("INSERT INTO bindings VALUES(?,?,?,?,?,?,?)",
                       (body["dco_id"],body["bridge_id"],gp,json.dumps(enabled),mode,body["endpoint_ref"],now_ms()))
        return body

    def bindings(self,bridge_id=ROBOTICS_BRIDGE_ID):
        with self._db() as db:
            rows=db.execute("SELECT * FROM bindings WHERE bridge_id=? ORDER BY dco_id",(str(bridge_id),)).fetchall()
        return [{"dco_id":r["dco_id"],"global_passport_sha256":r["global_passport_sha256"],
                 "enabled_interfaces":json.loads(r["enabled_interfaces_json"]),
                 "exposure_mode":r["exposure_mode"],"endpoint_ref":r["endpoint_ref"]} for r in rows]

    def route_envelope(self,dco_id,interface,operation,payload_ref,entitlement_ref=None):
        interface=str(interface)
        with self._db() as db:
            row=db.execute("SELECT * FROM bindings WHERE dco_id=? AND bridge_id=?",(str(dco_id),ROBOTICS_BRIDGE_ID)).fetchone()
        if not row: raise KeyError("DCO is not bound to robotics integration bridge")
        enabled=json.loads(row["enabled_interfaces_json"])
        if row["exposure_mode"]=="NOT_EXPOSED": raise PermissionError("DCO bridge exposure disabled")
        if interface not in enabled: raise PermissionError("interface not enabled")
        return {"schema":"entity-robotics-bridge-request-v1","dco_id":str(dco_id),
                "bridge_id":ROBOTICS_BRIDGE_ID,"interface":interface,"operation":str(operation),
                "payload_ref":str(payload_ref),"entitlement_ref":str(entitlement_ref) if entitlement_ref else None,
                "created_at_ms":now_ms(),"rights_must_be_verified_separately":True,
                "bridge_does_not_create_rights":True}
