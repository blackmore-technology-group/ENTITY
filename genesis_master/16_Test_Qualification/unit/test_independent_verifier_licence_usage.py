from pathlib import Path
import importlib.util, sys
ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod
V=load("iv_lu",ROOT/"16_Test_Qualification"/"verifier"/"independent_verifier.py")
I=load("iv_lu_i",ROOT/"01_Core_Runtime"/"identity"/"canonical_identity.py")
R=load("iv_lu_r",ROOT/"04_Entity_Registry"/"ownership_graphs"/"canonical_rights_claims.py")
C=load("iv_lu_c",ROOT/"01_Core_Runtime"/"contracts"/"canonical_contracts.py")
U=load("iv_lu_u",ROOT/"01_Core_Runtime"/"usage_control"/"canonical_usage_control.py")

def terms(asset):
    return {"assets":[asset],"rights":["AI_EVALUATION"],"purpose":"research","scope":{},"territory":"CA","duration":{},"consideration":{},"usage_requirements":{"max_quantity_per_event":2},"reporting_requirements":{},"retention_requirements":{},"derivative_rules":{},"revocation_rules":{},"termination_rules":{}}

def build(tmp_path):
    ids=I.EntityIdentityVault(tmp_path/"s"); grantor=ids.create("G","organization")["entity_id"]; licensee=ids.create("L","organization")["entity_id"]
    rights=R.RightsClaimsGraph(tmp_path/"s",ids); rights.assert_claim(grantor,asset_id="asset-1",right_type="LICENSING_AUTHORITY",evidence_origin="ENTITY_ASSERTION")
    contracts=C.ContractLicensingEngine(tmp_path/"s",ids,rights); d=contracts.create_draft(grantor,licensee,terms("asset-1")); contracts.offer(grantor,d["licence_id"]); contracts.accept(licensee,d["licence_id"]); contracts.activate(grantor,d["licence_id"])
    usage=U.UsageControlEngine(tmp_path/"s",ids,contracts); t=usage.issue_gateway_ticket(grantor,licence_id=d["licence_id"],asset_id="asset-1",use_type="AI_EVALUATION",nonce="t1")
    receipt=usage.consume_gateway_ticket(licensee,t["ticket_id"],purpose="research",nonce="r1")
    return ids,grantor,licensee,contracts.get(d["licence_id"]),receipt

def test_independent_licence_and_usage_verification(tmp_path):
    ids,g,l,licence,receipt=build(tmp_path)
    manifests={g:ids.load_manifest(g),l:ids.load_manifest(l)}
    lv=V.verify_licence_record(licence,manifests)
    uv=V.verify_usage_receipt(receipt,manifests[receipt["signature"]["entity_id"]])
    assert lv["valid"] is True and lv["events_verified"]==len(licence["events"])
    assert uv["valid"] is True and uv["assurance"]=="ENTITY_GATEWAY_OBSERVED"
    assert uv["independently_verified"] is False

def test_independent_verifier_rejects_tampering(tmp_path):
    ids,g,l,licence,receipt=build(tmp_path); manifests={g:ids.load_manifest(g),l:ids.load_manifest(l)}
    bad_licence=dict(licence); bad_events=[dict(x) for x in licence["events"]]; bad_events[-1]["to_state"]="TERMINATED"; bad_licence["events"]=bad_events
    assert V.verify_licence_record(bad_licence,manifests)["valid"] is False
    bad_receipt=dict(receipt); bad_receipt["evidence"]={"tampered":True}
    signer=receipt["signature"]["entity_id"]
    assert V.verify_usage_receipt(bad_receipt,manifests[signer])["valid"] is False
