from __future__ import annotations
from contextlib import contextmanager
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from threading import RLock
import hashlib, json, secrets, sqlite3, time

EVIDENCE_ORIGINS={"DIRECT_OBSERVATION","ENTITY_ASSERTION","COUNTERPARTY_ATTESTATION","EXTERNAL_AUTHORITATIVE_RECORD","DERIVED_INFERENCE","UNKNOWN"}
USAGE_ASSURANCE={"DECLARED","ENTITY_GATEWAY_OBSERVED","COUNTERPARTY_ATTESTED","ENVIRONMENT_ATTESTED"}
INSTRUMENT_CLASSES={"CORPORATE_EQUITY","DEBT_INSTRUMENT","OPTION_OR_WARRANT","CONVERTIBLE_INSTRUMENT","ROYALTY_INTEREST","CONTRACTUAL_REVENUE_INTEREST","NON_TRANSFERABLE_PARTICIPATION","INTERNAL_ACCOUNTING_UNIT","REGULATED_SECURITY","POTENTIALLY_REGULATED","CLASSIFICATION_UNKNOWN"}
MARKET_CLASSES={"TRADE","BID","ASK"}
def _now(): return int(time.time()*1000)
def _id(prefix): return f"{prefix}-"+secrets.token_hex(20)
def _canon(v): return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
def _sha(v): return hashlib.sha256(v if isinstance(v,(bytes,bytearray)) else _canon(v)).hexdigest()

