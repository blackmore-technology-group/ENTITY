from __future__ import annotations
from contextlib import contextmanager
from fractions import Fraction
from pathlib import Path
from threading import RLock
import hashlib, json, secrets, sqlite3, time

PRIMITIVES=("ENTITY","AUTHORITY","RIGHT","EVENT","VALUE")
OBJECT_TYPES={"PERSON","ORGANIZATION","AI_AGENT","DATASET","DOCUMENT","MODEL","SOFTWARE","API","DEVICE","VEHICLE","BUILDING","RESEARCH","DIGITAL_TWIN","FINANCIAL_INSTRUMENT","PHYSICAL_ASSET","OTHER"}
RIGHT_ACTIONS={"INSPECT","READ","COPY","DERIVE","TRAIN","INFER","EXECUTE","MODIFY","REDISTRIBUTE","COMMERCIALIZE","CONTROL","TRANSFER"}
AUTHORITY_ACTIONS={"ACT","SIGN","ACCESS_DATA","EXECUTE","PURCHASE","LICENSE","SETTLE","PUBLISH","RESOLVE","DELEGATE","CONTROL"}
VALUE_STATES=("POTENTIAL","OFFER","CONTRACTED","ACCRUED","SETTLED","REALIZED")


def _now(): return int(time.time()*1000)
def _id(prefix): return f"{prefix}-"+secrets.token_hex(20)
def _canon(v): return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()
def _sha(v): return hashlib.sha256(v if isinstance(v,(bytes,bytearray)) else _canon(v)).hexdigest()
def _sha256_hex(v):
    s=str(v or "").lower()
    if len(s)!=64 or any(c not in "0123456789abcdef" for c in s): raise ValueError("SHA-256 hex required")
    return s


