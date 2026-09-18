from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
import base64, hashlib, json, secrets, sqlite3, time

SCHEMA="entity-transaction-evidence-record-v1"
BUNDLE_SCHEMA="entity-transaction-evidence-bundle-v1"
RECOVERY_SCHEMA="entity-sovereign-transaction-export-v1"
REQUIRED_REFS={
    "asset_id","claim_id","licence_id","usage_receipt_id","license_settlement_id","value_id",
    "commodity_id","commodity_event_id","threshold_policy_id","threshold_request_id","share_class_id",
    "corporate_action_id","capital_event_id","capital_accounting_batch_id","share_settlement_id",
    "disclosure_snapshot_id","ledger_checkpoint_id"
}

def _now(): return int(time.time()*1000)
def _id(): return "txev1-"+secrets.token_hex(20)
def _canon(v): return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()
def _sha_bytes(v): return hashlib.sha256(v).hexdigest()
def _sha_file(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

class TransactionEvidenceExporter:
    """Self-contained, implementation-independent transaction evidence and recovery packaging."""
    def __init__(self,state_dir:str|Path,identity):
        self.state=Path(state_dir).resolve(); self.identity=identity
        self.root=self.state/"transaction_evidence"; self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/"transactions.sqlite"; self._init_db()
    @contextmanager
    def _connect(self,path:Path|None=None):
        db=sqlite3.connect(path or self.path,timeout=30); db.row_factory=sqlite3.Row
        try: yield db; db.commit()
        except Exception: db.rollback(); raise
        finally: db.close()

    def _init_db(self):
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("CREATE TABLE IF NOT EXISTS transactions(transaction_id TEXT PRIMARY KEY,issuer_entity_id TEXT NOT NULL,jurisdiction TEXT NOT NULL,references_json TEXT NOT NULL,participants_json TEXT NOT NULL,notes_json TEXT NOT NULL,created_at_ms INTEGER NOT NULL,signature_json TEXT NOT NULL)")

    def register(self,issuer_entity_id:str,*,jurisdiction:str,references:dict,participants:list[str],notes:dict|None=None)->dict:
        refs={str(k):str(v) for k,v in dict(references or {}).items() if str(v)}
        missing=sorted(REQUIRED_REFS-set(refs))
        if missing: raise ValueError(f"transaction evidence references missing: {missing}")
        people=sorted({str(x) for x in participants if str(x)})
        if issuer_entity_id not in people: people.append(issuer_entity_id); people.sort()
        for entity_id in people: self.identity.load_manifest(entity_id)
        txid=_id(); now=_now(); body={"schema":SCHEMA,"transaction_id":txid,"issuer_entity_id":issuer_entity_id,
            "jurisdiction":str(jurisdiction).upper(),"references":refs,"participants":people,"notes":dict(notes or {}),"created_at_ms":now}
        signature=self.identity.sign(issuer_entity_id,body)
        with self._connect() as db:
            db.execute("INSERT INTO transactions VALUES(?,?,?,?,?,?,?,?)",(txid,issuer_entity_id,body["jurisdiction"],json.dumps(refs,sort_keys=True),json.dumps(people),json.dumps(body["notes"],sort_keys=True),now,json.dumps(signature,sort_keys=True)))
        return {**body,"signature":signature}
    def get(self,transaction_id:str)->dict:
        with self._connect() as db: row=db.execute("SELECT * FROM transactions WHERE transaction_id=?",(str(transaction_id),)).fetchone()
        if not row: raise KeyError("transaction evidence record not found")
        out=dict(row); out["references"]=json.loads(out.pop("references_json")); out["participants"]=json.loads(out.pop("participants_json")); out["notes"]=json.loads(out.pop("notes_json")); out["signature"]=json.loads(out.pop("signature_json")); out["schema"]=SCHEMA
        return out

    def _one(self,relative_db:str,sql:str,args=()):
        path=self.state/relative_db
        if not path.is_file(): raise FileNotFoundError(str(path))
        with self._connect(path) as db: row=db.execute(sql,args).fetchone()
        if not row: raise KeyError(f"required evidence row missing in {relative_db}")
        return dict(row)

    def _many(self,relative_db:str,sql:str,args=()):
        path=self.state/relative_db
        if not path.is_file(): raise FileNotFoundError(str(path))
        with self._connect(path) as db: return [dict(r) for r in db.execute(sql,args).fetchall()]

    @staticmethod
    def _json_fields(row:dict,*fields):
        out=dict(row)
        for field in fields:
            if field in out: out[field[:-5] if field.endswith("_json") else field]=json.loads(out.pop(field) or "{}")
        return out

    def _manifest(self,entity_id:str)->dict: return self.identity.load_manifest(entity_id)

    def _transaction_record_body(self,record:dict)->dict:
        return {"schema":SCHEMA,"transaction_id":record["transaction_id"],"issuer_entity_id":record["issuer_entity_id"],"jurisdiction":record["jurisdiction"],"references":record["references"],"participants":record["participants"],"notes":record["notes"],"created_at_ms":record["created_at_ms"]}
    def _settlement_evidence(self,settlement_id:str)->dict:
        settlement=self._one("settlement/settlement.sqlite","SELECT * FROM settlements WHERE settlement_id=?",(settlement_id,))
        settlement=self._json_fields(settlement,"evidence_json"); settlement["money_movement_verified"]=bool(settlement["money_movement_verified"])
        events=self._many("settlement/settlement.sqlite","SELECT rowid AS _rowid,* FROM settlement_events WHERE settlement_id=? ORDER BY rowid",(settlement_id,))
        events=[self._json_fields(x,"payload_json","signature_json") for x in events]
        postings=self._many("settlement/settlement.sqlite","SELECT * FROM postings WHERE settlement_id=? ORDER BY direction,entry_id",(settlement_id,))
        return {"settlement":settlement,"events":events,"postings":postings}

    def _rights_evidence(self,claim_id:str)->dict:
        claim=self._one("rights_claims/rights_claims.sqlite","SELECT * FROM claims WHERE claim_id=?",(claim_id,))
        claim=self._json_fields(claim,"scope_json","evidence_json","signature_json")
        claim["share"]={"numerator":int(claim.pop("share_num")),"denominator":int(claim.pop("share_den"))}
        events=self._many("rights_claims/rights_claims.sqlite","SELECT * FROM claim_events WHERE claim_id=? ORDER BY sequence",(claim_id,))
        events=[self._json_fields(x,"payload_json","signature_json") for x in events]
        return {"claim":claim,"events":events}

    def _licence_evidence(self,licence_id:str)->dict:
        licence=self._one("contracts/licensing.sqlite","SELECT * FROM licences WHERE licence_id=?",(licence_id,))
        licence=self._json_fields(licence,"terms_json","authority_basis_json")
        events=self._many("contracts/licensing.sqlite","SELECT rowid AS _rowid,* FROM licence_events WHERE licence_id=? ORDER BY rowid",(licence_id,))
        events=[self._json_fields(x,"payload_json","signature_json") for x in events]
        return {"licence":licence,"events":events}
    def _threshold_evidence(self,policy_id:str,request_id:str)->dict:
        policy=self._one("authority/threshold_authority.sqlite","SELECT * FROM threshold_policies WHERE policy_id=?",(policy_id,))
        policy=self._json_fields(policy,"approvers_json","signature_json")
        votes=self._many("authority/threshold_authority.sqlite","SELECT * FROM threshold_votes WHERE policy_id=? AND request_id=? ORDER BY approver_entity_id",(policy_id,request_id))
        votes=[self._json_fields(x,"signature_json") for x in votes]
        return {"policy":policy,"request_id":request_id,"votes":votes}

    def _capital_evidence(self,class_id:str,action_id:str,capital_event_id:str,batch_id:str,disclosure_id:str)->dict:
        share=self._one("corporate_capital/corporate_capital.sqlite","SELECT * FROM share_classes WHERE class_id=?",(class_id,))
        share=self._json_fields(share,"rights_json")
        positions=self._many("corporate_capital/corporate_capital.sqlite","SELECT * FROM share_positions WHERE class_id=? ORDER BY holder_ref",(class_id,))
        events=self._many("corporate_capital/corporate_capital.sqlite","SELECT * FROM capital_evidence WHERE class_id=? ORDER BY created_at_ms,event_id",(class_id,))
        events=[self._json_fields(x,"payload_json","signature_json") for x in events]
        if not any(x["event_id"]==capital_event_id for x in events): raise KeyError("referenced capital event not found")
        action=self._one("corporate_actions/corporate_actions.sqlite","SELECT * FROM actions WHERE action_id=?",(action_id,)); action=self._json_fields(action,"payload_json","signature_json")
        batch=self._one("capital_accounting/capital_accounting.sqlite","SELECT * FROM accounting_batches WHERE batch_id=?",(batch_id,)); batch=self._json_fields(batch,"payload_json","signature_json")
        disclosure=self._one("corporate_capital/corporate_capital.sqlite","SELECT * FROM disclosure_snapshots WHERE snapshot_id=?",(disclosure_id,)); disclosure=self._json_fields(disclosure,"snapshot_json")
        return {"share_class":share,"positions":positions,"capital_events":events,"corporate_action":action,"accounting_batch":batch,"disclosure":disclosure}
    def _asset_and_provenance(self,asset_id:str)->dict:
        asset=self._one("asset_registry/assets.sqlite","SELECT * FROM assets WHERE asset_id=?",(asset_id,)); asset=self._json_fields(asset,"metadata_json")
        binding=self._one("asset_provenance/asset_provenance.sqlite","SELECT * FROM bindings WHERE asset_id=?",(asset_id,)); binding=self._json_fields(binding,"signature_json")
        return {"asset":asset,"provenance_binding":binding}

    def _usage_evidence(self,receipt_id:str)->dict:
        receipt=self._one("usage_control/usage.sqlite","SELECT * FROM receipts WHERE receipt_id=?",(receipt_id,))
        return self._json_fields(receipt,"evidence_json","signature_json")

    def _commodity_evidence(self,commodity_id:str,event_id:str)->dict:
        commodity=self._one("corporate_capital/corporate_capital.sqlite","SELECT * FROM digital_commodities WHERE commodity_id=?",(commodity_id,)); commodity=self._json_fields(commodity,"metadata_json"); commodity["commercialization_authority"]=bool(commodity["commercialization_authority"])
        event=self._one("corporate_capital/corporate_capital.sqlite","SELECT * FROM commodity_events WHERE event_id=? AND commodity_id=?",(event_id,commodity_id)); event=self._json_fields(event,"evidence_json","signature_json")
        event["evidence_sha256"]=_sha_bytes(_canon(event.get("evidence") or {}))
        return {"commodity":commodity,"event":event}

    def _ledger_evidence(self,checkpoint_id:str)->dict:
        rows=self._many("event_ledger/ledger.sqlite","SELECT * FROM events ORDER BY sequence")
        rows=[self._json_fields(x,"subject_ids_json","object_ids_json","signature_json") for x in rows]
        checkpoint=self._one("event_ledger/ledger.sqlite","SELECT * FROM checkpoints WHERE checkpoint_id=?",(checkpoint_id,)); checkpoint=self._json_fields(checkpoint,"signature_json")
        return {"events":rows,"checkpoint":checkpoint}

    def _trust_anchors(self)->list[dict]:
        path=self.state/"external_authorities"/"authorities.sqlite"
        if not path.is_file(): return []
        rows=self._many("external_authorities/authorities.sqlite","SELECT * FROM authorities WHERE status='ACTIVE' ORDER BY authority_id")
        return [self._json_fields(x,"jurisdictions_json","evidence_types_json") for x in rows]
    def build_bundle(self,transaction_id:str)->dict:
        record=self.get(transaction_id); refs=record["references"]
        manifests={entity_id:self._manifest(entity_id) for entity_id in record["participants"]}
        evidence={
            "transaction_record":{**self._transaction_record_body(record),"signature":record["signature"]},
            "manifests":manifests,
            "asset_provenance":self._asset_and_provenance(refs["asset_id"]),
            "rights":self._rights_evidence(refs["claim_id"]),
            "licence":self._licence_evidence(refs["licence_id"]),
            "usage_receipt":self._usage_evidence(refs["usage_receipt_id"]),
            "license_settlement":self._settlement_evidence(refs["license_settlement_id"]),
            "value_record":self._one("settlement/settlement.sqlite","SELECT * FROM value_records WHERE value_id=?",(refs["value_id"],)),
            "digital_commodity":self._commodity_evidence(refs["commodity_id"],refs["commodity_event_id"]),
            "corporate_authorization":self._threshold_evidence(refs["threshold_policy_id"],refs["threshold_request_id"]),
            "capital":self._capital_evidence(refs["share_class_id"],refs["corporate_action_id"],refs["capital_event_id"],refs["capital_accounting_batch_id"],refs["disclosure_snapshot_id"]),
            "share_settlement":self._settlement_evidence(refs["share_settlement_id"]),
            "event_ledger":self._ledger_evidence(refs["ledger_checkpoint_id"]),
            "external_trust_anchors":self._trust_anchors(),
        }
        transaction_root=_sha_bytes(_canon(evidence))
        header={"schema":BUNDLE_SCHEMA,"transaction_id":transaction_id,"issuer_entity_id":record["issuer_entity_id"],"transaction_root_sha256":transaction_root}
        signature=self.identity.sign(record["issuer_entity_id"],header)
        return {**header,"generated_at_ms":_now(),"evidence":evidence,"signature":signature,
            "evidence_boundary":{"cryptographic_validity_is_not_legal_truth":True,"recorded_rights_are_not_legal_adjudication":True,"external_trust_anchors_require_independent_real_world_trust_decisions":True}}
    def export_bundle(self,transaction_id:str,destination:str|Path)->dict:
        dest=Path(destination).resolve(); dest.mkdir(parents=True,exist_ok=True)
        bundle=self.build_bundle(transaction_id); path=dest/"TRANSACTION_BUNDLE.json"
        path.write_text(json.dumps(bundle,indent=2,sort_keys=True,default=str)+"\n",encoding="utf-8")
        (dest/"TRANSACTION_ROOT.sha256").write_text(bundle["transaction_root_sha256"]+"\n",encoding="utf-8")
        return {"path":str(path),"sha256":_sha_file(path),"transaction_root_sha256":bundle["transaction_root_sha256"],"bundle":bundle}

    def create_sovereign_export(self,transaction_id:str,destination:str|Path,portable_manager,*,backup_key:bytes|None=None)->dict:
        dest=Path(destination).resolve(); dest.mkdir(parents=True,exist_ok=True)
        public=self.export_bundle(transaction_id,dest)
        backup=portable_manager.create_encrypted_backup(dest/"STATE_BACKUP.enc",key=backup_key)
        key=base64.urlsafe_b64decode(backup["key_b64"])
        body={"schema":RECOVERY_SCHEMA,"transaction_id":transaction_id,"issuer_entity_id":public["bundle"]["issuer_entity_id"],
            "transaction_root_sha256":public["transaction_root_sha256"],"transaction_bundle_sha256":public["sha256"],
            "state_backup_sha256":backup["sha256"],"state_backup_cipher":backup["cipher"],"backup_key_sha256":_sha_bytes(key),
            "private_recovery_key_in_package":False,"created_at_ms":_now()}
        body["signature"]=self.identity.sign(body["issuer_entity_id"],{k:v for k,v in body.items() if k!="signature"})
        manifest=dest/"RECOVERY_MANIFEST.json"; manifest.write_text(json.dumps(body,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        return {"schema":RECOVERY_SCHEMA,"directory":str(dest),"transaction_root_sha256":public["transaction_root_sha256"],
            "recovery_manifest":str(manifest),"recovery_manifest_sha256":_sha_file(manifest),"state_backup":backup["path"],
            "backup_key_b64":backup["key_b64"],"backup_key_written_to_package":False}

    def status(self)->dict:
        with self._connect() as db: count=int(db.execute("SELECT COUNT(*) FROM transactions").fetchone()[0])
        return {"ready":True,"schema":BUNDLE_SCHEMA,"transactions":count,"deterministic_evidence_root":True,"encrypted_recovery_state_supported":True,"recovery_key_separate_from_export":True}
