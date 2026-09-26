from __future__ import annotations
from pathlib import Path
import argparse, base64, hashlib, json, sys
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

SIG_SUITE="ENTITY-SIG-ED25519-v1"
ZERO_HASH="0"*64

def canon(v)->bytes: return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()
def sha(v)->str: return hashlib.sha256(v if isinstance(v,(bytes,bytearray)) else canon(v)).hexdigest()
def unb64(v:str)->bytes: return base64.urlsafe_b64decode(str(v)+"="*(-len(str(v))%4))
def method(manifest,key_id): return next((x for x in manifest.get("verification_methods",[]) if x.get("key_id")==key_id),None)

def verify_manifest(manifest:dict)->bool:
    try:
        if manifest.get("schema")!="sovereign-entity-manifest-v2": return False
        body=dict(manifest); sig=dict(body.pop("signature")); m=method(body,str(sig.get("key_id") or ""))
        if not m or m.get("suite")!=SIG_SUITE or m.get("status")!="active": return False
        Ed25519PublicKey.from_public_bytes(unb64(m["public_key"])).verify(unb64(sig["signature"]),canon(body)); return True
    except Exception: return False

def verify_sig(manifest:dict,payload:dict,record:dict)->bool:
    try:
        if not verify_manifest(manifest) or record.get("entity_id")!=manifest.get("entity_id"): return False
        digest=sha(payload)
        if record.get("signature_schema")!="entity-signature-record-v2" or record.get("payload_sha256")!=digest: return False
        m=method(manifest,str(record.get("key_id") or ""))
        if not m or m.get("suite")!=record.get("suite"): return False
        signed={"signature_schema":record["signature_schema"],"entity_id":record["entity_id"],"key_id":record["key_id"],"suite":record["suite"],"signed_at_ms":record["signed_at_ms"],"payload_sha256":digest}
        Ed25519PublicKey.from_public_bytes(unb64(m["public_key"])).verify(unb64(record["signature"]),canon(signed)); return True
    except Exception: return False
def trust_map(rows:list[dict])->dict: return {str(x.get("authority_id")):x for x in rows}

def verify_external(evidence:dict,trust:dict)->bool:
    try:
        body=dict(evidence or {}); signature=str(body.pop("signature")); row=trust.get(str(body.get("authority_id")))
        if not row or body.get("schema")!="entity-external-authority-evidence-v1" or row.get("status")!="ACTIVE": return False
        if str(body.get("authority_type")).upper()!=str(row.get("authority_type")).upper(): return False
        if str(body.get("jurisdiction")).upper() not in {str(x).upper() for x in row.get("jurisdictions",[])}: return False
        if str(body.get("evidence_type")).upper() not in {str(x).upper() for x in row.get("evidence_types",[])}: return False
        Ed25519PublicKey.from_public_bytes(unb64(row["public_key_b64"])).verify(unb64(signature),canon(body)); return True
    except Exception: return False

def merkle_root(hashes:list[str])->str:
    if not hashes: return ZERO_HASH
    layer=[bytes.fromhex(x) for x in hashes]
    while len(layer)>1:
        if len(layer)%2: layer.append(layer[-1])
        layer=[hashlib.sha256(layer[i]+layer[i+1]).digest() for i in range(0,len(layer),2)]
    return layer[0].hex()

def add(checks:dict,name:str,ok:bool,detail=None):
    checks[name]={"pass":bool(ok)}
    if detail is not None: checks[name]["detail"]=detail
    return bool(ok)

def get_manifest(manifests:dict,entity_id:str)->dict:
    m=manifests.get(str(entity_id))
    if not m: raise KeyError(f"manifest missing for {entity_id}")
    return m
def verify_asset_provenance(section:dict,manifests:dict,issuer:str)->bool:
    asset=section["asset"]; binding=section["provenance_binding"]
    if asset.get("controller_entity_id")!=issuer or binding.get("controller_entity_id")!=issuer: return False
    if asset.get("asset_id")!=binding.get("asset_id") or asset.get("content_sha256")!=binding.get("content_sha256"): return False
    body={"schema":"entity-provenance-binding-v2","asset_id":binding["asset_id"],"controller_entity_id":binding["controller_entity_id"],
        "content_sha256":binding["content_sha256"],"soft_binding_type":binding.get("soft_binding_type"),"soft_binding_value":binding.get("soft_binding_value"),
        "c2pa_manifest_sha256":binding.get("c2pa_manifest_sha256"),"c2pa_reference":binding.get("c2pa_reference"),"provenance_status":"RECORDED",
        "truth_status":"NOT_ASSESSED","evidence_origin":binding["evidence_origin"],"recorded_at_ms":binding["recorded_at_ms"]}
    return verify_sig(get_manifest(manifests,issuer),body,binding.get("signature") or {})

