from pathlib import Path
import base64, importlib.util, sys

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); assert spec and spec.loader
    mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod

I=load("dr_identity",ROOT/"01_Core_Runtime"/"identity"/"canonical_identity.py")
L=load("dr_ledger",ROOT/"04_Entity_Registry"/"event_ledger"/"canonical_event_ledger.py")
R=load("dr_rights",ROOT/"04_Entity_Registry"/"ownership_graphs"/"canonical_rights_claims.py")
P=load("dr_prov",ROOT/"04_Entity_Registry"/"provenance"/"canonical_provenance.py")
A=load("dr_assets",ROOT/"04_Entity_Registry"/"asset_registry"/"canonical_asset_registry.py")
C=load("dr_contracts",ROOT/"01_Core_Runtime"/"contracts"/"canonical_contracts.py")
U=load("dr_usage",ROOT/"01_Core_Runtime"/"usage_control"/"canonical_usage_control.py")
E=load("dr_econ",ROOT/"01_Core_Runtime"/"service_runtime"/"canonical_economics.py")
V=load("dr_vault",ROOT/"08_Data_Vaults"/"canonical_encrypted_vault.py")
B=load("dr_backup",ROOT/"15_Operations"/"backups"/"canonical_portable_state.py")
M=load("dr_migration",ROOT/"15_Operations"/"migration"/"canonical_migration_config.py")

def build_runtime(state):
    ids=I.EntityIdentityVault(state); ledger=L.CanonicalEventLedger(state,ids); rights=R.RightsClaimsGraph(state,ids); prov=P.AssetProvenanceGraph(state,ids)
    assets=A.CanonicalAssetRegistry(state,ids,ledger,rights,prov); contracts=C.ContractLicensingEngine(state,ids,rights,ledger); usage=U.UsageControlEngine(state,ids,contracts,ledger); econ=E.SettlementEngine(state,ids)
    return ids,ledger,rights,prov,assets,contracts,usage,econ

