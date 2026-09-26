from pathlib import Path
import importlib.util, json, sqlite3, sys
import pytest

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); assert spec and spec.loader
    mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod

@pytest.fixture
def stack(tmp_path):
    im=load("cal_identity",ROOT/"01_Core_Runtime"/"identity"/"canonical_identity.py")
    rm=load("cal_rights",ROOT/"04_Entity_Registry"/"ownership_graphs"/"canonical_rights_claims.py")
    pm=load("cal_prov",ROOT/"04_Entity_Registry"/"provenance"/"canonical_provenance.py")
    lm=load("cal_ledger",ROOT/"04_Entity_Registry"/"event_ledger"/"canonical_event_ledger.py")
    am=load("cal_assets",ROOT/"04_Entity_Registry"/"asset_registry"/"canonical_asset_registry.py")
    identity=im.EntityIdentityVault(tmp_path/"state"); owner=identity.create("Owner","person")["entity_id"]
    rights=rm.RightsClaimsGraph(tmp_path/"state",identity); prov=pm.AssetProvenanceGraph(tmp_path/"state",identity)
    ledger=lm.CanonicalEventLedger(tmp_path/"state",identity); assets=am.CanonicalAssetRegistry(tmp_path/"state",identity,rights,prov,ledger)
    return tmp_path,identity,owner,rights,prov,ledger,assets
def test_signed_hash_chain_and_checkpoint(stack):
    _,_,owner,_,_,ledger,_=stack
    for i in range(3):
        ledger.append(owner,event_type="test.event",payload_sha256=(f"{i:064x}"),object_ids=[f"obj-{i}"])
    assert ledger.verify()["pass"] is True
    cp=ledger.create_checkpoint(owner)
    assert cp["leaf_count"]==3 and ledger.verify_checkpoint(cp["checkpoint_id"])["pass"] is True

def test_ledger_tamper_is_detected(stack):
    _,_,owner,_,_,ledger,_=stack
    ledger.append(owner,event_type="test.event",payload_sha256="11"*32)
    with sqlite3.connect(ledger.path) as db:
        db.execute("UPDATE events SET payload_sha256=? WHERE sequence=1",("22"*32,)); db.commit()
    result=ledger.verify()
    assert result["pass"] is False and result["reason"] in {"signature_failure","event_hash_failure"}

def test_asset_registration_does_not_infer_ownership(stack):
    _,_,owner,rights,prov,ledger,assets=stack
    out=assets.register(owner,content_sha256="ab"*32,size_bytes=42,media_type="text/plain",title="Evidence Asset")
    assert out["ownership_not_inferred"] is True
    record=assets.get(out["asset_id"])
    assert "not legal ownership" in record["owner_semantics"]
    claims=rights.claims_for_asset(out["asset_id"])
    assert len(claims)==1 and claims[0]["right_type"]=="DATA_CONTROLLER"
    assert prov.verify_hard_binding(out["asset_id"],"ab"*32)["hard_binding_match"] is True
    assert ledger.verify()["pass"] is True
def test_asset_state_change_preserves_history(stack):
    _,_,owner,rights,prov,ledger,assets=stack
    out=assets.register(owner,content_sha256="cd"*32,size_bytes=10,media_type="application/octet-stream",title="Delete test")
    before=prov.lineage(out["asset_id"])
    changed=assets.set_state(owner,out["asset_id"],"LOCAL_CONTENT_DELETED","content removed locally")
    after=prov.lineage(out["asset_id"])
    assert changed["historical_provenance_preserved"] is True
    assert assets.get(out["asset_id"])["state"]=="LOCAL_CONTENT_DELETED"
    assert before["binding"]["content_sha256"]==after["binding"]["content_sha256"]=="cd"*32
    assert len(rights.claims_for_asset(out["asset_id"]))==1
    assert ledger.verify()["blocks"]==2

def test_ledger_stores_commitment_not_private_payload(stack):
    _,_,owner,_,_,ledger,_=stack
    private=b"private bytes never written to shared ledger"
    digest=__import__("hashlib").sha256(private).hexdigest()
    result=ledger.append(owner,event_type="privacy.commitment",payload_sha256=digest,metadata={"class":"PRIVATE"})
    assert result["raw_payload_stored"] is False
    with sqlite3.connect(ledger.path) as db:
        text=json.dumps(db.execute("SELECT * FROM events").fetchall(),default=str)
    assert private.decode() not in text
