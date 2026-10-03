from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
from typing import Any
import hashlib, importlib.util, json, sqlite3, time

OPEN_ECONOMY_PROFILE="ENTITY_OPEN_DATA_ECONOMY"
OPEN_ECONOMY_VERSION="1.0.0"

CONSTITUTION={
    "everyone_can_participate": True,
    "registration_is_not_ownership": True,
    "rights_not_copies_are_economic_object": True,
    "users_choose_retained_and_offered_rights": True,
    "bounded_right_supply_supported": True,
    "markets_determine_price": True,
    "transferability_must_be_explicit": True,
    "participant_portfolios_supported": True,
    "contributor_pools_supported": True,
    "fiat_settlement_supported": True,
    "cryptocurrency_required": False,
    "gas_required": False,
    "protocol_tax_bps": 0,
    "automatic_btg_royalty_bps": 0,
    "issuer_neutral": True,
    "provider_neutral": True,
    "hidden_protocol_privilege": False,
}

PRIVACY_PROFILES={
    "PUBLIC_PROVENANCE","SELECTIVE_DISCLOSURE","CONFIDENTIAL_PROVENANCE","RESTRICTED_DISCLOSURE"
}

def now_ms()->int: return int(time.time()*1000)
def canon(v:Any)->bytes:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()
def sha(v:Any)->str:
    return hashlib.sha256(v if isinstance(v,(bytes,bytearray)) else canon(v)).hexdigest()
def require_sha256(v:str,name:str)->str:
    s=str(v or "").lower()
    if len(s)!=64 or any(c not in "0123456789abcdef" for c in s):
        raise ValueError(f"{name} must be lowercase SHA-256")
    return s

class OpenEconomyConstitution:
    @staticmethod
    def status()->dict:
        return {
            "schema":"entity-open-data-economy-constitution-v1",
            "profile":OPEN_ECONOMY_PROFILE,
            "version":OPEN_ECONOMY_VERSION,
            **CONSTITUTION,
        }

    @staticmethod
    def validate_runtime_claims(claims:dict)->dict:
        failures=[]
        c=dict(claims or {})
        if c.get("protocol_tax_bps",0)!=0: failures.append("protocol_tax_must_be_zero")
        if c.get("cryptocurrency_required",False) is not False: failures.append("mandatory_crypto_prohibited")
        if c.get("gas_required",False) is not False: failures.append("gas_prohibited")
        if c.get("automatic_btg_royalty_bps",0)!=0: failures.append("automatic_btg_royalty_prohibited")
        if c.get("issuer_neutral",True) is not True: failures.append("issuer_neutrality_required")
        if c.get("provider_neutral",True) is not True: failures.append("provider_neutrality_required")
        if c.get("registration_is_ownership",False) is True: failures.append("registration_cannot_create_ownership")
        return {"valid":not failures,"failures":failures,"constitution":OpenEconomyConstitution.status()}

