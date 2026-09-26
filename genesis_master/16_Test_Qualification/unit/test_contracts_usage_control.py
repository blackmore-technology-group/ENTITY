from pathlib import Path
import importlib.util, sqlite3, sys
import pytest
ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod

def build(tmp_path):
    im=load("cu_identity",ROOT/"01_Core_Runtime"/"identity"/"canonical_identity.py")
    lm=load("cu_ledger",ROOT/"04_Entity_Registry"/"event_ledger"/"canonical_event_ledger.py")
    rm=load("cu_rights",ROOT/"04_Entity_Registry"/"ownership_graphs"/"canonical_rights_claims.py")
    pm=load("cu_prov",ROOT/"04_Entity_Registry"/"provenance"/"canonical_provenance.py")
    am=load("cu_assets",ROOT/"04_Entity_Registry"/"asset_registry"/"canonical_asset_registry.py")
    cm=load("cu_contracts",ROOT/"01_Core_Runtime"/"contracts"/"canonical_contracts.py")
    um=load("cu_usage",ROOT/"01_Core_Runtime"/"usage_control"/"canonical_usage_control.py")
    state=tmp_path/"state"; ids=im.EntityIdentityVault(state)
    grantor=ids.create("Grantor","person")["entity_id"]; licensee=ids.create("Licensee","person")["entity_id"]
    ledger=lm.CanonicalEventLedger(state,ids); rights=rm.RightsClaimsGraph(state,ids); prov=pm.AssetProvenanceGraph(state,ids)
    assets=am.CanonicalAssetRegistry(state,ids,ledger,rights,prov)
    asset=assets.register(grantor,content_sha256="aa"*32,size_bytes=50,media_type="text/plain",title="Asset")
    contracts=cm.ContractLicensingEngine(state,ids,rights,ledger); usage=um.UsageControlEngine(state,ids,contracts,ledger)
    return state,ids,ledger,rights,assets,contracts,usage,grantor,licensee,asset

def terms(asset_id,purpose="research"):
    return {"assets":[asset_id],"rights":["AI_EVALUATION"],"purpose":purpose,"scope":{"field":"derived"},"territory":"CA","duration":{"days":30},"consideration":{"amount":10,"currency":"CAD"},"usage_requirements":{"max_quantity_per_event":5},"reporting_requirements":{},"retention_requirements":{},"derivative_rules":{},"revocation_rules":{},"termination_rules":{}}
def activate_contract(tmp_path):
    built=build(tmp_path); state,ids,ledger,rights,assets,contracts,usage,grantor,licensee,asset=built
    draft=contracts.create_draft(grantor,licensee,terms(asset["asset_id"]))
    offered=contracts.offer(grantor,draft["licence_id"]); assert offered["state"]=="OFFERED"
    accepted=contracts.accept(licensee,draft["licence_id"]); assert accepted["state"]=="ACCEPTED"
    active=contracts.activate(grantor,draft["licence_id"]); assert active["state"]=="ACTIVE"
    return built,draft["licence_id"]

def test_offer_requires_recorded_licensing_authority(tmp_path):
    state,ids,ledger,rights,assets,contracts,usage,grantor,licensee,asset=build(tmp_path)
    draft=contracts.create_draft(grantor,licensee,terms("asset-does-not-exist"))
    with pytest.raises(PermissionError): contracts.offer(grantor,draft["licence_id"])

def test_contract_activation_and_history_are_signed(tmp_path):
    built,licence_id=activate_contract(tmp_path); contracts=built[5]
    item=contracts.get(licence_id)
    assert item["state"]=="ACTIVE" and item["authority_basis_claim_ids"]
    assert contracts.verify_history(licence_id)["pass"] is True
    assert [e["to_state"] for e in item["events"]][-3:]==["OFFERED","ACCEPTED","ACTIVE"]

