from __future__ import annotations
from pathlib import Path
import base64, hashlib, json
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

SIG_SUITE="ENTITY-SIG-ED25519-v1"

def canonical_json(value)->bytes:
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")

def unb64(value:str)->bytes:
    return base64.urlsafe_b64decode(value+"="*(-len(value)%4))

def sha256_bytes(value:bytes)->str: return hashlib.sha256(value).hexdigest()
def sha256_file(path:str|Path)->str: return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def verify_sealed_json(document:dict, hash_field:str="evidence_sha256")->bool:
    try:
        expected=str(document[hash_field]).lower(); body=dict(document); body.pop(hash_field,None)
        return hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()==expected
    except Exception: return False

def _method(manifest:dict,key_id:str)->dict|None:
    for item in manifest.get("verification_methods") or []:
        if item.get("key_id")==key_id: return item
    return None

def verify_manifest(manifest:dict)->bool:
    try:
        if manifest.get("schema")!="sovereign-entity-manifest-v2": return False
        data=dict(manifest); sig=dict(data.pop("signature")); method=_method(data,str(sig.get("key_id") or ""))
        if not method or method.get("suite")!=SIG_SUITE or method.get("status")!="active": return False
        Ed25519PublicKey.from_public_bytes(unb64(method["public_key"])).verify(unb64(sig["signature"]),canonical_json(data)); return True
    except Exception: return False

def verify_signature_record(manifest:dict,payload,record:dict)->bool:
    try:
        if not verify_manifest(manifest) or record.get("entity_id")!=manifest.get("entity_id"): return False
        body=canonical_json(payload); digest=hashlib.sha256(body).hexdigest()
        if record.get("payload_sha256")!=digest or record.get("signature_schema")!="entity-signature-record-v2": return False
        method=_method(manifest,str(record.get("key_id") or ""))
        if not method or method.get("suite")!=record.get("suite"): return False
        status=method.get("status")
        if status not in {"active","retired","revoked"}: return False
        if status=="revoked":
            signed_at=record.get("signed_at_ms"); revoked_at=method.get("revoked_at_ms")
            if signed_at is None or revoked_at is None or int(signed_at)>int(revoked_at): return False
        signed={"signature_schema":record["signature_schema"],"entity_id":record["entity_id"],"key_id":record["key_id"],
                "suite":record["suite"],"signed_at_ms":record["signed_at_ms"],"payload_sha256":digest}
        Ed25519PublicKey.from_public_bytes(unb64(method["public_key"])).verify(unb64(record["signature"]),canonical_json(signed)); return True
    except Exception: return False

def verify_hash_chain(events:list[dict])->dict:
    previous="0"*64
    for index,event in enumerate(events):
        body=dict(event); claimed=str(body.pop("event_hash","")).lower()
        if body.get("previous_hash")!=previous: return {"valid":False,"index":index,"reason":"previous_hash_mismatch"}
        calculated=hashlib.sha256(canonical_json(body)).hexdigest()
        if claimed!=calculated: return {"valid":False,"index":index,"reason":"event_hash_mismatch"}
        previous=claimed
    return {"valid":True,"count":len(events),"root":previous}

def verify_merkle_proof(leaf_hash:str, proof:list[dict], root_hash:str)->bool:
    try:
        current=bytes.fromhex(leaf_hash)
        for step in proof:
            sibling=bytes.fromhex(step["hash"]); side=str(step["side"]).lower()
            current=hashlib.sha256((sibling+current) if side=="left" else (current+sibling)).digest()
        return current.hex()==str(root_hash).lower()
    except Exception: return False

def classify_external_payment(evidence:dict)->dict:
    level=str((evidence or {}).get("level") or "UNVERIFIED").upper()
    return {"classification":level,"external_money_movement_verified":level=="PROVIDER_CONFIRMED"}

def verify_release_manifest(manifest:dict, signer_manifest:dict)->bool:
    try:
        body=dict(manifest); signature=body.pop("signature")
        return verify_signature_record(signer_manifest,body,signature)
    except Exception: return False

