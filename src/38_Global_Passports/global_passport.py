from __future__ import annotations
from pathlib import Path
from typing import Any
import hashlib, json, secrets, sqlite3, time

CORE_PRIMITIVES=("ENTITY","AUTHORITY","RIGHT","EVENT","VALUE")
def now_ms()->int: return int(time.time()*1000)
def canon(v:Any)->bytes: return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()
def digest(v:Any)->str: return hashlib.sha256(v if isinstance(v,(bytes,bytearray)) else canon(v)).hexdigest()
def rid(prefix:str)->str: return prefix+"-"+secrets.token_hex(12)

class GlobalPassportRegistry:
    """One passport envelope, many composable profiles. It binds existing rights/evidence rather than replacing them."""
    def __init__(self,root:str|Path,identity,fabric,rights_passports,profile_registry):
        self.path=Path(root)/"entity_v3_4_global_passports.sqlite"; self.path.parent.mkdir(parents=True,exist_ok=True)
        self.identity=identity; self.fabric=fabric; self.rights=rights_passports; self.profiles=profile_registry
        with sqlite3.connect(self.path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS global_passports(
            passport_id TEXT PRIMARY KEY, object_id TEXT NOT NULL, controller_entity_id TEXT NOT NULL,
            version TEXT NOT NULL, body_sha256 TEXT NOT NULL, body_json TEXT NOT NULL,
            signature_json TEXT NOT NULL, created_at_ms INTEGER NOT NULL, UNIQUE(object_id,version))""")

    def issue(self,controller_entity_id:str,object_id:str,rights_passport_id:str,profile_refs:list[str],*,
              version:str="1.0",evidence_refs:list[str]|None=None,provenance_refs:list[str]|None=None,
              jurisdiction_profile_refs:list[str]|None=None,standards_mappings:list[dict]|None=None,
              economic_state:dict|None=None,industry_context:dict|None=None)->dict:
        self.identity.load_manifest(controller_entity_id); obj=self.fabric.get_object(object_id)
        if obj["controller_entity_id"]!=controller_entity_id: raise PermissionError("object controller required")
        right=self.rights.get(rights_passport_id)
        if right["object_id"]!=object_id or right["controller_entity_id"]!=controller_entity_id: raise ValueError("rights passport mismatch")
        if not self.rights.verify(right)["valid"]: raise ValueError("rights passport invalid")
        stack=self.profiles.resolve_stack(profile_refs)
        mappings=[]
        for item in standards_mappings or []:
            m=dict(item)
            if m.get("normative_equivalence_claimed") is True: raise ValueError("standards mapping cannot claim normative equivalence")
            m["normative_equivalence_claimed"]=False; mappings.append(m)
        econ=dict(economic_state or {"state":"POTENTIAL","amount_units":0,"currency":"UNSPECIFIED"})
        if int(econ.get("amount_units",0))<0: raise ValueError("economic amount cannot be negative")
        econ["market_observation_is_not_accounting_fair_value"]=True
        body={"schema":"entity-v3-global-passport-v1","passport_id":rid("gpassport3"),"object_id":object_id,
              "controller_entity_id":controller_entity_id,"version":str(version),"core_primitives":list(CORE_PRIMITIVES),
              "rights_passport_id":rights_passport_id,"rights_passport_sha256":right["passport_sha256"],
              "profile_stack":stack,"evidence_refs":sorted({str(x) for x in (evidence_refs or [])}),
              "provenance_refs":sorted({str(x) for x in (provenance_refs or [])}),
              "jurisdiction_profile_refs":sorted({str(x) for x in (jurisdiction_profile_refs or [])}),
              "standards_mappings":sorted(mappings,key=lambda x:json.dumps(x,sort_keys=True)),
              "economic_state":econ,"industry_context":dict(industry_context or {}),
              "one_passport_many_profiles":True,"profile_composition_does_not_create_authority":True,
              "standards_mapping_is_not_normative_equivalence":True,"evidence_does_not_establish_objective_truth":True,
              "legal_effect_is_deployment_specific":True,"underlying_information_remains_nonrival":True,"created_at_ms":now_ms()}
        body_sha=digest(body); sig=self.identity.sign(controller_entity_id,body)
        try:
            with sqlite3.connect(self.path) as db:
                db.execute("INSERT INTO global_passports VALUES(?,?,?,?,?,?,?,?)",(body["passport_id"],object_id,controller_entity_id,body["version"],body_sha,json.dumps(body,sort_keys=True),json.dumps(sig,sort_keys=True),body["created_at_ms"]))
        except sqlite3.IntegrityError as exc: raise ValueError("immutable global passport version already exists") from exc
        return dict(body,body_sha256=body_sha,signature=sig)
    def get(self,passport_id:str)->dict:
        with sqlite3.connect(self.path) as db:
            db.row_factory=sqlite3.Row; row=db.execute("SELECT * FROM global_passports WHERE passport_id=?",(str(passport_id),)).fetchone()
        if not row: raise KeyError("global passport missing")
        body=json.loads(row["body_json"])
        return dict(body,body_sha256=row["body_sha256"],signature=json.loads(row["signature_json"]))

    def verify(self,passport:dict)->dict:
        try:
            body={k:v for k,v in passport.items() if k not in {"body_sha256","signature"}}
            if body.get("schema")!="entity-v3-global-passport-v1" or body.get("core_primitives")!=list(CORE_PRIMITIVES): raise ValueError("schema/core")
            for flag in ("one_passport_many_profiles","profile_composition_does_not_create_authority","standards_mapping_is_not_normative_equivalence","evidence_does_not_establish_objective_truth","legal_effect_is_deployment_specific","underlying_information_remains_nonrival"):
                if body.get(flag) is not True: raise ValueError(flag)
            right=self.rights.get(body["rights_passport_id"])
            if right["passport_sha256"]!=body["rights_passport_sha256"] or not self.rights.verify(right)["valid"]: raise ValueError("rights passport")
            stack=self.profiles.resolve_stack(body["profile_stack"]["profile_refs"])
            if stack["profile_hashes"]!=body["profile_stack"]["profile_hashes"]: raise ValueError("profile stack")
            if any(m.get("normative_equivalence_claimed") is not False for m in body.get("standards_mappings",[])): raise ValueError("standards equivalence")
            expected=digest(body)
            if passport.get("body_sha256")!=expected: raise ValueError("hash")
            manifest=self.identity.load_manifest(body["controller_entity_id"])
            if not self.identity.verify_signature(manifest,body,dict(passport.get("signature") or {})): raise ValueError("signature")
            return {"valid":True,"passport_id":body["passport_id"],"body_sha256":expected,"objective_truth_claimed":False,"legal_compliance_claimed":False}
        except Exception as exc:
            return {"valid":False,"reason":type(exc).__name__,"objective_truth_claimed":False,"legal_compliance_claimed":False}