class UniversalTransactionFabric:
    """ENTITY v3 universal sovereign transaction fabric.

    The five primitives are ENTITY, AUTHORITY, RIGHT, EVENT and VALUE.
    Infrastructure, custody and transport never imply sovereign authority.
    """
    def __init__(self,state_dir:str|Path,identity):
        self.root=Path(state_dir)/"entity_v3"; self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/"universal_fabric.sqlite"; self.identity=identity; self._lock=RLock(); self._init_db()

    @contextmanager
    def _connect(self):
        db=sqlite3.connect(self.path,timeout=30); db.row_factory=sqlite3.Row
        try: yield db; db.commit()
        except Exception: db.rollback(); raise
        finally: db.close()
    def _init_db(self):
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL"); db.execute("PRAGMA synchronous=FULL")
            db.execute("CREATE TABLE IF NOT EXISTS objects(object_id TEXT PRIMARY KEY,controller_entity_id TEXT NOT NULL,object_type TEXT NOT NULL,title TEXT NOT NULL,content_sha256 TEXT,descriptor_json TEXT NOT NULL,status TEXT NOT NULL,created_at_ms INTEGER NOT NULL,signature_json TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS authorities(authority_id TEXT PRIMARY KEY,subject_ref TEXT NOT NULL,grantor_entity_id TEXT NOT NULL,grantee_entity_id TEXT NOT NULL,actions_json TEXT NOT NULL,scope_json TEXT NOT NULL,not_before_ms INTEGER NOT NULL,expires_at_ms INTEGER,status TEXT NOT NULL,created_at_ms INTEGER NOT NULL,revoked_at_ms INTEGER,signature_json TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS rights(right_id TEXT PRIMARY KEY,object_id TEXT NOT NULL,grantor_entity_id TEXT NOT NULL,grantee_ref TEXT NOT NULL,actions_json TEXT NOT NULL,constraints_json TEXT NOT NULL,economic_terms_json TEXT NOT NULL,not_before_ms INTEGER NOT NULL,expires_at_ms INTEGER,status TEXT NOT NULL,created_at_ms INTEGER NOT NULL,revoked_at_ms INTEGER,signature_json TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS events(event_id TEXT PRIMARY KEY,actor_entity_id TEXT NOT NULL,event_type TEXT NOT NULL,subject_refs_json TEXT NOT NULL,authority_ref TEXT,right_ref TEXT,payload_sha256 TEXT NOT NULL,nonce TEXT UNIQUE,created_at_ms INTEGER NOT NULL,signature_json TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS provenance_edges(edge_id TEXT PRIMARY KEY,parent_object_id TEXT NOT NULL,child_object_id TEXT NOT NULL,relation TEXT NOT NULL,contribution_bps INTEGER NOT NULL,evidence_json TEXT NOT NULL,actor_entity_id TEXT NOT NULL,created_at_ms INTEGER NOT NULL,signature_json TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS value_records(value_id TEXT PRIMARY KEY,object_id TEXT NOT NULL,controller_entity_id TEXT NOT NULL,state TEXT NOT NULL,amount_units INTEGER NOT NULL,currency TEXT NOT NULL,basis_ref TEXT NOT NULL,created_at_ms INTEGER NOT NULL,signature_json TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS attestations(attestation_id TEXT PRIMARY KEY,subject_ref TEXT NOT NULL,attestor_entity_id TEXT NOT NULL,claim_type TEXT NOT NULL,evidence_sha256 TEXT NOT NULL,claim_json TEXT NOT NULL,created_at_ms INTEGER NOT NULL,signature_json TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS resolution(object_id TEXT NOT NULL,version INTEGER NOT NULL,endpoints_json TEXT NOT NULL,expires_at_ms INTEGER,status TEXT NOT NULL,created_at_ms INTEGER NOT NULL,signature_json TEXT NOT NULL,PRIMARY KEY(object_id,version))")
            db.execute("CREATE TABLE IF NOT EXISTS trust_policies(policy_id TEXT PRIMARY KEY,controller_entity_id TEXT NOT NULL,claim_type TEXT NOT NULL,minimum_attestations INTEGER NOT NULL,required_attestors_json TEXT NOT NULL,allowed_attestors_json TEXT NOT NULL,status TEXT NOT NULL,created_at_ms INTEGER NOT NULL,signature_json TEXT NOT NULL)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_v3_auth_subject ON authorities(subject_ref,grantee_entity_id,status)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_v3_right_object ON rights(object_id,grantee_ref,status)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_v3_prov_child ON provenance_edges(child_object_id)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_v3_prov_parent ON provenance_edges(parent_object_id)")

    def _require_entity(self,entity_id:str): return self.identity.load_manifest(entity_id)
    def _sign(self,entity_id:str,body:dict)->dict: return self.identity.sign(entity_id,body)
    def _verify(self,entity_id:str,body:dict,signature:dict)->bool:
        return bool(self.identity.verify_signature(self.identity.load_manifest(entity_id),body,signature))
    def register_object(self,controller_entity_id:str,object_type:str,title:str,*,descriptor=None,content_sha256=None)->dict:
        self._require_entity(controller_entity_id); kind=str(object_type or "OTHER").upper()
        if kind not in OBJECT_TYPES: raise ValueError("unsupported object_type")
        digest=_sha256_hex(content_sha256) if content_sha256 else None
        oid=_id("obj3"); now=_now(); body={"schema":"entity-v3-object-v1","primitive":"ENTITY","object_id":oid,"controller_entity_id":controller_entity_id,"object_type":kind,"title":str(title)[:256],"content_sha256":digest,"descriptor":dict(descriptor or {}),"status":"ACTIVE","created_at_ms":now,"custody_is_not_authority":True}
        sig=self._sign(controller_entity_id,body)
        with self._connect() as db: db.execute("INSERT INTO objects VALUES(?,?,?,?,?,?,?,?,?)",(oid,controller_entity_id,kind,body["title"],digest,json.dumps(body["descriptor"],sort_keys=True),"ACTIVE",now,json.dumps(sig,sort_keys=True)))
        return dict(body,signature=sig)

    def get_object(self,object_id:str)->dict:
        with self._connect() as db: row=db.execute("SELECT * FROM objects WHERE object_id=?",(str(object_id),)).fetchone()
        if not row: raise KeyError("object not found")
        out=dict(row); out["descriptor"]=json.loads(out.pop("descriptor_json")); out["signature"]=json.loads(out.pop("signature_json")); out["primitive"]="ENTITY"; return out

    def delegate_authority(self,subject_ref:str,grantor_entity_id:str,grantee_entity_id:str,actions:list[str],*,scope=None,not_before_ms=None,expires_at_ms=None)->dict:
        self._require_entity(grantor_entity_id); self._require_entity(grantee_entity_id)
        acts=sorted({str(x).upper() for x in actions}); unknown=set(acts)-AUTHORITY_ACTIONS
        if not acts or unknown: raise ValueError("invalid authority actions")
        start=int(not_before_ms or _now()); end=int(expires_at_ms) if expires_at_ms is not None else None
        if end is not None and end<=start: raise ValueError("authority expiry must follow start")
        aid=_id("auth3"); now=_now(); body={"schema":"entity-v3-authority-v1","primitive":"AUTHORITY","authority_id":aid,"subject_ref":str(subject_ref),"grantor_entity_id":grantor_entity_id,"grantee_entity_id":grantee_entity_id,"actions":acts,"scope":dict(scope or {}),"not_before_ms":start,"expires_at_ms":end,"status":"ACTIVE","created_at_ms":now,"implicit_escalation_prohibited":True}
        sig=self._sign(grantor_entity_id,body)
        with self._connect() as db: db.execute("INSERT INTO authorities VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(aid,body["subject_ref"],grantor_entity_id,grantee_entity_id,json.dumps(acts),json.dumps(body["scope"],sort_keys=True),start,end,"ACTIVE",now,None,json.dumps(sig,sort_keys=True)))
        return dict(body,signature=sig)

    def revoke_authority(self,grantor_entity_id:str,authority_id:str)->dict:
        with self._connect() as db: row=db.execute("SELECT * FROM authorities WHERE authority_id=?",(authority_id,)).fetchone()
        if not row: raise KeyError("authority not found")
        if row["grantor_entity_id"]!=grantor_entity_id: raise PermissionError("grantor mismatch")
        now=_now()
        with self._connect() as db: db.execute("UPDATE authorities SET status='REVOKED',revoked_at_ms=? WHERE authority_id=?",(now,authority_id))
        return {"authority_id":authority_id,"status":"REVOKED","revoked_at_ms":now}
    def grant_right(self,object_id:str,grantor_entity_id:str,grantee_ref:str,actions:list[str],*,constraints=None,economic_terms=None,not_before_ms=None,expires_at_ms=None)->dict:
        obj=self.get_object(object_id)
        if obj["controller_entity_id"]!=grantor_entity_id: raise PermissionError("object controller required")
        acts=sorted({str(x).upper() for x in actions}); unknown=set(acts)-RIGHT_ACTIONS
        if not acts or unknown: raise ValueError("invalid right actions")
        start=int(not_before_ms or _now()); end=int(expires_at_ms) if expires_at_ms is not None else None
        if end is not None and end<=start: raise ValueError("right expiry must follow start")
        rid=_id("right3"); now=_now(); terms=dict(economic_terms or {})
        body={"schema":"entity-v3-right-v1","primitive":"RIGHT","right_id":rid,"object_id":object_id,"grantor_entity_id":grantor_entity_id,"grantee_ref":str(grantee_ref),"actions":acts,"constraints":dict(constraints or {}),"economic_terms":terms,"not_before_ms":start,"expires_at_ms":end,"status":"ACTIVE","created_at_ms":now,"access_is_not_ownership":True}
        sig=self._sign(grantor_entity_id,body)
        with self._connect() as db: db.execute("INSERT INTO rights VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",(rid,object_id,grantor_entity_id,body["grantee_ref"],json.dumps(acts),json.dumps(body["constraints"],sort_keys=True),json.dumps(terms,sort_keys=True),start,end,"ACTIVE",now,None,json.dumps(sig,sort_keys=True)))
        return dict(body,signature=sig)

    def active_authority(self,subject_ref:str,grantee_entity_id:str,action:str)->dict|None:
        now=_now(); act=str(action).upper()
        with self._connect() as db: rows=db.execute("SELECT * FROM authorities WHERE subject_ref=? AND grantee_entity_id=? AND status='ACTIVE' AND not_before_ms<=? AND (expires_at_ms IS NULL OR expires_at_ms>?) ORDER BY created_at_ms",(str(subject_ref),grantee_entity_id,now,now)).fetchall()
        for row in rows:
            if act in set(json.loads(row["actions_json"])):
                return {"authority_id":row["authority_id"],"grantor_entity_id":row["grantor_entity_id"],"scope":json.loads(row["scope_json"])}
        return None

    def active_right(self,object_id:str,grantee_ref:str,action:str,*,purpose=None,jurisdiction=None)->dict|None:
        now=_now(); act=str(action).upper()
        with self._connect() as db: rows=db.execute("SELECT * FROM rights WHERE object_id=? AND grantee_ref IN (?, '*') AND status='ACTIVE' AND not_before_ms<=? AND (expires_at_ms IS NULL OR expires_at_ms>?) ORDER BY created_at_ms",(object_id,str(grantee_ref),now,now)).fetchall()
        for row in rows:
            if act not in set(json.loads(row["actions_json"])): continue
            constraints=json.loads(row["constraints_json"]); purposes=set(constraints.get("purposes") or [])
            jurisdictions={str(x).upper() for x in constraints.get("jurisdictions") or []}
            if purposes and str(purpose or "") not in purposes: continue
            if jurisdictions and str(jurisdiction or "").upper() not in jurisdictions: continue
            return {"right_id":row["right_id"],"grantor_entity_id":row["grantor_entity_id"],"constraints":constraints,"economic_terms":json.loads(row["economic_terms_json"])}
        return None

    def revoke_right(self,grantor_entity_id:str,right_id:str)->dict:
        with self._connect() as db: row=db.execute("SELECT * FROM rights WHERE right_id=?",(right_id,)).fetchone()
        if not row: raise KeyError("right not found")
        if row["grantor_entity_id"]!=grantor_entity_id: raise PermissionError("grantor mismatch")
        now=_now()
        with self._connect() as db: db.execute("UPDATE rights SET status='REVOKED',revoked_at_ms=? WHERE right_id=?",(now,right_id))
        return {"right_id":right_id,"status":"REVOKED","revoked_at_ms":now}
    def _path_exists(self,start_object_id:str,target_object_id:str)->bool:
        seen=set(); stack=[start_object_id]
        with self._connect() as db:
            while stack:
                current=stack.pop()
                if current==target_object_id: return True
                if current in seen: continue
                seen.add(current)
                rows=db.execute("SELECT child_object_id FROM provenance_edges WHERE parent_object_id=?",(current,)).fetchall()
                stack.extend(str(r[0]) for r in rows)
        return False

    def add_provenance(self,actor_entity_id:str,parent_object_id:str,child_object_id:str,relation:str,*,contribution_bps:int,evidence=None)->dict:
        self._require_entity(actor_entity_id); self.get_object(parent_object_id); self.get_object(child_object_id)
        if parent_object_id==child_object_id or self._path_exists(child_object_id,parent_object_id): raise ValueError("provenance graph must remain acyclic")
        weight=int(contribution_bps)
        if weight<0 or weight>10000: raise ValueError("contribution_bps must be 0..10000")
        with self._connect() as db:
            total=int(db.execute("SELECT COALESCE(SUM(contribution_bps),0) FROM provenance_edges WHERE child_object_id=?",(child_object_id,)).fetchone()[0])
        if total+weight>10000: raise ValueError("incoming contribution weights exceed 10000 basis points")
        eid=_id("prov3"); now=_now(); body={"schema":"entity-v3-provenance-edge-v1","primitive":"EVENT","edge_id":eid,"parent_object_id":parent_object_id,"child_object_id":child_object_id,"relation":str(relation).upper(),"contribution_bps":weight,"evidence":dict(evidence or {}),"actor_entity_id":actor_entity_id,"created_at_ms":now,"provenance_is_not_ownership":True}
        sig=self._sign(actor_entity_id,body)
        with self._connect() as db: db.execute("INSERT INTO provenance_edges VALUES(?,?,?,?,?,?,?,?,?)",(eid,parent_object_id,child_object_id,body["relation"],weight,json.dumps(body["evidence"],sort_keys=True),actor_entity_id,now,json.dumps(sig,sort_keys=True)))
        return dict(body,signature=sig)

    def _root_contributions(self,object_id:str,multiplier=Fraction(1,1),trail=None)->dict[str,Fraction]:
        trail=set(trail or set())
        if object_id in trail: raise RuntimeError("provenance cycle detected")
        trail.add(object_id)
        with self._connect() as db: rows=db.execute("SELECT parent_object_id,contribution_bps FROM provenance_edges WHERE child_object_id=? ORDER BY parent_object_id",(object_id,)).fetchall()
        total=sum(int(r["contribution_bps"]) for r in rows); out={}
        if total<10000: out[object_id]=multiplier*Fraction(10000-total,10000)
        for row in rows:
            sub=self._root_contributions(str(row["parent_object_id"]),multiplier*Fraction(int(row["contribution_bps"]),10000),trail)
            for key,value in sub.items(): out[key]=out.get(key,Fraction(0,1))+value
        return {k:v for k,v in out.items() if v>0}

    def contribution_distribution(self,object_id:str,amount_units:int)->dict:
        self.get_object(object_id); amount=max(0,int(amount_units)); fractions=self._root_contributions(object_id)
        raw={k:Fraction(amount,1)*v for k,v in fractions.items()}; allocation={k:int(v) for k,v in raw.items()}
        remainder=amount-sum(allocation.values())
        order=sorted(raw,key=lambda k:(-(raw[k]-allocation[k]),k))
        for key in order[:remainder]: allocation[key]+=1
        bps={k:int(fractions[k]*10000) for k in sorted(fractions)}
        return {"schema":"entity-v3-derived-value-distribution-v1","primitive":"VALUE","object_id":object_id,"amount_units":amount,"root_contribution_bps":bps,"distribution":{k:allocation[k] for k in sorted(allocation)},"allocated_total":sum(allocation.values()),"deterministic":True}
    def authorize_use(self,actor_entity_id:str,principal_entity_id:str,object_id:str,action:str,*,quantity:int=1,purpose=None,jurisdiction=None,nonce:str)->dict:
        self._require_entity(actor_entity_id); self._require_entity(principal_entity_id); obj=self.get_object(object_id)
        act=str(action).upper()
        if act not in RIGHT_ACTIONS: raise ValueError("unsupported action")
        authority=None
        if actor_entity_id!=principal_entity_id:
            required="EXECUTE" if act=="EXECUTE" else "ACCESS_DATA"
            authority=self.active_authority(principal_entity_id,actor_entity_id,required)
            if authority is None: raise PermissionError("delegated authority missing")
        right=self.active_right(object_id,principal_entity_id,act,purpose=purpose,jurisdiction=jurisdiction)
        if right is None: raise PermissionError("applicable right missing")
        qty=max(1,int(quantity)); terms=dict(right["economic_terms"] or {}); price=dict(terms.get("pricing") or {})
        amount=0; currency=None
        if str(price.get("mode") or "").upper()=="PER_UNIT":
            amount=qty*max(0,int(price.get("unit_price_units") or 0)); currency=str(price.get("currency") or "").upper() or None
        now=_now(); eid=_id("evt3"); payload={"object_id":object_id,"action":act,"quantity":qty,"purpose":purpose,"jurisdiction":jurisdiction,"principal_entity_id":principal_entity_id}
        body={"schema":"entity-v3-event-v1","primitive":"EVENT","event_id":eid,"actor_entity_id":actor_entity_id,"event_type":"AUTHORIZED_USE","subject_refs":[object_id,principal_entity_id],"authority_ref":authority["authority_id"] if authority else None,"right_ref":right["right_id"],"payload_sha256":_sha(payload),"nonce":str(nonce),"created_at_ms":now}
        sig=self._sign(actor_entity_id,body)
        try:
            with self._connect() as db: db.execute("INSERT INTO events VALUES(?,?,?,?,?,?,?,?,?,?)",(eid,actor_entity_id,"AUTHORIZED_USE",json.dumps(body["subject_refs"]),body["authority_ref"],body["right_ref"],body["payload_sha256"],body["nonce"],now,json.dumps(sig,sort_keys=True)))
        except sqlite3.IntegrityError as exc: raise ValueError("duplicate/replayed event nonce") from exc
        obligation=None
        if amount>0:
            obligation={"schema":"entity-v3-settlement-obligation-v1","payer_entity_id":principal_entity_id,"payee_entity_id":obj["controller_entity_id"],"object_id":object_id,"usage_event_id":eid,"amount_units":amount,"currency":currency,"terms_ref":right["right_id"],"external_money_movement_verified":False}
        return {"authorized":True,"event":dict(body,signature=sig),"right":right,"authority":authority,"settlement_obligation":obligation,"ownership_transferred":False}

    def record_value(self,controller_entity_id:str,object_id:str,amount_units:int,currency:str,*,state="POTENTIAL",basis_ref="asserted")->dict:
        obj=self.get_object(object_id)
        if obj["controller_entity_id"]!=controller_entity_id: raise PermissionError("object controller required")
        state=str(state).upper(); amount=int(amount_units); unit=str(currency).upper()
        if state not in VALUE_STATES or amount<0 or not unit: raise ValueError("invalid value record")
        vid=_id("value3"); now=_now(); body={"schema":"entity-v3-value-v1","primitive":"VALUE","value_id":vid,"object_id":object_id,"controller_entity_id":controller_entity_id,"state":state,"amount_units":amount,"currency":unit,"basis_ref":str(basis_ref),"created_at_ms":now,"asserted_value_is_not_market_value":True}
        sig=self._sign(controller_entity_id,body)
        with self._connect() as db: db.execute("INSERT INTO value_records VALUES(?,?,?,?,?,?,?,?,?)",(vid,object_id,controller_entity_id,state,amount,unit,body["basis_ref"],now,json.dumps(sig,sort_keys=True)))
        return dict(body,signature=sig)
    def attest(self,attestor_entity_id:str,subject_ref:str,claim_type:str,evidence_sha256:str,*,claim=None)->dict:
        self._require_entity(attestor_entity_id); digest=_sha256_hex(evidence_sha256)
        aid=_id("att3"); now=_now(); body={"schema":"entity-v3-attestation-v1","primitive":"EVENT","attestation_id":aid,"subject_ref":str(subject_ref),"attestor_entity_id":attestor_entity_id,"claim_type":str(claim_type).upper(),"evidence_sha256":digest,"claim":dict(claim or {}),"created_at_ms":now,"attestation_is_evidence_not_truth":True}
        sig=self._sign(attestor_entity_id,body)
        with self._connect() as db: db.execute("INSERT INTO attestations VALUES(?,?,?,?,?,?,?,?)",(aid,body["subject_ref"],attestor_entity_id,body["claim_type"],digest,json.dumps(body["claim"],sort_keys=True),now,json.dumps(sig,sort_keys=True)))
        return dict(body,signature=sig)

    def create_trust_policy(self,controller_entity_id:str,claim_type:str,*,minimum_attestations:int=1,required_attestors=None,allowed_attestors=None)->dict:
        self._require_entity(controller_entity_id); minimum=max(1,int(minimum_attestations))
        required=sorted({str(x) for x in (required_attestors or [])}); allowed=sorted({str(x) for x in (allowed_attestors or [])})
        if allowed and not set(required).issubset(set(allowed)): raise ValueError("required attestors must be allowed")
        pid=_id("trust3"); now=_now(); body={"schema":"entity-v3-trust-policy-v1","policy_id":pid,"controller_entity_id":controller_entity_id,"claim_type":str(claim_type).upper(),"minimum_attestations":minimum,"required_attestors":required,"allowed_attestors":allowed,"status":"ACTIVE","created_at_ms":now,"policy_satisfaction_is_not_truth":True}
        sig=self._sign(controller_entity_id,body)
        with self._connect() as db: db.execute("INSERT INTO trust_policies VALUES(?,?,?,?,?,?,?,?,?)",(pid,controller_entity_id,body["claim_type"],minimum,json.dumps(required),json.dumps(allowed),"ACTIVE",now,json.dumps(sig,sort_keys=True)))
        return dict(body,signature=sig)

    def evaluate_trust(self,policy_id:str,subject_ref:str)->dict:
        with self._connect() as db:
            policy=db.execute("SELECT * FROM trust_policies WHERE policy_id=? AND status='ACTIVE'",(policy_id,)).fetchone()
            if not policy: raise KeyError("active trust policy not found")
            rows=db.execute("SELECT * FROM attestations WHERE subject_ref=? AND claim_type=? ORDER BY created_at_ms,attestation_id",(str(subject_ref),policy["claim_type"])).fetchall()
        allowed=set(json.loads(policy["allowed_attestors_json"])); required=set(json.loads(policy["required_attestors_json"])); valid=[]; seen=set()
        for row in rows:
            attestor=str(row["attestor_entity_id"])
            if attestor in seen or (allowed and attestor not in allowed): continue
            body={"schema":"entity-v3-attestation-v1","primitive":"EVENT","attestation_id":row["attestation_id"],"subject_ref":row["subject_ref"],"attestor_entity_id":attestor,"claim_type":row["claim_type"],"evidence_sha256":row["evidence_sha256"],"claim":json.loads(row["claim_json"]),"created_at_ms":row["created_at_ms"],"attestation_is_evidence_not_truth":True}
            if self._verify(attestor,body,json.loads(row["signature_json"])):
                seen.add(attestor); valid.append(row["attestation_id"])
        minimum=int(policy["minimum_attestations"]); satisfied=len(valid)>=minimum and required.issubset(seen)
        return {"schema":"entity-v3-trust-evaluation-v1","policy_id":policy_id,"subject_ref":str(subject_ref),"claim_type":policy["claim_type"],"policy_satisfied":satisfied,"valid_attestation_count":len(valid),"minimum_attestations":minimum,"required_attestors_present":required.issubset(seen),"attestation_ids":valid,"truth_inferred":False,"evaluated_at_ms":_now()}

    def open_settlement(self,settlement_engine,obligation:dict,*,transaction_nonce:str,settlement_kind="INTERNAL_ACCOUNTING")->dict:
        required={"payer_entity_id","payee_entity_id","amount_units","currency","usage_event_id"}
        if not required.issubset(set(obligation or {})): raise ValueError("incomplete settlement obligation")
        result=settlement_engine.create(str(obligation["payer_entity_id"]),str(obligation["payee_entity_id"]),amount_units=int(obligation["amount_units"]),currency=str(obligation["currency"]),obligation_ref=str(obligation["usage_event_id"]),transaction_nonce=str(transaction_nonce),settlement_kind=str(settlement_kind))
        return {"schema":"entity-v3-settlement-open-v1","usage_event_id":obligation["usage_event_id"],"settlement_id":result["settlement_id"],"state":result["state"],"amount_units":int(obligation["amount_units"]),"currency":str(obligation["currency"]),"external_money_movement_verified":False,"settlement":result}
    def publish_resolution(self,controller_entity_id:str,object_id:str,endpoints:list[dict],*,version:int,expires_at_ms=None)->dict:
        obj=self.get_object(object_id)
        if obj["controller_entity_id"]!=controller_entity_id: raise PermissionError("object controller required")
        ver=int(version)
        if ver<1: raise ValueError("resolution version must be positive")
        eps=[]
        for item in endpoints or []:
            endpoint={"service":str(item.get("service") or "").upper(),"uri":str(item.get("uri") or ""),"protocol":str(item.get("protocol") or "").upper()}
            if not endpoint["service"] or not endpoint["uri"]: raise ValueError("resolution endpoint service and uri required")
            eps.append(endpoint)
        if not eps: raise ValueError("at least one endpoint required")
        now=_now(); body={"schema":"entity-v3-resolution-v1","object_id":object_id,"controller_entity_id":controller_entity_id,"version":ver,"endpoints":eps,"expires_at_ms":int(expires_at_ms) if expires_at_ms is not None else None,"status":"ACTIVE","created_at_ms":now,"resolver_is_not_authority":True}
        sig=self._sign(controller_entity_id,body)
        try:
            with self._connect() as db: db.execute("INSERT INTO resolution VALUES(?,?,?,?,?,?,?)",(object_id,ver,json.dumps(eps,sort_keys=True),body["expires_at_ms"],"ACTIVE",now,json.dumps(sig,sort_keys=True)))
        except sqlite3.IntegrityError as exc: raise ValueError("resolution version already exists") from exc
        return dict(body,signature=sig)

    def resolve(self,object_id:str)->dict:
        obj=self.get_object(object_id); now=_now()
        with self._connect() as db: row=db.execute("SELECT * FROM resolution WHERE object_id=? AND status='ACTIVE' AND (expires_at_ms IS NULL OR expires_at_ms>?) ORDER BY version DESC LIMIT 1",(object_id,now)).fetchone()
        if not row: raise KeyError("no current resolution record")
        body={"schema":"entity-v3-resolution-v1","object_id":object_id,"controller_entity_id":obj["controller_entity_id"],"version":int(row["version"]),"endpoints":json.loads(row["endpoints_json"]),"expires_at_ms":row["expires_at_ms"],"status":"ACTIVE","created_at_ms":int(row["created_at_ms"]),"resolver_is_not_authority":True}
        sig=json.loads(row["signature_json"])
        if not self._verify(obj["controller_entity_id"],body,sig): raise PermissionError("resolution signature invalid")
        return {"schema":"entity-v3-resolution-proof-v1","object":obj,"resolution":dict(body,signature=sig),"verified":True,"resolved_at_ms":now,"resolver_is_not_authority":True}
    def _collect_ancestry(self,object_id:str)->tuple[set[str],list[dict]]:
        objects={object_id}; edges=[]; stack=[object_id]
        with self._connect() as db:
            while stack:
                child=stack.pop()
                rows=db.execute("SELECT * FROM provenance_edges WHERE child_object_id=? ORDER BY parent_object_id,edge_id",(child,)).fetchall()
                for row in rows:
                    edge=dict(row); edge["evidence"]=json.loads(edge.pop("evidence_json")); edge["signature"]=json.loads(edge.pop("signature_json")); edges.append(edge)
                    parent=str(row["parent_object_id"])
                    if parent not in objects: objects.add(parent); stack.append(parent)
        return objects,edges

    def _active_right_records(self,object_ids:set[str])->list[dict]:
        if not object_ids: return []
        marks=",".join("?" for _ in object_ids); now=_now()
        with self._connect() as db: rows=db.execute(f"SELECT * FROM rights WHERE object_id IN ({marks}) AND status='ACTIVE' AND not_before_ms<=? AND (expires_at_ms IS NULL OR expires_at_ms>?) ORDER BY right_id",[*sorted(object_ids),now,now]).fetchall()
        out=[]
        for row in rows:
            x=dict(row); x["actions"]=json.loads(x.pop("actions_json")); x["constraints"]=json.loads(x.pop("constraints_json")); x["economic_terms"]=json.loads(x.pop("economic_terms_json")); x["signature"]=json.loads(x.pop("signature_json")); out.append(x)
        return out

    def _active_authority_records(self,subject_refs:set[str])->list[dict]:
        if not subject_refs: return []
        marks=",".join("?" for _ in subject_refs); now=_now()
        with self._connect() as db: rows=db.execute(f"SELECT * FROM authorities WHERE subject_ref IN ({marks}) AND status='ACTIVE' AND not_before_ms<=? AND (expires_at_ms IS NULL OR expires_at_ms>?) ORDER BY authority_id",[*sorted(subject_refs),now,now]).fetchall()
        out=[]
        for row in rows:
            x=dict(row); x["actions"]=json.loads(x.pop("actions_json")); x["scope"]=json.loads(x.pop("scope_json")); x["signature"]=json.loads(x.pop("signature_json")); out.append(x)
        return out
    def _bundle_manifests(self,records:dict)->list[dict]:
        signer_ids=set()
        for obj in records.get("objects") or []: signer_ids.add(obj["controller_entity_id"])
        for row in records.get("authorities") or []: signer_ids.add(row["grantor_entity_id"])
        for row in records.get("rights") or []: signer_ids.add(row["grantor_entity_id"])
        for row in records.get("events") or []: signer_ids.add(row["actor_entity_id"])
        for row in records.get("provenance_edges") or []: signer_ids.add(row["actor_entity_id"])
        for row in records.get("values") or []: signer_ids.add(row["controller_entity_id"])
        for row in records.get("attestations") or []: signer_ids.add(row["attestor_entity_id"])
        for row in records.get("resolution") or []: signer_ids.add(row["controller_entity_id"])
        manifests=[]
        for entity_id in sorted(signer_ids): manifests.append(self.identity.load_manifest(entity_id))
        return manifests

    def export_bundle(self,object_id:str)->dict:
        object_ids,edges=self._collect_ancestry(object_id)
        objects=[self.get_object(x) for x in sorted(object_ids)]
        controllers={x["controller_entity_id"] for x in objects}
        rights=self._active_right_records(object_ids)
        authorities=self._active_authority_records(object_ids|controllers)
        with self._connect() as db:
            vals=[dict(r) for r in db.execute("SELECT * FROM value_records ORDER BY value_id") if r["object_id"] in object_ids]
            atts=[dict(r) for r in db.execute("SELECT * FROM attestations ORDER BY attestation_id") if r["subject_ref"] in object_ids]
            events=[dict(r) for r in db.execute("SELECT * FROM events ORDER BY event_id") if object_ids.intersection(set(json.loads(r["subject_refs_json"])))]
            resolutions=[]
            for oid in sorted(object_ids):
                row=db.execute("SELECT * FROM resolution WHERE object_id=? AND status='ACTIVE' ORDER BY version DESC LIMIT 1",(oid,)).fetchone()
                if row:
                    x=dict(row); x["controller_entity_id"]=next(o["controller_entity_id"] for o in objects if o["object_id"]==oid); resolutions.append(x)
        for x in vals: x["signature"]=json.loads(x.pop("signature_json"))
        for x in atts: x["claim"]=json.loads(x.pop("claim_json")); x["signature"]=json.loads(x.pop("signature_json"))
        for x in events: x["subject_refs"]=json.loads(x.pop("subject_refs_json")); x["signature"]=json.loads(x.pop("signature_json"))
        for x in resolutions: x["endpoints"]=json.loads(x.pop("endpoints_json")); x["signature"]=json.loads(x.pop("signature_json"))
        records={"objects":objects,"authorities":authorities,"rights":rights,"events":events,"provenance_edges":edges,"values":vals,"attestations":atts,"resolution":resolutions}
        manifests=self._bundle_manifests(records)
        bundle={"schema":"entity-v3-sovereign-bundle-v1","protocol_version":"3.0.0","root_object_id":object_id,"primitives":list(PRIMITIVES),"identity_manifests":manifests,**records,"provider_independent":True,"exported_at_ms":_now()}
        bundle["semantic_sha256"]=_sha({k:v for k,v in bundle.items() if k!="exported_at_ms"})
        return bundle

    @staticmethod
    def _record_body(kind:str,row:dict)->tuple[str,dict]:
        if kind=="object":
            return row["controller_entity_id"],{"schema":"entity-v3-object-v1","primitive":"ENTITY","object_id":row["object_id"],"controller_entity_id":row["controller_entity_id"],"object_type":row["object_type"],"title":row["title"],"content_sha256":row.get("content_sha256"),"descriptor":row.get("descriptor") or {},"status":"ACTIVE","created_at_ms":row["created_at_ms"],"custody_is_not_authority":True}
        if kind=="authority":
            return row["grantor_entity_id"],{"schema":"entity-v3-authority-v1","primitive":"AUTHORITY","authority_id":row["authority_id"],"subject_ref":row["subject_ref"],"grantor_entity_id":row["grantor_entity_id"],"grantee_entity_id":row["grantee_entity_id"],"actions":row["actions"],"scope":row["scope"],"not_before_ms":row["not_before_ms"],"expires_at_ms":row.get("expires_at_ms"),"status":"ACTIVE","created_at_ms":row["created_at_ms"],"implicit_escalation_prohibited":True}
        if kind=="right":
            return row["grantor_entity_id"],{"schema":"entity-v3-right-v1","primitive":"RIGHT","right_id":row["right_id"],"object_id":row["object_id"],"grantor_entity_id":row["grantor_entity_id"],"grantee_ref":row["grantee_ref"],"actions":row["actions"],"constraints":row["constraints"],"economic_terms":row["economic_terms"],"not_before_ms":row["not_before_ms"],"expires_at_ms":row.get("expires_at_ms"),"status":"ACTIVE","created_at_ms":row["created_at_ms"],"access_is_not_ownership":True}
        if kind=="event":
            return row["actor_entity_id"],{"schema":"entity-v3-event-v1","primitive":"EVENT","event_id":row["event_id"],"actor_entity_id":row["actor_entity_id"],"event_type":row["event_type"],"subject_refs":row["subject_refs"],"authority_ref":row.get("authority_ref"),"right_ref":row.get("right_ref"),"payload_sha256":row["payload_sha256"],"nonce":row.get("nonce"),"created_at_ms":row["created_at_ms"]}
        if kind=="provenance":
            return row["actor_entity_id"],{"schema":"entity-v3-provenance-edge-v1","primitive":"EVENT","edge_id":row["edge_id"],"parent_object_id":row["parent_object_id"],"child_object_id":row["child_object_id"],"relation":row["relation"],"contribution_bps":row["contribution_bps"],"evidence":row.get("evidence") or {},"actor_entity_id":row["actor_entity_id"],"created_at_ms":row["created_at_ms"],"provenance_is_not_ownership":True}
        if kind=="value":
            return row["controller_entity_id"],{"schema":"entity-v3-value-v1","primitive":"VALUE","value_id":row["value_id"],"object_id":row["object_id"],"controller_entity_id":row["controller_entity_id"],"state":row["state"],"amount_units":row["amount_units"],"currency":row["currency"],"basis_ref":row["basis_ref"],"created_at_ms":row["created_at_ms"],"asserted_value_is_not_market_value":True}
        if kind=="attestation":
            return row["attestor_entity_id"],{"schema":"entity-v3-attestation-v1","primitive":"EVENT","attestation_id":row["attestation_id"],"subject_ref":row["subject_ref"],"attestor_entity_id":row["attestor_entity_id"],"claim_type":row["claim_type"],"evidence_sha256":row["evidence_sha256"],"claim":row.get("claim") or {},"created_at_ms":row["created_at_ms"],"attestation_is_evidence_not_truth":True}
        if kind=="resolution":
            return row["controller_entity_id"],{"schema":"entity-v3-resolution-v1","object_id":row["object_id"],"controller_entity_id":row["controller_entity_id"],"version":row["version"],"endpoints":row["endpoints"],"expires_at_ms":row.get("expires_at_ms"),"status":"ACTIVE","created_at_ms":row["created_at_ms"],"resolver_is_not_authority":True}
        raise ValueError("unsupported record kind")

    def verify_bundle(self,bundle:dict)->dict:
        failures=[]; b=dict(bundle or {})
        if b.get("schema")!="entity-v3-sovereign-bundle-v1": failures.append("schema_invalid")
        expected=_sha({k:v for k,v in b.items() if k not in {"exported_at_ms","semantic_sha256"}})
        if b.get("semantic_sha256")!=expected: failures.append("semantic_hash_invalid")
        if set(b.get("primitives") or [])!=set(PRIMITIVES): failures.append("primitive_set_incomplete")
        manifests={}
        for manifest in b.get("identity_manifests") or []:
            entity_id=str(manifest.get("entity_id") or "")
            if not self.identity.verify_manifest(manifest): failures.append(f"manifest_invalid:{entity_id}")
            elif entity_id in manifests: failures.append(f"manifest_duplicate:{entity_id}")
            else: manifests[entity_id]=manifest
        object_ids={str(x.get("object_id")) for x in b.get("objects") or []}
        if b.get("root_object_id") not in object_ids: failures.append("root_object_missing")
        collections=(("object","objects"),("authority","authorities"),("right","rights"),("event","events"),("provenance","provenance_edges"),("value","values"),("attestation","attestations"),("resolution","resolution"))
        for kind,key in collections:
            for row in b.get(key) or []:
                try:
                    signer,body=self._record_body(kind,row); manifest=manifests.get(signer)
                    if manifest is None: failures.append(f"manifest_missing:{signer}")
                    elif not self.identity.verify_signature(manifest,body,row["signature"]): failures.append(f"signature_invalid:{kind}:{next((str(v) for k,v in row.items() if k.endswith('_id')), '?')}")
                except Exception as exc: failures.append(f"record_invalid:{kind}:{type(exc).__name__}")
        incoming={}; adjacency={oid:[] for oid in object_ids}
        for edge in b.get("provenance_edges") or []:
            parent=str(edge.get("parent_object_id")); child=str(edge.get("child_object_id")); weight=int(edge.get("contribution_bps") or 0)
            if parent not in object_ids or child not in object_ids: failures.append("provenance_reference_missing")
            incoming[child]=incoming.get(child,0)+weight; adjacency.setdefault(parent,[]).append(child)
        if any(v>10000 for v in incoming.values()): failures.append("provenance_weight_overflow")
        visiting=set(); visited=set()
        def visit(node):
            if node in visiting: return False
            if node in visited: return True
            visiting.add(node)
            for child in adjacency.get(node,[]):
                if not visit(child): return False
            visiting.remove(node); visited.add(node); return True
        if any(not visit(oid) for oid in sorted(object_ids) if oid not in visited): failures.append("provenance_cycle")
        return {"valid":not failures,"failures":failures,"root_object_id":b.get("root_object_id"),"semantic_sha256":b.get("semantic_sha256"),"provider_independent":bool(b.get("provider_independent")),"portable_verification_uses_embedded_manifests":True,"primitive_set_complete":set(b.get("primitives") or [])==set(PRIMITIVES),"verified_manifest_count":len(manifests)}
    def register_digital_commodity(self,controller_entity_id:str,title:str,content_sha256:str,*,commodity_class="DATA",measurement_unit="USE",metadata=None)->dict:
        descriptor={"digital_commodity":True,"commodity_class":str(commodity_class).upper(),"measurement_unit":str(measurement_unit).upper(),"raw_data_transfer_default":False,"metadata":dict(metadata or {})}
        result=self.register_object(controller_entity_id,"DATASET",title,descriptor=descriptor,content_sha256=content_sha256)
        result["digital_commodity_object"]=True; return result

    def register_ai_agent(self,controller_entity_id:str,agent_entity_id:str,title:str,*,model_ref=None,policy_refs=None,capabilities=None)->dict:
        self._require_entity(agent_entity_id)
        descriptor={"agent_entity_id":agent_entity_id,"model_ref":model_ref,"policy_refs":sorted({str(x) for x in (policy_refs or [])}),"declared_capabilities":sorted({str(x).upper() for x in (capabilities or [])}),"self_authority_inferred":False}
        result=self.register_object(controller_entity_id,"AI_AGENT",title,descriptor=descriptor)
        result["agent_entity_id"]=agent_entity_id; return result

    def status(self)->dict:
        with self._connect() as db:
            counts={name:int(db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]) for name,table in {"entities":"objects","authorities":"authorities","rights":"rights","events":"events","values":"value_records","provenance_edges":"provenance_edges","attestations":"attestations","trust_policies":"trust_policies","resolution_records":"resolution"}.items()}
        return {"ready":True,"schema":"entity-v3-universal-transaction-fabric-v1","protocol_version":"3.0.0","primitives":list(PRIMITIVES),"counts":counts,"machine_readable_rights":True,"delegated_ai_authority":True,"digital_commodity_objects":True,"causal_provenance":True,"derived_value_distribution":True,"settlement_obligations":True,"entity_native_resolution":True,"trust_attestations":True,"trust_policy_thresholds":True,"settlement_engine_bridge":True,"provider_independent_exports":True,"infrastructure_possession_is_not_authority":True}