class CreateMyDCOService:
    """Human-facing issuance planner. It creates a canonical plan, not ownership.

    Canonical registration/passport/EEP issuance remains in the existing ENTITY stores.
    The issuer/controller is supplied by the caller; BTG has no special path.
    """
    def __init__(self,state_dir:str|Path):
        self.root=Path(state_dir)/"open_economy"; self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/"create_my_dco.sqlite"; self._init()

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
            CREATE TABLE IF NOT EXISTS issuance_drafts(
              draft_id TEXT PRIMARY KEY,issuer_entity_id TEXT NOT NULL,name TEXT NOT NULL,
              asset_class TEXT NOT NULL,content_sha256 TEXT NOT NULL,provenance_root TEXT NOT NULL,
              authority_evidence_sha256 TEXT NOT NULL,privacy_profile TEXT NOT NULL,
              plan_sha256 TEXT NOT NULL,plan_json TEXT NOT NULL,status TEXT NOT NULL,
              created_at_ms INTEGER NOT NULL);
            CREATE INDEX IF NOT EXISTS idx_issuance_issuer ON issuance_drafts(issuer_entity_id,created_at_ms);
            """)

    @staticmethod
    def _normalize_right(right:dict,offered:bool)->dict:
        r=dict(right or {})
        action=str(r.get("action") or "").upper().strip()
        if not action: raise ValueError("right action required")
        q=r.get("quantity")
        if offered and (type(q) is not int or q<1): raise ValueError("offered right quantity must be positive integer")
        if not offered and q is not None and (type(q) is not int or q<1): raise ValueError("retained right quantity must be positive")
        duration=r.get("duration_ms")
        if duration is not None and (type(duration) is not int or duration<1): raise ValueError("duration_ms must be positive")
        return {
            "action":action,
            "quantity":q,
            "duration_ms":duration,
            "transferable":bool(r.get("transferable",False)),
            "derivation_allowed":bool(r.get("derivation_allowed",False)),
            "raw_transfer_allowed":bool(r.get("raw_transfer_allowed",False)),
            "commercial_use_allowed":bool(r.get("commercial_use_allowed",False)),
            "jurisdiction":None if r.get("jurisdiction") in {None,""} else str(r.get("jurisdiction")).upper(),
            "conditions":dict(r.get("conditions") or {}),
            "obligations":sorted({str(x) for x in (r.get("obligations") or [])}),
        }

    def create_draft(self,*,issuer_entity_id:str,name:str,asset_class:str,
                     content_sha256:str,provenance_root:str,authority_evidence_sha256:str,
                     privacy_profile:str,retained_rights:list[dict],offered_rights:list[dict],
                     description:str="",metadata:dict|None=None)->dict:
        issuer=str(issuer_entity_id or "").strip()
        if not issuer: raise ValueError("issuer/controller entity required")
        privacy=str(privacy_profile).upper()
        if privacy not in PRIVACY_PROFILES: raise ValueError("unsupported privacy profile")
        retained=[self._normalize_right(x,False) for x in retained_rights]
        offered=[self._normalize_right(x,True) for x in offered_rights]
        if not retained and not offered: raise ValueError("at least one retained or offered right required")
        # A right cannot simultaneously be unrestricted retained and offered under identical action/bounds.
        plan={
            "schema":"entity-create-my-dco-plan-v1",
            "issuer_entity_id":issuer,
            "controller_entity_id":issuer,
            "name":str(name).strip(),
            "description":str(description),
            "asset_class":str(asset_class).upper(),
            "content_sha256":require_sha256(content_sha256,"content_sha256"),
            "provenance_root":require_sha256(provenance_root,"provenance_root"),
            "authority_evidence_sha256":require_sha256(authority_evidence_sha256,"authority_evidence_sha256"),
            "privacy_profile":privacy,
            "retained_rights":retained,
            "offered_rights":offered,
            "metadata":dict(metadata or {}),
            "registration_is_not_ownership":True,
            "ownership_or_control_claim_requires_authority_evidence":True,
            "underlying_bytes_need_not_transfer":True,
            "rights_are_economic_object":True,
            "protocol_tax_bps":0,
            "automatic_btg_royalty_bps":0,
            "cryptocurrency_required":False,
            "gas_required":False,
            "issuer_neutral":True,
            "provider_neutral":True,
            "created_at_ms":now_ms(),
        }
        if not plan["name"]: raise ValueError("name required")
        psha=sha({k:v for k,v in plan.items() if k!="created_at_ms"})
        did="dcodraft-"+psha[:24]
        body={**plan,"draft_id":did,"plan_sha256":psha,"status":"DRAFT"}
        with self._db(True) as db:
            prior=db.execute("SELECT plan_sha256 FROM issuance_drafts WHERE draft_id=?",(did,)).fetchone()
            if prior and prior["plan_sha256"]!=psha: raise ValueError("draft hash conflict")
            db.execute("""INSERT OR IGNORE INTO issuance_drafts
                          VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                       (did,issuer,plan["name"],plan["asset_class"],plan["content_sha256"],plan["provenance_root"],
                        plan["authority_evidence_sha256"],privacy,psha,json.dumps(body,sort_keys=True),"DRAFT",plan["created_at_ms"]))
        return body

    def draft(self,draft_id:str)->dict:
        with self._db() as db:
            row=db.execute("SELECT plan_json FROM issuance_drafts WHERE draft_id=?",(str(draft_id),)).fetchone()
        if not row: raise KeyError("DCO issuance draft not found")
        return json.loads(row["plan_json"])

    @staticmethod
    def user_experience_schema()->dict:
        return {
            "schema":"entity-create-my-dco-user-experience-v1",
            "steps":[
                {"id":"WHAT_IS_IT","prompt":"What data or information asset do you control?"},
                {"id":"AUTHORITY","prompt":"What gives you authority to offer rights in it?"},
                {"id":"PROVENANCE","prompt":"Provide or generate provenance evidence."},
                {"id":"PRIVACY","prompt":"What information remains private?","choices":sorted(PRIVACY_PROFILES)},
                {"id":"RETAIN","prompt":"Which rights do you keep?"},
                {"id":"OFFER","prompt":"Which rights do you want to make available?"},
                {"id":"BOUNDS","prompt":"How many rights, for how long, and with what restrictions?"},
                {"id":"REVIEW","prompt":"Review before DCO/passport/instrument issuance."},
            ],
            "internal_terms_hidden_from_normal_user":["EEP","EOPP","BTDU"],
            "registration_is_not_ownership":True,
        }

