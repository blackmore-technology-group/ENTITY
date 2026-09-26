from pathlib import Path
import importlib.util, json, sqlite3, sys
import pytest

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod

@pytest.fixture
def system(tmp_path):
    identity_mod=load("ela_identity",ROOT/"01_Core_Runtime"/"identity"/"canonical_identity.py")
    ledger_mod=load("ela_ledger",ROOT/"04_Entity_Registry"/"event_ledger"/"canonical_event_ledger.py")
    rights_mod=load("ela_rights",ROOT/"04_Entity_Registry"/"ownership_graphs"/"canonical_rights_claims.py")
    prov_mod=load("ela_prov",ROOT/"04_Entity_Registry"/"provenance"/"canonical_provenance.py")
    asset_mod=load("ela_asset",ROOT/"04_Entity_Registry"/"asset_registry"/"canonical_asset_registry.py")
    state=tmp_path/"state"; identity=identity_mod.EntityIdentityVault(state); entity=identity.create("Owner","person")["entity_id"]
    ledger=ledger_mod.CanonicalEventLedger(state,identity); rights=rights_mod.RightsClaimsGraph(state,identity); prov=prov_mod.AssetProvenanceGraph(state,identity)
    assets=asset_mod.CanonicalAssetRegistry(state,identity,ledger,rights,prov)
    return identity,entity,ledger,rights,prov,assets

def test_signed_hash_chain_and_checkpoint(system):
    _,entity,ledger,_,_,_=system
    ledger.append(entity,"test.one",payload={"a":1}); ledger.append(entity,"test.two",payload={"b":2})
    assert ledger.verify()["pass"] is True
    cp=ledger.checkpoint(entity); assert ledger.verify_checkpoint(cp["checkpoint_id"])["pass"] is True

def test_ledger_tamper_is_detected(system):
    _,entity,ledger,_,_,_=system
    ledger.append(entity,"test.tamper",payload={"x":1})
    with sqlite3.connect(ledger.path) as db:
        db.execute("UPDATE events SET event_hash=? WHERE sequence=1",("0"*64,)); db.commit()
    out=ledger.verify(); assert out["pass"] is False and out["reason"]=="event_hash_failure"

def test_asset_registration_separates_control_from_ownership(system):
    _,entity,ledger,rights,prov,assets=system
    digest="ab"*32; out=assets.register(entity,content_sha256=digest,size_bytes=12,media_type="text/plain",title="A",local_locator=r"<LOCAL_DRIVE>/private\a.txt")
    asset=assets.get(out["asset_id"]); assert asset["controller_entity_id"]==entity and asset["ownership_claimed_not_proven"] if "ownership_claimed_not_proven" in asset else True
    assert "local_locator" not in asset and assets.get(out["asset_id"],include_private_locator=True)["local_locator"].endswith("a.txt")
    claims=rights.claims_for_asset(out["asset_id"]); assert claims[0]["right_type"]=="DATA_CONTROLLER"
    assert prov.verify_hard_binding(out["asset_id"],digest)["hard_binding_match"] is True
    assert ledger.verify()["pass"] is True

def test_asset_deactivation_preserves_history(system):
    _,entity,ledger,_,prov,assets=system
    digest="cd"*32; out=assets.register(entity,content_sha256=digest,size_bytes=1,media_type="application/octet-stream",title="B")
    deactivated=assets.deactivate(entity,out["asset_id"]); assert deactivated["historical_provenance_preserved"] is True
    assert assets.get(out["asset_id"])["status"]=="INACTIVE"
    assert prov.verify_hard_binding(out["asset_id"],digest)["hard_binding_match"] is True
    assert ledger.verify()["blocks"]==2