def verify_rights(section:dict,manifests:dict,asset_id:str)->bool:
    claim=section["claim"]; claimant=str(claim["claimant_entity_id"])
    if claim.get("asset_id")!=asset_id: return False
    body={"schema":"entity-rights-claim-v2","claim_id":claim["claim_id"],"asset_id":claim["asset_id"],"claimant_entity_id":claimant,
        "right_type":claim["right_type"],"share":claim["share"],"territory":claim["territory"],"jurisdiction":claim["jurisdiction"],
        "legal_basis":claim["legal_basis"],"scope":claim.get("scope") or {},"evidence":claim.get("evidence") or {},"evidence_origin":claim["evidence_origin"],
        "effective_at_ms":claim["effective_at_ms"],"expires_at_ms":claim.get("expires_at_ms"),"verification_level":"SELF_ASSERTED","lifecycle_status":"ACTIVE","supersedes_claim_id":claim.get("supersedes_claim_id")}
    if not verify_sig(get_manifest(manifests,claimant),body,claim.get("signature") or {}): return False
    authoritative=False
    for event in section.get("events",[]):
        ebody={"claim_id":event["claim_id"],"event_type":event["event_type"],"actor_entity_id":event["actor_entity_id"],"payload":event.get("payload") or {},"timestamp_ms":event["timestamp_ms"]}
        actor_manifest=get_manifest(manifests,event["actor_entity_id"])
        if not verify_sig(actor_manifest,ebody,event.get("signature") or {}): return False
        if event["event_type"]=="claim.verification_added" and (event.get("payload") or {}).get("verification_level")=="AUTHORITATIVELY_VERIFIED":
            roles={str(x).upper() for x in (actor_manifest.get("metadata") or {}).get("authority_roles",[])}
            authoritative="RIGHTS_AUTHORITY" in roles and bool((event.get("payload") or {}).get("evidence",{}).get("authority_reference"))
    return authoritative and claim.get("verification_level")=="AUTHORITATIVELY_VERIFIED" and claim.get("lifecycle_status")=="ACTIVE"
def verify_licence(section:dict,manifests:dict,asset_id:str,claim_id:str,issuer:str,counterparty:str)->bool:
    lic=section["licence"]
    if lic.get("grantor_entity_id")!=issuer or lic.get("licensee_entity_id")!=counterparty: return False
    terms=lic.get("terms") or {}
    if asset_id not in set(terms.get("assets") or []) or claim_id not in set(lic.get("authority_basis") or []): return False
    previous=None; first_terms=None
    for event in section.get("events",[]):
        body={"schema":"entity-licence-event-v2","event_id":event["event_id"],"licence_id":event["licence_id"],"event_type":event["event_type"],
            "actor_entity_id":event["actor_entity_id"],"from_state":event.get("from_state"),"to_state":event.get("to_state"),"terms_version":event["terms_version"],
            "payload":event.get("payload") or {},"created_at_ms":event["created_at_ms"]}
        if not verify_sig(get_manifest(manifests,event["actor_entity_id"]),body,event.get("signature") or {}): return False
        if previous is not None and event.get("from_state")!=previous: return False
        if event.get("event_type")=="LICENCE_DRAFT_CREATED": first_terms=(event.get("payload") or {}).get("terms")
        previous=event.get("to_state")
    return bool(section.get("events")) and previous==lic.get("state")=="ACTIVE" and first_terms==terms