class ParticipantPortfolioView:
    """Consumer-facing transformation of an existing PARTICIPANT wallet snapshot."""
    @staticmethod
    def simplify(snapshot:dict)->dict:
        if snapshot.get("schema")!="entity-economic-wallet-snapshot-v1":
            raise ValueError("participant wallet snapshot required")
        w=dict(snapshot.get("wallet") or {})
        if str(w.get("wallet_type")).upper()!="PARTICIPANT":
            raise ValueError("normal participant wallet required")
        positions=[]
        held=offered=licensed=transferred=0
        for p in snapshot.get("positions") or []:
            rights=dict(p.get("rights") or {})
            units=int(p.get("units") or 0); held+=units
            ask=(p.get("market") or {}).get("ask")
            positions.append({
                "instrument_id":p.get("instrument_id"),
                "underlying_object_id":p.get("underlying_object_id"),
                "product":rights.get("display_name") or rights.get("product_code") or p.get("instrument_class"),
                "symbol":rights.get("symbol"),
                "rights":rights.get("actions") or [],
                "units":units,
                "transferable":bool(p.get("transferable")),
                "settlement_currency":p.get("settlement_currency"),
                "last":(p.get("market") or {}).get("last"),
                "bid":(p.get("market") or {}).get("bid"),
                "ask":ask,
                "observed_market_value":p.get("market_value_amount_units"),
                "usage_units_recorded":int(p.get("usage_units_recorded") or 0),
                "not_accounting_fair_value":True,
            })
        for o in snapshot.get("orders") or []:
            if o.get("status") in {"OPEN","PARTIAL"} and o.get("side")=="SELL": offered+=int(o.get("remaining") or 0)
        for e in snapshot.get("entitlements") or []: licensed+=int(e.get("quantity") or 0)
        # "transferred" is measured from completed outgoing position history elsewhere; do not infer from current balance.
        obligations=dict(snapshot.get("obligations") or {})
        return {
            "schema":"entity-my-data-portfolio-v1",
            "owner_entity_id":w.get("owner_entity_id"),
            "display_name":w.get("name"),
            "positions":positions,
            "summary":{
                "rights_held":held,
                "rights_currently_offered":offered,
                "rights_licensed_or_entitled":licensed,
                "rights_transferred":transferred,
                "rights_producing_revenue":len(obligations.get("receivable") or []),
                "economic_obligations":obligations.get("summary") or {},
            },
            "portfolio_by_currency":snapshot.get("portfolio_by_currency") or {},
            "fiat_custody":snapshot.get("fiat_custody"),
            "market_value_policy":snapshot.get("market_value_policy"),
            "protocol_tax_bps":0,
            "cryptocurrency_required":False,
            "legal_classification_not_inferred":True,
        }