def test_full_destructive_sovereignty_restore_preserves_authoritative_domains(tmp_path):
    state=tmp_path/"state"; ids,ledger,rights,prov,assets,contracts,usage,econ=build_runtime(state)
    owner=ids.create("Recovery Owner","organization")["entity_id"]; user=ids.create("Recovery User","organization")["entity_id"]
    asset=assets.register(owner,content_sha256="ab"*32,size_bytes=123,media_type="application/octet-stream",title="Recovery Asset")
    claim=rights.assert_claim(owner,asset_id=asset["asset_id"],right_type="COPYRIGHT_OWNER",evidence_origin="DIRECT_OBSERVATION",evidence={"source":"qualified-test"})
    assert rights.can_license(owner,asset["asset_id"])["allowed"] is True
    terms={"assets":[asset["asset_id"]],"rights":["VIEW"],"purpose":"research","scope":"single-user","territory":"CA","duration":{"type":"fixed"},"consideration":{"amount_minor":500,"currency":"CAD"},"usage_requirements":{"max_quantity_per_event":10},"reporting_requirements":{},"retention_requirements":{},"derivative_rules":{},"revocation_rules":{},"termination_rules":{}}
    draft=contracts.create_draft(owner,user,terms); contracts.offer(owner,draft["licence_id"]); contracts.accept(user,draft["licence_id"]); contracts.activate(owner,draft["licence_id"])
    receipt=usage.record_declared(user,draft["licence_id"],asset_id=asset["asset_id"],use_type="VIEW",purpose="research",quantity=2,evidence={"session":"r1"},nonce="recovery-usage-1")
    settlement=econ.create(user,owner,amount_units=500,currency="CAD",obligation_ref=draft["licence_id"],transaction_nonce="recovery-payment-1",settlement_kind="EXTERNAL_PAYMENT")
    econ.authorize(user,settlement["settlement_id"]); econ.record_external_evidence(user,settlement["settlement_id"],"PROVIDER_CONFIRMED",{"provider":"test-bank","payment_id":"recovery-pay-1"}); econ.confirm(user,settlement["settlement_id"])
    value=econ.create_value_record(owner,asset["asset_id"],500,"CAD")
    for target in ("OFFER","CONTRACTED","ACCRUED"): value=econ.advance_value(owner,value["value_id"],target)
    value=econ.advance_value(owner,value["value_id"],"SETTLED",settlement_id=settlement["settlement_id"]); value=econ.advance_value(owner,value["value_id"],"REALIZED")
    vault=V.EncryptedDataVault(state); secret=vault.put_bytes(owner,b"recoverable sovereign payload",classification="RESTRICTED")
    migration=M.MigrationConfiguration(state,ids); migration.create(owner,external_dependencies=[{"provider":"payment-provider","locally_recoverable":False}])
    checkpoint=ledger.checkpoint(owner); assert ledger.verify_checkpoint(checkpoint["checkpoint_id"])["pass"] is True
    assert contracts.verify_history(draft["licence_id"])["pass"] is True and usage.verify_receipt(receipt["receipt_id"])["pass"] is True
    assert econ.get_value(value["value_id"])["state"]=="REALIZED" and econ.get_value(value["value_id"])["realized_external"] is True

    portable=B.PortableStateManager(state,ids); backup=portable.create_encrypted_backup(tmp_path/"complete-state.enc")
    key=base64.urlsafe_b64decode(backup["key_b64"]); unavailable=tmp_path/"state_unavailable"; state.rename(unavailable); assert not state.exists()
    portable.restore_encrypted_backup(backup["path"],key,state); assert state.exists()

    ids2,ledger2,rights2,prov2,assets2,contracts2,usage2,econ2=build_runtime(state)
    assert ids2.load_manifest(owner)["entity_id"]==owner and ids2.load_manifest(user)["entity_id"]==user
    restored_asset=assets2.get(asset["asset_id"]); assert restored_asset["controller_entity_id"]==owner
    restored_claims=rights2.claims_for_asset(asset["asset_id"]); assert any(x["claim_id"]==claim["claim_id"] for x in restored_claims)
    assert rights2.verify_record_signature(claim["claim_id"]) is True and rights2.can_license(owner,asset["asset_id"])["allowed"] is True
    assert prov2.verify_hard_binding(asset["asset_id"],"ab"*32)["hard_binding_match"] is True
    assert ledger2.verify()["pass"] is True and ledger2.verify_checkpoint(checkpoint["checkpoint_id"])["pass"] is True
    restored_contract=contracts2.get(draft["licence_id"]); assert restored_contract["state"]=="ACTIVE" and contracts2.verify_history(draft["licence_id"])["pass"] is True
    restored_receipt=usage2.get_receipt(receipt["receipt_id"]); assert restored_receipt["licence_id"]==draft["licence_id"] and usage2.verify_receipt(receipt["receipt_id"])["pass"] is True
    restored_settlement=econ2.get(settlement["settlement_id"]); assert restored_settlement["state"]=="CONFIRMED" and restored_settlement["money_movement_verified"] is True
    assert econ2.balance(owner,"CAD")["net"]==500 and econ2.balance(user,"CAD")["net"]==-500
    restored_value=econ2.get_value(value["value_id"]); assert restored_value["state"]=="REALIZED" and restored_value["realized_external"] is True
    vault2=V.EncryptedDataVault(state); assert vault2.read_bytes(owner,secret["vault_object_id"])==b"recoverable sovereign payload"
    migration2=M.MigrationConfiguration(state,ids2); migration_check=migration2.verify(); assert migration_check["pass"] is True and migration_check["relative_domain_paths"] is True

    export_dir=tmp_path/"independent_export"; exported=B.PortableStateManager(state,ids2).export_entity(owner,export_dir)
    assert exported["private_keys_included"] is False and exported["raw_vault_content_included"] is False and exported["local_paths_redacted"] is True
    assert (export_dir/"EXPORT_MANIFEST.json").is_file() and len(exported["files"])>=8
    verifier=load("dr_independent_verifier",ROOT/"16_Test_Qualification"/"verifier"/"independent_verifier.py")
    manifest=ids2.load_manifest(owner); export_body={k:v for k,v in exported.items() if k!="signature"}
    assert verifier.verify_signature_record(manifest,export_body,exported["signature"]) is True
    inventory=[{"path":item["name"],"sha256":item["sha256"]} for item in exported["files"]]
    assert verifier.verify_file_inventory(export_dir,inventory)["valid"] is True