def verify_usage(receipt:dict,manifests:dict,licence:dict,asset_id:str,counterparty:str)->bool:
    assurance=str(receipt.get("assurance") or "").upper(); levels={"DECLARED":1,"ENTITY_GATEWAY_OBSERVED":2,"COUNTERPARTY_ATTESTED":3,"ENVIRONMENT_ATTESTED":4}
    if assurance not in levels or int(receipt.get("assurance_level",0))!=levels[assurance]: return False
    evidence=receipt.get("evidence") or {}
    if sha(evidence)!=str(receipt.get("evidence_sha256") or "").lower(): return False
    if receipt.get("asset_id")!=asset_id or receipt.get("actor_entity_id")!=counterparty or receipt.get("licence_id")!=licence.get("licence_id"): return False
    if receipt.get("use_type") not in set((licence.get("terms") or {}).get("rights") or []): return False
    if receipt.get("purpose")!=(licence.get("terms") or {}).get("purpose"): return False
    body={"schema":"entity-usage-receipt-v2","receipt_id":receipt["receipt_id"],"licence_id":receipt["licence_id"],"actor_entity_id":receipt["actor_entity_id"],
        "asset_id":receipt["asset_id"],"use_type":receipt["use_type"],"purpose":receipt["purpose"],"quantity":receipt["quantity"],"assurance":assurance,
        "assurance_level":receipt["assurance_level"],"evidence_origin":receipt["evidence_origin"],"evidence_sha256":receipt["evidence_sha256"],"nonce":receipt["nonce"],"created_at_ms":receipt["created_at_ms"]}
    signer=str((receipt.get("signature") or {}).get("entity_id") or "")
    return assurance=="ENTITY_GATEWAY_OBSERVED" and verify_sig(get_manifest(manifests,signer),body,receipt.get("signature") or {})
def verify_settlement(section:dict,manifests:dict,trust:dict,*,obligation_ref:str,payer:str,payee:str)->bool:
    s=section["settlement"]
    if s.get("payer_entity_id")!=payer or s.get("payee_entity_id")!=payee or s.get("obligation_ref")!=obligation_ref: return False
    if s.get("state")!="CONFIRMED" or s.get("settlement_kind")!="EXTERNAL_PAYMENT" or not bool(s.get("money_movement_verified")): return False
    package=s.get("evidence") or {}
    if package.get("level")!="PROVIDER_CONFIRMED" or package.get("external_cryptographic_verification_required") is not True: return False
    external=package.get("evidence") or {}
    if external.get("evidence_type")!="PAYMENT_SETTLEMENT_CONFIRMATION" or external.get("subject_entity_id")!=payee or not verify_external(external,trust): return False
    ep=external.get("payload") or {}
    if str(ep.get("settlement_id"))!=str(s["settlement_id"]) or int(ep.get("amount_units",-1))!=int(s["amount_units"]) or str(ep.get("currency")).upper()!=str(s["currency"]).upper(): return False
    for event in section.get("events",[]):
        body={"schema":"entity-settlement-event-v2","event_id":event["event_id"],"settlement_id":event["settlement_id"],"event_type":event["event_type"],
            "actor_entity_id":event["actor_entity_id"],"from_state":event.get("from_state"),"to_state":event.get("to_state"),"payload":event.get("payload") or {},"created_at_ms":event["created_at_ms"]}
        if not verify_sig(get_manifest(manifests,event["actor_entity_id"]),body,event.get("signature") or {}): return False
    finals=[x for x in section.get("postings",[]) if x.get("posting_kind")=="FINAL"]
    if len(finals)!=2: return False
    deb=[x for x in finals if x.get("direction")=="DEBIT" and x.get("entity_id")==payer]
    cre=[x for x in finals if x.get("direction")=="CREDIT" and x.get("entity_id")==payee]
    return len(deb)==1 and len(cre)==1 and int(deb[0]["amount_units"])==int(cre[0]["amount_units"])==int(s["amount_units"]) and deb[0]["currency"]==cre[0]["currency"]==s["currency"]

def verify_value(value:dict,asset_id:str,settlement:dict)->bool:
    return value.get("asset_ref")==asset_id and value.get("state")=="REALIZED" and bool(value.get("realized_external")) and value.get("settlement_id")==settlement.get("settlement_id") and int(value.get("amount_units",-1))==int(settlement.get("amount_units",-2)) and value.get("currency")==settlement.get("currency")