class RightsMarketDiscovery:
    """Rights-first search across active EEP listings.

    Search criteria describe desired rights, not a preferred issuer. The result exposes
    observable quotes/trades but does not rank by issuer or infer fair value.
    """
    def __init__(self,exchange_db:str|Path):
        self.path=Path(exchange_db)

    @contextmanager
    def _db(self):
        db=sqlite3.connect(self.path,timeout=30.0); db.row_factory=sqlite3.Row
        try: yield db
        finally: db.close()

    @staticmethod
    def _match_rights(rights:dict,criteria:dict)->bool:
        actions={str(x).upper() for x in (rights.get("actions") or [])}
        required={str(x).upper() for x in (criteria.get("actions") or [])}
        if not required.issubset(actions): return False
        if criteria.get("commercial_use_required") and not (
            rights.get("commercial_use_allowed") is True or
            bool({"COMMERCIALIZE","INFER","TRAIN"} & actions)
        ): return False
        if criteria.get("derivative_models_required") and not (
            rights.get("derivation_allowed") is True or "DERIVE" in actions
        ): return False
        if criteria.get("raw_transfer_required") is False and rights.get("raw_dataset_delivery") is True:
            return False
        if criteria.get("raw_transfer_required") is True and not (
            rights.get("raw_dataset_delivery") is True or rights.get("raw_transfer_allowed") is True
        ): return False
        region=criteria.get("region")
        if region:
            candidates={str(rights.get(k) or "").upper() for k in ("jurisdiction","exclusive_region","region")}
            if str(region).upper() not in candidates and "GLOBAL" not in candidates and "" not in candidates:
                return False
        asset_class=criteria.get("asset_class")
        if asset_class and str(rights.get("asset_class") or rights.get("product_family") or "").upper()!=str(asset_class).upper():
            return False
        return True

    def search(self,criteria:dict,limit:int=100)->dict:
        c=dict(criteria or {})
        out=[]
        with self._db() as db:
            rows=db.execute("""SELECT l.listing_id,l.venue_id,l.instrument_id,l.lister,l.min_lot,l.tick_size,
                              i.issuer,i.underlying_object_id,i.instrument_class,i.rights_json,i.total_units,
                              i.transferable,i.duration_ms,i.settlement_currency,i.delivery_mode,
                              v.name venue_name,v.jurisdiction venue_jurisdiction
                              FROM listings l
                              JOIN instruments i ON i.instrument_id=l.instrument_id
                              JOIN venues v ON v.venue_id=l.venue_id
                              WHERE l.status='ACTIVE' AND i.status='ACTIVE'
                              ORDER BY l.created_at_ms,l.listing_id""").fetchall()
            for row in rows:
                d=dict(row); rights=json.loads(d.pop("rights_json") or "{}")
                if not self._match_rights(rights,c): continue
                iid=d["instrument_id"]
                last=db.execute("""SELECT price,quantity,created_at_ms FROM trades
                                   WHERE instrument_id=? AND status='SETTLED'
                                   ORDER BY created_at_ms DESC,trade_id DESC LIMIT 1""",(iid,)).fetchone()
                bid=db.execute("""SELECT MAX(limit_price) p FROM orders WHERE instrument_id=?
                                  AND side='BUY' AND status IN ('OPEN','PARTIAL')""",(iid,)).fetchone()
                ask=db.execute("""SELECT MIN(limit_price) p FROM orders WHERE instrument_id=?
                                  AND side='SELL' AND status IN ('OPEN','PARTIAL')""",(iid,)).fetchone()
                out.append({
                    **d,"rights":rights,
                    "market":{
                        "last":None if not last else int(last["price"]),
                        "last_quantity":None if not last else int(last["quantity"]),
                        "last_at_ms":None if not last else int(last["created_at_ms"]),
                        "bid":None if not bid or bid["p"] is None else int(bid["p"]),
                        "ask":None if not ask or ask["p"] is None else int(ask["p"]),
                    },
                    "issuer_is_ranking_factor":False,
                    "market_price_is_not_protocol_fair_value":True,
                })
                if len(out)>=int(limit): break
        return {
            "schema":"entity-data-rights-market-search-v1",
            "criteria":c,"results":out,"result_count":len(out),
            "available_actions":["BUY","BID","REQUEST_QUOTE"],
            "rights_not_copies_are_market_object":True,
            "issuer_neutral":True,"provider_neutral":True,
            "protocol_tax_bps":0,"cryptocurrency_required":False,
        }

