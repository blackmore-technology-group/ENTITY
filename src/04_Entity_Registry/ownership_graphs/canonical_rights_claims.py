from __future__ import annotations
from pathlib import Path
from contextlib import contextmanager
from threading import RLock
import json, re, sqlite3, time, uuid

ENTITY_ID_RE=re.compile(r"^(?:ent1|ent2)-[a-z2-7]{52}$")
VERIFICATION_LEVELS=("SELF_ASSERTED","CORROBORATED","VERIFIED","AUTHORITATIVELY_VERIFIED")
CLAIM_STATES={"ACTIVE","CHALLENGED","DISPUTED","SUPERSEDED","ADJUDICATED"}
RIGHT_TYPES={"AUTHOR","CREATOR","COPYRIGHT_CLAIMANT","COPYRIGHT_OWNER","CONTROLLER","CUSTODIAN","DATA_CONTROLLER","DATA_CUSTODIAN","PERSONAL_DATA_SUBJECT","DEPICTED_PERSON","TRADEMARK_INTEREST","PATENT_INTEREST","CONFIDENTIALITY_INTEREST","LICENSEE","LICENSOR","LICENSING_AUTHORITY","ROYALTY_PARTICIPANT","EMPLOYEE_EMPLOYER_INTEREST","EMPLOYER_INTEREST","EMPLOYEE_INTEREST","COLLECTIVE_OWNER","COLLECTIVE_CONTROLLER","GUARDIAN","ESTATE","ESTATE_INTEREST","PLATFORM_LICENSE_HOLDER","AUTHORIZED_AGENT","AGENT"}
LICENSING_RIGHTS={"COPYRIGHT_OWNER","DATA_CONTROLLER","LICENSOR","LICENSING_AUTHORITY","COLLECTIVE_CONTROLLER","PLATFORM_LICENSE_HOLDER"}
ONTOLOGY_VERSION="entity-rights-ontology-v1"
EVIDENCE_ORIGINS={"DIRECT_OBSERVATION","ENTITY_ASSERTION","COUNTERPARTY_ATTESTATION","EXTERNAL_AUTHORITATIVE_RECORD","DERIVED_INFERENCE","UNKNOWN"}

def _now(): return int(time.time()*1000)
def _id(): return "claim1-"+uuid.uuid4().hex