def verify_file_inventory(base:str|Path, inventory:list[dict])->dict:
    root=Path(base); failures=[]
    for item in inventory:
        path=(root/str(item["path"])).resolve()
        try: path.relative_to(root.resolve())
        except ValueError: failures.append({"path":item.get("path"),"reason":"path_escape"}); continue
        if not path.is_file(): failures.append({"path":item.get("path"),"reason":"missing"}); continue
        if sha256_file(path)!=str(item.get("sha256") or "").lower(): failures.append({"path":item.get("path"),"reason":"hash_mismatch"})
    return {"valid":not failures,"checked":len(inventory),"failures":failures}

def verify_external_authority_evidence(evidence:dict, trust_record:dict)->bool:
    try:
        body=dict(evidence or {}); signature=str(body.pop("signature"))
        if body.get("schema")!="entity-external-authority-evidence-v1": return False
        if str(body.get("authority_id"))!=str(trust_record.get("authority_id")): return False
        if str(body.get("authority_type")).upper()!=str(trust_record.get("authority_type")).upper(): return False
        if str(trust_record.get("status","ACTIVE")).upper()!="ACTIVE": return False
        if str(body.get("jurisdiction")).upper() not in {str(x).upper() for x in trust_record.get("jurisdictions",[])}: return False
        if str(body.get("evidence_type")).upper() not in {str(x).upper() for x in trust_record.get("evidence_types",[])}: return False
        if not body.get("external_authority_ref") or not body.get("subject_entity_id") or not body.get("nonce"): return False
        Ed25519PublicKey.from_public_bytes(unb64(str(trust_record["public_key_b64"]))).verify(unb64(signature),canonical_json(body)); return True
    except Exception: return False

def verify_corporate_capital_tables(manifest:dict,tables:dict,trust_records:list[dict]|None=None)->dict:
    failures=[]; trust={str(x.get("authority_id")):x for x in (trust_records or [])}
    classes={str(x["class_id"]):x for x in tables.get("share_classes",[])}
    positions=tables.get("share_positions",[])
    for class_id,row in classes.items():
        authorized=int(row["authorized_units"]); issued=int(row["recorded_issued_units"]); outstanding=int(row["recorded_outstanding_units"])
        if issued>authorized: failures.append(f"{class_id}:issued_exceeds_authorized")
        if outstanding>issued: failures.append(f"{class_id}:outstanding_exceeds_issued")
        total=sum(int(x["units"]) for x in positions if str(x["class_id"])==class_id)
        if total not in {0,outstanding}: failures.append(f"{class_id}:positions_do_not_reconcile")
    verified_capital=0; verified_external=0
    for row in tables.get("capital_evidence",[]):
        payload=json.loads(row.get("payload_json") or "{}")
        body={"schema":"entity-capital-evidence-v1","event_id":row["event_id"],"event_nonce":row["event_nonce"],"issuer_entity_id":row["issuer_entity_id"],"event_type":row["event_type"],"class_id":row.get("class_id"),"quantity":int(row["quantity"]),"payload":payload,"external_authority_ref":row.get("external_authority_ref"),"created_at_ms":int(row["created_at_ms"])}
        sig=json.loads(row.get("signature_json") or "{}")
        if not verify_signature_record(manifest,body,sig): failures.append(f"{row['event_id']}:entity_signature_invalid")
        else: verified_capital+=1
        external=dict(payload.get("external_evidence") or {})
        if external:
            record=trust.get(str(external.get("authority_id")))
            if not record or not verify_external_authority_evidence(external,record): failures.append(f"{row['event_id']}:external_authority_invalid")
            elif external.get("external_authority_ref")!=row.get("external_authority_ref"): failures.append(f"{row['event_id']}:external_ref_mismatch")
            else: verified_external+=1
    for row in tables.get("valuation_evidence",[]):
        kind=str(row.get("evidence_kind") or ""); origin=str(row.get("evidence_origin") or "")
        if kind=="MODELLED_INDICATIVE_VALUE" and origin!="DERIVED_INFERENCE": failures.append(f"{row['evidence_id']}:modelled_value_origin_invalid")
        if kind.startswith("EXTERNAL_MARKET_"):
            if origin!="EXTERNAL_AUTHORITATIVE_RECORD": failures.append(f"{row['evidence_id']}:market_value_origin_invalid")
            meta=json.loads(row.get("metadata_json") or "{}"); external=dict(meta.get("external_evidence") or {}); record=trust.get(str(external.get("authority_id")))
            if not record or not verify_external_authority_evidence(external,record): failures.append(f"{row['evidence_id']}:market_external_authority_invalid")
    verified_disclosures=0
    for row in tables.get("disclosure_snapshots",[]):
        try:
            snapshot=json.loads(row["snapshot_json"]); digest=hashlib.sha256(canonical_json(snapshot)).hexdigest()
            if digest!=str(row["snapshot_sha256"]): failures.append(f"{row['snapshot_id']}:disclosure_hash_invalid")
            else: verified_disclosures+=1
        except Exception: failures.append(f"{row.get('snapshot_id','unknown')}:disclosure_unreadable")
    return {"valid":not failures,"failures":failures,"share_classes_checked":len(classes),"positions_checked":len(positions),"capital_events_verified":verified_capital,"external_evidence_verified":verified_external,"disclosures_verified":verified_disclosures}

