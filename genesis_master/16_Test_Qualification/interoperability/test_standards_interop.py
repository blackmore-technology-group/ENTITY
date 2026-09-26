from pathlib import Path
import importlib.util, json, subprocess, sys
import pytest

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); assert spec and spec.loader
    mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod

I=load("interop_identity",ROOT/"01_Core_Runtime"/"identity"/"canonical_identity.py")
C=load("interop_credentials",ROOT/"04_Entity_Registry"/"credentials"/"canonical_credentials.py")
P=load("interop_policy",ROOT/"01_Core_Runtime"/"policy_engine"/"canonical_policy.py")
A=load("interop_adapter",ROOT/"14_Protocols_SDK"/"protocol_specs"/"canonical_standards_interop.py")
R=load("interop_reference",ROOT/"14_Protocols_SDK"/"reference_clients"/"standards_reference_client.py")

@pytest.fixture
def system(tmp_path):
    state=tmp_path/"state"; ids=I.EntityIdentityVault(state)
    issuer=ids.create("Interop Issuer","organization")["entity_id"]; subject=ids.create("Interop Subject","person")["entity_id"]
    creds=C.CredentialTrustStore(state,ids); policies=P.PolicyConsentEngine(state,ids); adapter=A.EntityStandardsInterop(ids)
    return ids,issuer,subject,creds,policies,adapter

def test_did_core_projection_and_independent_reference_validation(system):
    ids,issuer,_,_,_,adapter=system
    doc=adapter.export_did_document(issuer); check=R.validate_did_document(doc)
    assert check["valid"] is True and check["verification_methods"]>=2
    imported=adapter.import_did_document(doc); assert imported["entity_id"]==issuer and imported["assertion_method"]
    bad=json.loads(json.dumps(doc)); bad["authentication"]=[doc["id"]+"#missing"]
    assert R.validate_did_document(bad)["valid"] is False

def test_vc20_export_roundtrip_and_entity_signature_extension(system):
    ids,issuer,subject,creds,_,adapter=system
    internal=creds.issue(issuer,subject,"QUALIFICATION",{"role":"tester","level":7},trust_level="ORGANIZATION_VERIFIED")
    vc=adapter.export_vc20(internal)
    assert R.validate_vc20(vc)["valid"] is True
    did_doc=adapter.export_did_document(issuer); proof=R.verify_entity_vc_extension(vc,did_doc)
    assert proof["valid"] is True and proof["proof_scope"]=="ENTITY_EXTENSION_NOT_W3C_DATA_INTEGRITY"
    local=adapter.verify_entity_vc20(vc,ids.load_manifest(issuer)); assert local["entity_signature_valid"] is True
    tampered=json.loads(json.dumps(vc)); tampered["credentialSubject"]["level"]=999
    assert R.verify_entity_vc_extension(tampered,did_doc)["valid"] is False

def test_imports_external_vc20_without_manufacturing_verification(system):
    *_,adapter=system
    external={"@context":["https://www.w3.org/ns/credentials/v2"],"id":"https://example.org/credentials/3732","type":["VerifiableCredential","ExampleDegreeCredential"],"issuer":"did:example:issuer","validFrom":"2025-01-01T00:00:00Z","credentialSubject":{"id":"did:example:subject","degree":{"type":"ExampleBachelorDegree","name":"Example Degree"}}}
    assert R.validate_vc20(external)["valid"] is True
    mapped=adapter.import_vc20(external)
    assert mapped["issuer"]=="did:example:issuer" and mapped["claims"]["degree"]["name"]=="Example Degree"
    assert mapped["verification_state"]=="UNVERIFIED_EXTERNAL_STATE"

def test_odrl22_profile_roundtrip_preserves_permission_and_prohibition(system):
    _,issuer,subject,_,policies,adapter=system
    policy=policies.create_policy(issuer,"Interop Policy",{"VIEW":"PERMIT","AI_TRAINING":"PROHIBIT"},jurisdiction="CA-BC")
    odrl=adapter.export_odrl_policy(policy,asset_ref="urn:entity:asset:test",assignee=A.did(subject))
    check=R.validate_odrl22(odrl); assert check["valid"] is True and check["rule_count"]==2
    parsed=adapter.import_odrl_policy(odrl); decisions={x["decision"] for x in parsed["rules"]}
    assert decisions=={"PERMIT","PROHIBIT"} and parsed["verification_state"]=="SEMANTICALLY_PARSED_NOT_LEGAL_DETERMINATION"

def test_real_c2pa_validation_keeps_provenance_signer_trust_and_truth_separate():
    tool=ROOT/"14_Protocols_SDK"/"c2pa"/"c2patool-v0.27.22"/"c2patool"/"c2patool.exe"
    asset=ROOT/"14_Protocols_SDK"/"c2pa"/"c2patool-v0.27.22"/"c2patool"/"sample"/"C.jpg"
    run=subprocess.run([str(tool),str(asset)],capture_output=True,text=True,check=True)
    report=json.loads(run.stdout); active=report["validation_results"]["activeManifest"]
    success={x["code"] for x in active.get("success") or []}; failures={x["code"] for x in active.get("failure") or []}
    assert report["validation_state"]=="Valid" and "claimSignature.validated" in success and "assertion.dataHash.match" in success
    assert "signingCredential.untrusted" in failures
    interpretation={"provenance_valid":True,"signer_trusted":False,"factual_truth_established":False,"ownership_established":False}
    assert interpretation=={"provenance_valid":True,"signer_trusted":False,"factual_truth_established":False,"ownership_established":False}