def verify_commodity(section:dict,manifests:dict,issuer:str,asset_id:str,receipt_id:str,licence_id:str,settlement:dict)->bool:
    c=section["commodity"]; e=section["event"]
    if c.get("corporate_entity_id")!=issuer or c.get("asset_ref")!=asset_id or not bool(c.get("commercialization_authority")): return False
    evidence=e.get("evidence") or {}
    if evidence.get("usage_receipt_id")!=receipt_id or evidence.get("licence_id")!=licence_id or evidence.get("settlement_id")!=settlement.get("settlement_id"): return False
    if sha(evidence)!=str(e.get("evidence_sha256") or "").lower(): return False
    if e.get("commodity_id")!=c.get("commodity_id") or e.get("corporate_entity_id")!=issuer or e.get("assurance_level")!="ENTITY_GATEWAY_OBSERVED": return False
    if int(e.get("recognized_revenue_units",-1))!=int(settlement.get("amount_units",-2)) or int(e.get("obligation_units",-1))!=int(settlement.get("amount_units",-2)): return False
    body={"schema":"entity-digital-commodity-usage-v1","event_id":e["event_id"],"event_nonce":e["event_nonce"],"commodity_id":e["commodity_id"],
        "corporate_entity_id":e["corporate_entity_id"],"usage_class":e["usage_class"],"assurance_level":e["assurance_level"],"quantity":e["quantity"],"unit":e["unit"],
        "obligation_units":e["obligation_units"],"recognized_revenue_units":e["recognized_revenue_units"],"cash_received_units":e["cash_received_units"],
        "currency":e.get("currency"),"evidence_origin":e["evidence_origin"],"evidence_sha256":e["evidence_sha256"],"created_at_ms":e["created_at_ms"]}
    return verify_sig(get_manifest(manifests,issuer),body,e.get("signature") or {})

def verify_threshold(section:dict,manifests:dict,issuer:str,class_id:str)->bool:
    p=section["policy"]; request_id=str(section["request_id"])
    if p.get("controller_entity_id")!=issuer or p.get("status")!="ACTIVE": return False
    body={"schema":"entity-threshold-authority-v1","policy_id":p["policy_id"],"controller_entity_id":issuer,"operation":p["operation"],
        "approvers":p.get("approvers") or [],"threshold":int(p["threshold_n"]),"status":"ACTIVE","created_at_ms":p["created_at_ms"]}
    if not verify_sig(get_manifest(manifests,issuer),body,p.get("signature") or {}): return False
    approved=set()
    for vote in section.get("votes",[]):
        if vote.get("policy_id")!=p["policy_id"] or vote.get("request_id")!=request_id or vote.get("object_ref")!=class_id: return False
        vb={"schema":"entity-threshold-vote-v1","vote_id":vote["vote_id"],"policy_id":vote["policy_id"],"request_id":vote["request_id"],
            "approver_entity_id":vote["approver_entity_id"],"operation":p["operation"],"object_ref":vote.get("object_ref"),"created_at_ms":vote["created_at_ms"]}
        if vote["approver_entity_id"] not in set(p.get("approvers") or []) or not verify_sig(get_manifest(manifests,vote["approver_entity_id"]),vb,vote.get("signature") or {}): return False
        approved.add(vote["approver_entity_id"])
    return p.get("operation")=="SHARE_ISSUANCE" and len(approved)>=int(p["threshold_n"])
