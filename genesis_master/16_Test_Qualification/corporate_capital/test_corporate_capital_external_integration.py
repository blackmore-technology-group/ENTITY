from pathlib import Path
import base64, importlib.util, json, time, uuid
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); assert spec and spec.loader
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

def b64(raw): return base64.urlsafe_b64encode(raw).decode().rstrip("=")
def canon(v): return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
def pub(priv): return b64(priv.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw))

def sign_external(priv,authority_id,authority_type,evidence_type,subject,ref,*,jurisdiction="CA-BC",payload=None):
    now=int(time.time()*1000)
    body={"schema":"entity-external-authority-evidence-v1","authority_id":authority_id,"authority_type":authority_type,"jurisdiction":jurisdiction,"evidence_type":evidence_type,"external_authority_ref":ref,"subject_entity_id":subject,"payload":dict(payload or {}),"issued_at_ms":now,"effective_at_ms":now,"nonce":uuid.uuid4().hex}
    body["signature"]=b64(priv.sign(canon(body)))
    return body

@pytest.fixture
def integrated(tmp_path):
    identity_mod=load("ext_identity",ROOT/"01_Core_Runtime"/"identity"/"canonical_identity.py")
    econ_mod=load("ext_econ",ROOT/"01_Core_Runtime"/"service_runtime"/"canonical_economics.py")
    capital_mod=load("ext_capital",ROOT/"21_Corporate_Capital"/"capital_structure"/"canonical_corporate_capital.py")
    external_mod=load("ext_registry",ROOT/"21_Corporate_Capital"/"external_authorities"/"canonical_external_authority.py")
    class_mod=load("ext_class",ROOT/"21_Corporate_Capital"/"jurisdiction"/"canonical_instrument_classification.py")
    action_mod=load("ext_action",ROOT/"21_Corporate_Capital"/"corporate_actions"/"canonical_corporate_actions.py")
    accounting_mod=load("ext_accounting",ROOT/"21_Corporate_Capital"/"accounting"/"canonical_capital_accounting.py")
    identity=identity_mod.EntityIdentityVault(tmp_path/"state"); issuer=identity.create("Issuer","organization")["entity_id"]; investor=identity.create("Investor","organization")["entity_id"]
    registry=external_mod.ExternalAuthorityRegistry(tmp_path/"state")
    register_key=Ed25519PrivateKey.generate(); market_key=Ed25519PrivateKey.generate(); accounting_key=Ed25519PrivateKey.generate()
    registry.trust_authority("register-1","CORPORATE_REGISTER",pub(register_key),jurisdictions=["CA-BC"],evidence_types=["SHARE_CLASS_REGISTER","SHAREHOLDER_REGISTER","CAPITAL_STRUCTURE_SNAPSHOT","CORPORATE_ACTION_RESULT"])
    registry.trust_authority("market-1","MARKET_DATA_PROVIDER",pub(market_key),jurisdictions=["CA-BC"],evidence_types=["MARKET_PRICE_OBSERVATION","MARKET_BID_ASK"])
    registry.trust_authority("accounting-1","ACCOUNTING_SYSTEM",pub(accounting_key),jurisdictions=["CA-BC"],evidence_types=["ACCOUNTING_JOURNAL"])
    classifier=class_mod.InstrumentClassificationRegistry(tmp_path/"state"); now=int(time.time()*1000)-1000
    for action in ("RECORD_ISSUANCE","RECORD_TRANSFER","RECORD_CANCELLATION","RECORD_DIVIDEND"):
        classifier.register_rule(f"bc-equity-{action.lower()}",jurisdiction="CA-BC",instrument_class="CORPORATE_EQUITY",action=action,decision="ALLOW_EVIDENCE_ONLY",version=1,effective_at_ms=now,authority_ref="configured-test-policy")
    settlement=econ_mod.SettlementEngine(tmp_path/"state",identity)
    capital=capital_mod.CorporateCapitalEngine(tmp_path/"state",identity,settlement_engine=settlement,external_authority_verifier=registry)
    actions=action_mod.CorporateActionLedger(tmp_path/"state",identity,capital,registry,classifier)
    accounting=accounting_mod.CapitalAccountingReconciler(tmp_path/"state",identity,capital,registry,settlement_engine=settlement)
    authority={"approved":True,"approvers":["board-resolution-100"]}
    return {"identity":identity,"issuer":issuer,"investor":investor,"registry":registry,"register_key":register_key,"market_key":market_key,"accounting_key":accounting_key,"classifier":classifier,"settlement":settlement,"capital":capital,"actions":actions,"accounting":accounting,"authority":authority}