class RightsClaimsGraph:
    """Many-to-many signed rights claims. Registration/signature never equals legal truth."""
    def __init__(self,state_dir: str|Path,identity,local_controller_check=None):
        self.root=Path(state_dir)/"rights_claims"; self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/"rights_claims.sqlite"; self.identity=identity
        self.local_controller_check=local_controller_check or self._default_local
        self._lock=RLock(); self._init_db()
    def _default_local(self,entity_id: str) -> bool:
        try: self.identity.load_manifest(entity_id); return True
        except Exception: return False
    def _require_local(self,entity_id: str):
        if not ENTITY_ID_RE.fullmatch(str(entity_id or "")): raise ValueError("invalid Entity ID")
        if not self.local_controller_check(entity_id): raise PermissionError("operation requires a locally controlled Entity")
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
            db.execute("CREATE TABLE IF NOT EXISTS claims(claim_id TEXT PRIMARY KEY,asset_id TEXT NOT NULL,claimant_entity_id TEXT NOT NULL,right_type TEXT NOT NULL,share_num INTEGER NOT NULL,share_den INTEGER NOT NULL,territory TEXT NOT NULL,jurisdiction TEXT NOT NULL,legal_basis TEXT NOT NULL,scope_json TEXT NOT NULL,evidence_json TEXT NOT NULL,evidence_origin TEXT NOT NULL,effective_at_ms INTEGER NOT NULL,expires_at_ms INTEGER,verification_level TEXT NOT NULL,lifecycle_status TEXT NOT NULL,supersedes_claim_id TEXT,signature_json TEXT NOT NULL,created_at_ms INTEGER NOT NULL,updated_at_ms INTEGER NOT NULL)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_rights_asset ON claims(asset_id)")
            db.execute("CREATE TABLE IF NOT EXISTS claim_events(sequence INTEGER PRIMARY KEY AUTOINCREMENT,event_id TEXT UNIQUE NOT NULL,claim_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_entity_id TEXT NOT NULL,payload_json TEXT NOT NULL,signature_json TEXT NOT NULL,timestamp_ms INTEGER NOT NULL)")
    def _event(self,db,claim_id,event_type,actor,payload):
        ts=_now(); body={"claim_id":claim_id,"event_type":event_type,"actor_entity_id":actor,"payload":payload,"timestamp_ms":ts}
        sig=self.identity.sign(actor,body); eid="evt1-"+uuid.uuid4().hex
        db.execute("INSERT INTO claim_events(event_id,claim_id,event_type,actor_entity_id,payload_json,signature_json,timestamp_ms) VALUES(?,?,?,?,?,?,?)",(eid,claim_id,event_type,actor,json.dumps(payload,sort_keys=True),json.dumps(sig,sort_keys=True),ts))
        return {"event_id":eid,"timestamp_ms":ts,"signature":sig}
    def assert_claim(self,claimant_entity_id: str,*,asset_id: str,right_type: str,share_num: int=1,share_den: int=1,territory: str="unspecified",jurisdiction: str="unspecified",legal_basis: str="self_asserted",scope: dict|None=None,evidence: dict|None=None,evidence_origin: str="ENTITY_ASSERTION",effective_at_ms: int|None=None,expires_at_ms: int|None=None,supersedes_claim_id: str|None=None) -> dict:
        self._require_local(claimant_entity_id); rtype=str(right_type or "").upper(); origin=str(evidence_origin or "UNKNOWN").upper()
        if rtype not in RIGHT_TYPES: raise ValueError("unsupported right_type")
        if origin not in EVIDENCE_ORIGINS: raise ValueError("unsupported evidence_origin")
        share_num=int(share_num); share_den=int(share_den)
        if share_den<1 or share_num<1 or share_num>share_den: raise ValueError("invalid fractional share")
        now=_now(); claim_id=_id()
        body={"schema":"entity-rights-claim-v2","claim_id":claim_id,"asset_id":str(asset_id),"claimant_entity_id":claimant_entity_id,"right_type":rtype,"share":{"numerator":share_num,"denominator":share_den},"territory":str(territory),"jurisdiction":str(jurisdiction),"legal_basis":str(legal_basis),"scope":dict(scope or {}),"evidence":dict(evidence or {}),"evidence_origin":origin,"effective_at_ms":int(effective_at_ms or now),"expires_at_ms":expires_at_ms,"verification_level":"SELF_ASSERTED","lifecycle_status":"ACTIVE","supersedes_claim_id":supersedes_claim_id}
        sig=self.identity.sign(claimant_entity_id,body)
        with self._lock,self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("INSERT INTO claims VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(claim_id,str(asset_id),claimant_entity_id,rtype,share_num,share_den,body["territory"],body["jurisdiction"],body["legal_basis"],json.dumps(body["scope"],sort_keys=True),json.dumps(body["evidence"],sort_keys=True),origin,body["effective_at_ms"],expires_at_ms,"SELF_ASSERTED","ACTIVE",supersedes_claim_id,json.dumps(sig,sort_keys=True),now,now))
            event=self._event(db,claim_id,"claim.asserted",claimant_entity_id,{"right_type":rtype,"verification_level":"SELF_ASSERTED","evidence_origin":origin})
        return dict(body,signature=sig,event=event)
    def assert_claims_batch(self,claimant_entity_id:str,claims:list[dict])->list[dict]:
        """Assert many individually signed rights claims and signed claim events in one transaction."""
        self._require_local(claimant_entity_id); items=list(claims or [])
        if not items: return []
        sign=self.identity.open_signing_session(claimant_entity_id); claim_rows=[]; event_rows=[]; out=[]
        for item in items:
            rtype=str(item.get("right_type") or "DATA_CONTROLLER").upper(); origin=str(item.get("evidence_origin") or "ENTITY_ASSERTION").upper()
            if rtype not in RIGHT_TYPES: raise ValueError("unsupported right_type")
            if origin not in EVIDENCE_ORIGINS: raise ValueError("unsupported evidence_origin")
            now=_now(); claim_id=_id(); scope=dict(item.get("scope") or {}); evidence=dict(item.get("evidence") or {})
            body={"schema":"entity-rights-claim-v2","claim_id":claim_id,"asset_id":str(item["asset_id"]),"claimant_entity_id":claimant_entity_id,"right_type":rtype,"share":{"numerator":1,"denominator":1},"territory":str(item.get("territory") or "unspecified"),"jurisdiction":str(item.get("jurisdiction") or "unspecified"),"legal_basis":str(item.get("legal_basis") or "entity_asset_registration"),"scope":scope,"evidence":evidence,"evidence_origin":origin,"effective_at_ms":int(item.get("effective_at_ms") or now),"expires_at_ms":item.get("expires_at_ms"),"verification_level":"SELF_ASSERTED","lifecycle_status":"ACTIVE","supersedes_claim_id":None}
            sig=sign(body); claim_rows.append((claim_id,body["asset_id"],claimant_entity_id,rtype,1,1,body["territory"],body["jurisdiction"],body["legal_basis"],json.dumps(scope,sort_keys=True),json.dumps(evidence,sort_keys=True),origin,body["effective_at_ms"],body["expires_at_ms"],"SELF_ASSERTED","ACTIVE",None,json.dumps(sig,sort_keys=True),now,now))
            ep={"right_type":rtype,"verification_level":"SELF_ASSERTED","evidence_origin":origin}; eb={"claim_id":claim_id,"event_type":"claim.asserted","actor_entity_id":claimant_entity_id,"payload":ep,"timestamp_ms":now}; es=sign(eb); eid="evt1-"+uuid.uuid4().hex
            event_rows.append((eid,claim_id,"claim.asserted",claimant_entity_id,json.dumps(ep,sort_keys=True),json.dumps(es,sort_keys=True),now)); out.append(dict(body,signature=sig,event={"event_id":eid,"timestamp_ms":now,"signature":es}))
        with self._lock,self._connect() as db:
            db.execute("BEGIN IMMEDIATE"); db.executemany("INSERT INTO claims VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",claim_rows); db.executemany("INSERT INTO claim_events(event_id,claim_id,event_type,actor_entity_id,payload_json,signature_json,timestamp_ms) VALUES(?,?,?,?,?,?,?)",event_rows)
        return out

    def verify_claim(self,verifier_entity_id: str,claim_id: str,level: str,evidence: dict) -> dict:
        self._require_local(verifier_entity_id); target=str(level or "").upper(); evidence=dict(evidence or {})
        if target not in VERIFICATION_LEVELS or target=="SELF_ASSERTED": raise ValueError("verification level must be CORROBORATED or stronger")
        if not evidence: raise ValueError("verification evidence is required")
        with self._lock,self._connect() as db:
            db.execute("BEGIN IMMEDIATE"); row=db.execute("SELECT * FROM claims WHERE claim_id=?",(claim_id,)).fetchone()
            if not row: raise KeyError("claim not found")
            if row["claimant_entity_id"]==verifier_entity_id: raise PermissionError("claimant cannot independently verify own claim")
            if row["lifecycle_status"] in {"SUPERSEDED","ADJUDICATED"}: raise ValueError("claim is closed")
            if target=="AUTHORITATIVELY_VERIFIED":
                manifest=self.identity.load_manifest(verifier_entity_id); roles={str(x).upper() for x in (manifest.get("metadata") or {}).get("authority_roles",[])}
                if "RIGHTS_AUTHORITY" not in roles: raise PermissionError("RIGHTS_AUTHORITY role required")
                if not str(evidence.get("authority_reference") or "").strip(): raise ValueError("authority_reference required")
            db.execute("UPDATE claims SET verification_level=?,updated_at_ms=? WHERE claim_id=?",(target,_now(),claim_id))
            event=self._event(db,claim_id,"claim.verification_added",verifier_entity_id,{"verification_level":target,"evidence":evidence})
        return {"claim_id":claim_id,"verification_level":target,"event":event}

    def set_state(self,actor_entity_id: str,claim_id: str,state: str,reason: str="",evidence: dict|None=None) -> dict:
        self._require_local(actor_entity_id); target=str(state or "").upper()
        if target not in CLAIM_STATES or target=="ACTIVE": raise ValueError("unsupported claim transition")
        with self._lock,self._connect() as db:
            db.execute("BEGIN IMMEDIATE"); row=db.execute("SELECT * FROM claims WHERE claim_id=?",(claim_id,)).fetchone()
            if not row: raise KeyError("claim not found")
            if row["lifecycle_status"] in {"SUPERSEDED","ADJUDICATED"}: raise ValueError("closed claim cannot transition")
            if target=="SUPERSEDED" and actor_entity_id!=row["claimant_entity_id"]: raise PermissionError("only claimant may supersede its claim")
            db.execute("UPDATE claims SET lifecycle_status=?,updated_at_ms=? WHERE claim_id=?",(target,_now(),claim_id))
            event=self._event(db,claim_id,"claim."+target.lower(),actor_entity_id,{"reason":str(reason),"evidence":dict(evidence or {})})
        return {"claim_id":claim_id,"lifecycle_status":target,"event":event}
    @staticmethod
    def _row(row) -> dict:
        return {"claim_id":row["claim_id"],"asset_id":row["asset_id"],"claimant_entity_id":row["claimant_entity_id"],"right_type":row["right_type"],"share":{"numerator":row["share_num"],"denominator":row["share_den"]},"territory":row["territory"],"jurisdiction":row["jurisdiction"],"legal_basis":row["legal_basis"],"scope":json.loads(row["scope_json"]),"evidence":json.loads(row["evidence_json"]),"evidence_origin":row["evidence_origin"],"effective_at_ms":row["effective_at_ms"],"expires_at_ms":row["expires_at_ms"],"verification_level":row["verification_level"],"lifecycle_status":row["lifecycle_status"],"supersedes_claim_id":row["supersedes_claim_id"],"created_at_ms":row["created_at_ms"],"updated_at_ms":row["updated_at_ms"]}

    def claims_for_asset(self,asset_id: str) -> list[dict]:
        with self._connect() as db: rows=db.execute("SELECT * FROM claims WHERE asset_id=? ORDER BY created_at_ms,claim_id",(str(asset_id),)).fetchall()
        return [self._row(r) for r in rows]

    def verify_record_signature(self,claim_id: str) -> bool:
        with self._connect() as db: row=db.execute("SELECT * FROM claims WHERE claim_id=?",(claim_id,)).fetchone()
        if not row: return False
        item=self._row(row)
        body={"schema":"entity-rights-claim-v2","claim_id":item["claim_id"],"asset_id":item["asset_id"],"claimant_entity_id":item["claimant_entity_id"],"right_type":item["right_type"],"share":item["share"],"territory":item["territory"],"jurisdiction":item["jurisdiction"],"legal_basis":item["legal_basis"],"scope":item["scope"],"evidence":item["evidence"],"evidence_origin":item["evidence_origin"],"effective_at_ms":item["effective_at_ms"],"expires_at_ms":item["expires_at_ms"],"verification_level":"SELF_ASSERTED","lifecycle_status":"ACTIVE","supersedes_claim_id":item["supersedes_claim_id"]}
        sig=json.loads(row["signature_json"]); manifest=self.identity.load_manifest(item["claimant_entity_id"])
        return bool(self.identity.verify_signature(manifest,body,sig))

    def can_license(self,claimant_entity_id: str,asset_id: str) -> dict:
        now=_now(); claims=self.claims_for_asset(asset_id); eligible=[]; blocked=[]
        for claim in claims:
            if claim["claimant_entity_id"]!=claimant_entity_id or claim["right_type"] not in LICENSING_RIGHTS: continue
            if claim["expires_at_ms"] and int(claim["expires_at_ms"])<=now: blocked.append(dict(claim,reason="expired")); continue
            if claim["lifecycle_status"]!="ACTIVE": blocked.append(dict(claim,reason="not_active")); continue
            if claim["evidence_origin"] in {"UNKNOWN","DERIVED_INFERENCE"}: blocked.append(dict(claim,reason="insufficient_evidence_origin")); continue
            eligible.append(claim)
        return {"allowed":bool(eligible),"basis":"RECORDED_RIGHTS_CLAIMS_NOT_LEGAL_ADJUDICATION","eligible_claims":eligible,"blocked_claims":blocked}
    def status(self) -> dict:
        with self._connect() as db:
            count=db.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
            conflicts=db.execute("SELECT COUNT(*) FROM claims WHERE lifecycle_status IN ('CHALLENGED','DISPUTED')").fetchone()[0]
        return {"ready":True,"schema":"entity-rights-claims-graph-v2","claims":int(count),"challenged_or_disputed":int(conflicts),"many_to_many":True,"fractional_share":True,"territory_and_jurisdiction":True,"signatures_prove_assertions_not_truth":True,"provenance_distinct_from_rights":True}