def verify_capital(section:dict,manifests:dict,trust:dict,issuer:str,threshold:dict,capital_event_id:str)->bool:
    share=section["share_class"]; positions=section.get("positions",[]); action=section["corporate_action"]
    if share.get("issuer_entity_id")!=issuer or action.get("issuer_entity_id")!=issuer or action.get("class_id")!=share.get("class_id") or action.get("status")!="RECONCILED" or action.get("action_type")!="ISSUANCE": return False
    authorized=int(share["authorized_units"]); issued=int(share["recorded_issued_units"]); outstanding=int(share["recorded_outstanding_units"])
    if not (0<=outstanding<=issued<=authorized) or sum(int(x["units"]) for x in positions)!=outstanding: return False
    ap=action.get("payload") or {}; auth=ap.get("authority") or {}; policy=threshold["policy"]
    if auth.get("threshold_policy_id")!=policy.get("policy_id") or auth.get("threshold_request_id")!=threshold.get("request_id") or auth.get("approved") is not True: return False
    external=ap.get("external_evidence") or {}
    if external.get("subject_entity_id")!=issuer or not verify_external(external,trust): return False
    expected=ap.get("expected_post_snapshot") or {}
    actual_positions={str(x["holder_ref"]):int(x["units"]) for x in positions}
    if int(expected.get("authorized_units",-1))!=authorized or int(expected.get("recorded_issued_units",-1))!=issued or {str(k):int(v) for k,v in (expected.get("positions") or {}).items()}!=actual_positions: return False
    action_body={"schema":"entity-corporate-action-evidence-v1","issuer_entity_id":issuer,"class_id":share["class_id"],"action_type":action["action_type"],
        "jurisdiction":action["jurisdiction"],"instrument_class":action["instrument_class"],"effective_at_ms":action["effective_at_ms"],
        "external_authority_ref":action["external_authority_ref"],"payload":ap}
    if not verify_sig(get_manifest(manifests,issuer),action_body,action.get("signature") or {}): return False
    seen=False
    for event in section.get("capital_events",[]):
        payload=event.get("payload") or {}; body={"schema":"entity-capital-evidence-v1","event_id":event["event_id"],"event_nonce":event["event_nonce"],
            "issuer_entity_id":event["issuer_entity_id"],"event_type":event["event_type"],"class_id":event.get("class_id"),"quantity":int(event["quantity"]),
            "payload":payload,"external_authority_ref":event.get("external_authority_ref"),"created_at_ms":event["created_at_ms"]}
        if not verify_sig(get_manifest(manifests,issuer),body,event.get("signature") or {}): return False
        ext=payload.get("external_evidence") or {}
        if ext and (ext.get("subject_entity_id")!=issuer or not verify_external(ext,trust)): return False
        if event["event_id"]==capital_event_id: seen=event["event_type"]=="CAPITALIZATION_SNAPSHOT_RECORDED"
    return seen
def verify_capital_accounting(batch:dict,manifests:dict,trust:dict,issuer:str,capital_event_id:str,expected_amount:int,currency:str)->bool:
    if batch.get("issuer_entity_id")!=issuer: return False
    payload=batch.get("payload") or {}
    if not verify_sig(get_manifest(manifests,issuer),payload,batch.get("signature") or {}): return False
    external=payload.get("external_evidence") or {}
    if external.get("subject_entity_id")!=issuer or external.get("evidence_type")!="ACCOUNTING_JOURNAL" or not verify_external(external,trust): return False
    entries=[x for x in payload.get("entries",[]) if x.get("capital_event_id")==capital_event_id and str(x.get("currency")).upper()==currency.upper()]
    debits=sum(int(x["amount_minor"]) for x in entries if x.get("direction")=="DEBIT")
    credits=sum(int(x["amount_minor"]) for x in entries if x.get("direction")=="CREDIT")
    return debits==credits==int(expected_amount) and (payload.get("totals") or {}).get(currency.upper(),{}).get("DEBIT")==int(expected_amount) and (payload.get("totals") or {}).get(currency.upper(),{}).get("CREDIT")==int(expected_amount)

def verify_disclosure(row:dict,issuer:str,share:dict,commodity_event:dict)->bool:
    snap=row.get("snapshot") or {}
    if row.get("issuer_entity_id")!=issuer or snap.get("issuer_entity_id")!=issuer: return False
    if sha(snap)!=str(row.get("snapshot_sha256") or "").lower(): return False
    cap=snap.get("capitalization") or {}
    if int(cap.get("authorized_units",-1))!=int(share["authorized_units"]) or int(cap.get("recorded_issued_units",-1))!=int(share["recorded_issued_units"]) or int(cap.get("recorded_outstanding_units",-1))!=int(share["recorded_outstanding_units"]): return False
    currency=str(commodity_event.get("currency") or "NON_MONETARY")
    econ=(snap.get("economics_by_currency") or {}).get(currency) or {}
    return int(snap.get("digital_commodities",0))>=1 and int(econ.get("recognized_revenue_units",-1))>=int(commodity_event.get("recognized_revenue_units",0)) and "usage does not establish market price" in set(snap.get("limitations") or [])