def test_signed_external_authority_evidence_is_subject_and_type_bound(integrated):
    s=integrated; evidence=sign_external(s["register_key"],"register-1","CORPORATE_REGISTER","SHARE_CLASS_REGISTER",s["issuer"],"corp-register:class-a:v1")
    assert s["registry"].verify(evidence,expected_subject=s["issuer"],allowed_evidence_types={"SHARE_CLASS_REGISTER"}) is True
    tampered=dict(evidence); tampered["external_authority_ref"]="corp-register:tampered"
    assert s["registry"].verify(tampered,expected_subject=s["issuer"],allowed_evidence_types={"SHARE_CLASS_REGISTER"}) is False
    assert s["registry"].verify(evidence,expected_subject=s["investor"],allowed_evidence_types={"SHARE_CLASS_REGISTER"}) is False
    assert s["registry"].verify(evidence,expected_subject=s["issuer"],allowed_evidence_types={"ACCOUNTING_JOURNAL"}) is False

def test_jurisdiction_registry_fails_closed_without_configured_rule(integrated):
    s=integrated
    known=s["classifier"].evaluate(jurisdiction="CA-BC",instrument_class="CORPORATE_EQUITY",action="RECORD_ISSUANCE")
    assert known["decision"]=="ALLOW_EVIDENCE_ONLY" and known["legal_determination"] is False
    unknown=s["classifier"].evaluate(jurisdiction="US-NY",instrument_class="CORPORATE_EQUITY",action="RECORD_ISSUANCE")
    assert unknown["decision"]=="REQUIRE_AUTHORIZED_REVIEW" and unknown["legal_determination"] is False
    with pytest.raises(PermissionError,match="authorized jurisdiction"): s["classifier"].require_evidence_operation(jurisdiction="US-NY",instrument_class="CORPORATE_EQUITY",action="RECORD_ISSUANCE")
def seed_capital(s):
    class_ev=sign_external(s["register_key"],"register-1","CORPORATE_REGISTER","SHARE_CLASS_REGISTER",s["issuer"],"corp-register:class-a:v1")
    share=s["capital"].record_share_class_snapshot(s["issuer"],"A",authorized_units=1000000,recorded_issued_units=100000,recorded_outstanding_units=100000,external_evidence=class_ev,authority=s["authority"],transaction_nonce="seed-class")
    holders_ev=sign_external(s["register_key"],"register-1","CORPORATE_REGISTER","SHAREHOLDER_REGISTER",s["issuer"],"corp-register:holders-a:v1")
    s["capital"].record_shareholder_snapshot(s["issuer"],share["class_id"],{"founder":60000,"investor-a":40000},external_evidence=holders_ev,authority=s["authority"],transaction_nonce="seed-holders")
    return share

def test_market_observation_requires_signed_market_authority(integrated):
    s=integrated; share=seed_capital(s); now=int(time.time()*1000)
    market_ev=sign_external(s["market_key"],"market-1","MARKET_DATA_PROVIDER","MARKET_PRICE_OBSERVATION",s["issuer"],"market:test:trade-1")
    observed=s["capital"].record_external_market_observation(s["issuer"],share["class_id"],amount_minor=725,currency="CAD",source="market-1",observed_at_ms=now,external_evidence=market_ev,price_class="TRADE")
    assert observed["is_externally_observed_market_price"] is True and observed["external_authority_ref"]=="market:test:trade-1"
    forged=dict(market_ev); forged["amount_minor"]=999999
    with pytest.raises(PermissionError,match="failed verification"): s["capital"].record_external_market_observation(s["issuer"],share["class_id"],amount_minor=999,currency="CAD",source="market-1",observed_at_ms=now,external_evidence=forged,price_class="TRADE")