def test_counter_offer_versions_terms_and_requires_correct_party(tmp_path):
    state,ids,ledger,rights,assets,contracts,usage,grantor,licensee,asset=build(tmp_path)
    draft=contracts.create_draft(grantor,licensee,terms(asset["asset_id"])); contracts.offer(grantor,draft["licence_id"])
    with pytest.raises(PermissionError): contracts.counter(grantor,draft["licence_id"],terms(asset["asset_id"],"counter"))
    counter=contracts.counter(licensee,draft["licence_id"],terms(asset["asset_id"],"counter")); assert counter["terms_version"]==2
    accepted=contracts.accept(grantor,draft["licence_id"]); assert accepted["state"]=="ACCEPTED" and accepted["authority_basis_claim_ids"]
def test_usage_assurance_classes_remain_distinct(tmp_path):
    built,licence_id=activate_contract(tmp_path); usage,grantor,licensee,asset=built[6],built[7],built[8],built[9]
    declared=usage.record_declared(licensee,licence_id,asset_id=asset["asset_id"],use_type="AI_EVALUATION",purpose="research",quantity=1,evidence={"note":"self report"},nonce="usage-1")
    assert declared["assurance"]=="DECLARED" and declared["assurance_level"]==1 and declared["independently_verified"] is False
    ticket=usage.issue_gateway_ticket(grantor,licence_id=licence_id,asset_id=asset["asset_id"],use_type="AI_EVALUATION",quantity=1,nonce="ticket-1")
    observed=usage.consume_gateway_ticket(licensee,ticket["ticket_id"],purpose="research",nonce="usage-2")
    assert observed["assurance"]=="ENTITY_GATEWAY_OBSERVED" and observed["assurance_level"]==2 and "downstream" in observed["meaning"]
    attested=usage.record_counterparty_attested(grantor,licensee,licence_id,asset_id=asset["asset_id"],use_type="AI_EVALUATION",purpose="research",evidence={"report":"signed"},nonce="usage-3")
    assert attested["assurance"]=="COUNTERPARTY_ATTESTED" and attested["assurance_level"]==3 and attested["independently_verified"] is False
    usage.register_environment_verifier("test-env",lambda e: e.get("attested")==True)
    env=usage.record_environment_attested(grantor,licensee,licence_id,asset_id=asset["asset_id"],use_type="AI_EVALUATION",purpose="research",evidence={"attested":True},verifier_id="test-env",nonce="usage-4")
    assert env["assurance"]=="ENVIRONMENT_ATTESTED" and env["assurance_level"]==4 and env["independently_verified"] is True

def test_usage_scope_replay_and_revocation_fail_closed(tmp_path):
    built,licence_id=activate_contract(tmp_path); contracts,usage,grantor,licensee,asset=built[5],built[6],built[7],built[8],built[9]
    with pytest.raises(PermissionError): usage.record_declared(licensee,licence_id,asset_id=asset["asset_id"],use_type="AI_EVALUATION",purpose="wrong",nonce="scope-1")
    usage.record_declared(licensee,licence_id,asset_id=asset["asset_id"],use_type="AI_EVALUATION",purpose="research",nonce="replay")
    with pytest.raises(ValueError): usage.record_declared(licensee,licence_id,asset_id=asset["asset_id"],use_type="AI_EVALUATION",purpose="research",nonce="replay")
    contracts.future_revoke(grantor,licence_id,"withdraw future use")
    with pytest.raises(PermissionError): usage.record_declared(licensee,licence_id,asset_id=asset["asset_id"],use_type="AI_EVALUATION",purpose="research",nonce="after-revoke")

def test_usage_receipt_tamper_is_detected(tmp_path):
    built,licence_id=activate_contract(tmp_path); usage,licensee,asset=built[6],built[8],built[9]
    receipt=usage.record_declared(licensee,licence_id,asset_id=asset["asset_id"],use_type="AI_EVALUATION",purpose="research",evidence={"x":1},nonce="tamper-1")
    assert usage.verify_receipt(receipt["receipt_id"])["pass"] is True
    with sqlite3.connect(usage.path) as db:
        db.execute("UPDATE receipts SET evidence_json=? WHERE receipt_id=?",('{"x":2}',receipt["receipt_id"])); db.commit()
    check=usage.verify_receipt(receipt["receipt_id"]); assert check["pass"] is False and check["evidence_hash_valid"] is False
