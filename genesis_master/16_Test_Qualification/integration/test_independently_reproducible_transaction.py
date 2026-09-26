from pathlib import Path
import base64, importlib.util, json, os, shutil, subprocess, sys, time, uuid
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); assert spec and spec.loader
    mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod
def b64(raw): return base64.urlsafe_b64encode(raw).decode().rstrip("=")
def canon(v): return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
def pub(priv): return b64(priv.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw))
def sign_external(priv,authority_id,authority_type,evidence_type,subject,ref,*,payload=None,jurisdiction="CA-BC"):
    now=int(time.time()*1000); body={"schema":"entity-external-authority-evidence-v1","authority_id":authority_id,"authority_type":authority_type,
        "jurisdiction":jurisdiction,"evidence_type":evidence_type,"external_authority_ref":ref,"subject_entity_id":subject,"payload":dict(payload or {}),
        "issued_at_ms":now,"effective_at_ms":now,"nonce":uuid.uuid4().hex}
    body["signature"]=b64(priv.sign(canon(body))); return body

def run_isolated(verifier,bundle,cwd,recovery_manifest=None,state_backup=None):
    env=os.environ.copy(); env.pop("PYTHONPATH",None); env["PYTHONNOUSERSITE"]="1"
    command=[sys.executable,"-I",str(verifier),str(bundle),"--json"]
    if recovery_manifest is not None or state_backup is not None:
        assert recovery_manifest is not None and state_backup is not None
        command.extend(["--recovery-manifest",str(recovery_manifest),"--state-backup",str(state_backup)])
    run=subprocess.run(command,cwd=str(cwd),env=env,capture_output=True,text=True)
    assert run.returncode==0,run.stdout+"\n"+run.stderr
    return json.loads(run.stdout)