def verify_ledger(section:dict,manifests:dict)->bool:
    prior=ZERO_HASH; hashes=[]
    for row in section.get("events",[]):
        if row.get("prior_hash")!=prior: return False
        body={"schema":row["schema_version"],"event_id":row["event_id"],"event_type":row["event_type"],"actor_entity_id":row["actor_entity_id"],
            "subject_ids":row.get("subject_ids") or [],"object_ids":row.get("object_ids") or [],"payload_hash":row["payload_hash"],"evidence_origin":row["evidence_origin"],
            "confidence":row["confidence"],"timestamp_ms":row["timestamp_ms"],"prior_hash":row["prior_hash"]}
        sig=row.get("signature") or {}
        if not verify_sig(get_manifest(manifests,row["actor_entity_id"]),body,sig): return False
        calculated=sha({"body":body,"signature":sig})
        if calculated!=row.get("event_hash"): return False
        prior=calculated; hashes.append(calculated)
    cp=section.get("checkpoint") or {}
    selected=[x for x in section.get("events",[]) if int(cp.get("from_sequence",0))<=int(x["sequence"])<=int(cp.get("to_sequence",-1))]
    root=merkle_root([x["event_hash"] for x in selected])
    if len(selected)!=int(cp.get("event_count",-1)) or root!=cp.get("merkle_root") or (selected and selected[-1]["event_hash"]!=cp.get("head_hash")): return False
    body={"schema":"entity-ledger-checkpoint-v1","checkpoint_id":cp["checkpoint_id"],"from_sequence":cp["from_sequence"],"to_sequence":cp["to_sequence"],
        "event_count":cp["event_count"],"merkle_root":cp["merkle_root"],"head_hash":cp["head_hash"],"created_at_ms":cp["created_at_ms"],"signer_entity_id":cp["signer_entity_id"]}
    return bool(selected) and verify_sig(get_manifest(manifests,cp["signer_entity_id"]),body,cp.get("signature") or {})

def verify_bundle(bundle:dict)->dict:
    checks={}; failures=[]
    evidence=bundle.get("evidence") or {}; tx=evidence.get("transaction_record") or {}; refs=tx.get("references") or {}; manifests=evidence.get("manifests") or {}; issuer=str(bundle.get("issuer_entity_id") or "")
    expected_root=sha(evidence); add(checks,"transaction_root",expected_root==bundle.get("transaction_root_sha256"))
    header={"schema":bundle.get("schema"),"transaction_id":bundle.get("transaction_id"),"issuer_entity_id":issuer,"transaction_root_sha256":bundle.get("transaction_root_sha256")}
    add(checks,"bundle_signature",issuer in manifests and verify_sig(manifests[issuer],header,bundle.get("signature") or {}))
    txbody={k:v for k,v in tx.items() if k!="signature"}
    add(checks,"transaction_record_signature",issuer in manifests and verify_sig(manifests[issuer],txbody,tx.get("signature") or {}))
    add(checks,"all_entity_manifests",bool(manifests) and all(verify_manifest(x) for x in manifests.values()))
    trust=trust_map(evidence.get("external_trust_anchors") or [])
    licence=(evidence.get("licence") or {}).get("licence") or {}; counterparty=str(licence.get("licensee_entity_id") or "")
    asset=(evidence.get("asset_provenance") or {}).get("asset") or {}; asset_id=str(asset.get("asset_id") or "")
    add(checks,"asset_provenance",verify_asset_provenance(evidence.get("asset_provenance") or {},manifests,issuer))
    rights=evidence.get("rights") or {}; claim=(rights.get("claim") or {}); add(checks,"rights_claim",verify_rights(rights,manifests,asset_id))
    add(checks,"signed_licence",verify_licence(evidence.get("licence") or {},manifests,asset_id,str(claim.get("claim_id") or ""),issuer,counterparty))
    receipt=evidence.get("usage_receipt") or {}; add(checks,"usage_receipt",verify_usage(receipt,manifests,licence,asset_id,counterparty))
    lic_set=(evidence.get("license_settlement") or {}).get("settlement") or {}
    add(checks,"license_settlement",verify_settlement(evidence.get("license_settlement") or {},manifests,trust,obligation_ref=str(licence.get("licence_id") or ""),payer=counterparty,payee=issuer))
    add(checks,"realized_value",verify_value(evidence.get("value_record") or {},asset_id,lic_set))
    commodity=evidence.get("digital_commodity") or {}; commodity_event=commodity.get("event") or {}
    add(checks,"digital_commodity",verify_commodity(commodity,manifests,issuer,asset_id,str(receipt.get("receipt_id") or ""),str(licence.get("licence_id") or ""),lic_set))
    capital=evidence.get("capital") or {}; share=capital.get("share_class") or {}; class_id=str(share.get("class_id") or "")
    threshold=evidence.get("corporate_authorization") or {}; add(checks,"corporate_authorization",verify_threshold(threshold,manifests,issuer,class_id))
    capital_event_id=str(refs.get("capital_event_id") or "")
    add(checks,"share_issuance_cap_table",verify_capital(capital,manifests,trust,issuer,threshold,capital_event_id))
    action=capital.get("corporate_action") or {}; financial=(action.get("payload") or {}).get("financial_effect") or {}; share_amount=int(financial.get("consideration_minor",-1)); share_currency=str(financial.get("currency") or "").upper()
    add(checks,"capital_accounting",share_amount>0 and bool(share_currency) and verify_capital_accounting(capital.get("accounting_batch") or {},manifests,trust,issuer,capital_event_id,share_amount,share_currency))
    add(checks,"share_settlement",verify_settlement(evidence.get("share_settlement") or {},manifests,trust,obligation_ref=capital_event_id,payer=counterparty,payee=issuer))
    add(checks,"disclosure_snapshot",verify_disclosure(capital.get("disclosure") or {},issuer,share,commodity_event))
    add(checks,"event_ledger_checkpoint",verify_ledger(evidence.get("event_ledger") or {},manifests))
    for name,item in checks.items():
        if not item["pass"]: failures.append(name)
    summary={"schema":"entity-transaction-independent-verification-v1","transaction_id":bundle.get("transaction_id"),"transaction_root_sha256":bundle.get("transaction_root_sha256"),"valid":not failures,"failed_checks":sorted(failures),"checks":{k:v["pass"] for k,v in sorted(checks.items())}}
    summary["result_sha256"]=sha({k:v for k,v in summary.items() if k!="result_sha256"})
    return summary

