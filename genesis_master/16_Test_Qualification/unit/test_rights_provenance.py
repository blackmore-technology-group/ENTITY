from pathlib import Path
import importlib.util, json, sqlite3
import pytest

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); assert spec and spec.loader
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

@pytest.fixture
def rp(tmp_path):
    identity_mod=load("rp_identity",ROOT/"01_Core_Runtime"/"identity"/"canonical_identity.py")
    rights_mod=load("rp_rights",ROOT/"04_Entity_Registry"/"ownership_graphs"/"canonical_rights_claims.py")
    prov_mod=load("rp_prov",ROOT/"04_Entity_Registry"/"provenance"/"canonical_provenance.py")
    identity=identity_mod.EntityIdentityVault(tmp_path/"state")
    rights=rights_mod.RightsClaimsGraph(tmp_path/"state",identity)
    prov=prov_mod.AssetProvenanceGraph(tmp_path/"state",identity)
    return identity_mod,rights_mod,prov_mod,identity,rights,prov

def test_multiple_claimants_and_fractional_rights_coexist(rp):
    _,_,_,identity,rights,_=rp
    a=identity.create("A","person")["entity_id"]; b=identity.create("B","person")["entity_id"]
    ca=rights.assert_claim(a,asset_id="asset-1",right_type="COPYRIGHT_OWNER",share_num=1,share_den=2,territory="CA",evidence_origin="ENTITY_ASSERTION")
    cb=rights.assert_claim(b,asset_id="asset-1",right_type="COPYRIGHT_OWNER",share_num=1,share_den=2,territory="CA",evidence_origin="COUNTERPARTY_ATTESTATION")
    claims=rights.claims_for_asset("asset-1")
    assert len(claims)==2 and {x["claimant_entity_id"] for x in claims}=={a,b}
    assert rights.verify_record_signature(ca["claim_id"]) and rights.verify_record_signature(cb["claim_id"])

def test_claim_verification_conflict_and_supersession_are_explicit(rp):
    _,_,_,identity,rights,_=rp
    claimant=identity.create("Claimant","person")["entity_id"]
    verifier=identity.create("Verifier","person")["entity_id"]
    claim=rights.assert_claim(claimant,asset_id="asset-2",right_type="AUTHOR",evidence={"note":"asserted"})
    with pytest.raises(PermissionError):
        rights.verify_claim(claimant,claim["claim_id"],"CORROBORATED",{"ref":"self"})
    rights.verify_claim(verifier,claim["claim_id"],"CORROBORATED",{"ref":"independent"})
    challenged=rights.set_state(verifier,claim["claim_id"],"CHALLENGED","competing evidence")
    assert challenged["lifecycle_status"]=="CHALLENGED"
    disputed=rights.set_state(verifier,claim["claim_id"],"DISPUTED","formal dispute")
    assert disputed["lifecycle_status"]=="DISPUTED"
    superseding=rights.assert_claim(claimant,asset_id="asset-2",right_type="AUTHOR",evidence={"note":"corrected"},supersedes_claim_id=claim["claim_id"])
    old=rights.set_state(claimant,claim["claim_id"],"SUPERSEDED","corrected by later claim")
    assert old["lifecycle_status"]=="SUPERSEDED" and superseding["supersedes_claim_id"]==claim["claim_id"]

def test_authoritative_verification_requires_authority_role_and_reference(rp):
    _,_,_,identity,rights,_=rp
    claimant=identity.create("Owner","person")["entity_id"]
    ordinary=identity.create("Ordinary","person")["entity_id"]
    authority=identity.create("Authority","organization",metadata={"authority_roles":["RIGHTS_AUTHORITY"]})["entity_id"]
    claim=rights.assert_claim(claimant,asset_id="asset-3",right_type="COPYRIGHT_OWNER")
    with pytest.raises(PermissionError): rights.verify_claim(ordinary,claim["claim_id"],"AUTHORITATIVELY_VERIFIED",{"authority_reference":"x"})
    with pytest.raises(ValueError): rights.verify_claim(authority,claim["claim_id"],"AUTHORITATIVELY_VERIFIED",{})
    out=rights.verify_claim(authority,claim["claim_id"],"AUTHORITATIVELY_VERIFIED",{"authority_reference":"record-77"})
    assert out["verification_level"]=="AUTHORITATIVELY_VERIFIED"