class DataPoolManager:
    """Provider-neutral contributor pools with deterministic economic allocation.

    It records contribution weight/provenance and produces an allocation plan. It does not
    silently transfer ownership, settle fiat, or create an automatic protocol fee.
    """
    def __init__(self,state_dir:str|Path):
        self.root=Path(state_dir)/"open_economy"; self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/"data_pools.sqlite"; self._init()

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
            CREATE TABLE IF NOT EXISTS pools(
              pool_id TEXT PRIMARY KEY,controller_entity_id TEXT NOT NULL,name TEXT NOT NULL,
              purpose TEXT NOT NULL,terms_sha256 TEXT NOT NULL,status TEXT NOT NULL,created_at_ms INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS contributions(
              pool_id TEXT NOT NULL,contributor_entity_id TEXT NOT NULL,dco_ref TEXT NOT NULL,
              contribution_ref TEXT NOT NULL,weight_units INTEGER NOT NULL,provenance_sha256 TEXT NOT NULL,
              rights_summary_json TEXT NOT NULL,status TEXT NOT NULL,created_at_ms INTEGER NOT NULL,
              PRIMARY KEY(pool_id,contribution_ref));
            """)

    def create_pool(self,controller_entity_id:str,name:str,purpose:str,terms_sha256:str)->dict:
        controller=str(controller_entity_id or "")
        if not controller: raise ValueError("controller required")
        terms=require_sha256(terms_sha256,"terms_sha256")
        body={"schema":"entity-data-pool-v1","controller_entity_id":controller,"name":str(name),
              "purpose":str(purpose),"terms_sha256":terms,"protocol_tax_bps":0,
              "automatic_btg_royalty_bps":0,"provider_neutral":True,"created_at_ms":now_ms()}
        pid="pool3-"+sha(body)[:24]; body["pool_id"]=pid
        with self._db(True) as db:
            db.execute("INSERT OR IGNORE INTO pools VALUES(?,?,?,?,?,?,?)",
                       (pid,controller,body["name"],body["purpose"],terms,"ACTIVE",body["created_at_ms"]))
        return body

    def add_contribution(self,pool_id:str,contributor_entity_id:str,dco_ref:str,contribution_ref:str,
                         weight_units:int,provenance_sha256:str,rights_summary:dict)->dict:
        w=int(weight_units)
        if w<1: raise ValueError("weight_units must be positive")
        prov=require_sha256(provenance_sha256,"provenance_sha256")
        with self._db() as db:
            if not db.execute("SELECT 1 FROM pools WHERE pool_id=? AND status='ACTIVE'",(str(pool_id),)).fetchone():
                raise KeyError("active pool not found")
        body={"schema":"entity-data-pool-contribution-v1","pool_id":str(pool_id),
              "contributor_entity_id":str(contributor_entity_id),"dco_ref":str(dco_ref),
              "contribution_ref":str(contribution_ref),"weight_units":w,
              "provenance_sha256":prov,"rights_summary":dict(rights_summary or {}),
              "registration_is_not_ownership":True,"created_at_ms":now_ms()}
        with self._db(True) as db:
            db.execute("INSERT INTO contributions VALUES(?,?,?,?,?,?,?,?,?)",
                       (body["pool_id"],body["contributor_entity_id"],body["dco_ref"],body["contribution_ref"],
                        w,prov,json.dumps(body["rights_summary"],sort_keys=True),"ACTIVE",body["created_at_ms"]))
        return body

    def allocation_plan(self,pool_id:str,gross_amount_units:int,currency:str,evidence_sha256:str)->dict:
        gross=int(gross_amount_units)
        if gross<0: raise ValueError("gross amount must be non-negative")
        ev=require_sha256(evidence_sha256,"evidence_sha256")
        with self._db() as db:
            rows=[dict(r) for r in db.execute("""SELECT contributor_entity_id,contribution_ref,weight_units
                    FROM contributions WHERE pool_id=? AND status='ACTIVE'
                    ORDER BY contributor_entity_id,contribution_ref""",(str(pool_id),)).fetchall()]
        if not rows: raise ValueError("pool has no active contributors")
        total=sum(int(r["weight_units"]) for r in rows)
        exact=[]
        floor_total=0
        for r in rows:
            numerator=gross*int(r["weight_units"])
            floor=numerator//total; rem=numerator%total; floor_total+=floor
            exact.append({**r,"amount_units":floor,"remainder":rem})
        residual=gross-floor_total
        for r in sorted(exact,key=lambda x:(-x["remainder"],x["contributor_entity_id"],x["contribution_ref"]))[:residual]:
            r["amount_units"]+=1
        allocations=[{"contributor_entity_id":r["contributor_entity_id"],"contribution_ref":r["contribution_ref"],
                      "weight_units":int(r["weight_units"]),"amount_units":int(r["amount_units"])}
                     for r in exact]
        return {
            "schema":"entity-data-pool-allocation-plan-v1","pool_id":str(pool_id),
            "gross_amount_units":gross,"currency":str(currency).upper(),"evidence_sha256":ev,
            "total_weight_units":total,"allocations":allocations,
            "allocated_amount_units":sum(x["amount_units"] for x in allocations),
            "protocol_tax_bps":0,"automatic_btg_royalty_bps":0,
            "fiat_settlement_occurs_externally":True,
            "allocation_plan_is_not_settlement":True,
            "provider_neutral":True,
        }

class OptionalServiceProviderRegistry:
    """Open registry for optional market/certification/API/infrastructure providers."""
    ALLOWED={"MARKET_HOSTING","CERTIFICATION","VERIFICATION","MANAGED_INFRASTRUCTURE","ENTERPRISE_API",
             "ANALYTICS","CUSTODY_CONNECTIVITY","MARKET_DATA","SPECIALIZED_TOOLING"}
    def __init__(self,state_dir:str|Path):
        self.root=Path(state_dir)/"open_economy"; self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/"service_providers.sqlite"; self._init()

    @contextmanager
    def _db(self,write=False):
        db=sqlite3.connect(self.path,timeout=30.0); db.row_factory=sqlite3.Row
        try:
            yield db
            if write: db.commit()
        except Exception:
            if write: db.rollback()
            raise
        finally: db.close()

    def _init(self):
        with self._db(True) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS providers(
              provider_entity_id TEXT NOT NULL,service_type TEXT NOT NULL,terms_sha256 TEXT NOT NULL,
              status TEXT NOT NULL,created_at_ms INTEGER NOT NULL,
              PRIMARY KEY(provider_entity_id,service_type))""")

    def register(self,provider_entity_id:str,service_type:str,terms_sha256:str)->dict:
        service=str(service_type).upper()
        if service not in self.ALLOWED: raise ValueError("unsupported optional service")
        terms=require_sha256(terms_sha256,"terms_sha256")
        body={"schema":"entity-optional-service-provider-v1","provider_entity_id":str(provider_entity_id),
              "service_type":service,"terms_sha256":terms,"protocol_privilege":False,
              "exclusive_provider":False,"created_at_ms":now_ms()}
        with self._db(True) as db:
            db.execute("INSERT OR REPLACE INTO providers VALUES(?,?,?,?,?)",
                       (body["provider_entity_id"],service,terms,"ACTIVE",body["created_at_ms"]))
        return body

    def providers(self,service_type:str)->list[dict]:
        service=str(service_type).upper()
        with self._db() as db:
            rows=[dict(r) for r in db.execute("""SELECT provider_entity_id,service_type,terms_sha256,status,created_at_ms
                        FROM providers WHERE service_type=? AND status='ACTIVE'
                        ORDER BY provider_entity_id""",(service,)).fetchall()]
        return [{**r,"protocol_privilege":False,"exclusive_provider":False} for r in rows]
