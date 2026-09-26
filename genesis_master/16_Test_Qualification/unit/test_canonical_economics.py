from pathlib import Path
import base64, importlib.util, json, time, uuid
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); assert spec and spec.loader
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

@pytest.fixture
def econ(tmp_path):
    identity_mod=load("econ_identity",ROOT/"01_Core_Runtime"/"identity"/"canonical_identity.py")
    econ_mod=load("econ_runtime",ROOT/"01_Core_Runtime"/"service_runtime"/"canonical_economics.py")
    identity=identity_mod.EntityIdentityVault(tmp_path/"state")
    payer=identity.create("Payer","organization")["entity_id"]
    payee=identity.create("Payee","organization")["entity_id"]
    other=identity.create("Other","organization")["entity_id"]
    engine=econ_mod.SettlementEngine(tmp_path/"state",identity)
    return econ_mod,identity,engine,payer,payee,other

def test_external_payment_requires_provider_evidence_replay_safe_and_balanced(econ):
    _,_,engine,payer,payee,_=econ
    created=engine.create(payer,payee,amount_units=5000,currency="CAD",obligation_ref="lic-1",transaction_nonce="nonce-1",settlement_kind="EXTERNAL_PAYMENT")
    with pytest.raises(ValueError,match="duplicate/replayed"): engine.create(payer,payee,amount_units=5000,currency="CAD",obligation_ref="lic-1",transaction_nonce="nonce-1",settlement_kind="EXTERNAL_PAYMENT")
    with pytest.raises(PermissionError): engine.authorize(payee,created["settlement_id"])
    engine.authorize(payer,created["settlement_id"])
    with pytest.raises(PermissionError,match="provider-confirmed"): engine.confirm(payer,created["settlement_id"])
    engine.record_external_evidence(payer,created["settlement_id"],"COUNTERPARTY_ATTESTED",{"ref":"attested"})
    with pytest.raises(PermissionError): engine.confirm(payer,created["settlement_id"])
    engine.record_external_evidence(payer,created["settlement_id"],"PROVIDER_CONFIRMED",{"provider":"processor","payment_id":"p-1"})
    confirmed=engine.confirm(payer,created["settlement_id"])
    assert confirmed["external_money_movement_verified"] is True and confirmed["double_entry_balanced"] is True
    assert engine.balance(payee,"CAD")["net"]==5000 and engine.balance(payer,"CAD")["net"]==-5000
    reversed_tx=engine.compensate(payee,created["settlement_id"],reason="provider reversal")
    assert reversed_tx["state"]=="REVERSED"
    assert engine.balance(payee,"CAD")["net"]==0 and engine.balance(payer,"CAD")["net"]==0
    with pytest.raises((RuntimeError,ValueError)): engine.compensate(payee,created["settlement_id"])

def test_internal_accounting_never_claims_external_money_movement(econ):
    _,_,engine,payer,payee,_=econ
    created=engine.create(payer,payee,amount_units=250,currency="EVC",obligation_ref="internal-1",transaction_nonce="internal-nonce",settlement_kind="INTERNAL_ACCOUNTING")
    engine.authorize(payer,created["settlement_id"])
    out=engine.confirm(payer,created["settlement_id"])
    row=engine.get(created["settlement_id"])
    assert out["external_money_movement_verified"] is False and row["money_movement_verified"] is False

def test_value_lifecycle_cannot_skip_states_or_realize_without_external_payment(econ):
    _,_,engine,payer,payee,_=econ
    value=engine.create_value_record(payer,"asset-value",1000,"CAD")
    with pytest.raises(ValueError): engine.advance_value(payer,value["value_id"],"CONTRACTED")
    for state in ("OFFER","CONTRACTED","ACCRUED"):
        value=engine.advance_value(payer,value["value_id"],state)
    internal=engine.create(payer,payee,amount_units=1000,currency="CAD",obligation_ref="asset-value",transaction_nonce="v-int",settlement_kind="INTERNAL_ACCOUNTING")
    engine.authorize(payer,internal["settlement_id"]); engine.confirm(payer,internal["settlement_id"])
    value=engine.advance_value(payer,value["value_id"],"SETTLED",settlement_id=internal["settlement_id"])
    with pytest.raises(PermissionError,match="verified external payment"): engine.advance_value(payer,value["value_id"],"REALIZED")

