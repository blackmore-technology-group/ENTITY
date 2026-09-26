from pathlib import Path
import base64, importlib.util, json, sqlite3, time, uuid
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
def sign_external(priv,authority_id,authority_type,evidence_type,subject,ref,*,payload=None):
    now=int(time.time()*1000); body={"schema":"entity-external-authority-evidence-v1","authority_id":authority_id,"authority_type":authority_type,"jurisdiction":"CA-BC","evidence_type":evidence_type,"external_authority_ref":ref,"subject_entity_id":subject,"payload":dict(payload or {}),"issued_at_ms":now,"effective_at_ms":now,"nonce":uuid.uuid4().hex}
    body["signature"]=b64(priv.sign(canon(body))); return body
def sqlite_tables(path):
    db=sqlite3.connect(path); db.row_factory=sqlite3.Row
    try:
        names=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        return {n:[dict(r) for r in db.execute(f'SELECT * FROM "{n}"')] for n in names}
    finally: db.close()
def trust_records(path):
    rows=sqlite_tables(path).get("authorities",[]); out=[]
    for row in rows:
        row=dict(row); row["jurisdictions"]=json.loads(row.pop("jurisdictions_json")); row["evidence_types"]=json.loads(row.pop("evidence_types_json")); out.append(row)
    return out