def verify_corporate_action_tables(manifest:dict,tables:dict,trust_records:list[dict]|None=None)->dict:
    failures=[]; verified=0; trust={str(x.get("authority_id")):x for x in (trust_records or [])}
    for row in tables.get("actions",[]):
        try:
            payload=json.loads(row.get("payload_json") or "{}")
            body={"schema":"entity-corporate-action-evidence-v1","issuer_entity_id":row["issuer_entity_id"],"class_id":row["class_id"],"action_type":row["action_type"],"jurisdiction":row["jurisdiction"],"instrument_class":row["instrument_class"],"effective_at_ms":int(row["effective_at_ms"]),"external_authority_ref":row["external_authority_ref"],"payload":payload}
            sig=json.loads(row.get("signature_json") or "{}")
            if not verify_signature_record(manifest,body,sig): failures.append(f"{row['action_id']}:signature_invalid")
            else: verified+=1
            external=dict(payload.get("external_evidence") or {}); record=trust.get(str(external.get("authority_id")))
            if not record or not verify_external_authority_evidence(external,record): failures.append(f"{row['action_id']}:external_authority_invalid")
            elif external.get("external_authority_ref")!=row.get("external_authority_ref"): failures.append(f"{row['action_id']}:external_ref_mismatch")
            if str(row.get("status")) not in {"RECORDED","RECONCILED","MISMATCH"}: failures.append(f"{row['action_id']}:invalid_status")
        except Exception: failures.append(f"{row.get('action_id','unknown')}:unreadable")
    return {"valid":not failures,"failures":failures,"actions_verified":verified}

def verify_capital_accounting_tables(manifest:dict,tables:dict,trust_records:list[dict]|None=None)->dict:
    failures=[]; verified=0; trust={str(x.get("authority_id")):x for x in (trust_records or [])}
    for row in tables.get("accounting_batches",[]):
        try:
            payload=json.loads(row.get("payload_json") or "{}"); sig=json.loads(row.get("signature_json") or "{}")
            if not verify_signature_record(manifest,payload,sig): failures.append(f"{row['batch_id']}:signature_invalid")
            external=dict(payload.get("external_evidence") or {}); record=trust.get(str(external.get("authority_id")))
            if not record or not verify_external_authority_evidence(external,record): failures.append(f"{row['batch_id']}:external_authority_invalid")
            elif external.get("external_authority_ref")!=row.get("external_authority_ref"): failures.append(f"{row['batch_id']}:external_ref_mismatch")
            totals={}
            for item in payload.get("entries",[]):
                unit=str(item.get("currency") or "").upper(); direction=str(item.get("direction") or "").upper(); amount=int(item.get("amount_minor",0)); bucket=totals.setdefault(unit,{"DEBIT":0,"CREDIT":0}); bucket[direction]+=amount
            if any(x["DEBIT"]!=x["CREDIT"] for x in totals.values()): failures.append(f"{row['batch_id']}:unbalanced")
            else: verified+=1
        except Exception: failures.append(f"{row.get('batch_id','unknown')}:unreadable")
    return {"valid":not failures,"failures":failures,"accounting_batches_verified":verified}

