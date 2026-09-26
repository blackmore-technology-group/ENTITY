from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
import json, secrets, sqlite3, time

ACTION_TYPES={"ISSUANCE","TRANSFER","SPLIT","CONSOLIDATION","CONVERSION","REPURCHASE","REDEMPTION","CANCELLATION","DIVIDEND","DISTRIBUTION"}
ACTION_POLICY={"ISSUANCE":"RECORD_ISSUANCE","TRANSFER":"RECORD_TRANSFER","SPLIT":"RECORD_ISSUANCE","CONSOLIDATION":"RECORD_CANCELLATION","CONVERSION":"RECORD_CONVERSION","REPURCHASE":"RECORD_REPURCHASE","REDEMPTION":"RECORD_REDEMPTION","CANCELLATION":"RECORD_CANCELLATION","DIVIDEND":"RECORD_DIVIDEND","DISTRIBUTION":"RECORD_DIVIDEND"}

def _now(): return int(time.time()*1000)
def _id(prefix): return f"{prefix}-"+secrets.token_hex(20)

class CorporateActionLedger:
    """Evidence/reconciliation layer for externally effective corporate actions."""
    def __init__(self,state_dir: str|Path,identity,capital_engine,external_registry,classification_registry):
        self.root=Path(state_dir)/"corporate_actions"; self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/"corporate_actions.sqlite"; self.identity=identity; self.capital=capital_engine
        self.external=external_registry; self.classification=classification_registry; self._init_db()

    @contextmanager
    def _connect(self):
        db=sqlite3.connect(self.path,timeout=30); db.row_factory=sqlite3.Row
        try: yield db; db.commit()
        except Exception: db.rollback(); raise
        finally: db.close()

    def _init_db(self):
        with self._connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS actions(action_id TEXT PRIMARY KEY,transaction_nonce TEXT UNIQUE NOT NULL,issuer_entity_id TEXT NOT NULL,class_id TEXT NOT NULL,action_type TEXT NOT NULL,jurisdiction TEXT NOT NULL,instrument_class TEXT NOT NULL,status TEXT NOT NULL,effective_at_ms INTEGER NOT NULL,external_authority_ref TEXT NOT NULL,payload_json TEXT NOT NULL,signature_json TEXT NOT NULL,created_at_ms INTEGER NOT NULL)")
    def _authority(self,issuer,authority,action):
        auth=dict(authority or {}); approvers=sorted({str(x) for x in auth.get("approvers") or [] if str(x)})
        self.capital._require_local(issuer)
        if auth.get("approved") is not True or not approvers: raise PermissionError(f"{action} requires approved corporate authority")
        return {**auth,"approvers":approvers,"action":action}

    def record_action(self,issuer_entity_id,class_id,*,action_type,jurisdiction,instrument_class,effective_at_ms,external_evidence,authority,transaction_nonce,expected_post_snapshot=None,financial_effect=None):
        kind=str(action_type or "").upper(); jur=str(jurisdiction or "").upper(); ic=str(instrument_class or "").upper(); nonce=str(transaction_nonce or "").strip()
        if kind not in ACTION_TYPES or not nonce or int(effective_at_ms)<=0: raise ValueError("invalid corporate action")
        share_class=self.capital._class(class_id)
        if share_class["issuer_entity_id"]!=issuer_entity_id: raise PermissionError("share class issuer mismatch")
        self._authority(issuer_entity_id,authority,f"CORPORATE_ACTION_{kind}")
        policy=self.classification.require_evidence_operation(jurisdiction=jur,instrument_class=ic,action=ACTION_POLICY[kind],at_ms=int(effective_at_ms))
        if not self.external.verify(external_evidence,expected_subject=issuer_entity_id,allowed_evidence_types={"CORPORATE_ACTION_RESULT"}): raise PermissionError("external corporate-action evidence failed verification")
        external_payload=dict(external_evidence.get("payload") or {}); expected=dict(expected_post_snapshot or {})
        if str(external_payload.get("action_type") or "").upper()!=kind or str(external_payload.get("class_id") or "")!=str(class_id): raise PermissionError("external evidence is not bound to this corporate action")
        if expected and dict(external_payload.get("post_capitalization") or {})!=expected: raise PermissionError("external post-capitalization evidence does not match requested snapshot")
        payload={"expected_post_snapshot":expected,"financial_effect":dict(financial_effect or {}),"policy_rule_id":policy.get("rule_id"),"authority":dict(authority or {}),"external_evidence":dict(external_evidence or {})}
        body={"schema":"entity-corporate-action-evidence-v1","issuer_entity_id":issuer_entity_id,"class_id":class_id,"action_type":kind,"jurisdiction":jur,"instrument_class":ic,"effective_at_ms":int(effective_at_ms),"external_authority_ref":external_evidence["external_authority_ref"],"payload":payload}
        signature=self.identity.sign(issuer_entity_id,body); action_id=_id("cact1"); now=_now()
        with self._connect() as db:
            try: db.execute("INSERT INTO actions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",(action_id,nonce,issuer_entity_id,class_id,kind,jur,ic,"RECORDED",int(effective_at_ms),external_evidence["external_authority_ref"],json.dumps(payload,sort_keys=True),json.dumps(signature,sort_keys=True),now))
            except sqlite3.IntegrityError as exc: raise ValueError("duplicate/replayed corporate action") from exc
        adopted=None
        if expected_post_snapshot:
            snap=dict(expected_post_snapshot)
            adopted=self.capital.record_capitalization_snapshot(issuer_entity_id,class_id,authorized_units=int(snap["authorized_units"]),recorded_issued_units=int(snap["recorded_issued_units"]),positions=dict(snap["positions"]),external_evidence=external_evidence,authority=authority,transaction_nonce=nonce+":capital",reason=f"corporate action {kind}")
        result=self.reconcile(action_id)
        return {"action_id":action_id,"status":result["status"],"action_type":kind,"adopted_capitalization":adopted,"reconciliation":result}

    def get(self,action_id: str) -> dict:
        with self._connect() as db: row=db.execute("SELECT * FROM actions WHERE action_id=?",(str(action_id),)).fetchone()
        if not row: raise KeyError("corporate action not found")
        out=dict(row); out["payload"]=json.loads(out.pop("payload_json") or "{}"); out["signature"]=json.loads(out.pop("signature_json") or "{}"); return out

    def reconcile(self,action_id: str) -> dict:
        action=self.get(action_id); expected=dict(action["payload"].get("expected_post_snapshot") or {})
        failures=[]
        if expected:
            cap=self.capital.capitalization(action["issuer_entity_id"]); classes={x["class_id"]:x for x in cap["classes"]}; row=classes.get(action["class_id"])
            if not row: failures.append("share_class_missing")
            else:
                if int(row["authorized_units"])!=int(expected["authorized_units"]): failures.append("authorized_units_mismatch")
                if int(row["recorded_issued_units"])!=int(expected["recorded_issued_units"]): failures.append("issued_units_mismatch")
                positions={p["holder_ref"]:int(p["units"]) for p in cap["positions"] if p["class_id"]==action["class_id"]}
                if positions!={str(k):int(v) for k,v in dict(expected["positions"]).items()}: failures.append("share_positions_mismatch")
        status="RECONCILED" if not failures else "MISMATCH"
        with self._connect() as db: db.execute("UPDATE actions SET status=? WHERE action_id=?",(status,action_id))
        return {"action_id":action_id,"status":status,"failures":failures,"external_action_is_not_internal_execution":True}