from pathlib import Path
import hashlib, importlib.util, sys
ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod
I=load("scale_i",ROOT/"01_Core_Runtime"/"identity"/"canonical_identity.py")
L=load("scale_l",ROOT/"04_Entity_Registry"/"event_ledger"/"canonical_event_ledger.py")
R=load("scale_r",ROOT/"04_Entity_Registry"/"ownership_graphs"/"canonical_rights_claims.py")
P=load("scale_p",ROOT/"04_Entity_Registry"/"provenance"/"canonical_provenance.py")
A=load("scale_a",ROOT/"04_Entity_Registry"/"asset_registry"/"canonical_asset_registry.py")

def test_batch_assets_preserve_full_semantics(tmp_path):
    ids=I.EntityIdentityVault(tmp_path); owner=ids.create("Scale Owner","organization")["entity_id"]
    ledger=L.CanonicalEventLedger(tmp_path,ids); rights=R.RightsClaimsGraph(tmp_path,ids); prov=P.AssetProvenanceGraph(tmp_path,ids)
    assets=A.CanonicalAssetRegistry(tmp_path,ids,ledger,rights,prov)
    items=[{"content_sha256":hashlib.sha256(f"asset-{i}".encode()).hexdigest(),"size_bytes":i+1,"media_type":"application/octet-stream","title":f"asset-{i}"} for i in range(100)]
    out=assets.register_batch(owner,items); assert len(out)==100
    assert ledger.verify()["pass"] is True and ledger.verify()["blocks"]==100
    for i in (0,1,50,99):
        rec=out[i]; assert assets.get(rec["asset_id"])["content_sha256"]==items[i]["content_sha256"]
        assert prov.verify_binding_signature(rec["asset_id"]) is True
        claims=rights.claims_for_asset(rec["asset_id"]); assert len(claims)==1 and claims[0]["right_type"]=="DATA_CONTROLLER"
        assert rights.verify_record_signature(claims[0]["claim_id"]) is True
        assert rec["event"]["raw_payload_stored"] is False