LICENCE_STATES={"DRAFT","OFFERED","COUNTERED","ACCEPTED","ACTIVE","SUSPENDED","REVOKED_FOR_FUTURE_USE","EXPIRED","TERMINATED","DISPUTED","CLOSED"}
USAGE_ASSURANCE={"DECLARED":1,"ENTITY_GATEWAY_OBSERVED":2,"COUNTERPARTY_ATTESTED":3,"ENVIRONMENT_ATTESTED":4}
USAGE_ORIGIN={"DECLARED":"ENTITY_ASSERTION","ENTITY_GATEWAY_OBSERVED":"DIRECT_OBSERVATION","COUNTERPARTY_ATTESTED":"COUNTERPARTY_ATTESTATION","ENVIRONMENT_ATTESTED":"EXTERNAL_AUTHORITATIVE_RECORD"}

def verify_licence_record(licence:dict, manifests:dict[str,dict])->dict:
    failures=[]; events=list(licence.get("events") or [])
    if str(licence.get("state") or "") not in LICENCE_STATES: failures.append("invalid_licence_state")
    previous=None; verified=0
    for event in events:
        body={"schema":"entity-licence-event-v2","event_id":event.get("event_id"),"licence_id":event.get("licence_id"),
          "event_type":event.get("event_type"),"actor_entity_id":event.get("actor_entity_id"),"from_state":event.get("from_state"),
          "to_state":event.get("to_state"),"terms_version":event.get("terms_version"),"payload":event.get("payload") or {},"created_at_ms":event.get("created_at_ms")}
        actor=str(event.get("actor_entity_id") or ""); manifest=manifests.get(actor)
        if str(event.get("licence_id"))!=str(licence.get("licence_id")): failures.append(f"{event.get('event_id')}:licence_id_mismatch")
        if previous is not None and event.get("from_state")!=previous: failures.append(f"{event.get('event_id')}:state_chain_mismatch")
        if event.get("to_state") not in LICENCE_STATES: failures.append(f"{event.get('event_id')}:invalid_to_state")
        if not manifest or not verify_signature_record(manifest,body,event.get("signature") or {}): failures.append(f"{event.get('event_id')}:signature_invalid")
        else: verified+=1
        previous=event.get("to_state")
    if events and previous!=licence.get("state"): failures.append("final_state_mismatch")
    return {"valid":not failures,"failures":failures,"events_verified":verified,"final_state":licence.get("state")}

def verify_usage_receipt(receipt:dict, signer_manifest:dict)->dict:
    failures=[]; assurance=str(receipt.get("assurance") or "").upper(); level=receipt.get("assurance_level")
    if assurance not in USAGE_ASSURANCE: failures.append("invalid_assurance")
    elif int(level)!=USAGE_ASSURANCE[assurance]: failures.append("assurance_level_mismatch")
    expected_origin=USAGE_ORIGIN.get(assurance)
    if expected_origin and str(receipt.get("evidence_origin") or "").upper()!=expected_origin: failures.append("evidence_origin_mismatch")
    evidence=dict(receipt.get("evidence") or {})
    if hashlib.sha256(canonical_json(evidence)).hexdigest()!=str(receipt.get("evidence_sha256") or "").lower(): failures.append("evidence_hash_mismatch")
    body={"schema":"entity-usage-receipt-v2","receipt_id":receipt.get("receipt_id"),"licence_id":receipt.get("licence_id"),
      "actor_entity_id":receipt.get("actor_entity_id"),"asset_id":receipt.get("asset_id"),"use_type":receipt.get("use_type"),
      "purpose":receipt.get("purpose"),"quantity":receipt.get("quantity"),"assurance":assurance,"assurance_level":level,
      "evidence_origin":receipt.get("evidence_origin"),"evidence_sha256":receipt.get("evidence_sha256"),"nonce":receipt.get("nonce"),
      "created_at_ms":receipt.get("created_at_ms")}
    if not verify_signature_record(signer_manifest,body,receipt.get("signature") or {}): failures.append("signature_invalid")
    independent=assurance=="ENVIRONMENT_ATTESTED" and not failures
    return {"valid":not failures,"failures":failures,"assurance":assurance,"independently_verified":independent,
      "meaning":"verification is limited to the declared assurance class and supplied evidence"}
