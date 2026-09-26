from pathlib import Path
import importlib.util
import time
import pytest

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); assert spec and spec.loader
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

@pytest.fixture
def system(tmp_path):
    identity_mod=load("cc_identity",ROOT/"01_Core_Runtime"/"identity"/"canonical_identity.py")
    capital_mod=load("cc_capital",ROOT/"21_Corporate_Capital"/"capital_structure"/"canonical_corporate_capital.py")
    identity=identity_mod.EntityIdentityVault(tmp_path/"state")
    issuer=identity.create("Corporate Entity A","organization")["entity_id"]
    verifier=lambda evidence: str((evidence or {}).get("external_authority_ref") or "").startswith("corp-register:")
    engine=capital_mod.CorporateCapitalEngine(tmp_path/"state",identity,external_authority_verifier=verifier)
    authority={"approved":True,"approvers":["board-resolution-001"]}
    return engine,issuer,authority

def test_usage_economics_cannot_mint_equity_or_claim_cash(system):
    engine,issuer,authority=system
    commodity=engine.register_digital_commodity(issuer,"asset-program-1",commodity_type="SOFTWARE",commercialization_authority=True)
    before=engine.capitalization(issuer)["summary"]
    usage=engine.record_usage(issuer,commodity["commodity_id"],event_nonce="usage-1",usage_class="API_REQUEST",assurance_level="ENTITY_GATEWAY_OBSERVED",quantity=5000,unit="REQUEST",obligation_units=20000,recognized_revenue_units=15000,currency="CAD")
    after=engine.capitalization(issuer)["summary"]
    assert usage["usage_is_not_equity"] is True and before==after
    signed_body={k:v for k,v in usage.items() if k not in {"signature","evidence","usage_is_not_equity"}}
    assert engine.identity.verify_signature(engine.identity.load_manifest(issuer),signed_body,usage["signature"]) is True
    with pytest.raises(PermissionError,match="cash receipt"): engine.record_usage(issuer,commodity["commodity_id"],event_nonce="usage-cash",usage_class="API_REQUEST",assurance_level="ENTITY_GATEWAY_OBSERVED",quantity=1,unit="REQUEST",cash_received_units=100,currency="CAD")

def test_share_state_requires_external_authority_and_reconciles(system):
    engine,issuer,authority=system
    external={"external_authority_ref":"corp-register:class-a:v1","source":"corporate-register"}
    share=engine.record_share_class_snapshot(issuer,"A",authorized_units=1000000,recorded_issued_units=100000,recorded_outstanding_units=100000,external_evidence=external,authority=authority,transaction_nonce="class-a-1")
    with pytest.raises(PermissionError,match="external authoritative"): engine.record_shareholder_snapshot(issuer,share["class_id"],{"holder-a":100000},external_evidence={},authority=authority,transaction_nonce="holders-bad")
    with pytest.raises(PermissionError,match="failed verification"): engine.record_shareholder_snapshot(issuer,share["class_id"],{"holder-a":100000},external_evidence={"external_authority_ref":"forged:holders:v1"},authority=authority,transaction_nonce="holders-forged")
    with pytest.raises(ValueError,match="reconcile"): engine.record_shareholder_snapshot(issuer,share["class_id"],{"holder-a":90000},external_evidence=external,authority=authority,transaction_nonce="holders-wrong")
    snap=engine.record_shareholder_snapshot(issuer,share["class_id"],{"holder-a":60000,"holder-b":40000},external_evidence={"external_authority_ref":"corp-register:holders:v1"},authority=authority,transaction_nonce="holders-good")
    assert snap["recorded_outstanding_units"]==100000
    cap=engine.capitalization(issuer)
    assert cap["summary"]["recorded_outstanding_units"]==100000
    assert sum(int(p["units"]) for p in cap["positions"])==100000

def test_modeled_value_and_external_market_observation_never_collapse(system):
    engine,issuer,authority=system
    ext={"external_authority_ref":"corp-register:class-b:v1"}
    share=engine.record_share_class_snapshot(issuer,"B",authorized_units=500000,recorded_issued_units=50000,recorded_outstanding_units=50000,external_evidence=ext,authority=authority,transaction_nonce="class-b")
    modeled=engine.record_modeled_valuation(issuer,class_id=share["class_id"],amount_minor=125000000,currency="CAD",methodology="asset-income-hybrid",assumptions={"scenario":"test"})
    assert modeled["evidence_origin"]=="DERIVED_INFERENCE" and modeled["is_market_price"] is False
    observed=engine.record_external_market_observation(issuer,share["class_id"],amount_minor=725,currency="CAD",source="authorized-test-market-feed",observed_at_ms=int(time.time()*1000),external_evidence={"external_authority_ref":"corp-register:market:v1"},price_class="TRADE")
    assert observed["is_externally_observed_market_price"] is True
    metrics=engine.per_share_metrics(issuer,share["class_id"],"CAD")
    assert metrics["externally_observed_market_price"]["amount_minor"]==725
    assert metrics["internal_metrics_are_not_market_price"] is True

def test_replay_protection_disclosure_and_invariants(system):
    engine,issuer,authority=system
    ext={"external_authority_ref":"corp-register:class-c:v1"}
    share=engine.record_share_class_snapshot(issuer,"C",authorized_units=10000,recorded_issued_units=1000,recorded_outstanding_units=1000,external_evidence=ext,authority=authority,transaction_nonce="class-c")
    with pytest.raises(ValueError,match="duplicate/replayed"): engine.record_share_class_snapshot(issuer,"C2",authorized_units=10000,recorded_issued_units=0,recorded_outstanding_units=0,external_evidence={"external_authority_ref":"corp-register:class-c2:v1"},authority=authority,transaction_nonce="class-c")
    engine.record_shareholder_snapshot(issuer,share["class_id"],{"holder-x":1000},external_evidence={"external_authority_ref":"corp-register:holders-c:v1"},authority=authority,transaction_nonce="holders-c")
    check=engine.verify_invariants(issuer)
    assert check["pass"] is True and check["regulated_execution_enabled"] is False
    disclosure=engine.disclosure_snapshot(issuer,scope="INVESTOR_CONFIDENTIAL")
    assert len(disclosure["snapshot_sha256"])==64
    assert "internal valuation does not establish market price" in disclosure["snapshot"]["limitations"]

def test_noncommercial_data_cannot_create_economic_evidence(system):
    engine,issuer,_=system
    commodity=engine.register_digital_commodity(issuer,"asset-private",commodity_type="DATASET",commercialization_authority=False)
    engine.record_usage(issuer,commodity["commodity_id"],event_nonce="private-usage",usage_class="INTERNAL_QUERY",assurance_level="DIRECTED" if False else "DECLARED",quantity=3,unit="QUERY")
    with pytest.raises(PermissionError,match="commercialization authority"): engine.record_usage(issuer,commodity["commodity_id"],event_nonce="private-revenue",usage_class="LICENSED_QUERY",assurance_level="COUNTERPARTY_ATTESTED",quantity=1,unit="QUERY",obligation_units=100,currency="CAD")