def test_section170_destructive_restore_and_independent_validation(tmp_path):
    I=load("g170_identity",ROOT/"01_Core_Runtime"/"identity"/"canonical_identity.py")
    E=load("g170_econ",ROOT/"01_Core_Runtime"/"service_runtime"/"canonical_economics.py")
    C=load("g170_capital",ROOT/"21_Corporate_Capital"/"capital_structure"/"canonical_corporate_capital.py")
    X=load("g170_external",ROOT/"21_Corporate_Capital"/"external_authorities"/"canonical_external_authority.py")
    J=load("g170_class",ROOT/"21_Corporate_Capital"/"jurisdiction"/"canonical_instrument_classification.py")
    A=load("g170_actions",ROOT/"21_Corporate_Capital"/"corporate_actions"/"canonical_corporate_actions.py")
    K=load("g170_accounting",ROOT/"21_Corporate_Capital"/"accounting"/"canonical_capital_accounting.py")
    P=load("g170_portable",ROOT/"15_Operations"/"backups"/"canonical_portable_state.py")
    V=load("g170_verifier",ROOT/"16_Test_Qualification"/"verifier"/"independent_verifier.py")
    state=tmp_path/"state"; identity=I.EntityIdentityVault(state)
    issuer=identity.create("Golden Issuer","organization")["entity_id"]; investor=identity.create("Golden Investor","organization")["entity_id"]
    registry=X.ExternalAuthorityRegistry(state); reg_key=Ed25519PrivateKey.generate(); market_key=Ed25519PrivateKey.generate(); acct_key=Ed25519PrivateKey.generate()
    registry.trust_authority("register-00000001","CORPORATE_REGISTER",pub(reg_key),jurisdictions=["CA-BC"],evidence_types=["SHARE_CLASS_REGISTER","SHAREHOLDER_REGISTER","CAPITAL_STRUCTURE_SNAPSHOT","CORPORATE_ACTION_RESULT"])
    registry.trust_authority("market-00000001","MARKET_DATA_PROVIDER",pub(market_key),jurisdictions=["CA-BC"],evidence_types=["MARKET_PRICE_OBSERVATION"])
    registry.trust_authority("accounting-00000001","ACCOUNTING_SYSTEM",pub(acct_key),jurisdictions=["CA-BC"],evidence_types=["ACCOUNTING_JOURNAL"])
    classifier=J.InstrumentClassificationRegistry(state); effective=int(time.time()*1000)-1000
    classifier.register_rule("bc-equity-issuance",jurisdiction="CA-BC",instrument_class="CORPORATE_EQUITY",action="RECORD_ISSUANCE",decision="ALLOW_EVIDENCE_ONLY",version=1,effective_at_ms=effective,authority_ref="configured-golden-policy")
    classifier.register_rule("bc-equity-transfer",jurisdiction="CA-BC",instrument_class="CORPORATE_EQUITY",action="RECORD_TRANSFER",decision="ALLOW_EVIDENCE_ONLY",version=1,effective_at_ms=effective,authority_ref="configured-golden-policy")
    settlement=E.SettlementEngine(state,identity); capital=C.CorporateCapitalEngine(state,identity,settlement_engine=settlement,external_authority_verifier=registry)
    actions=A.CorporateActionLedger(state,identity,capital,registry,classifier); accounting=K.CapitalAccountingReconciler(state,identity,capital,registry,settlement_engine=settlement)
    authority={"approved":True,"approvers":["board-resolution-golden"]}
    commodity=capital.register_digital_commodity(issuer,"program-golden-1",commodity_type="SOFTWARE",commercialization_authority=True)
    capital.record_usage(issuer,commodity["commodity_id"],event_nonce="golden-usage",usage_class="API_REQUEST",assurance_level="ENTITY_GATEWAY_OBSERVED",quantity=250000,unit="REQUEST",obligation_units=50000,recognized_revenue_units=40000,currency="CAD")
    class_ev=sign_external(reg_key,"register-00000001","CORPORATE_REGISTER","SHARE_CLASS_REGISTER",issuer,"corp-register:golden-class")
    share=capital.record_share_class_snapshot(issuer,"A",authorized_units=1000000,recorded_issued_units=100000,recorded_outstanding_units=100000,external_evidence=class_ev,authority=authority,transaction_nonce="golden-class")
    holders_ev=sign_external(reg_key,"register-00000001","CORPORATE_REGISTER","SHAREHOLDER_REGISTER",issuer,"corp-register:golden-holders")
    capital.record_shareholder_snapshot(issuer,share["class_id"],{"founder":60000,"investor-a":40000},external_evidence=holders_ev,authority=authority,transaction_nonce="golden-holders")
    market_ev=sign_external(market_key,"market-00000001","MARKET_DATA_PROVIDER","MARKET_PRICE_OBSERVATION",issuer,"market:golden-trade")
    capital.record_external_market_observation(issuer,share["class_id"],amount_minor=725,currency="CAD",source="market-00000001",observed_at_ms=int(time.time()*1000),external_evidence=market_ev,price_class="TRADE")
    capital.record_modeled_valuation(issuer,class_id=share["class_id"],amount_minor=125000000,currency="CAD",methodology="golden-test-model")
    post={"authorized_units":1000000,"recorded_issued_units":120000,"positions":{"founder":60000,"investor-a":40000,"investor-b":20000}}
    action_ev=sign_external(reg_key,"register-00000001","CORPORATE_REGISTER","CORPORATE_ACTION_RESULT",issuer,"corp-register:golden-issuance",payload={"action_type":"ISSUANCE","class_id":share["class_id"],"post_capitalization":post})
    action=actions.record_action(issuer,share["class_id"],action_type="ISSUANCE",jurisdiction="CA-BC",instrument_class="CORPORATE_EQUITY",effective_at_ms=int(time.time()*1000),external_evidence=action_ev,authority=authority,transaction_nonce="golden-issuance",expected_post_snapshot=post,financial_effect={"consideration_minor":20000,"currency":"CAD"})
    assert action["status"]=="RECONCILED"; capital_event_id=action["adopted_capitalization"]["event"]["event_id"]
    assert 60000/100000==0.6 and 60000/120000==0.5
    transfer_post={"authorized_units":1000000,"recorded_issued_units":120000,"positions":{"founder":60000,"investor-a":30000,"investor-b":30000}}
    transfer_ev=sign_external(reg_key,"register-00000001","CORPORATE_REGISTER","CORPORATE_ACTION_RESULT",issuer,"corp-register:golden-transfer",payload={"action_type":"TRANSFER","class_id":share["class_id"],"post_capitalization":transfer_post})
    forged=dict(transfer_ev); forged["external_authority_ref"]="corp-register:forged-transfer"
    with pytest.raises(PermissionError): actions.record_action(issuer,share["class_id"],action_type="TRANSFER",jurisdiction="CA-BC",instrument_class="CORPORATE_EQUITY",effective_at_ms=int(time.time()*1000),external_evidence=forged,authority=authority,transaction_nonce="golden-transfer-forged",expected_post_snapshot=transfer_post)
    transfer=actions.record_action(issuer,share["class_id"],action_type="TRANSFER",jurisdiction="CA-BC",instrument_class="CORPORATE_EQUITY",effective_at_ms=int(time.time()*1000),external_evidence=transfer_ev,authority=authority,transaction_nonce="golden-transfer",expected_post_snapshot=transfer_post)
    assert transfer["status"]=="RECONCILED"
    metrics=capital.per_share_metrics(issuer,share["class_id"],"CAD"); assert metrics["denominator"]==120000 and metrics["externally_observed_market_price"]["amount_minor"]==725
    acct_ev=sign_external(acct_key,"accounting-00000001","ACCOUNTING_SYSTEM","ACCOUNTING_JOURNAL",issuer,"accounting:golden-capital")
    entries=[{"account_code":"CASH","direction":"DEBIT","amount_minor":20000,"currency":"CAD","capital_event_id":capital_event_id},{"account_code":"SHARE_CAPITAL","direction":"CREDIT","amount_minor":20000,"currency":"CAD","capital_event_id":capital_event_id}]
    batch=accounting.record_journal_snapshot(issuer,entries,external_evidence=acct_ev,authority=authority,transaction_nonce="golden-journal")
    payment=settlement.create(investor,issuer,amount_units=20000,currency="CAD",obligation_ref=capital_event_id,transaction_nonce="golden-payment",settlement_kind="EXTERNAL_PAYMENT")
    settlement.authorize(investor,payment["settlement_id"]); settlement.record_external_evidence(investor,payment["settlement_id"],"PROVIDER_CONFIRMED",{"provider":"golden-test-bank","payment_id":"pay-golden-1"}); settlement.confirm(investor,payment["settlement_id"])
    reconciled=accounting.reconcile_capital_event(issuer,capital_event_id,batch["batch_id"],expected_amount_minor=20000,currency="CAD",settlement_id=payment["settlement_id"],require_external_cash=True)
    assert reconciled["accounting_reconciled"] is True and reconciled["external_cash_verified"] is True
    disclosure=capital.disclosure_snapshot(issuer,scope="INVESTOR_CONFIDENTIAL"); assert len(disclosure["snapshot_sha256"])==64
    assert capital.verify_invariants(issuer)["pass"] is True
    portable=P.PortableStateManager(state,identity); backup=portable.create_encrypted_backup(tmp_path/"golden-state.enc")
    key=base64.urlsafe_b64decode(backup["key_b64"]); unavailable=tmp_path/"state_unavailable"; state.rename(unavailable); assert not state.exists()
    portable.restore_encrypted_backup(backup["path"],key,state); assert state.exists()
    restored_identity=I.EntityIdentityVault(state); manifest=restored_identity.load_manifest(issuer); assert V.verify_manifest(manifest)
    restored_registry=X.ExternalAuthorityRegistry(state); restored_settlement=E.SettlementEngine(state,restored_identity)
    restored_capital=C.CorporateCapitalEngine(state,restored_identity,settlement_engine=restored_settlement,external_authority_verifier=restored_registry)
    assert restored_capital.verify_invariants(issuer)["pass"] is True
    trust=trust_records(state/"external_authorities"/"authorities.sqlite")
    capital_tables=sqlite_tables(state/"corporate_capital"/"corporate_capital.sqlite")
    action_tables=sqlite_tables(state/"corporate_actions"/"corporate_actions.sqlite")
    accounting_tables=sqlite_tables(state/"capital_accounting"/"capital_accounting.sqlite")
    cap_check=V.verify_corporate_capital_tables(manifest,capital_tables,trust)
    action_check=V.verify_corporate_action_tables(manifest,action_tables,trust)
    accounting_check=V.verify_capital_accounting_tables(manifest,accounting_tables,trust)
    assert cap_check["valid"] is True and cap_check["capital_events_verified"]>=4
    assert action_check["valid"] is True and action_check["actions_verified"]==2
    assert accounting_check["valid"] is True and accounting_check["accounting_batches_verified"]==1
    export_dir=tmp_path/"portable_export"; export=P.PortableStateManager(state,restored_identity).export_entity(issuer,export_dir)
    export_body={k:v for k,v in export.items() if k!="signature"}; assert V.verify_signature_record(manifest,export_body,export["signature"])
    inventory=[{"path":x["name"],"sha256":x["sha256"]} for x in export["files"]]; assert V.verify_file_inventory(export_dir,inventory)["valid"] is True
    portable_cap=json.loads(next(export_dir.glob("*corporate_capital.sqlite.json")).read_text(encoding="utf-8"))["tables"]
    portable_actions=json.loads(next(export_dir.glob("*corporate_actions.sqlite.json")).read_text(encoding="utf-8"))["tables"]
    portable_accounting=json.loads(next(export_dir.glob("*capital_accounting.sqlite.json")).read_text(encoding="utf-8"))["tables"]
    assert V.verify_corporate_capital_tables(manifest,portable_cap,trust)["valid"] is True
    assert V.verify_corporate_action_tables(manifest,portable_actions,trust)["valid"] is True
    assert V.verify_capital_accounting_tables(manifest,portable_accounting,trust)["valid"] is True