def test_verified_external_settlement_can_reach_realized(econ):
    _,_,engine,payer,payee,_=econ
    value=engine.create_value_record(payer,"asset-real",750,"CAD")
    for state in ("OFFER","CONTRACTED","ACCRUED"): value=engine.advance_value(payer,value["value_id"],state)
    s=engine.create(payer,payee,amount_units=750,currency="CAD",obligation_ref="asset-real",transaction_nonce="v-ext",settlement_kind="EXTERNAL_PAYMENT")
    engine.authorize(payer,s["settlement_id"]); engine.record_external_evidence(payer,s["settlement_id"],"PROVIDER_CONFIRMED",{"provider":"processor","payment_id":"ext-1"}); engine.confirm(payer,s["settlement_id"])
    value=engine.advance_value(payer,value["value_id"],"SETTLED",settlement_id=s["settlement_id"])
    value=engine.advance_value(payer,value["value_id"],"REALIZED")
    assert value["state"]=="REALIZED" and value["realized_external"] is True

def test_royalty_allocation_is_deterministic_balanced_and_idempotent(econ):
    _,_,engine,payer,payee,other=econ
    plan=engine.create_royalty_plan(payer,{payee:6000,other:4000},version=3)
    out=engine.allocate_royalties(plan["plan_id"],"settlement-r1",101,"CAD")
    assert out["plan_version"]==3 and out["allocated_total"]==101
    assert sum(out["distribution"].values())==101
    out2=dict(out["distribution"])
    assert out2==dict(sorted(out2.items())) or sum(out2.values())==101
    with pytest.raises(ValueError,match="already allocated"): engine.allocate_royalties(plan["plan_id"],"settlement-r1",101,"CAD")
    with pytest.raises(ValueError,match="10000"): engine.create_royalty_plan(payer,{payee:5000,other:4000})

def test_provider_confirmed_strong_mode_requires_cryptographic_provider_attestation(tmp_path):
    identity_mod=load("econ_strong_identity",ROOT/"01_Core_Runtime"/"identity"/"canonical_identity.py")
    econ_mod=load("econ_strong_runtime",ROOT/"01_Core_Runtime"/"service_runtime"/"canonical_economics.py")
    ext_mod=load("econ_strong_external",ROOT/"21_Corporate_Capital"/"external_authorities"/"canonical_external_authority.py")
    state=tmp_path/"strong"; identity=identity_mod.EntityIdentityVault(state)
    payer=identity.create("Strong Payer","organization")["entity_id"]; payee=identity.create("Strong Payee","organization")["entity_id"]
    registry=ext_mod.ExternalAuthorityRegistry(state); private=Ed25519PrivateKey.generate(); public=private.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
    public_b64=base64.urlsafe_b64encode(public).decode().rstrip("=")
    registry.trust_authority("payment-test","PAYMENT_PROVIDER",public_b64,jurisdictions=["CA-BC"],evidence_types=["PAYMENT_SETTLEMENT_CONFIRMATION"])
    engine=econ_mod.SettlementEngine(state,identity,external_payment_verifier=registry)
    created=engine.create(payer,payee,amount_units=1200,currency="CAD",obligation_ref="strong-licence",transaction_nonce="strong-payment",settlement_kind="EXTERNAL_PAYMENT")
    engine.authorize(payer,created["settlement_id"])
    body={"schema":"entity-external-authority-evidence-v1","authority_id":"payment-test","authority_type":"PAYMENT_PROVIDER","jurisdiction":"CA-BC","evidence_type":"PAYMENT_SETTLEMENT_CONFIRMATION","external_authority_ref":"payment:test:1","subject_entity_id":payee,"payload":{"settlement_id":created["settlement_id"],"amount_units":1200,"currency":"CAD"},"issued_at_ms":int(time.time()*1000),"effective_at_ms":int(time.time()*1000),"nonce":uuid.uuid4().hex}
    raw=json.dumps(body,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode(); evidence=dict(body,signature=base64.urlsafe_b64encode(private.sign(raw)).decode().rstrip("="))
    tampered=dict(evidence); tampered["payload"]=dict(tampered["payload"],amount_units=1201)
    with pytest.raises(PermissionError,match="cryptographic verification"):
        engine.record_external_evidence(payer,created["settlement_id"],"PROVIDER_CONFIRMED",tampered)
    engine.record_external_evidence(payer,created["settlement_id"],"PROVIDER_CONFIRMED",evidence)
    confirmed=engine.confirm(payer,created["settlement_id"])
    assert confirmed["external_money_movement_verified"] is True
