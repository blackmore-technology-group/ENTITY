from pathlib import Path
import base64, importlib.util, sys
import pytest

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); assert spec and spec.loader
    mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod

I=load("e2e_identity",ROOT/"01_Core_Runtime"/"identity"/"canonical_identity.py")
POL=load("e2e_policy",ROOT/"01_Core_Runtime"/"policy_engine"/"canonical_policy.py")
L=load("e2e_ledger",ROOT/"04_Entity_Registry"/"event_ledger"/"canonical_event_ledger.py")
R=load("e2e_rights",ROOT/"04_Entity_Registry"/"ownership_graphs"/"canonical_rights_claims.py")
P=load("e2e_prov",ROOT/"04_Entity_Registry"/"provenance"/"canonical_provenance.py")
A=load("e2e_assets",ROOT/"04_Entity_Registry"/"asset_registry"/"canonical_asset_registry.py")
C=load("e2e_contracts",ROOT/"01_Core_Runtime"/"contracts"/"canonical_contracts.py")
U=load("e2e_usage",ROOT/"01_Core_Runtime"/"usage_control"/"canonical_usage_control.py")
E=load("e2e_econ",ROOT/"01_Core_Runtime"/"service_runtime"/"canonical_economics.py")
B=load("e2e_backup",ROOT/"15_Operations"/"backups"/"canonical_portable_state.py")
V=load("e2e_verifier",ROOT/"16_Test_Qualification"/"verifier"/"independent_verifier.py")

def runtime(state):
    ids=I.EntityIdentityVault(state); ledger=L.CanonicalEventLedger(state,ids); rights=R.RightsClaimsGraph(state,ids); prov=P.AssetProvenanceGraph(state,ids)
    assets=A.CanonicalAssetRegistry(state,ids,ledger,rights,prov); policies=POL.PolicyConsentEngine(state,ids); contracts=C.ContractLicensingEngine(state,ids,rights,ledger); usage=U.UsageControlEngine(state,ids,contracts,ledger); econ=E.SettlementEngine(state,ids)
    return ids,ledger,rights,prov,assets,policies,contracts,usage,econ

