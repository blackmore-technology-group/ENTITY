from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
import json, secrets, sqlite3, time

def _now(): return int(time.time()*1000)
def _id(prefix): return f"{prefix}-"+secrets.token_hex(20)

class CapitalAccountingReconciler:
    """Links externally attested journals, capital evidence and verified settlements without conflating them."""
    def __init__(self,state_dir: str|Path,identity,capital_engine,external_registry,*,settlement_engine=None):
        self.root=Path(state_dir)/"capital_accounting"; self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/"capital_accounting.sqlite"; self.identity=identity; self.capital=capital_engine
        self.external=external_registry; self.settlement=settlement_engine; self._init_db()

    @contextmanager
    def _connect(self):
        db=sqlite3.connect(self.path,timeout=30); db.row_factory=sqlite3.Row
        try: yield db; db.commit()
        except Exception: db.rollback(); raise
        finally: db.close()

    def _init_db(self):
        with self._connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS accounting_batches(batch_id TEXT PRIMARY KEY,transaction_nonce TEXT UNIQUE NOT NULL,issuer_entity_id TEXT NOT NULL,external_authority_ref TEXT NOT NULL,payload_json TEXT NOT NULL,signature_json TEXT NOT NULL,created_at_ms INTEGER NOT NULL)")

    def _authority(self,issuer,authority):
        self.capital._require_local(issuer); auth=dict(authority or {}); approvers=sorted({str(x) for x in auth.get("approvers") or [] if str(x)})
        if auth.get("approved") is not True or not approvers: raise PermissionError("accounting evidence adoption requires approved corporate authority")
        return {**auth,"approvers":approvers}
    def record_journal_snapshot(self,issuer_entity_id,entries,*,external_evidence,authority,transaction_nonce):
        auth=self._authority(issuer_entity_id,authority); nonce=str(transaction_nonce or "").strip()
        if not nonce: raise ValueError("transaction_nonce required")
        if not self.external.verify(external_evidence,expected_subject=issuer_entity_id,allowed_evidence_types={"ACCOUNTING_JOURNAL"}): raise PermissionError("external accounting evidence failed verification")
        clean=[]; totals={}
        for item in list(entries or []):
            row=dict(item); direction=str(row.get("direction") or "").upper(); currency=str(row.get("currency") or "").upper(); amount=int(row.get("amount_minor",0))
            if direction not in {"DEBIT","CREDIT"} or not currency or amount<=0 or not str(row.get("account_code") or "").strip(): raise ValueError("invalid accounting journal line")
            clean.append({"account_code":str(row["account_code"]),"direction":direction,"amount_minor":amount,"currency":currency,"capital_event_id":None if row.get("capital_event_id") is None else str(row.get("capital_event_id")),"memo":str(row.get("memo") or "")[:512]})
            bucket=totals.setdefault(currency,{"DEBIT":0,"CREDIT":0}); bucket[direction]+=amount
        if not clean or any(v["DEBIT"]!=v["CREDIT"] for v in totals.values()): raise ValueError("external accounting journal must balance by currency")
        payload={"schema":"entity-capital-accounting-snapshot-v1","entries":clean,"totals":totals,"authority":auth,"external_authority_ref":external_evidence["external_authority_ref"],"external_evidence":dict(external_evidence or {})}
        signature=self.identity.sign(issuer_entity_id,payload); batch_id=_id("acct1"); now=_now()
        with self._connect() as db:
            try: db.execute("INSERT INTO accounting_batches VALUES(?,?,?,?,?,?,?)",(batch_id,nonce,issuer_entity_id,external_evidence["external_authority_ref"],json.dumps(payload,sort_keys=True),json.dumps(signature,sort_keys=True),now))
            except sqlite3.IntegrityError as exc: raise ValueError("duplicate/replayed accounting batch") from exc
        return {"batch_id":batch_id,"issuer_entity_id":issuer_entity_id,"currencies":sorted(totals),"balanced":True,"external_authority_ref":external_evidence["external_authority_ref"]}
    def get(self,batch_id: str) -> dict:
        with self._connect() as db: row=db.execute("SELECT * FROM accounting_batches WHERE batch_id=?",(str(batch_id),)).fetchone()
        if not row: raise KeyError("accounting batch not found")
        out=dict(row); out["payload"]=json.loads(out.pop("payload_json") or "{}"); out["signature"]=json.loads(out.pop("signature_json") or "{}"); return out

    def reconcile_capital_event(self,issuer_entity_id,capital_event_id,batch_id,*,expected_amount_minor,currency,settlement_id=None,require_external_cash=False,issuer_settlement_role="PAYEE"):
        batch=self.get(batch_id)
        if batch["issuer_entity_id"]!=issuer_entity_id: raise PermissionError("accounting batch issuer mismatch")
        expected=int(expected_amount_minor); unit=str(currency or "").upper(); tagged=[x for x in batch["payload"]["entries"] if x.get("capital_event_id")==str(capital_event_id) and x["currency"]==unit]
        debits=sum(int(x["amount_minor"]) for x in tagged if x["direction"]=="DEBIT"); credits=sum(int(x["amount_minor"]) for x in tagged if x["direction"]=="CREDIT")
        accounting_ok=expected>=0 and debits==expected and credits==expected
        settlement_ok=None
        if require_external_cash:
            if self.settlement is None or not settlement_id: raise PermissionError("verified settlement evidence required")
            settlement=self.settlement.get(str(settlement_id)); role=str(issuer_settlement_role or "PAYEE").upper()
            if role not in {"PAYEE","PAYER"}: raise ValueError("issuer_settlement_role must be PAYEE or PAYER")
            party_ok=settlement["payee_entity_id"]==issuer_entity_id if role=="PAYEE" else settlement["payer_entity_id"]==issuer_entity_id
            settlement_ok=bool(party_ok and settlement["state"] in {"CONFIRMED","RECONCILED"} and settlement["settlement_kind"]=="EXTERNAL_PAYMENT" and settlement["money_movement_verified"] and int(settlement["amount_units"])==expected and settlement["currency"]==unit)
        return {"issuer_entity_id":issuer_entity_id,"capital_event_id":str(capital_event_id),"batch_id":batch_id,"currency":unit,"expected_amount_minor":expected,"accounting_debits":debits,"accounting_credits":credits,"accounting_reconciled":accounting_ok,"external_cash_required":bool(require_external_cash),"external_cash_verified":settlement_ok,"accounting_record_is_not_legal_share_ownership":True,"accounting_record_is_not_cash_proof":True if not require_external_cash else not bool(settlement_ok is True)}