class CorporateCapitalEngine:
    """ENTITY v2.1 authority for digital commodities, capital structure and capital-market evidence."""
    def __init__(self,state_dir,identity,*,event_ledger=None,settlement_engine=None,local_controller_check=None,external_authority_verifier=None):
        self.root=Path(state_dir)/"corporate_capital"; self.root.mkdir(parents=True,exist_ok=True); self.path=self.root/"corporate_capital.sqlite"
        self.identity=identity; self.event_ledger=event_ledger; self.settlement_engine=settlement_engine; self.local_controller_check=local_controller_check or self._default_local; self.external_authority_verifier=external_authority_verifier; self._lock=RLock(); self._init_db()
    def _default_local(self,entity_id):
        try: self.identity.load_manifest(entity_id); return True
        except Exception: return False
    def _require_local(self,entity_id):
        if not self.local_controller_check(entity_id): raise PermissionError("operation requires locally controlled corporate Entity")
    @contextmanager
    def _connect(self):
        db=sqlite3.connect(self.path,timeout=30); db.row_factory=sqlite3.Row
        try: yield db; db.commit()
        except Exception: db.rollback(); raise
        finally: db.close()
    def _init_db(self):
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL"); db.execute("PRAGMA synchronous=FULL")
            db.execute("CREATE TABLE IF NOT EXISTS digital_commodities(commodity_id TEXT PRIMARY KEY,corporate_entity_id TEXT NOT NULL,asset_ref TEXT NOT NULL,commodity_type TEXT NOT NULL,commercialization_authority INTEGER NOT NULL,status TEXT NOT NULL,metadata_json TEXT NOT NULL,created_at_ms INTEGER NOT NULL,UNIQUE(corporate_entity_id,asset_ref))")
            db.execute("CREATE TABLE IF NOT EXISTS commodity_events(event_id TEXT PRIMARY KEY,event_nonce TEXT UNIQUE NOT NULL,commodity_id TEXT NOT NULL,corporate_entity_id TEXT NOT NULL,usage_class TEXT NOT NULL,assurance_level TEXT NOT NULL,quantity INTEGER NOT NULL,unit TEXT NOT NULL,obligation_units INTEGER NOT NULL,recognized_revenue_units INTEGER NOT NULL,cash_received_units INTEGER NOT NULL,currency TEXT,evidence_origin TEXT NOT NULL,evidence_json TEXT NOT NULL,created_at_ms INTEGER NOT NULL,signature_json TEXT)")
            columns={str(r[1]) for r in db.execute("PRAGMA table_info(commodity_events)")}
            if "signature_json" not in columns: db.execute("ALTER TABLE commodity_events ADD COLUMN signature_json TEXT")
            db.execute("CREATE TABLE IF NOT EXISTS share_classes(class_id TEXT PRIMARY KEY,issuer_entity_id TEXT NOT NULL,class_code TEXT NOT NULL,authorized_units INTEGER NOT NULL,recorded_issued_units INTEGER NOT NULL,recorded_outstanding_units INTEGER NOT NULL,instrument_classification TEXT NOT NULL,rights_json TEXT NOT NULL,status TEXT NOT NULL,created_at_ms INTEGER NOT NULL,UNIQUE(issuer_entity_id,class_code))")
            db.execute("CREATE TABLE IF NOT EXISTS share_positions(issuer_entity_id TEXT NOT NULL,class_id TEXT NOT NULL,holder_ref TEXT NOT NULL,units INTEGER NOT NULL,updated_at_ms INTEGER NOT NULL,PRIMARY KEY(issuer_entity_id,class_id,holder_ref))")
            db.execute("CREATE TABLE IF NOT EXISTS capital_evidence(event_id TEXT PRIMARY KEY,event_nonce TEXT UNIQUE NOT NULL,issuer_entity_id TEXT NOT NULL,event_type TEXT NOT NULL,class_id TEXT,quantity INTEGER NOT NULL,payload_json TEXT NOT NULL,signature_json TEXT NOT NULL,external_authority_ref TEXT,created_at_ms INTEGER NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS valuation_evidence(evidence_id TEXT PRIMARY KEY,issuer_entity_id TEXT NOT NULL,class_id TEXT,evidence_kind TEXT NOT NULL,amount_minor INTEGER NOT NULL,currency TEXT NOT NULL,source TEXT NOT NULL,evidence_origin TEXT NOT NULL,metadata_json TEXT NOT NULL,observed_at_ms INTEGER NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS disclosure_snapshots(snapshot_id TEXT PRIMARY KEY,issuer_entity_id TEXT NOT NULL,scope TEXT NOT NULL,snapshot_json TEXT NOT NULL,snapshot_sha256 TEXT NOT NULL,created_at_ms INTEGER NOT NULL)")
    def _authority(self,issuer,authority,action):
        self._require_local(issuer); auth=dict(authority or {}); approvers=sorted({str(x) for x in auth.get("approvers") or [] if str(x)})
        if auth.get("approved") is not True or not approvers: raise PermissionError(f"{action} requires approved corporate authority")
        auth["approvers"]=approvers; auth["action"]=action; return auth
    def _external_ref(self,evidence,*,expected_subject=None,allowed_evidence_types=None):
        package=dict(evidence or {}); ref=str(package.get("external_authority_ref") or "").strip()
        if not ref: raise PermissionError("capital state requires external authoritative record/attestation")
        if self.external_authority_verifier is None: raise PermissionError("external authority verifier is not configured")
        verifier=self.external_authority_verifier
        if hasattr(verifier,"verify"):
            ok=verifier.verify(package,expected_subject=expected_subject,allowed_evidence_types=set(allowed_evidence_types or []))
        else:
            ok=verifier(package)
            if ok and expected_subject is not None and package.get("subject_entity_id") not in {None,expected_subject}: ok=False
            if ok and allowed_evidence_types and package.get("evidence_type") is not None and str(package.get("evidence_type")).upper() not in {str(x).upper() for x in allowed_evidence_types}: ok=False
        if ok is not True: raise PermissionError("external authoritative evidence failed verification")
        return ref
    def _nonce(self,db,nonce):
        if not str(nonce or "").strip(): raise ValueError("event nonce required")
        if db.execute("SELECT 1 FROM capital_evidence WHERE event_nonce=?",(str(nonce),)).fetchone(): raise ValueError("duplicate/replayed capital event")
    def _capital_event(self,db,issuer,event_type,nonce,*,class_id=None,quantity=0,payload=None,external_authority_ref=None):
        self._nonce(db,nonce); event_id=_id("capev1"); now=_now(); body={"schema":"entity-capital-evidence-v1","event_id":event_id,"event_nonce":str(nonce),"issuer_entity_id":issuer,"event_type":event_type,"class_id":class_id,"quantity":int(quantity),"payload":dict(payload or {}),"external_authority_ref":external_authority_ref,"created_at_ms":now}; sig=self.identity.sign(issuer,body)
        db.execute("INSERT INTO capital_evidence VALUES(?,?,?,?,?,?,?,?,?,?)",(event_id,str(nonce),issuer,event_type,class_id,int(quantity),json.dumps(body["payload"],sort_keys=True),json.dumps(sig,sort_keys=True),external_authority_ref,now))
        if self.event_ledger is not None: self.event_ledger.append(issuer,event_type,subject_ids=[issuer],object_ids=[x for x in [class_id] if x],payload={"capital_evidence_id":event_id,"external_authority_ref":external_authority_ref},evidence_origin="DIRECT_OBSERVATION")
        return {**body,"signature":sig}
    def register_digital_commodity(self,corporate_entity_id,asset_ref,*,commodity_type,commercialization_authority,metadata=None):
        self._require_local(corporate_entity_id); asset=str(asset_ref or "").strip(); kind=str(commodity_type or "").strip().upper()
        if not asset or not kind: raise ValueError("asset_ref and commodity_type required")
        cid=_id("dcom1"); now=_now()
        try:
            with self._connect() as db: db.execute("INSERT INTO digital_commodities VALUES(?,?,?,?,?,?,?,?)",(cid,corporate_entity_id,asset,kind,1 if commercialization_authority else 0,"ACTIVE",json.dumps(dict(metadata or {}),sort_keys=True),now))
        except sqlite3.IntegrityError as exc: raise ValueError("digital commodity already registered") from exc
        return {"commodity_id":cid,"corporate_entity_id":corporate_entity_id,"asset_ref":asset,"commodity_type":kind,"commercialization_authority":bool(commercialization_authority),"status":"ACTIVE"}
    def _commodity(self,commodity_id):
        with self._connect() as db: row=db.execute("SELECT * FROM digital_commodities WHERE commodity_id=?",(commodity_id,)).fetchone()
        if not row: raise KeyError("digital commodity not found")
        out=dict(row); out["commercialization_authority"]=bool(out["commercialization_authority"]); out["metadata"]=json.loads(out.pop("metadata_json") or "{}"); return out
    def record_usage(self,corporate_entity_id,commodity_id,*,event_nonce,usage_class,assurance_level,quantity,unit,evidence_origin="DIRECT_OBSERVATION",obligation_units=0,recognized_revenue_units=0,cash_received_units=0,currency=None,evidence=None):
        self._require_local(corporate_entity_id); commodity=self._commodity(commodity_id)
        if commodity["corporate_entity_id"]!=corporate_entity_id: raise PermissionError("commodity controller mismatch")
        assurance=str(assurance_level or "").upper(); origin=str(evidence_origin or "").upper(); qty=int(quantity); obligation=int(obligation_units); revenue=int(recognized_revenue_units); cash=int(cash_received_units)
        if assurance not in USAGE_ASSURANCE or origin not in EVIDENCE_ORIGINS: raise ValueError("unsupported evidence classification")
        if qty<=0 or min(obligation,revenue,cash)<0: raise ValueError("invalid usage/economic quantity")
        if not commodity["commercialization_authority"] and any(x>0 for x in (obligation,revenue,cash)): raise PermissionError("commodity lacks commercialization authority")
        if any(x>0 for x in (obligation,revenue,cash)) and not currency: raise ValueError("currency required for economic evidence")
        if cash>0: raise PermissionError("cash receipt must enter through verified settlement/accounting evidence, not usage telemetry")
        eid=_id("dcuev1"); nonce=str(event_nonce or "").strip(); now=_now(); use_class=str(usage_class or "").upper(); use_unit=str(unit or "").upper(); use_currency=str(currency or "").upper() or None; ev=dict(evidence or {}); ev_hash=_sha(ev)
        if not nonce: raise ValueError("event_nonce required")
        body={"schema":"entity-digital-commodity-usage-v1","event_id":eid,"event_nonce":nonce,"commodity_id":commodity_id,"corporate_entity_id":corporate_entity_id,"usage_class":use_class,"assurance_level":assurance,"quantity":qty,"unit":use_unit,"obligation_units":obligation,"recognized_revenue_units":revenue,"cash_received_units":0,"currency":use_currency,"evidence_origin":origin,"evidence_sha256":ev_hash,"created_at_ms":now}
        signature=self.identity.sign(corporate_entity_id,body)
        try:
            with self._connect() as db: db.execute("INSERT INTO commodity_events(event_id,event_nonce,commodity_id,corporate_entity_id,usage_class,assurance_level,quantity,unit,obligation_units,recognized_revenue_units,cash_received_units,currency,evidence_origin,evidence_json,created_at_ms,signature_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(eid,nonce,commodity_id,corporate_entity_id,use_class,assurance,qty,use_unit,obligation,revenue,0,use_currency,origin,json.dumps(ev,sort_keys=True),now,json.dumps(signature,sort_keys=True)))
        except sqlite3.IntegrityError as exc: raise ValueError("duplicate/replayed commodity event") from exc
        if self.event_ledger is not None: self.event_ledger.append(corporate_entity_id,"DIGITAL_COMMODITY_USAGE",subject_ids=[corporate_entity_id],object_ids=[commodity_id],payload={"commodity_event_id":eid,"quantity":qty,"unit":use_unit,"recognized_revenue_units":revenue,"currency":use_currency,"evidence_sha256":ev_hash},evidence_origin=origin)
        return {**body,"signature":signature,"evidence":ev,"usage_is_not_equity":True}
    def record_share_class_snapshot(self,issuer_entity_id,class_code,*,authorized_units,recorded_issued_units=0,recorded_outstanding_units=0,instrument_classification="CORPORATE_EQUITY",rights=None,external_evidence,authority,transaction_nonce):
        auth=self._authority(issuer_entity_id,authority,"RECORD_SHARE_CLASS"); ext=self._external_ref(external_evidence,expected_subject=issuer_entity_id,allowed_evidence_types={"SHARE_CLASS_REGISTER","CAPITAL_STRUCTURE"}); code=str(class_code or "").strip().upper(); authorized=int(authorized_units); issued=int(recorded_issued_units); outstanding=int(recorded_outstanding_units); ic=str(instrument_classification or "").upper()
        if not code or authorized<=0 or min(issued,outstanding)<0 or outstanding>issued or issued>authorized: raise ValueError("invalid capitalization quantities")
        if ic not in INSTRUMENT_CLASSES: raise ValueError("unsupported instrument classification")
        class_id=_id("shrcls1"); now=_now()
        with self._lock,self._connect() as db:
            self._nonce(db,transaction_nonce)
            db.execute("INSERT INTO share_classes VALUES(?,?,?,?,?,?,?,?,?,?)",(class_id,issuer_entity_id,code,authorized,issued,outstanding,ic,json.dumps(dict(rights or {}),sort_keys=True),"EXTERNALLY_ATTESTED",now))
            ev=self._capital_event(db,issuer_entity_id,"SHARE_CLASS_SNAPSHOT_RECORDED",transaction_nonce,class_id=class_id,quantity=outstanding,payload={"authority":auth,"external_evidence":dict(external_evidence or {})},external_authority_ref=ext)
        return {"class_id":class_id,"issuer_entity_id":issuer_entity_id,"class_code":code,"authorized_units":authorized,"recorded_issued_units":issued,"recorded_outstanding_units":outstanding,"external_authority_ref":ext,"event":ev}
    def _class(self,class_id):
        with self._connect() as db: row=db.execute("SELECT * FROM share_classes WHERE class_id=?",(class_id,)).fetchone()
        if not row: raise KeyError("share class not found")
        return row
    def record_shareholder_snapshot(self,issuer_entity_id,class_id,positions,*,external_evidence,authority,transaction_nonce):
        auth=self._authority(issuer_entity_id,authority,"RECORD_SHAREHOLDER_SNAPSHOT"); ext=self._external_ref(external_evidence,expected_subject=issuer_entity_id,allowed_evidence_types={"SHAREHOLDER_REGISTER","TRANSFER_AGENT_REGISTER"}); row=self._class(class_id)
        if row["issuer_entity_id"]!=issuer_entity_id: raise PermissionError("share class issuer mismatch")
        clean={str(holder):int(units) for holder,units in dict(positions or {}).items() if int(units)>=0}; total=sum(clean.values())
        if total!=int(row["recorded_outstanding_units"]): raise ValueError("shareholder snapshot must reconcile to recorded outstanding units")
        with self._lock,self._connect() as db:
            self._nonce(db,transaction_nonce); db.execute("DELETE FROM share_positions WHERE issuer_entity_id=? AND class_id=?",(issuer_entity_id,class_id)); now=_now()
            for holder,units in sorted(clean.items()): db.execute("INSERT INTO share_positions VALUES(?,?,?,?,?)",(issuer_entity_id,class_id,holder,units,now))
            ev=self._capital_event(db,issuer_entity_id,"SHAREHOLDER_REGISTER_SNAPSHOT_RECORDED",transaction_nonce,class_id=class_id,quantity=total,payload={"authority":auth,"holder_count":len(clean),"external_evidence":dict(external_evidence or {})},external_authority_ref=ext)
        return {"class_id":class_id,"holder_count":len(clean),"recorded_outstanding_units":total,"external_authority_ref":ext,"event":ev}
    def record_capitalization_snapshot(self,issuer_entity_id,class_id,*,authorized_units,recorded_issued_units,positions,external_evidence,authority,transaction_nonce,reason=""):
        auth=self._authority(issuer_entity_id,authority,"RECORD_CAPITALIZATION_SNAPSHOT"); ext=self._external_ref(external_evidence,expected_subject=issuer_entity_id,allowed_evidence_types={"CAPITAL_STRUCTURE_SNAPSHOT","TRANSFER_AGENT_REGISTER","CORPORATE_ACTION_RESULT"}); row=self._class(class_id)
        if row["issuer_entity_id"]!=issuer_entity_id: raise PermissionError("share class issuer mismatch")
        authorized=int(authorized_units); issued=int(recorded_issued_units); clean={str(h):int(u) for h,u in dict(positions or {}).items() if int(u)>=0}; outstanding=sum(clean.values())
        if authorized<=0 or min(issued,outstanding)<0 or outstanding>issued or issued>authorized: raise ValueError("invalid capitalization snapshot")
        with self._lock,self._connect() as db:
            self._nonce(db,transaction_nonce); db.execute("UPDATE share_classes SET authorized_units=?,recorded_issued_units=?,recorded_outstanding_units=?,status='EXTERNALLY_ATTESTED' WHERE class_id=?",(authorized,issued,outstanding,class_id))
            db.execute("DELETE FROM share_positions WHERE issuer_entity_id=? AND class_id=?",(issuer_entity_id,class_id)); now=_now()
            for holder,units in sorted(clean.items()): db.execute("INSERT INTO share_positions VALUES(?,?,?,?,?)",(issuer_entity_id,class_id,holder,units,now))
            ev=self._capital_event(db,issuer_entity_id,"CAPITALIZATION_SNAPSHOT_RECORDED",transaction_nonce,class_id=class_id,quantity=outstanding,payload={"authority":auth,"reason":str(reason)[:1024],"authorized_units":authorized,"recorded_issued_units":issued,"holder_count":len(clean),"external_evidence":dict(external_evidence or {})},external_authority_ref=ext)
        return {"class_id":class_id,"authorized_units":authorized,"recorded_issued_units":issued,"recorded_outstanding_units":outstanding,"holder_count":len(clean),"external_authority_ref":ext,"event":ev}
    def capitalization(self,issuer_entity_id):
        with self._connect() as db:
            classes=[dict(r) for r in db.execute("SELECT * FROM share_classes WHERE issuer_entity_id=? ORDER BY class_code",(issuer_entity_id,))]; positions=[dict(r) for r in db.execute("SELECT * FROM share_positions WHERE issuer_entity_id=? ORDER BY class_id,holder_ref",(issuer_entity_id,))]
        for row in classes: row["rights"]=json.loads(row.pop("rights_json") or "{}")
        return {"issuer_entity_id":issuer_entity_id,"summary":{"authorized_units":sum(int(x["authorized_units"]) for x in classes),"recorded_issued_units":sum(int(x["recorded_issued_units"]) for x in classes),"recorded_outstanding_units":sum(int(x["recorded_outstanding_units"]) for x in classes)},"classes":classes,"positions":positions,"legal_effect":"EVIDENCE_MODEL_ONLY_UNLESS_EXTERNAL_AUTHORITY_CONTROLS"}
    def corporate_economic_state(self,issuer_entity_id):
        with self._connect() as db:
            commodities=int(db.execute("SELECT COUNT(*) FROM digital_commodities WHERE corporate_entity_id=?",(issuer_entity_id,)).fetchone()[0]); rows=[dict(r) for r in db.execute("SELECT currency,COUNT(*) event_count,COALESCE(SUM(quantity),0) usage_quantity,COALESCE(SUM(obligation_units),0) obligation_units,COALESCE(SUM(recognized_revenue_units),0) recognized_revenue_units FROM commodity_events WHERE corporate_entity_id=? GROUP BY currency ORDER BY currency",(issuer_entity_id,))]
        by_currency={}
        for row in rows: by_currency[row["currency"] or "NON_MONETARY"]={"event_count":int(row["event_count"]),"usage_quantity":int(row["usage_quantity"]),"obligation_units":int(row["obligation_units"]),"recognized_revenue_units":int(row["recognized_revenue_units"])}
        return {"issuer_entity_id":issuer_entity_id,"digital_commodities":commodities,"economics_by_currency":by_currency,"capitalization":self.capitalization(issuer_entity_id)["summary"],"usage_does_not_equal_revenue":True,"revenue_does_not_equal_cash":True,"economic_state_does_not_equal_market_price":True}
    def record_modeled_valuation(self,issuer_entity_id,*,amount_minor,currency,methodology,class_id=None,assumptions=None):
        self._require_local(issuer_entity_id); amount=int(amount_minor)
        if amount<0 or not str(methodology or "").strip(): raise ValueError("nonnegative amount and methodology required")
        eid=_id("vale1"); now=_now()
        with self._connect() as db: db.execute("INSERT INTO valuation_evidence VALUES(?,?,?,?,?,?,?,?,?,?)",(eid,issuer_entity_id,class_id,"MODELLED_INDICATIVE_VALUE",amount,str(currency or "").upper(),str(methodology),"DERIVED_INFERENCE",json.dumps(dict(assumptions or {}),sort_keys=True),now))
        return {"evidence_id":eid,"evidence_kind":"MODELLED_INDICATIVE_VALUE","amount_minor":amount,"currency":str(currency or "").upper(),"evidence_origin":"DERIVED_INFERENCE","is_market_price":False}
    def record_external_market_observation(self,issuer_entity_id,class_id,*,amount_minor,currency,source,observed_at_ms,external_evidence,price_class="TRADE",metadata=None):
        self._require_local(issuer_entity_id); row=self._class(class_id); kind=str(price_class or "").upper(); amount=int(amount_minor)
        if row["issuer_entity_id"]!=issuer_entity_id: raise PermissionError("share class issuer mismatch")
        if kind not in MARKET_CLASSES or amount<0 or not str(source or "").strip(): raise ValueError("invalid external market observation")
        ext=self._external_ref(external_evidence,expected_subject=issuer_entity_id,allowed_evidence_types={"MARKET_PRICE_OBSERVATION","MARKET_BID_ASK"})
        eid=_id("mkobs1"); meta=dict(metadata or {}); meta["external_authority_ref"]=ext; meta["external_evidence"]=dict(external_evidence or {})
        with self._connect() as db: db.execute("INSERT INTO valuation_evidence VALUES(?,?,?,?,?,?,?,?,?,?)",(eid,issuer_entity_id,class_id,f"EXTERNAL_MARKET_{kind}",amount,str(currency or "").upper(),str(source),"EXTERNAL_AUTHORITATIVE_RECORD",json.dumps(meta,sort_keys=True),int(observed_at_ms)))
        return {"evidence_id":eid,"evidence_kind":f"EXTERNAL_MARKET_{kind}","amount_minor":amount,"currency":str(currency or "").upper(),"source":str(source),"external_authority_ref":ext,"is_externally_observed_market_price":True}
    def latest_external_market_observation(self,issuer_entity_id,class_id):
        with self._connect() as db: row=db.execute("SELECT * FROM valuation_evidence WHERE issuer_entity_id=? AND class_id=? AND evidence_kind LIKE 'EXTERNAL_MARKET_%' ORDER BY observed_at_ms DESC LIMIT 1",(issuer_entity_id,class_id)).fetchone()
        if not row: return None
        out=dict(row); out["metadata"]=json.loads(out.pop("metadata_json") or "{}"); return out
    def per_share_metrics(self,issuer_entity_id,class_id,currency):
        row=self._class(class_id); unit=str(currency or "").upper(); outstanding=int(row["recorded_outstanding_units"])
        if row["issuer_entity_id"]!=issuer_entity_id: raise PermissionError("share class issuer mismatch")
        econ=self.corporate_economic_state(issuer_entity_id)["economics_by_currency"].get(unit,{})
        revenue=int(econ.get("recognized_revenue_units",0)); obligation=int(econ.get("obligation_units",0)); div=lambda n: None if outstanding<=0 else format((Decimal(n)/Decimal(outstanding)).quantize(Decimal("0.000001"),rounding=ROUND_HALF_UP),"f")
        market=self.latest_external_market_observation(issuer_entity_id,class_id)
        return {"issuer_entity_id":issuer_entity_id,"class_id":class_id,"currency":unit,"denominator":outstanding,"denominator_method":"RECORDED_OUTSTANDING_SHARES","recognized_revenue_per_share":div(revenue),"contractual_obligation_per_share":div(obligation),"externally_observed_market_price":None if not market else {"amount_minor":int(market["amount_minor"]),"currency":market["currency"],"source":market["source"],"evidence_kind":market["evidence_kind"],"observed_at_ms":int(market["observed_at_ms"])},"internal_metrics_are_not_market_price":True}
    def disclosure_snapshot(self,issuer_entity_id,*,scope="INTERNAL"):
        self._require_local(issuer_entity_id); state=self.corporate_economic_state(issuer_entity_id); cap=self.capitalization(issuer_entity_id)
        payload={"schema":"entity-corporate-disclosure-v1","issuer_entity_id":issuer_entity_id,"scope":str(scope or "INTERNAL").upper(),"created_at_ms":_now(),"digital_commodities":state["digital_commodities"],"economics_by_currency":state["economics_by_currency"],"capitalization":cap["summary"],"limitations":["usage does not establish market price","internal valuation does not establish market price","recorded share state does not override an external authoritative register"]}
        sid=_id("disc1"); digest=_sha(payload)
        with self._connect() as db: db.execute("INSERT INTO disclosure_snapshots VALUES(?,?,?,?,?,?)",(sid,issuer_entity_id,payload["scope"],json.dumps(payload,sort_keys=True),digest,payload["created_at_ms"]))
        return {"snapshot_id":sid,"snapshot_sha256":digest,"snapshot":payload}
    def verify_invariants(self,issuer_entity_id):
        failures=[]
        with self._connect() as db:
            classes=[dict(r) for r in db.execute("SELECT * FROM share_classes WHERE issuer_entity_id=?",(issuer_entity_id,))]
            for row in classes:
                if int(row["recorded_issued_units"])>int(row["authorized_units"]): failures.append(f"{row['class_id']}:issued_exceeds_authorized")
                if int(row["recorded_outstanding_units"])>int(row["recorded_issued_units"]): failures.append(f"{row['class_id']}:outstanding_exceeds_issued")
                total=int(db.execute("SELECT COALESCE(SUM(units),0) FROM share_positions WHERE issuer_entity_id=? AND class_id=?",(issuer_entity_id,row["class_id"])).fetchone()[0])
                if total not in {0,int(row["recorded_outstanding_units"])}: failures.append(f"{row['class_id']}:shareholder_snapshot_mismatch")
            events=[dict(r) for r in db.execute("SELECT * FROM capital_evidence WHERE issuer_entity_id=?",(issuer_entity_id,))]
        manifest=self.identity.load_manifest(issuer_entity_id)
        for row in events:
            body={"schema":"entity-capital-evidence-v1","event_id":row["event_id"],"event_nonce":row["event_nonce"],"issuer_entity_id":row["issuer_entity_id"],"event_type":row["event_type"],"class_id":row["class_id"],"quantity":int(row["quantity"]),"payload":json.loads(row["payload_json"] or "{}"),"external_authority_ref":row["external_authority_ref"],"created_at_ms":int(row["created_at_ms"])}
            if not self.identity.verify_signature(manifest,body,json.loads(row["signature_json"])): failures.append(f"{row['event_id']}:signature_invalid")
        return {"pass":not failures,"issuer_entity_id":issuer_entity_id,"failures":failures,"classes_checked":len(classes),"capital_evidence_events_checked":len(events),"usage_cannot_issue_shares":True,"internal_valuation_cannot_be_market_price":True,"regulated_execution_enabled":False}
    def status(self):
        with self._connect() as db:
            commodities=int(db.execute("SELECT COUNT(*) FROM digital_commodities").fetchone()[0]); usage=int(db.execute("SELECT COUNT(*) FROM commodity_events").fetchone()[0]); classes=int(db.execute("SELECT COUNT(*) FROM share_classes").fetchone()[0])
        return {"ready":True,"schema":"entity-corporate-capital-evidence-v1","sers":"SERS-ENTITY-003","digital_commodities":commodities,"usage_events":usage,"share_classes":classes,"regulated_execution_enabled":False,"external_authority_required_for_share_state":True,"usage_to_equity_issuance_prohibited":True,"valuation_market_price_separation":True}
