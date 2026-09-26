from pathlib import Path
import importlib.util, json, sys

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); assert spec and spec.loader
    mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod

A=load("release_attestation_test",ROOT/"17_Release"/"supply_chain"/"canonical_release_attestation.py")
I=load("release_identity_test",ROOT/"01_Core_Runtime"/"identity"/"canonical_identity.py")
V=load("release_verifier_test",ROOT/"16_Test_Qualification"/"verifier"/"independent_verifier.py")


def mini_root(tmp_path):
    root=tmp_path/"repo"; (root/"src").mkdir(parents=True); (root/"16_Test_Qualification"/"evidence").mkdir(parents=True)
    (root/"src"/"component.py").write_text("from cryptography.hazmat.primitives import hashes\n",encoding="utf-8")
    evidence={"schema":"test-evidence-v1","status":"PASS","evidence_sha256":"placeholder"}
    (root/"16_Test_Qualification"/"evidence"/"ENTITY_TEST_CURRENT.json").write_text(json.dumps(evidence),encoding="utf-8")
    return root


def test_release_attestation_produces_three_distinct_boms(tmp_path):
    root=mini_root(tmp_path); result=A.create_release_attestation(root,tmp_path/"out","rel-1",source_roots=["src"])
    assert result["sbom"]["schema"]=="entity-sbom-v1"
    assert result["rbom"]["schema"]=="entity-rbom-v1" and result["rbom"]["authorship_percentages_inferred"] is False
    assert result["pbom"]["schema"]=="entity-pbom-v1" and result["pbom"]["hidden_model_reasoning_included"] is False
    assert result["manifest"]["signed"] is False and "signature" not in result["manifest"]

def test_rbom_never_infers_commercial_or_redistribution_rights(tmp_path):
    root=mini_root(tmp_path); result=A.create_release_attestation(root,tmp_path/"out2","rel-2",source_roots=["src"])
    assert result["rbom"]["unknowns_explicit"] is True
    for item in result["rbom"]["components"]:
        assert item["commercial_rights"]=="NOT_INFERRED"
        assert item["redistribution_rights"]=="NOT_INFERRED"


def test_signed_release_manifest_is_independently_verifiable(tmp_path):
    root=mini_root(tmp_path); identity=I.EntityIdentityVault(tmp_path/"state")
    signer=identity.create("Qualification Release Signer","organization"); eid=signer["entity_id"]
    result=A.create_release_attestation(root,tmp_path/"out3","rel-3",identity,eid,source_roots=["src"])
    assert result["manifest"]["signed"] is True
    assert V.verify_release_manifest(result["manifest"],signer)
    tampered=dict(result["manifest"]); tampered["release_id"]="rel-evil"
    assert not V.verify_release_manifest(tampered,signer)


def test_manifest_hashes_match_written_artifacts(tmp_path):
    root=mini_root(tmp_path); out=tmp_path/"out4"
    result=A.create_release_attestation(root,out,"rel-4",source_roots=["src"])
    for name in ["SBOM.json","RBOM.json","PBOM.json"]:
        ref=next(x for x in result["manifest"]["artifacts"] if Path(x["path"]).name==name)
        assert V.sha256_file(ref["path"])==ref["sha256"]
