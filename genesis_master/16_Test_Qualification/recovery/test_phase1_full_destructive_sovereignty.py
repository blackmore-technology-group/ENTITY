from pathlib import Path
import base64, importlib.util, shutil, sys
ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod

def terms(asset_id):
    return {"assets":[asset_id],"rights":["AI_EVALUATION"],"purpose":"research","scope":{"derived_only":True},"territory":"CA","duration":{"days":30},"consideration":{"amount":50,"currency":"CAD"},"usage_requirements":{"max_quantity_per_event":5},"reporting_requirements":{},"retention_requirements":{},"derivative_rules":{},"revocation_rules":{},"termination_rules":{}}

def test_phase1_full_destructive_sovereignty(tmp_path):
    im=load("p1_identity",ROOT/"01_Core_Runtime"/"identity"/"canonical_identity.py")
    polm=load("p1_policy",ROOT/"01_Core_Runtime"/"policy_engine"/"canonical_policy.py")
    capm=load("p1_caps",ROOT/"01_Core_Runtime"/"permissions"/"canonical_permissions.py")
    crm=load("p1_credentials",ROOT/"04_Entity_Registry"/"credentials"/"canonical_credentials.py")
    migm=load("p1_migration",ROOT/"15_Operations"/"migration"/"canonical_migration_config.py")
    sm=load("p1_sources",ROOT/"08_Data_Vaults"/"canonical_data_source_gateway.py")
    vm=load("p1_vault",ROOT/"08_Data_Vaults"/"canonical_encrypted_vault.py")
    lm=load("p1_ledger",ROOT/"04_Entity_Registry"/"event_ledger"/"canonical_event_ledger.py")
    rm=load("p1_rights",ROOT/"04_Entity_Registry"/"ownership_graphs"/"canonical_rights_claims.py")
    pm=load("p1_prov",ROOT/"04_Entity_Registry"/"provenance"/"canonical_provenance.py")
    am=load("p1_assets",ROOT/"04_Entity_Registry"/"asset_registry"/"canonical_asset_registry.py")
    cm=load("p1_contracts",ROOT/"01_Core_Runtime"/"contracts"/"canonical_contracts.py")
    um=load("p1_usage",ROOT/"01_Core_Runtime"/"usage_control"/"canonical_usage_control.py")
    em=load("p1_econ",ROOT/"01_Core_Runtime"/"service_runtime"/"canonical_economics.py")
    bm=load("p1_backup",ROOT/"15_Operations"/"backups"/"canonical_portable_state.py")
    state=tmp_path/"live"; ids=im.EntityIdentityVault(state)
    grantor=ids.create("Grantor","organization")["entity_id"]; licensee=ids.create("Licensee","organization")["entity_id"]
    historical_payload={"phase":"before-recovery"}; historical_sig=ids.sign(grantor,historical_payload)
    credentials=crm.CredentialTrustStore(state,ids); cred=credentials.issue(grantor,licensee,"QUALIFIED_RELATIONSHIP",{"scope":"phase1"},trust_level="ORGANIZATION_VERIFIED")
    recovered_manifest=ids.recover_signing_key(grantor); assert any(m.get("status")=="revoked" for m in recovered_manifest.get("verification_methods") or [])
    policy=polm.PolicyConsentEngine(state,ids); p=policy.create_policy(grantor,"Phase1",{"VIEW":"PERMIT","AI_TRAINING":"PROHIBIT"}); consent=policy.grant_consent(grantor,p["policy_id"],purpose="research",asset_scope=["phase1-scope"],counterparty_entity_id=licensee)
    caps=capm.AuthorityCapabilityStore(state,ids); cap=caps.grant(grantor,"agent-1",operations=["VIEW"])
    source_root=tmp_path/"source_data"; source_root.mkdir(); sample=source_root/"sample.txt"; sample.write_text("sovereign source",encoding="utf-8")
    sources=sm.DataSourceGateway(state); src=sources.enroll_source(grantor,source_root,mode="MANAGED",discovery_allowed=True,content_allowed=True,economic_allowed=True,niki_content_allowed=False)
    vault=vm.EncryptedDataVault(state); vaulted=vault.put_bytes(grantor,b"private sovereign bytes",media_type="text/plain",classification="PRIVATE")
    ledger=lm.CanonicalEventLedger(state,ids); rights=rm.RightsClaimsGraph(state,ids); prov=pm.AssetProvenanceGraph(state,ids)
    assets=am.CanonicalAssetRegistry(state,ids,ledger,rights,prov)
    asset=assets.register(grantor,content_sha256="ab"*32,size_bytes=23,media_type="text/plain",title="Phase1 asset")
    contracts=cm.ContractLicensingEngine(state,ids,rights,ledger)
    draft=contracts.create_draft(grantor,licensee,terms(asset["asset_id"])); contracts.offer(grantor,draft["licence_id"]); contracts.accept(licensee,draft["licence_id"]); contracts.activate(grantor,draft["licence_id"])
    usage=um.UsageControlEngine(state,ids,contracts,ledger)
    ticket=usage.issue_gateway_ticket(grantor,licence_id=draft["licence_id"],asset_id=asset["asset_id"],use_type="AI_EVALUATION",quantity=1,nonce="gateway-ticket")
    receipt=usage.consume_gateway_ticket(licensee,ticket["ticket_id"],purpose="research",nonce="usage-receipt")
    econ=em.SettlementEngine(state,ids); settlement=econ.create(licensee,grantor,amount_units=50,currency="CAD",obligation_ref=draft["licence_id"],transaction_nonce="payment-1",settlement_kind="EXTERNAL_PAYMENT")
    econ.authorize(licensee,settlement["settlement_id"]); econ.record_external_evidence(licensee,settlement["settlement_id"],"PROVIDER_CONFIRMED",{"provider":"qualified-test-provider","transaction_id":"external-1"}); econ.confirm(licensee,settlement["settlement_id"])
    checkpoint=ledger.checkpoint(grantor); before_balance=econ.balance(grantor,"CAD")
    migration=migm.MigrationConfiguration(state,ids); migration.create(grantor,external_dependencies=[{"provider":"qualified-test-provider","dependency":"future payment-status queries","locally_recoverable":False,"historical_evidence_snapshot_locally_recoverable":True}])
    manager=bm.PortableStateManager(state,ids); backup=manager.create_encrypted_backup(tmp_path/"phase1-full.backup.enc")
    key=base64.urlsafe_b64decode(backup["key_b64"]); shutil.rmtree(state)
    restored=tmp_path/"restored"; manager.restore_encrypted_backup(backup["path"],key,restored)

    ids2=im.EntityIdentityVault(restored); policy2=polm.PolicyConsentEngine(restored,ids2); caps2=capm.AuthorityCapabilityStore(restored,ids2)
    credentials2=crm.CredentialTrustStore(restored,ids2); migration2=migm.MigrationConfiguration(restored,ids2)
    sources2=sm.DataSourceGateway(restored); vault2=vm.EncryptedDataVault(restored); ledger2=lm.CanonicalEventLedger(restored,ids2)
    rights2=rm.RightsClaimsGraph(restored,ids2); prov2=pm.AssetProvenanceGraph(restored,ids2); assets2=am.CanonicalAssetRegistry(restored,ids2,ledger2,rights2,prov2)
    contracts2=cm.ContractLicensingEngine(restored,ids2,rights2,ledger2); usage2=um.UsageControlEngine(restored,ids2,contracts2,ledger2); econ2=em.SettlementEngine(restored,ids2)
    restored_manifest=ids2.load_manifest(grantor); assert im.EntityIdentityVault.verify_manifest(restored_manifest)
    assert im.EntityIdentityVault.verify_signature(restored_manifest,historical_payload,historical_sig) is True
    assert any(m.get("status")=="revoked" for m in restored_manifest.get("verification_methods") or [])
    assert credentials2.verify(cred["credential_id"])["signature_valid"] is True
    migration_check=migration2.verify(); assert migration_check["pass"] is True and migration_check["external_dependencies"][0]["locally_recoverable"] is False
    for rel in migration2.load()["domains"].values(): assert (restored/rel).exists()
    assert policy2.evaluate(p["policy_id"],"VIEW")["allowed"] is True; assert policy2.authorize_consent(consent["consent_id"],counterparty_entity_id=licensee,purpose="research",asset_scope=["phase1-scope"],action="VIEW")["allowed"] is True
    assert caps2.authorize(cap["capability_id"],"agent-1","VIEW")["allowed"] is True
    assert sources2.assess_path(sample,purpose="content")["allowed"] is True and sources2.assess_path(sample,purpose="niki_content")["allowed"] is False
    assert vault2.read_bytes(grantor,vaulted["vault_object_id"])==b"private sovereign bytes"
    assert ledger2.verify()["pass"] is True and ledger2.verify_checkpoint(checkpoint["checkpoint_id"])["pass"] is True
    restored_asset=assets2.get(asset["asset_id"]); assert restored_asset["content_sha256"]=="ab"*32
    assert rights2.can_license(grantor,asset["asset_id"])["allowed"] is True
    assert prov2.verify_hard_binding(asset["asset_id"],"ab"*32)["hard_binding_match"] is True
    assert contracts2.get(draft["licence_id"])["state"]=="ACTIVE" and contracts2.verify_history(draft["licence_id"])["pass"] is True
    assert usage2.verify_receipt(receipt["receipt_id"])["pass"] is True and usage2.get_receipt(receipt["receipt_id"])["assurance"]=="ENTITY_GATEWAY_OBSERVED"
    assert econ2.get(settlement["settlement_id"])["money_movement_verified"] is True and econ2.balance(grantor,"CAD")==before_balance