def test_full_entity_golden_e2e_with_malicious_c_and_recovery(tmp_path):
    state=tmp_path/"state"; ids,ledger,rights,prov,assets,policies,contracts,usage,econ=runtime(state)
    entity_a=ids.create("Entity A","organization")["entity_id"]; entity_b=ids.create("Entity B","organization")["entity_id"]; entity_c=ids.create("Malicious Entity C","organization")["entity_id"]
    asset=assets.register(entity_a,content_sha256="44"*32,size_bytes=2048,media_type="application/octet-stream",title="Golden Asset")
    claim=rights.assert_claim(entity_a,asset_id=asset["asset_id"],right_type="COPYRIGHT_OWNER",evidence_origin="DIRECT_OBSERVATION",evidence={"basis":"golden-scenario"})
    assert prov.verify_hard_binding(asset["asset_id"],"44"*32)["hard_binding_match"] is True and rights.can_license(entity_a,asset["asset_id"])["allowed"] is True
    policy=policies.create_policy(entity_a,"Golden Access",{"VIEW":"PERMIT","AI_TRAINING":"PROHIBIT"},jurisdiction="CA-BC")
    consent=policies.grant_consent(entity_a,policy["policy_id"],purpose="research",asset_scope=[asset["asset_id"]],counterparty_entity_id=entity_b)
    assert policies.authorize_consent(consent["consent_id"],counterparty_entity_id=entity_b,purpose="research",asset_scope=[asset["asset_id"]],action="VIEW")["allowed"] is True
    assert policies.authorize_consent(consent["consent_id"],counterparty_entity_id=entity_c,purpose="research",asset_scope=[asset["asset_id"]],action="VIEW")["allowed"] is False
    terms={"assets":[asset["asset_id"]],"rights":["VIEW"],"purpose":"research","scope":"named-licensee","territory":"CA","duration":{"type":"fixed"},"consideration":{"amount_minor":2500,"currency":"CAD"},"usage_requirements":{"max_quantity_per_event":5},"reporting_requirements":{},"retention_requirements":{},"derivative_rules":{},"revocation_rules":{},"termination_rules":{}}
    draft=contracts.create_draft(entity_a,entity_b,terms); contracts.offer(entity_a,draft["licence_id"]); contracts.accept(entity_b,draft["licence_id"]); active=contracts.activate(entity_a,draft["licence_id"])
    assert active["state"]=="ACTIVE"
    ticket=usage.issue_gateway_ticket(entity_a,licence_id=draft["licence_id"],asset_id=asset["asset_id"],use_type="VIEW",quantity=3,nonce="golden-ticket")
    receipt=usage.consume_gateway_ticket(entity_b,ticket["ticket_id"],purpose="research",nonce="golden-receipt")
    assert receipt["assurance"]=="ENTITY_GATEWAY_OBSERVED" and usage.verify_receipt(receipt["receipt_id"])["pass"] is True
    with pytest.raises(PermissionError): usage.record_declared(entity_c,draft["licence_id"],asset_id=asset["asset_id"],use_type="VIEW",purpose="research",quantity=1,nonce="malicious-c-use")

    payment=econ.create(entity_b,entity_a,amount_units=2500,currency="CAD",obligation_ref=draft["licence_id"],transaction_nonce="golden-settlement",settlement_kind="EXTERNAL_PAYMENT")
    econ.authorize(entity_b,payment["settlement_id"]); econ.record_external_evidence(entity_b,payment["settlement_id"],"PROVIDER_CONFIRMED",{"provider":"qualified-test-bank","payment_id":"golden-pay"}); econ.confirm(entity_b,payment["settlement_id"])
    value=econ.create_value_record(entity_a,asset["asset_id"],2500,"CAD")
    for target in ("OFFER","CONTRACTED","ACCRUED"): value=econ.advance_value(entity_a,value["value_id"],target)
    value=econ.advance_value(entity_a,value["value_id"],"SETTLED",settlement_id=payment["settlement_id"]); value=econ.advance_value(entity_a,value["value_id"],"REALIZED")
    assert value["realized_external"] is True and econ.balance(entity_a,"CAD")["net"]==2500

    revoked=contracts.future_revoke(entity_a,draft["licence_id"],"golden scenario future-use revocation"); assert revoked["state"]=="REVOKED_FOR_FUTURE_USE"
    policies.revoke_consent(entity_a,consent["consent_id"])
    assert policies.authorize_consent(consent["consent_id"],counterparty_entity_id=entity_b,purpose="research",asset_scope=[asset["asset_id"]],action="VIEW")["allowed"] is False
    with pytest.raises(PermissionError): usage.record_declared(entity_b,draft["licence_id"],asset_id=asset["asset_id"],use_type="VIEW",purpose="research",quantity=1,nonce="post-revoke-use")
    disputed=rights.set_state(entity_b,claim["claim_id"],"DISPUTED","golden scenario dispute"); assert disputed["lifecycle_status"]=="DISPUTED"
    assert usage.verify_receipt(receipt["receipt_id"])["pass"] is True
    checkpoint=ledger.checkpoint(entity_a); assert ledger.verify_checkpoint(checkpoint["checkpoint_id"])["pass"] is True
    portable=B.PortableStateManager(state,ids); backup=portable.create_encrypted_backup(tmp_path/"golden-e2e.enc")
    key=base64.urlsafe_b64decode(backup["key_b64"]); unavailable=tmp_path/"state_unavailable"; state.rename(unavailable); assert not state.exists()
    portable.restore_encrypted_backup(backup["path"],key,state)
    ids2,ledger2,rights2,prov2,assets2,policies2,contracts2,usage2,econ2=runtime(state)
    assert ids2.load_manifest(entity_a)["entity_id"]==entity_a and ids2.load_manifest(entity_b)["entity_id"]==entity_b and ids2.load_manifest(entity_c)["entity_id"]==entity_c
    assert assets2.get(asset["asset_id"])["controller_entity_id"]==entity_a
    assert prov2.verify_hard_binding(asset["asset_id"],"44"*32)["hard_binding_match"] is True
    assert any(x["claim_id"]==claim["claim_id"] and x["lifecycle_status"]=="DISPUTED" for x in rights2.claims_for_asset(asset["asset_id"]))
    assert contracts2.get(draft["licence_id"])["state"]=="REVOKED_FOR_FUTURE_USE" and contracts2.verify_history(draft["licence_id"])["pass"] is True
    assert usage2.verify_receipt(receipt["receipt_id"])["pass"] is True
    assert econ2.get(payment["settlement_id"])["money_movement_verified"] is True and econ2.get_value(value["value_id"])["state"]=="REALIZED"
    assert ledger2.verify()["pass"] is True and ledger2.verify_checkpoint(checkpoint["checkpoint_id"])["pass"] is True

    export_dir=tmp_path/"golden-export"; exported=B.PortableStateManager(state,ids2).export_entity(entity_a,export_dir)
    manifest=ids2.load_manifest(entity_a); body={k:v for k,v in exported.items() if k!="signature"}
    assert V.verify_signature_record(manifest,body,exported["signature"]) is True
    inventory=[{"path":x["name"],"sha256":x["sha256"]} for x in exported["files"]]
    assert V.verify_file_inventory(export_dir,inventory)["valid"] is True