def test_independently_reproducible_transaction_survives_live_state_loss(tmp_path):
    I=load("irt_identity",ROOT/"01_Core_Runtime"/"identity"/"canonical_identity.py")
    PERM=load("irt_permissions",ROOT/"01_Core_Runtime"/"permissions"/"canonical_permissions.py")
    L=load("irt_ledger",ROOT/"04_Entity_Registry"/"event_ledger"/"canonical_event_ledger.py")
    R=load("irt_rights",ROOT/"04_Entity_Registry"/"ownership_graphs"/"canonical_rights_claims.py")
    P=load("irt_prov",ROOT/"04_Entity_Registry"/"provenance"/"canonical_provenance.py")
    A=load("irt_assets",ROOT/"04_Entity_Registry"/"asset_registry"/"canonical_asset_registry.py")
    C=load("irt_contracts",ROOT/"01_Core_Runtime"/"contracts"/"canonical_contracts.py")
    U=load("irt_usage",ROOT/"01_Core_Runtime"/"usage_control"/"canonical_usage_control.py")
    E=load("irt_econ",ROOT/"01_Core_Runtime"/"service_runtime"/"canonical_economics.py")
    X=load("irt_external",ROOT/"21_Corporate_Capital"/"external_authorities"/"canonical_external_authority.py")
    J=load("irt_jurisdiction",ROOT/"21_Corporate_Capital"/"jurisdiction"/"canonical_instrument_classification.py")
    CAP=load("irt_capital",ROOT/"21_Corporate_Capital"/"capital_structure"/"canonical_corporate_capital.py")
    ACT=load("irt_actions",ROOT/"21_Corporate_Capital"/"corporate_actions"/"canonical_corporate_actions.py")
    ACC=load("irt_accounting",ROOT/"21_Corporate_Capital"/"accounting"/"canonical_capital_accounting.py")
    B=load("irt_backup",ROOT/"15_Operations"/"backups"/"canonical_portable_state.py")
    T=load("irt_transaction",ROOT/"15_Operations"/"transaction_evidence"/"canonical_transaction_evidence.py")
    state=tmp_path/"state"; ids=I.EntityIdentityVault(state)
    issuer=ids.create("Independent Transaction Corp","organization")["entity_id"]; counterparty=ids.create("Independent Licensee Investor","organization")["entity_id"]
    board1=ids.create("Board Approver One","person")["entity_id"]; board2=ids.create("Board Approver Two","person")["entity_id"]
    rights_authority=ids.create("Rights Authority","organization",metadata={"authority_roles":["RIGHTS_AUTHORITY"]})["entity_id"]
    registry=X.ExternalAuthorityRegistry(state); reg_key=Ed25519PrivateKey.generate(); acct_key=Ed25519PrivateKey.generate(); pay_key=Ed25519PrivateKey.generate()
    registry.trust_authority("corp-register-independent","CORPORATE_REGISTER",pub(reg_key),jurisdictions=["CA-BC"],evidence_types=["SHARE_CLASS_REGISTER","SHAREHOLDER_REGISTER","CAPITAL_STRUCTURE_SNAPSHOT","CORPORATE_ACTION_RESULT"])
    registry.trust_authority("accounting-independent","ACCOUNTING_SYSTEM",pub(acct_key),jurisdictions=["CA-BC"],evidence_types=["ACCOUNTING_JOURNAL"])
    registry.trust_authority("payment-independent","PAYMENT_PROVIDER",pub(pay_key),jurisdictions=["CA-BC"],evidence_types=["PAYMENT_SETTLEMENT_CONFIRMATION"])
    classifier=J.InstrumentClassificationRegistry(state); effective=int(time.time()*1000)-1000
    classifier.register_rule("bc-independent-issuance",jurisdiction="CA-BC",instrument_class="CORPORATE_EQUITY",action="RECORD_ISSUANCE",decision="ALLOW_EVIDENCE_ONLY",version=1,effective_at_ms=effective,authority_ref="qualified-independent-policy")
    ledger=L.CanonicalEventLedger(state,ids); rights=R.RightsClaimsGraph(state,ids); prov=P.AssetProvenanceGraph(state,ids)
    assets=A.CanonicalAssetRegistry(state,ids,ledger,rights,prov); contracts=C.ContractLicensingEngine(state,ids,rights,ledger); usage=U.UsageControlEngine(state,ids,contracts,ledger)
    econ=E.SettlementEngine(state,ids,external_payment_verifier=registry)
    capital=CAP.CorporateCapitalEngine(state,ids,event_ledger=ledger,settlement_engine=econ,external_authority_verifier=registry)
    actions=ACT.CorporateActionLedger(state,ids,capital,registry,classifier); accounting=ACC.CapitalAccountingReconciler(state,ids,capital,registry,settlement_engine=econ)
    threshold=PERM.ThresholdAuthorityStore(state,ids)

    asset=assets.register(issuer,content_sha256="51"*32,size_bytes=4096,media_type="application/octet-stream",title="Independently Verifiable Program")
    assert prov.verify_hard_binding(asset["asset_id"],"51"*32)["hard_binding_match"] is True
    claim=rights.assert_claim(issuer,asset_id=asset["asset_id"],right_type="COPYRIGHT_OWNER",jurisdiction="CA-BC",legal_basis="documented-corporate-ip-record",evidence_origin="DIRECT_OBSERVATION",evidence={"record":"ip-register-1"})
    rights.verify_claim(rights_authority,claim["claim_id"],"AUTHORITATIVELY_VERIFIED",{"authority_reference":"rights-authority-record-1"})
    terms={"assets":[asset["asset_id"]],"rights":["VIEW"],"purpose":"commercial-evaluation","scope":"named-licensee","territory":"CA",
        "duration":{"type":"fixed"},"consideration":{"amount_minor":2500,"currency":"CAD"},"usage_requirements":{"max_quantity_per_event":10},
        "reporting_requirements":{},"retention_requirements":{},"derivative_rules":{},"revocation_rules":{},"termination_rules":{}}
    draft=contracts.create_draft(issuer,counterparty,terms); contracts.offer(issuer,draft["licence_id"]); contracts.accept(counterparty,draft["licence_id"]); contracts.activate(issuer,draft["licence_id"])
    assert claim["claim_id"] in set(contracts.get(draft["licence_id"])["authority_basis_claim_ids"])
    ticket=usage.issue_gateway_ticket(issuer,licence_id=draft["licence_id"],asset_id=asset["asset_id"],use_type="VIEW",quantity=3,nonce="independent-ticket")
    receipt=usage.consume_gateway_ticket(counterparty,ticket["ticket_id"],purpose="commercial-evaluation",nonce="independent-receipt")
    assert usage.verify_receipt(receipt["receipt_id"])["pass"] is True

    license_payment=econ.create(counterparty,issuer,amount_units=2500,currency="CAD",obligation_ref=draft["licence_id"],transaction_nonce="independent-license-payment",settlement_kind="EXTERNAL_PAYMENT")
    pay_ev=sign_external(pay_key,"payment-independent","PAYMENT_PROVIDER","PAYMENT_SETTLEMENT_CONFIRMATION",issuer,"payment:license:independent",
        payload={"settlement_id":license_payment["settlement_id"],"amount_units":2500,"currency":"CAD","payment_id":"provider-license-1"})
    econ.authorize(counterparty,license_payment["settlement_id"]); econ.record_external_evidence(counterparty,license_payment["settlement_id"],"PROVIDER_CONFIRMED",pay_ev); econ.confirm(counterparty,license_payment["settlement_id"])
    value=econ.create_value_record(issuer,asset["asset_id"],2500,"CAD")
    for target in ("OFFER","CONTRACTED","ACCRUED"): value=econ.advance_value(issuer,value["value_id"],target)
    value=econ.advance_value(issuer,value["value_id"],"SETTLED",settlement_id=license_payment["settlement_id"]); value=econ.advance_value(issuer,value["value_id"],"REALIZED")
    assert value["realized_external"] is True
    commodity=capital.register_digital_commodity(issuer,asset["asset_id"],commodity_type="SOFTWARE",commercialization_authority=True,metadata={"title":"Independent Program Commodity"})
    commodity_event=capital.record_usage(issuer,commodity["commodity_id"],event_nonce="independent-commodity-use",usage_class="LICENSED_ACCESS",assurance_level="ENTITY_GATEWAY_OBSERVED",quantity=3,unit="ACCESS",obligation_units=2500,recognized_revenue_units=2500,currency="CAD",evidence={"usage_receipt_id":receipt["receipt_id"],"licence_id":draft["licence_id"],"settlement_id":license_payment["settlement_id"]})
    basic_authority={"approved":True,"approvers":[board1,board2],"basis":"initial externally attested capitalization"}
    class_ev=sign_external(reg_key,"corp-register-independent","CORPORATE_REGISTER","SHARE_CLASS_REGISTER",issuer,"corp-register:independent:class-a",payload={"class_code":"A","authorized_units":1000000})
    share=capital.record_share_class_snapshot(issuer,"A",authorized_units=1000000,recorded_issued_units=100000,recorded_outstanding_units=100000,rights={"votes_per_share":1,"economic_rights":True},external_evidence=class_ev,authority=basic_authority,transaction_nonce="independent-class-a")
    holders_ev=sign_external(reg_key,"corp-register-independent","CORPORATE_REGISTER","SHAREHOLDER_REGISTER",issuer,"corp-register:independent:holders-a-v1",payload={"class_id":share["class_id"],"positions":{board1:60000,board2:40000}})
    capital.record_shareholder_snapshot(issuer,share["class_id"],{board1:60000,board2:40000},external_evidence=holders_ev,authority=basic_authority,transaction_nonce="independent-holders-a-v1")

    policy=threshold.create_policy(issuer,"SHARE_ISSUANCE",[board1,board2],2); request_id="issuance-request-"+uuid.uuid4().hex
    threshold.approve(policy["policy_id"],request_id,board1,object_ref=share["class_id"]); threshold.approve(policy["policy_id"],request_id,board2,object_ref=share["class_id"])
    authorization=threshold.authorize(policy["policy_id"],request_id,"SHARE_ISSUANCE",object_ref=share["class_id"]); assert authorization["allowed"] is True
    corporate_authority={"approved":True,"approvers":[board1,board2],"threshold_policy_id":policy["policy_id"],"threshold_request_id":request_id,"threshold":authorization["threshold"],"approvals":authorization["approvals"]}
    post={"authorized_units":1000000,"recorded_issued_units":120000,"positions":{board1:60000,board2:40000,counterparty:20000}}
    action_ev=sign_external(reg_key,"corp-register-independent","CORPORATE_REGISTER","CORPORATE_ACTION_RESULT",issuer,"corp-register:independent:issuance-1",payload={"action_type":"ISSUANCE","class_id":share["class_id"],"post_capitalization":post})
    action=actions.record_action(issuer,share["class_id"],action_type="ISSUANCE",jurisdiction="CA-BC",instrument_class="CORPORATE_EQUITY",effective_at_ms=int(time.time()*1000),external_evidence=action_ev,authority=corporate_authority,transaction_nonce="independent-share-issuance",expected_post_snapshot=post,financial_effect={"consideration_minor":20000,"currency":"CAD"})
    assert action["status"]=="RECONCILED"; capital_event_id=action["adopted_capitalization"]["event"]["event_id"]
    share_payment=econ.create(counterparty,issuer,amount_units=20000,currency="CAD",obligation_ref=capital_event_id,transaction_nonce="independent-share-payment",settlement_kind="EXTERNAL_PAYMENT")
    share_pay_ev=sign_external(pay_key,"payment-independent","PAYMENT_PROVIDER","PAYMENT_SETTLEMENT_CONFIRMATION",issuer,"payment:shares:independent",
        payload={"settlement_id":share_payment["settlement_id"],"amount_units":20000,"currency":"CAD","payment_id":"provider-shares-1"})
    econ.authorize(counterparty,share_payment["settlement_id"]); econ.record_external_evidence(counterparty,share_payment["settlement_id"],"PROVIDER_CONFIRMED",share_pay_ev); econ.confirm(counterparty,share_payment["settlement_id"])
    acct_ev=sign_external(acct_key,"accounting-independent","ACCOUNTING_SYSTEM","ACCOUNTING_JOURNAL",issuer,"accounting:independent:share-issuance",payload={"capital_event_id":capital_event_id,"amount_minor":20000,"currency":"CAD"})
    entries=[{"account_code":"CASH","direction":"DEBIT","amount_minor":20000,"currency":"CAD","capital_event_id":capital_event_id,"memo":"share subscription cash"},
        {"account_code":"SHARE_CAPITAL","direction":"CREDIT","amount_minor":20000,"currency":"CAD","capital_event_id":capital_event_id,"memo":"share issuance"}]
    batch=accounting.record_journal_snapshot(issuer,entries,external_evidence=acct_ev,authority=corporate_authority,transaction_nonce="independent-capital-journal")
    reconciliation=accounting.reconcile_capital_event(issuer,capital_event_id,batch["batch_id"],expected_amount_minor=20000,currency="CAD",settlement_id=share_payment["settlement_id"],require_external_cash=True)
    assert reconciliation["accounting_reconciled"] is True and reconciliation["external_cash_verified"] is True
    disclosure=capital.disclosure_snapshot(issuer,scope="INDEPENDENT_TRANSACTION_DISCLOSURE")
    assert capital.verify_invariants(issuer)["pass"] is True
    checkpoint=ledger.checkpoint(issuer); assert ledger.verify_checkpoint(checkpoint["checkpoint_id"])["pass"] is True

    exporter=T.TransactionEvidenceExporter(state,ids)
    refs={"asset_id":asset["asset_id"],"claim_id":claim["claim_id"],"licence_id":draft["licence_id"],"usage_receipt_id":receipt["receipt_id"],
        "license_settlement_id":license_payment["settlement_id"],"value_id":value["value_id"],"commodity_id":commodity["commodity_id"],"commodity_event_id":commodity_event["event_id"],
        "threshold_policy_id":policy["policy_id"],"threshold_request_id":request_id,"share_class_id":share["class_id"],"corporate_action_id":action["action_id"],
        "capital_event_id":capital_event_id,"capital_accounting_batch_id":batch["batch_id"],"share_settlement_id":share_payment["settlement_id"],
        "disclosure_snapshot_id":disclosure["snapshot_id"],"ledger_checkpoint_id":checkpoint["checkpoint_id"]}
    tx=exporter.register(issuer,jurisdiction="CA-BC",references=refs,participants=[issuer,counterparty,board1,board2,rights_authority],notes={"purpose":"independently reproducible sovereign economic transaction"})
    portable=B.PortableStateManager(state,ids); package_dir=tmp_path/"sovereign_transaction_export"
    package=exporter.create_sovereign_export(tx["transaction_id"],package_dir,portable)
    recovery_manifest=json.loads(Path(package["recovery_manifest"]).read_text(encoding="utf-8"))
    assert recovery_manifest["private_recovery_key_in_package"] is False and "backup_key_b64" not in recovery_manifest
    verifier_source=ROOT/"16_Test_Qualification"/"verifier"/"standalone_transaction_verifier.py"; isolated_dir=tmp_path/"independent_third_party"
    isolated_dir.mkdir(); isolated_verifier=isolated_dir/"verify_entity_transaction.py"; shutil.copy2(verifier_source,isolated_verifier)
    verifier_text=isolated_verifier.read_text(encoding="utf-8"); assert "Sovereign_Entity_Network" not in verifier_text and "importlib" not in verifier_text
    bundle_path=package_dir/"TRANSACTION_BUNDLE.json"; before=run_isolated(isolated_verifier,bundle_path,isolated_dir,package["recovery_manifest"],package["state_backup"])
    assert before["valid"] is True and before["recovery_package_valid"] is True and all(before["checks"].values())

    tampered=json.loads(bundle_path.read_text(encoding="utf-8")); tampered["evidence"]["digital_commodity"]["event"]["recognized_revenue_units"]+=1
    tampered_path=isolated_dir/"tampered.json"; tampered_path.write_text(json.dumps(tampered,indent=2,sort_keys=True),encoding="utf-8")
    bad=subprocess.run([sys.executable,"-I",str(isolated_verifier),str(tampered_path),"--json"],cwd=str(isolated_dir),capture_output=True,text=True)
    assert bad.returncode==2

    unavailable=tmp_path/"btg_server_state_unavailable"; state.rename(unavailable); assert not state.exists()
    without_server=run_isolated(isolated_verifier,bundle_path,isolated_dir,package["recovery_manifest"],package["state_backup"])
    assert without_server["valid"] is True and without_server["recovery_package_valid"] is True and without_server["transaction_root_sha256"]==before["transaction_root_sha256"] and without_server["result_sha256"]==before["result_sha256"]
    key=base64.urlsafe_b64decode(package["backup_key_b64"]); portable.restore_encrypted_backup(package["state_backup"],key,state); assert state.exists()
    ids2=I.EntityIdentityVault(state); exporter2=T.TransactionEvidenceExporter(state,ids2); restored_dir=tmp_path/"restored_transaction_export"
    restored=exporter2.export_bundle(tx["transaction_id"],restored_dir); after=run_isolated(isolated_verifier,Path(restored["path"]),isolated_dir)
    assert restored["transaction_root_sha256"]==before["transaction_root_sha256"]
    assert after["valid"] is True and after["transaction_root_sha256"]==before["transaction_root_sha256"] and after["result_sha256"]==before["result_sha256"]
