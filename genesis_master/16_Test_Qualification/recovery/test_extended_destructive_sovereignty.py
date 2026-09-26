from pathlib import Path
import base64, importlib.util, shutil, sys
ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod

def test_extended_destructive_recovery(tmp_path):
    im=load("edr_identity",ROOT/"01_Core_Runtime"/"identity"/"canonical_identity.py")
    lm=load("edr_ledger",ROOT/"04_Entity_Registry"/"event_ledger"/"canonical_event_ledger.py")
    rm=load("edr_rights",ROOT/"04_Entity_Registry"/"ownership_graphs"/"canonical_rights_claims.py")
    pm=load("edr_prov",ROOT/"04_Entity_Registry"/"provenance"/"canonical_provenance.py")
    am=load("edr_assets",ROOT/"04_Entity_Registry"/"asset_registry"/"canonical_asset_registry.py")
    em=load("edr_economics",ROOT/"01_Core_Runtime"/"service_runtime"/"canonical_economics.py")
    bm=load("edr_backup",ROOT/"15_Operations"/"backups"/"canonical_portable_state.py")
    state=tmp_path/"live"; ids=im.EntityIdentityVault(state)
    payer=ids.create("Payer","person")["entity_id"]; payee=ids.create("Payee","person")["entity_id"]
    ledger=lm.CanonicalEventLedger(state,ids); rights=rm.RightsClaimsGraph(state,ids); prov=pm.AssetProvenanceGraph(state,ids)
    assets=am.CanonicalAssetRegistry(state,ids,ledger,rights,prov)
    asset=assets.register(payee,content_sha256="ab"*32,size_bytes=10,media_type="text/plain",title="Qualified asset")
    checkpoint=ledger.checkpoint(payee)
    econ=em.SettlementEngine(state,ids)
    settlement=econ.create(payer,payee,amount_units=250,currency="CAD",obligation_ref="lic-test",transaction_nonce="nonce-001",settlement_kind="EXTERNAL_PAYMENT")
    econ.authorize(payer,settlement["settlement_id"])
    econ.record_external_evidence(payer,settlement["settlement_id"],"PROVIDER_CONFIRMED",{"provider":"test-provider","transaction_id":"tx-001"})
    econ.confirm(payer,settlement["settlement_id"])
    before_balance=econ.balance(payee,"CAD")
    manager=bm.PortableStateManager(state,ids); backup=manager.create_encrypted_backup(tmp_path/"entity-backup.bin")
    key=base64.urlsafe_b64decode(backup["key_b64"])
    shutil.rmtree(state)
    restored=tmp_path/"restored"; manager.restore_encrypted_backup(tmp_path/"entity-backup.bin",key,restored)

    ids2=im.EntityIdentityVault(restored); ledger2=lm.CanonicalEventLedger(restored,ids2)
    rights2=rm.RightsClaimsGraph(restored,ids2); prov2=pm.AssetProvenanceGraph(restored,ids2)
    assets2=am.CanonicalAssetRegistry(restored,ids2,ledger2,rights2,prov2); econ2=em.SettlementEngine(restored,ids2)
    assert ids2.load_manifest(payee)["entity_id"]==payee
    assert ledger2.verify()["pass"] is True
    assert ledger2.verify_checkpoint(checkpoint["checkpoint_id"])["pass"] is True
    restored_asset=assets2.get(asset["asset_id"]); assert restored_asset["content_sha256"]=="ab"*32
    assert rights2.claims_for_asset(asset["asset_id"])[0]["right_type"]=="DATA_CONTROLLER"
    assert prov2.verify_hard_binding(asset["asset_id"],"ab"*32)["hard_binding_match"] is True
    assert econ2.get(settlement["settlement_id"])["money_movement_verified"] is True
    assert econ2.balance(payee,"CAD")==before_balance
