from __future__ import annotations
from pathlib import Path
from contextlib import contextmanager
from threading import RLock
import hashlib, json, secrets, sqlite3, time

ASSURANCE={"DECLARED":1,"ENTITY_GATEWAY_OBSERVED":2,"COUNTERPARTY_ATTESTED":3,"ENVIRONMENT_ATTESTED":4}

def _now(): return int(time.time()*1000)
def _id(prefix): return f"{prefix}-"+secrets.token_hex(20)
def _canon(v): return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
def _sha(v): return hashlib.sha256(v if isinstance(v,(bytes,bytearray)) else _canon(v)).hexdigest()

class UsageControlEngine:
    """Licence-bound usage evidence; assurance describes evidence strength, not universal downstream control."""
    def __init__(self,state_dir: str|Path,identity,contracts,event_ledger=None):
        self.root=Path(state_dir)/"usage_control"; self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/"usage.sqlite"; self.identity=identity; self.contracts=contracts; self.ledger=event_ledger
        self._lock=RLock(); self._environment_verifiers={}; self._init_db()
    @contextmanager
    def _connect(self):
        db=sqlite3.connect(self.path,timeout=30); db.row_factory=sqlite3.Row
        try: yield db; db.commit()
        except Exception: db.rollback(); raise
        finally: db.close()
    def _init_db(self):
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL"); db.execute("PRAGMA synchronous=FULL")
            db.execute("CREATE TABLE IF NOT EXISTS tickets(ticket_id TEXT PRIMARY KEY,issuer_entity_id TEXT NOT NULL,licence_id TEXT NOT NULL,asset_id TEXT NOT NULL,use_type TEXT NOT NULL,quantity INTEGER NOT NULL,nonce TEXT UNIQUE NOT NULL,expires_at_ms INTEGER NOT NULL,status TEXT NOT NULL,signature_json TEXT NOT NULL,created_at_ms INTEGER NOT NULL,consumed_at_ms INTEGER)")
            db.execute("CREATE TABLE IF NOT EXISTS receipts(receipt_id TEXT PRIMARY KEY,licence_id TEXT NOT NULL,actor_entity_id TEXT NOT NULL,asset_id TEXT NOT NULL,use_type TEXT NOT NULL,purpose TEXT NOT NULL,quantity INTEGER NOT NULL,assurance TEXT NOT NULL,assurance_level INTEGER NOT NULL,evidence_origin TEXT NOT NULL,evidence_json TEXT NOT NULL,evidence_sha256 TEXT NOT NULL,nonce TEXT UNIQUE NOT NULL,signature_json TEXT NOT NULL,created_at_ms INTEGER NOT NULL)")
    def _contract_scope(self,actor_entity_id: str,licence_id: str,asset_id: str,use_type: str,purpose: str,quantity: int) -> dict:
        contract=self.contracts.get(licence_id)
        if contract["state"]!="ACTIVE": raise PermissionError("licence is not active")
        if contract["licensee_entity_id"]!=actor_entity_id: raise PermissionError("named licensee required")
        terms=contract["terms"]; right=str(use_type).upper(); requested_purpose=str(purpose or "")
        if asset_id not in set(terms.get("assets") or []): raise PermissionError("asset outside licence scope")
        if right not in set(terms.get("rights") or []): raise PermissionError("use outside licence rights")
        allowed_purpose=str(terms.get("purpose") or "")
        if allowed_purpose and requested_purpose!=allowed_purpose: raise PermissionError("purpose outside licence scope")
        qty=max(1,int(quantity)); req=dict(terms.get("usage_requirements") or {})
        max_qty=int(req.get("max_quantity_per_event",qty))
        if qty>max(1,max_qty): raise PermissionError("quantity exceeds licence usage requirement")
        return {"contract":contract,"right":right,"purpose":requested_purpose,"quantity":qty}
    def _audit(self,signer: str,receipt: dict):
        if self.ledger is not None:
            self.ledger.append(signer,"usage.receipted",subject_ids=[receipt["licence_id"],receipt["actor_entity_id"]],object_ids=[receipt["asset_id"]],payload={"receipt_id":receipt["receipt_id"],"assurance":receipt["assurance"],"evidence_sha256":receipt["evidence_sha256"]},evidence_origin=receipt["evidence_origin"],confidence=1.0)
    def _receipt(self,*,signer: str,licence_id: str,actor: str,asset_id: str,use_type: str,purpose: str,quantity: int,assurance: str,evidence_origin: str,evidence: dict,nonce: str) -> dict:
        mode=str(assurance).upper(); level=ASSURANCE[mode]; now=_now(); receipt_id=_id("urc2")
        ev=dict(evidence or {}); ev_hash=_sha(ev)
        body={"schema":"entity-usage-receipt-v2","receipt_id":receipt_id,"licence_id":licence_id,"actor_entity_id":actor,"asset_id":asset_id,"use_type":str(use_type).upper(),"purpose":str(purpose),"quantity":int(quantity),"assurance":mode,"assurance_level":level,"evidence_origin":str(evidence_origin).upper(),"evidence_sha256":ev_hash,"nonce":str(nonce),"created_at_ms":now}
        signature=self.identity.sign(signer,body)
        with self._lock,self._connect() as db:
            try: db.execute("INSERT INTO receipts VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(receipt_id,licence_id,actor,asset_id,body["use_type"],body["purpose"],body["quantity"],mode,level,body["evidence_origin"],json.dumps(ev,sort_keys=True),ev_hash,str(nonce),json.dumps(signature,sort_keys=True),now))
            except sqlite3.IntegrityError as exc: raise ValueError("duplicate/replayed usage nonce") from exc
        out={**body,"signature":signature,"evidence":ev,"verified_scope":"EVIDENCE_CLASS_ONLY"}
        self._audit(signer,out); return out
    def record_declared(self,actor_entity_id: str,licence_id: str,*,asset_id: str,use_type: str,purpose: str,quantity: int=1,evidence: dict|None=None,nonce: str) -> dict:
        scoped=self._contract_scope(actor_entity_id,licence_id,asset_id,use_type,purpose,quantity)
        out=self._receipt(signer=actor_entity_id,licence_id=licence_id,actor=actor_entity_id,asset_id=asset_id,use_type=scoped["right"],purpose=scoped["purpose"],quantity=scoped["quantity"],assurance="DECLARED",evidence_origin="ENTITY_ASSERTION",evidence=dict(evidence or {}),nonce=nonce)
        out["independently_verified"]=False; out["meaning"]="licensee-declared usage only"
        return out
    def issue_gateway_ticket(self,grantor_entity_id: str,*,licence_id: str,asset_id: str,use_type: str,quantity: int=1,ttl_ms: int=300000,nonce: str|None=None) -> dict:
        contract=self.contracts.get(licence_id)
        if contract["state"]!="ACTIVE" or contract["grantor_entity_id"]!=grantor_entity_id: raise PermissionError("active grantor licence required")
        self.identity.load_manifest(grantor_entity_id)
        terms=contract["terms"]; right=str(use_type).upper()
        if asset_id not in set(terms.get("assets") or []) or right not in set(terms.get("rights") or []): raise PermissionError("ticket outside licence scope")
        qty=max(1,int(quantity)); now=_now(); ticket_id=_id("ugt1"); token=str(nonce or secrets.token_urlsafe(18)); expires=now+max(1000,int(ttl_ms))
        body={"schema":"entity-usage-gateway-ticket-v1","ticket_id":ticket_id,"issuer_entity_id":grantor_entity_id,"licence_id":licence_id,"asset_id":asset_id,"use_type":right,"quantity":qty,"nonce":token,"expires_at_ms":expires,"created_at_ms":now}
        signature=self.identity.sign(grantor_entity_id,body)
        with self._connect() as db:
            try: db.execute("INSERT INTO tickets VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(ticket_id,grantor_entity_id,licence_id,asset_id,right,qty,token,expires,"ISSUED",json.dumps(signature,sort_keys=True),now,None))
            except sqlite3.IntegrityError as exc: raise ValueError("duplicate/replayed ticket nonce") from exc
        return {**body,"signature":signature,"status":"ISSUED"}
    def consume_gateway_ticket(self,actor_entity_id: str,ticket_id: str,*,purpose: str,nonce: str) -> dict:
        now=_now()
        with self._lock,self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row=db.execute("SELECT * FROM tickets WHERE ticket_id=?",(ticket_id,)).fetchone()
            if not row: raise KeyError("usage ticket not found")
            if row["status"]!="ISSUED" or row["consumed_at_ms"] is not None: raise PermissionError("usage ticket already consumed")
            if int(row["expires_at_ms"])<=now: raise PermissionError("usage ticket expired")
            contract=self.contracts.get(row["licence_id"])
            if contract["licensee_entity_id"]!=actor_entity_id: raise PermissionError("usage ticket licensee mismatch")
            scoped=self._contract_scope(actor_entity_id,row["licence_id"],row["asset_id"],row["use_type"],purpose,int(row["quantity"]))
            body={"schema":"entity-usage-gateway-ticket-v1","ticket_id":row["ticket_id"],"issuer_entity_id":row["issuer_entity_id"],"licence_id":row["licence_id"],"asset_id":row["asset_id"],"use_type":row["use_type"],"quantity":row["quantity"],"nonce":row["nonce"],"expires_at_ms":row["expires_at_ms"],"created_at_ms":row["created_at_ms"]}
            manifest=self.identity.load_manifest(row["issuer_entity_id"]); signature=json.loads(row["signature_json"])
            if not self.identity.verify_signature(manifest,body,signature): raise PermissionError("usage ticket signature invalid")
            db.execute("UPDATE tickets SET status='CONSUMED',consumed_at_ms=? WHERE ticket_id=?",(now,ticket_id))
        evidence={"ticket_id":ticket_id,"issuer_entity_id":row["issuer_entity_id"],"consumed_at_ms":now,"observation":"authorized gateway access consumed"}
        out=self._receipt(signer=row["issuer_entity_id"],licence_id=row["licence_id"],actor=actor_entity_id,asset_id=row["asset_id"],use_type=scoped["right"],purpose=scoped["purpose"],quantity=scoped["quantity"],assurance="ENTITY_GATEWAY_OBSERVED",evidence_origin="DIRECT_OBSERVATION",evidence=evidence,nonce=nonce)
        out["independently_verified"]=False; out["meaning"]="ENTITY gateway observed authorized access; downstream use beyond the gateway is not proven"
        return out
    def record_counterparty_attested(self,attestor_entity_id: str,actor_entity_id: str,licence_id: str,*,asset_id: str,use_type: str,purpose: str,quantity: int=1,evidence: dict|None=None,nonce: str) -> dict:
        contract=self.contracts.get(licence_id)
        if attestor_entity_id not in {contract["grantor_entity_id"],contract["licensee_entity_id"]} or attestor_entity_id==actor_entity_id: raise PermissionError("independent contract counterparty attestor required")
        self.identity.load_manifest(attestor_entity_id)
        scoped=self._contract_scope(actor_entity_id,licence_id,asset_id,use_type,purpose,quantity)
        out=self._receipt(signer=attestor_entity_id,licence_id=licence_id,actor=actor_entity_id,asset_id=asset_id,use_type=scoped["right"],purpose=scoped["purpose"],quantity=scoped["quantity"],assurance="COUNTERPARTY_ATTESTED",evidence_origin="COUNTERPARTY_ATTESTATION",evidence=dict(evidence or {}),nonce=nonce)
        out["independently_verified"]=False; out["meaning"]="signed counterparty attestation; not independent environmental verification"
        return out
    def register_environment_verifier(self,verifier_id: str,verifier_fn) -> None:
        if not str(verifier_id).strip() or not callable(verifier_fn): raise ValueError("verifier id and callable required")
        self._environment_verifiers[str(verifier_id)]=verifier_fn
    def record_environment_attested(self,recorder_entity_id: str,actor_entity_id: str,licence_id: str,*,asset_id: str,use_type: str,purpose: str,quantity: int=1,evidence: dict,verifier_id: str,nonce: str) -> dict:
        contract=self.contracts.get(licence_id)
        if recorder_entity_id!=contract["grantor_entity_id"]: raise PermissionError("grantor recorder required")
        self.identity.load_manifest(recorder_entity_id)
        verifier=self._environment_verifiers.get(str(verifier_id))
        if verifier is None: raise PermissionError("environment verifier is not registered")
        scoped=self._contract_scope(actor_entity_id,licence_id,asset_id,use_type,purpose,quantity); ev=dict(evidence or {})
        if not bool(verifier(ev)): raise PermissionError("environment attestation verification failed")
        ev["verifier_id"]=str(verifier_id)
        out=self._receipt(signer=recorder_entity_id,licence_id=licence_id,actor=actor_entity_id,asset_id=asset_id,use_type=scoped["right"],purpose=scoped["purpose"],quantity=scoped["quantity"],assurance="ENVIRONMENT_ATTESTED",evidence_origin="EXTERNAL_AUTHORITATIVE_RECORD",evidence=ev,nonce=nonce)
        out["independently_verified"]=True; out["meaning"]="registered environment verifier accepted the supplied evidence within its declared scope"
        return out
    def get_receipt(self,receipt_id: str) -> dict:
        with self._connect() as db: row=db.execute("SELECT * FROM receipts WHERE receipt_id=?",(receipt_id,)).fetchone()
        if not row: raise KeyError("usage receipt not found")
        out=dict(row); out["evidence"]=json.loads(out.pop("evidence_json")); out["signature"]=json.loads(out.pop("signature_json")); return out
    def verify_receipt(self,receipt_id: str) -> dict:
        item=self.get_receipt(receipt_id); signer=str(item["signature"].get("entity_id") or "")
        body={"schema":"entity-usage-receipt-v2","receipt_id":item["receipt_id"],"licence_id":item["licence_id"],"actor_entity_id":item["actor_entity_id"],"asset_id":item["asset_id"],"use_type":item["use_type"],"purpose":item["purpose"],"quantity":item["quantity"],"assurance":item["assurance"],"assurance_level":item["assurance_level"],"evidence_origin":item["evidence_origin"],"evidence_sha256":item["evidence_sha256"],"nonce":item["nonce"],"created_at_ms":item["created_at_ms"]}
        try:
            manifest=self.identity.load_manifest(signer); sig_ok=self.identity.verify_signature(manifest,body,item["signature"])
        except Exception: sig_ok=False
        ev_ok=_sha(item["evidence"])==item["evidence_sha256"]
        return {"pass":bool(sig_ok and ev_ok),"receipt_id":receipt_id,"signature_valid":bool(sig_ok),"evidence_hash_valid":bool(ev_ok),"assurance":item["assurance"],"assurance_level":item["assurance_level"]}
    def status(self) -> dict:
        with self._connect() as db:
            tickets=int(db.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]); receipts=int(db.execute("SELECT COUNT(*) FROM receipts").fetchone()[0])
        return {"ready":True,"schema":"entity-usage-control-v2","assurance_levels":dict(ASSURANCE),"self_declaration_not_independent_verification":True,"gateway_observation_not_downstream_control":True,"environment_verification_fail_closed":True,"tickets":tickets,"receipts":receipts,"database":str(self.path)}