def test_corporate_action_adopts_only_bound_external_result_and_reconciles(integrated):
    s=integrated; share=seed_capital(s); class_id=share["class_id"]; now=int(time.time()*1000)
    post={"authorized_units":1000000,"recorded_issued_units":120000,"positions":{"founder":70000,"investor-a":40000,"investor-b":10000}}
    action_ev=sign_external(s["register_key"],"register-1","CORPORATE_REGISTER","CORPORATE_ACTION_RESULT",s["issuer"],"corp-register:issuance-2",payload={"action_type":"ISSUANCE","class_id":class_id,"post_capitalization":post})
    out=s["actions"].record_action(s["issuer"],class_id,action_type="ISSUANCE",jurisdiction="CA-BC",instrument_class="CORPORATE_EQUITY",effective_at_ms=now,external_evidence=action_ev,authority=s["authority"],transaction_nonce="issuance-2",expected_post_snapshot=post,financial_effect={"consideration_minor":20000,"currency":"CAD"})
    assert out["status"]=="RECONCILED" and out["adopted_capitalization"]["recorded_outstanding_units"]==120000
    cap=s["capital"].capitalization(s["issuer"])
    assert cap["summary"]["recorded_issued_units"]==120000 and cap["summary"]["recorded_outstanding_units"]==120000
    wrong=dict(post); wrong["positions"]={"founder":80000,"investor-a":40000}
    with pytest.raises(PermissionError,match="does not match"): s["actions"].record_action(s["issuer"],class_id,action_type="ISSUANCE",jurisdiction="CA-BC",instrument_class="CORPORATE_EQUITY",effective_at_ms=now,external_evidence=action_ev,authority=s["authority"],transaction_nonce="issuance-forged",expected_post_snapshot=wrong)
def test_accounting_reconciliation_requires_balanced_external_journal_and_cash_proof(integrated):
    s=integrated; share=seed_capital(s); class_id=share["class_id"]; now=int(time.time()*1000)
    post={"authorized_units":1000000,"recorded_issued_units":120000,"positions":{"founder":60000,"investor-a":40000,"investor-b":20000}}
    action_ev=sign_external(s["register_key"],"register-1","CORPORATE_REGISTER","CORPORATE_ACTION_RESULT",s["issuer"],"corp-register:issuance-cash",payload={"action_type":"ISSUANCE","class_id":class_id,"post_capitalization":post})
    action=s["actions"].record_action(s["issuer"],class_id,action_type="ISSUANCE",jurisdiction="CA-BC",instrument_class="CORPORATE_EQUITY",effective_at_ms=now,external_evidence=action_ev,authority=s["authority"],transaction_nonce="issuance-cash",expected_post_snapshot=post,financial_effect={"consideration_minor":20000,"currency":"CAD"})
    capital_event_id=action["adopted_capitalization"]["event"]["event_id"]
    accounting_ev=sign_external(s["accounting_key"],"accounting-1","ACCOUNTING_SYSTEM","ACCOUNTING_JOURNAL",s["issuer"],"accounting:journal:capital-1")
    entries=[{"account_code":"CASH","direction":"DEBIT","amount_minor":20000,"currency":"CAD","capital_event_id":capital_event_id},{"account_code":"SHARE_CAPITAL","direction":"CREDIT","amount_minor":20000,"currency":"CAD","capital_event_id":capital_event_id}]
    batch=s["accounting"].record_journal_snapshot(s["issuer"],entries,external_evidence=accounting_ev,authority=s["authority"],transaction_nonce="journal-capital-1")
    reconciliation=s["accounting"].reconcile_capital_event(s["issuer"],capital_event_id,batch["batch_id"],expected_amount_minor=20000,currency="CAD")
    assert reconciliation["accounting_reconciled"] is True and reconciliation["external_cash_verified"] is None
    tx=s["settlement"].create(s["investor"],s["issuer"],amount_units=20000,currency="CAD",obligation_ref=capital_event_id,transaction_nonce="share-cash-payment",settlement_kind="EXTERNAL_PAYMENT")
    s["settlement"].authorize(s["investor"],tx["settlement_id"]); s["settlement"].record_external_evidence(s["investor"],tx["settlement_id"],"PROVIDER_CONFIRMED",{"provider":"test-bank","payment_id":"pay-1"}); s["settlement"].confirm(s["investor"],tx["settlement_id"])
    cash=s["accounting"].reconcile_capital_event(s["issuer"],capital_event_id,batch["batch_id"],expected_amount_minor=20000,currency="CAD",settlement_id=tx["settlement_id"],require_external_cash=True)
    assert cash["accounting_reconciled"] is True and cash["external_cash_verified"] is True