def test_unknown_or_inferred_claim_cannot_silently_enable_licensing(rp):
    _,_,_,identity,rights,_=rp
    owner=identity.create("Potential Owner","person")["entity_id"]
    unknown=rights.assert_claim(owner,asset_id="asset-4",right_type="COPYRIGHT_OWNER",evidence_origin="UNKNOWN")
    decision=rights.can_license(owner,"asset-4")
    assert decision["allowed"] is False and decision["blocked_claims"][0]["reason"]=="insufficient_evidence_origin"
    attested=rights.assert_claim(owner,asset_id="asset-5",right_type="COPYRIGHT_OWNER",evidence_origin="COUNTERPARTY_ATTESTATION")
    assert rights.can_license(owner,"asset-5")["allowed"] is True
    assert unknown["verification_level"]=="SELF_ASSERTED" and attested["verification_level"]=="SELF_ASSERTED"

def test_provenance_hard_binding_c2pa_and_truth_are_separate(rp):
    _,_,_,identity,_,prov=rp
    owner=identity.create("Provenance Owner","person")["entity_id"]
    digest="ab"*32; prov.register_binding(owner,"asset-p1",digest)
    assert prov.verify_hard_binding("asset-p1",digest)["provenance_status"]=="HARD_BINDING_VERIFIED"
    mismatch=prov.verify_hard_binding("asset-p1","cd"*32)
    assert mismatch["hard_binding_match"] is False and mismatch["rights_verified"] is False
    c2pa=prov.apply_c2pa_verification("asset-p1",{"file_sha256":digest,"provenance_verified":True,"validation_state":"VALID","signer_trust":"TRUSTED","active_manifest":"urn:c2pa:test","report_sha256":"ef"*32})
    assert c2pa["provenance_verified"] is True
    assert c2pa["truth_verified"] is False and c2pa["rights_verified"] is False
    assert c2pa["truth_status"]=="NOT_ASSESSED"

def test_provenance_lineage_and_signature_tamper_detection(rp):
    _,_,_,identity,_,prov=rp
    owner=identity.create("Lineage Owner","person")["entity_id"]
    p="11"*32; c="22"*32
    prov.register_binding(owner,"parent",p)
    prov.register_binding(owner,"child",c)
    drv=prov.add_derivation(owner,"parent","child","edit",{"tool":"qualified-editor"})
    lineage=prov.lineage("child")
    assert len(lineage["parents"])==1 and lineage["parents"][0]["derivation_id"]==drv["derivation_id"]
    assert lineage["provenance_is_not_truth"] and lineage["provenance_is_not_rights"]
    assert prov.verify_binding_signature("parent") is True
    with sqlite3.connect(prov.path) as db:
        db.execute("UPDATE bindings SET signature_json=? WHERE asset_id='parent'",(json.dumps({"signature":"tampered"}),)); db.commit()
    assert prov.verify_binding_signature("parent") is False

def test_invalid_fractional_share_and_evidence_origin_fail_closed(rp):
    _,_,_,identity,rights,prov=rp
    owner=identity.create("Validation Owner","person")["entity_id"]
    with pytest.raises(ValueError): rights.assert_claim(owner,asset_id="x",right_type="COPYRIGHT_OWNER",share_num=2,share_den=1)
    with pytest.raises(ValueError): rights.assert_claim(owner,asset_id="x",right_type="COPYRIGHT_OWNER",evidence_origin="MAGIC")
    with pytest.raises(ValueError): prov.register_binding(owner,"x","00"*32,evidence_origin="MAGIC")
