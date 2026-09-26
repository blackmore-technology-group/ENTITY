from pathlib import Path
import base64, importlib.util, sys

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); assert spec and spec.loader
    mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod

def test_destructive_restore_assets_rights_provenance_ledger_and_economics(tmp_path):
    im=load("dsx_id",ROOT/"01_Core_Runtime"/"identity"/"canonical_identity.py")
    rm=load("dsx_rights",ROOT/"04_Entity_Registry"/"ownership_graphs"/"canonical_rights_claims.py")
    pm=load("dsx_prov",ROOT/"04_Entity_Registry"/"provenance"/"canonical_provenance.py")
    lm=load("dsx_ledger",ROOT/"04_Entity_Registry"/"event_ledger"/"canonical_event_ledger.py")
    am=load("dsx_assets",ROOT/"04_Entity_Registry"/"asset_registry"/"canonical_asset_registry.py")
    em=load("dsx_econ",ROOT/"01_Core_Runtime"/"service_runtime"/"canonical_economics.py")
    bm=load("dsx_backup",ROOT/"15_Operations"/"backups"/"canonical_portable_state.py")
    state=tmp_path/"live"; identity=im.EntityIdentityVault(state)
    a=identity.create("Entity A","person")["entity_id"]; b=identity.create("Entity B","person")["entity_id"]
    rights=rm.RightsClaimsGraph(state,identity); prov=pm.AssetProvenanceGraph(state,identity)
    ledger=lm.CanonicalEventLedger(state,identity); assets=am.CanonicalAssetRegistry(state,identity,rights,prov,ledger)
    economics=em.SettlementEngine(state,identity)
    asset=assets.register(a,content_sha256="aa"*32,size_bytes=128,media_type="application/octet-stream",title="Recovery Asset")
    cp=ledger.create_checkpoint(a)
    settlement=economics.create(a,b,amount_units=250,currency="CAD",obligation_ref="lic-1",transaction_nonce="nonce-1")
    economics.authorize(a,settlement["settlement_id"]); economics.confirm(a,settlement["settlement_id"])
    before_balance=economics.balance(b,"CAD")
    assert before_balance["credits"]==250 and ledger.verify_checkpoint(cp["checkpoint_id"])["pass"] is True
    manager=bm.PortableStateManager(state,identity); backup=manager.create_encrypted_backup(tmp_path/"entity.enc")
    key=base64.urlsafe_b64decode(backup["key_b64"])
    restored=tmp_path/"restored"; manager.restore_encrypted_backup(tmp_path/"entity.enc",key,restored)
    restored_identity=im.EntityIdentityVault(restored)
    restored_rights=rm.RightsClaimsGraph(restored,restored_identity); restored_prov=pm.AssetProvenanceGraph(restored,restored_identity)
    restored_ledger=lm.CanonicalEventLedger(restored,restored_identity); restored_assets=am.CanonicalAssetRegistry(restored,restored_identity,restored_rights,restored_prov,restored_ledger)
    restored_econ=em.SettlementEngine(restored,restored_identity)
    restored_asset=restored_assets.get(asset["asset_id"])
    assert restored_asset and restored_asset["content_sha256"]=="aa"*32
    assert restored_ledger.verify()["pass"] is True
    assert restored_ledger.verify_checkpoint(cp["checkpoint_id"])["pass"] is True
    claims=restored_rights.claims_for_asset(asset["asset_id"])
    assert claims and claims[0]["right_type"]=="DATA_CONTROLLER"
    assert restored_prov.verify_hard_binding(asset["asset_id"],"aa"*32)["hard_binding_match"] is True
    after_balance=restored_econ.balance(b,"CAD")
    assert after_balance==before_balance
    restored_settlement=restored_econ.get(settlement["settlement_id"])
    assert restored_settlement["state"]=="CONFIRMED" and restored_settlement["money_movement_verified"] is False