def verify_recovery_package(bundle:dict,bundle_path:Path,manifest_path:Path,backup_path:Path)->bool:
    try:
        record=json.loads(manifest_path.read_text(encoding="utf-8")); signature=dict(record.get("signature") or {}); body={k:v for k,v in record.items() if k!="signature"}
        issuer=str(bundle.get("issuer_entity_id") or ""); manifests=(bundle.get("evidence") or {}).get("manifests") or {}
        if body.get("schema")!="entity-sovereign-transaction-export-v1" or body.get("issuer_entity_id")!=issuer: return False
        if body.get("transaction_root_sha256")!=bundle.get("transaction_root_sha256"): return False
        if body.get("transaction_bundle_sha256")!=hashlib.sha256(bundle_path.read_bytes()).hexdigest(): return False
        if body.get("state_backup_sha256")!=hashlib.sha256(backup_path.read_bytes()).hexdigest(): return False
        if body.get("private_recovery_key_in_package") is not False: return False
        return verify_sig(get_manifest(manifests,issuer),body,signature)
    except Exception: return False

def main(argv=None)->int:
    ap=argparse.ArgumentParser(description="Implementation-independent verifier for ENTITY Transaction Evidence Bundle v1")
    ap.add_argument("bundle"); ap.add_argument("--json",action="store_true"); ap.add_argument("--recovery-manifest"); ap.add_argument("--state-backup")
    args=ap.parse_args(argv); bundle_path=Path(args.bundle); bundle=json.loads(bundle_path.read_text(encoding="utf-8")); result=verify_bundle(bundle)
    if args.recovery_manifest or args.state_backup:
        recovery_ok=bool(args.recovery_manifest and args.state_backup and verify_recovery_package(bundle,bundle_path,Path(args.recovery_manifest),Path(args.state_backup)))
        result["recovery_package_valid"]=recovery_ok; result["valid"]=bool(result["valid"] and recovery_ok)
    print(json.dumps(result,indent=2,sort_keys=True) if args.json else ("PASS " if result["valid"] else "FAIL ")+result["result_sha256"])
    return 0 if result["valid"] else 2

if __name__=="__main__": raise SystemExit(main())
