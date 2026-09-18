from __future__ import annotations
from pathlib import Path
from contextlib import contextmanager
from threading import RLock
import json, secrets, sqlite3, time

SETTLEMENT_STATES={"CREATED","AUTHORIZED","RESERVED","EXECUTING","CONFIRMED","FAILED","REVERSED","REFUNDED","DISPUTED","RECONCILED"}
VALUE_STATES=("POTENTIAL","OFFER","CONTRACTED","ACCRUED","SETTLED","REALIZED")
VALUE_NEXT={VALUE_STATES[i]:VALUE_STATES[i+1] for i in range(len(VALUE_STATES)-1)}
EVIDENCE_LEVELS={"PROVIDER_CONFIRMED","COUNTERPARTY_ATTESTED","MANUALLY_ENTERED","UNVERIFIED"}

def _now(): return int(time.time()*1000)
def _id(prefix): return f"{prefix}-"+secrets.token_hex(20)

class SettlementEngine:
    """Authoritative replay-safe double-entry settlement engine."""
    def __init__(self,state_dir: str|Path,identity,local_controller_check=None,external_payment_verifier=None):
        self.root=Path(state_dir)/"settlement"; self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/"settlement.sqlite"; self.identity=identity
        self.local_controller_check=local_controller_check or self._default_local
        self.external_payment_verifier=external_payment_verifier
        self._lock=RLock(); self._init_db()

    def _default_local(self,entity_id: str) -> bool:
        try: self.identity.load_manifest(entity_id); return True
        except Exception: return False

    def _require_local(self,entity_id: str):
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
            db.execute("CREATE TABLE IF NOT EXISTS settlements(settlement_id TEXT PRIMARY KEY,payer_entity_id TEXT NOT NULL,payee_entity_id TEXT NOT NULL,amount_units INTEGER NOT NULL,currency TEXT NOT NULL,obligation_ref TEXT NOT NULL,transaction_nonce TEXT UNIQUE NOT NULL,settlement_kind TEXT NOT NULL,state TEXT NOT NULL,evidence_json TEXT NOT NULL,money_movement_verified INTEGER NOT NULL,created_at_ms INTEGER NOT NULL,updated_at_ms INTEGER NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS postings(entry_id TEXT PRIMARY KEY,settlement_id TEXT NOT NULL,entity_id TEXT NOT NULL,direction TEXT NOT NULL,amount_units INTEGER NOT NULL,currency TEXT NOT NULL,posting_kind TEXT NOT NULL,created_at_ms INTEGER NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS settlement_events(event_id TEXT PRIMARY KEY,settlement_id TEXT NOT NULL,event_type TEXT NOT NULL,actor_entity_id TEXT NOT NULL,from_state TEXT,to_state TEXT,payload_json TEXT NOT NULL,signature_json TEXT NOT NULL,created_at_ms INTEGER NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS value_records(value_id TEXT PRIMARY KEY,controller_entity_id TEXT NOT NULL,asset_ref TEXT NOT NULL,amount_units INTEGER NOT NULL,currency TEXT NOT NULL,state TEXT NOT NULL,settlement_id TEXT,realized_external INTEGER NOT NULL,created_at_ms INTEGER NOT NULL,updated_at_ms INTEGER NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS royalty_plans(plan_id TEXT PRIMARY KEY,controller_entity_id TEXT NOT NULL,version INTEGER NOT NULL,shares_json TEXT NOT NULL,status TEXT NOT NULL,created_at_ms INTEGER NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS royalty_allocations(allocation_id TEXT PRIMARY KEY,plan_id TEXT NOT NULL,settlement_id TEXT UNIQUE NOT NULL,amount_units INTEGER NOT NULL,currency TEXT NOT NULL,distribution_json TEXT NOT NULL,created_at_ms INTEGER NOT NULL)")
    def _event(self,db,settlement_id,event_type,actor,from_state,to_state,payload):
        event_id=_id("sev1"); now=_now(); body={"schema":"entity-settlement-event-v2","event_id":event_id,"settlement_id":settlement_id,"event_type":event_type,"actor_entity_id":actor,"from_state":from_state,"to_state":to_state,"payload":dict(payload or {}),"created_at_ms":now}
        sig=self.identity.sign(actor,body)
        db.execute("INSERT INTO settlement_events VALUES(?,?,?,?,?,?,?,?,?)",(event_id,settlement_id,event_type,actor,from_state,to_state,json.dumps(body["payload"],sort_keys=True),json.dumps(sig,sort_keys=True),now))
        return dict(body,signature=sig)

    def create(self,payer_entity_id: str,payee_entity_id: str,*,amount_units: int,currency: str,obligation_ref: str,transaction_nonce: str,settlement_kind: str="INTERNAL_ACCOUNTING") -> dict:
        self._require_local(payer_entity_id)
        amount=int(amount_units); nonce=str(transaction_nonce or "").strip(); kind=str(settlement_kind or "").upper(); unit=str(currency or "").upper()
        if amount<=0: raise ValueError("settlement amount must be positive")
        if not nonce: raise ValueError("transaction_nonce required")
        if not unit: raise ValueError("currency required")
        if kind not in {"INTERNAL_ACCOUNTING","EXTERNAL_PAYMENT"}: raise ValueError("unsupported settlement_kind")
        settlement_id=_id("set1"); now=_now()
        with self._lock,self._connect() as db:
            try: db.execute("INSERT INTO settlements VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",(settlement_id,payer_entity_id,payee_entity_id,amount,unit,str(obligation_ref),nonce,kind,"CREATED","{}",0,now,now))
            except sqlite3.IntegrityError as exc: raise ValueError("duplicate/replayed transaction_nonce") from exc
            event=self._event(db,settlement_id,"SETTLEMENT_CREATED",payer_entity_id,None,"CREATED",{"amount_units":amount,"currency":unit,"obligation_ref":str(obligation_ref),"settlement_kind":kind})
        return {"settlement_id":settlement_id,"state":"CREATED","event":event}

    def _load(self,settlement_id: str):
        with self._connect() as db: row=db.execute("SELECT * FROM settlements WHERE settlement_id=?",(settlement_id,)).fetchone()
        if not row: raise KeyError("settlement not found")
        return row
    def _transition(self,row,actor: str,to_state: str,event_type: str,payload: dict|None=None) -> dict:
        from_state=str(row["state"]); now=_now()
        if to_state not in SETTLEMENT_STATES: raise ValueError("unsupported settlement state")
        with self._lock,self._connect() as db:
            current=db.execute("SELECT state FROM settlements WHERE settlement_id=?",(row["settlement_id"],)).fetchone()
            if not current or current["state"]!=from_state: raise RuntimeError("settlement state changed concurrently")
            db.execute("UPDATE settlements SET state=?,updated_at_ms=? WHERE settlement_id=?",(to_state,now,row["settlement_id"]))
            event=self._event(db,row["settlement_id"],event_type,actor,from_state,to_state,dict(payload or {}))
        return {"settlement_id":row["settlement_id"],"state":to_state,"event":event}

    def authorize(self,payer_entity_id: str,settlement_id: str) -> dict:
        row=self._load(settlement_id)
        if row["payer_entity_id"]!=payer_entity_id: raise PermissionError("only payer may authorize")
        self._require_local(payer_entity_id)
        if row["state"]!="CREATED": raise ValueError("settlement must be CREATED")
        return self._transition(row,payer_entity_id,"AUTHORIZED","SETTLEMENT_AUTHORIZED")

    def begin_execution(self,payer_entity_id: str,settlement_id: str) -> dict:
        row=self._load(settlement_id)
        if row["payer_entity_id"]!=payer_entity_id: raise PermissionError("only payer may execute")
        self._require_local(payer_entity_id)
        if row["state"] not in {"AUTHORIZED","RESERVED"}: raise ValueError("settlement must be AUTHORIZED or RESERVED")
        return self._transition(row,payer_entity_id,"EXECUTING","SETTLEMENT_EXECUTING")

    def record_external_evidence(self,payer_entity_id: str,settlement_id: str,evidence_level: str,evidence: dict) -> dict:
        row=self._load(settlement_id)
        if row["payer_entity_id"]!=payer_entity_id: raise PermissionError("payer authority required")
        self._require_local(payer_entity_id); level=str(evidence_level).upper(); supplied=dict(evidence or {})
        if level not in EVIDENCE_LEVELS: raise ValueError("unsupported payment evidence level")
        if level=="PROVIDER_CONFIRMED" and self.external_payment_verifier is not None:
            verifier=self.external_payment_verifier
            if hasattr(verifier,"verify"):
                ok=verifier.verify(supplied,expected_subject=str(row["payee_entity_id"]),allowed_evidence_types={"PAYMENT_SETTLEMENT_CONFIRMATION"})
            else:
                ok=bool(verifier(supplied))
            if ok is not True: raise PermissionError("provider-confirmed payment evidence failed external cryptographic verification")
        package={"level":level,"evidence":supplied,"recorded_at_ms":_now(),"external_cryptographic_verification_required":bool(level=="PROVIDER_CONFIRMED" and self.external_payment_verifier is not None)}
        with self._lock,self._connect() as db:
            db.execute("UPDATE settlements SET evidence_json=?,updated_at_ms=? WHERE settlement_id=?",(json.dumps(package,sort_keys=True),_now(),settlement_id))
            event=self._event(db,settlement_id,"PAYMENT_EVIDENCE_RECORDED",payer_entity_id,row["state"],row["state"],package)
        return {"settlement_id":settlement_id,"evidence":package,"event":event}

    def confirm(self,payer_entity_id: str,settlement_id: str) -> dict:
        row=self._load(settlement_id)
        if row["payer_entity_id"]!=payer_entity_id: raise PermissionError("payer authority required")
        self._require_local(payer_entity_id)
        if row["state"] not in {"AUTHORIZED","RESERVED","EXECUTING"}: raise ValueError("settlement not confirmable")
        evidence=json.loads(row["evidence_json"] or "{}"); kind=row["settlement_kind"]
        if kind=="EXTERNAL_PAYMENT" and evidence.get("level")!="PROVIDER_CONFIRMED":
            raise PermissionError("external payment confirmation requires provider-confirmed evidence")
        if kind=="EXTERNAL_PAYMENT" and self.external_payment_verifier is not None and evidence.get("external_cryptographic_verification_required") is not True:
            raise PermissionError("external payment confirmation requires cryptographically verified provider evidence")
        movement_verified=kind=="EXTERNAL_PAYMENT" and evidence.get("level")=="PROVIDER_CONFIRMED" and (self.external_payment_verifier is None or evidence.get("external_cryptographic_verification_required") is True)
        now=_now(); amount=int(row["amount_units"]); currency=row["currency"]
        with self._lock,self._connect() as db:
            current=db.execute("SELECT state FROM settlements WHERE settlement_id=?",(settlement_id,)).fetchone()
            if not current or current["state"]!=row["state"]: raise RuntimeError("settlement state changed concurrently")
            if db.execute("SELECT 1 FROM postings WHERE settlement_id=? AND posting_kind='FINAL' LIMIT 1",(settlement_id,)).fetchone(): raise RuntimeError("settlement already posted")
            db.execute("INSERT INTO postings VALUES(?,?,?,?,?,?,?,?)",(_id("post1"),settlement_id,row["payer_entity_id"],"DEBIT",amount,currency,"FINAL",now))
            db.execute("INSERT INTO postings VALUES(?,?,?,?,?,?,?,?)",(_id("post1"),settlement_id,row["payee_entity_id"],"CREDIT",amount,currency,"FINAL",now))
            db.execute("UPDATE settlements SET state='CONFIRMED',money_movement_verified=?,updated_at_ms=? WHERE settlement_id=?",(1 if movement_verified else 0,now,settlement_id))
            event=self._event(db,settlement_id,"SETTLEMENT_CONFIRMED",payer_entity_id,row["state"],"CONFIRMED",{"external_money_movement_verified":bool(movement_verified),"evidence_level":evidence.get("level")})
        return {"settlement_id":settlement_id,"state":"CONFIRMED","double_entry_balanced":True,"external_money_movement_verified":bool(movement_verified),"event":event}
    def compensate(self,actor_entity_id: str,settlement_id: str,*,refund: bool=False,reason: str="") -> dict:
        row=self._load(settlement_id)
        if actor_entity_id not in {row["payer_entity_id"],row["payee_entity_id"]}: raise PermissionError("settlement party required")
        self._require_local(actor_entity_id)
        if row["state"] not in {"CONFIRMED","DISPUTED"}: raise ValueError("only confirmed/disputed settlement may be compensated")
        target="REFUNDED" if refund else "REVERSED"; kind="REFUND" if refund else "REVERSAL"; now=_now(); amount=int(row["amount_units"]); currency=row["currency"]
        with self._lock,self._connect() as db:
            if db.execute("SELECT 1 FROM postings WHERE settlement_id=? AND posting_kind IN ('REVERSAL','REFUND') LIMIT 1",(settlement_id,)).fetchone(): raise RuntimeError("settlement already compensated")
            db.execute("INSERT INTO postings VALUES(?,?,?,?,?,?,?,?)",(_id("post1"),settlement_id,row["payer_entity_id"],"CREDIT",amount,currency,kind,now))
            db.execute("INSERT INTO postings VALUES(?,?,?,?,?,?,?,?)",(_id("post1"),settlement_id,row["payee_entity_id"],"DEBIT",amount,currency,kind,now))
            db.execute("UPDATE settlements SET state=?,updated_at_ms=? WHERE settlement_id=?",(target,now,settlement_id))
            event=self._event(db,settlement_id,f"SETTLEMENT_{target}",actor_entity_id,row["state"],target,{"reason":str(reason)[:2048],"compensating_entries":True})
        return {"settlement_id":settlement_id,"state":target,"compensating_entries":True,"event":event}

    def balance(self,entity_id: str,currency: str) -> dict:
        unit=str(currency).upper()
        with self._connect() as db:
            credits=int(db.execute("SELECT COALESCE(SUM(amount_units),0) FROM postings WHERE entity_id=? AND currency=? AND direction='CREDIT'",(entity_id,unit)).fetchone()[0])
            debits=int(db.execute("SELECT COALESCE(SUM(amount_units),0) FROM postings WHERE entity_id=? AND currency=? AND direction='DEBIT'",(entity_id,unit)).fetchone()[0])
        return {"entity_id":entity_id,"currency":unit,"credits":credits,"debits":debits,"net":credits-debits,"balanced_posting_model":True}

    def get(self,settlement_id: str) -> dict:
        row=self._load(settlement_id); out=dict(row); out["evidence"]=json.loads(out.pop("evidence_json") or "{}"); out["money_movement_verified"]=bool(out["money_movement_verified"]); return out
    def create_value_record(self,controller_entity_id: str,asset_ref: str,amount_units: int,currency: str) -> dict:
        self._require_local(controller_entity_id); amount=int(amount_units)
        if amount<0: raise ValueError("amount_units cannot be negative")
        value_id=_id("val1"); now=_now(); unit=str(currency).upper()
        with self._connect() as db:
            db.execute("INSERT INTO value_records VALUES(?,?,?,?,?,?,?,?,?,?)",(value_id,controller_entity_id,str(asset_ref),amount,unit,"POTENTIAL",None,0,now,now))
        return {"value_id":value_id,"state":"POTENTIAL","amount_units":amount,"currency":unit,"realized_external":False}

    def advance_value(self,controller_entity_id: str,value_id: str,target_state: str,*,settlement_id: str|None=None) -> dict:
        target=str(target_state or "").upper()
        with self._connect() as db: row=db.execute("SELECT * FROM value_records WHERE value_id=?",(value_id,)).fetchone()
        if not row: raise KeyError("value record not found")
        if row["controller_entity_id"]!=controller_entity_id: raise PermissionError("value controller mismatch")
        current=row["state"]
        if VALUE_NEXT.get(current)!=target: raise ValueError(f"invalid value transition {current}->{target}")
        realized_external=False; sid=settlement_id or row["settlement_id"]
        if target in {"SETTLED","REALIZED"}:
            if not sid: raise ValueError("settlement evidence required")
            settlement=self.get(sid)
            if settlement["state"] not in {"CONFIRMED","RECONCILED"}: raise ValueError("settlement is not final enough")
            if target=="REALIZED":
                if settlement["settlement_kind"]!="EXTERNAL_PAYMENT" or not settlement["money_movement_verified"]:
                    raise PermissionError("REALIZED monetary value requires verified external payment evidence")
                realized_external=True
        now=_now()
        with self._connect() as db:
            db.execute("UPDATE value_records SET state=?,settlement_id=?,realized_external=?,updated_at_ms=? WHERE value_id=?",(target,sid,1 if realized_external else int(row["realized_external"]),now,value_id))
        return {"value_id":value_id,"from_state":current,"state":target,"settlement_id":sid,"realized_external":bool(realized_external or row["realized_external"])}

    def get_value(self,value_id: str) -> dict:
        with self._connect() as db: row=db.execute("SELECT * FROM value_records WHERE value_id=?",(value_id,)).fetchone()
        if not row: raise KeyError("value record not found")
        out=dict(row); out["realized_external"]=bool(out["realized_external"]); return out
    def create_royalty_plan(self,controller_entity_id: str,shares_basis_points: dict[str,int],version: int=1) -> dict:
        self._require_local(controller_entity_id); shares={str(k):int(v) for k,v in dict(shares_basis_points or {}).items()}
        if not shares or any(v<0 for v in shares.values()) or sum(shares.values())!=10000: raise ValueError("royalty shares must sum to 10000 basis points")
        plan_id=_id("roy1"); now=_now()
        with self._connect() as db: db.execute("INSERT INTO royalty_plans VALUES(?,?,?,?,?,?)",(plan_id,controller_entity_id,int(version),json.dumps(shares,sort_keys=True),"ACTIVE",now))
        return {"plan_id":plan_id,"controller_entity_id":controller_entity_id,"version":int(version),"shares_basis_points":shares,"status":"ACTIVE"}

    def allocate_royalties(self,plan_id: str,settlement_id: str,amount_units: int,currency: str) -> dict:
        with self._connect() as db: plan=db.execute("SELECT * FROM royalty_plans WHERE plan_id=?",(plan_id,)).fetchone()
        if not plan or plan["status"]!="ACTIVE": raise KeyError("active royalty plan not found")
        amount=int(amount_units)
        if amount<0: raise ValueError("amount_units cannot be negative")
        shares=json.loads(plan["shares_json"]); ordered=sorted(shares.items())
        distribution={}; allocated=0
        for index,(entity_id,bps) in enumerate(ordered):
            units=(amount*int(bps))//10000
            distribution[entity_id]=units; allocated+=units
        remainder=amount-allocated
        for entity_id,_ in ordered[:remainder]: distribution[entity_id]+=1
        allocation_id=_id("alloc1"); now=_now(); unit=str(currency).upper()
        try:
            with self._connect() as db: db.execute("INSERT INTO royalty_allocations VALUES(?,?,?,?,?,?,?)",(allocation_id,plan_id,str(settlement_id),amount,unit,json.dumps(distribution,sort_keys=True),now))
        except sqlite3.IntegrityError as exc: raise ValueError("royalties already allocated for settlement") from exc
        return {"allocation_id":allocation_id,"plan_id":plan_id,"plan_version":int(plan["version"]),"settlement_id":str(settlement_id),"amount_units":amount,"currency":unit,"distribution":distribution,"allocated_total":sum(distribution.values())}

    def status(self) -> dict:
        with self._connect() as db:
            settlements=int(db.execute("SELECT COUNT(*) FROM settlements").fetchone()[0]); values=int(db.execute("SELECT COUNT(*) FROM value_records").fetchone()[0])
        return {"ready":True,"schema":"entity-canonical-economics-v1","replay_protection":True,"double_entry":True,"payer_payee_direction":True,"reversal_refund_compensation":True,"external_payment_requires_provider_confirmation":True,"value_states":list(VALUE_STATES),"internal_records_do_not_prove_external_money":True,"deterministic_royalties":True,"settlements":settlements,"value_records":values}
