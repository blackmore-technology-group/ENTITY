from pathlib import Path
import hashlib, importlib.util, json, sys

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); assert spec and spec.loader
    mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod

V=load("entity_independent_verifier_test",ROOT/"16_Test_Qualification"/"verifier"/"independent_verifier.py")
I=load("entity_identity_for_verifier_test",ROOT/"01_Core_Runtime"/"identity"/"canonical_identity.py")


def test_identity_manifest_and_historical_signature_are_independently_verified(tmp_path):
    identity=I.EntityIdentityVault(tmp_path/"state")
    manifest=identity.create("Verifier Subject","organization")
    entity_id=manifest["entity_id"]; payload={"kind":"rights-event","value":7}
    sig=identity.sign(entity_id,payload)
    manifest=identity.rotate_signing_key(entity_id)
    assert V.verify_manifest(manifest)
    assert V.verify_signature_record(manifest,payload,sig)
    bad=dict(sig); bad["payload_sha256"]="00"*32
    assert not V.verify_signature_record(manifest,payload,bad)


def _chain_event(previous_hash:str, sequence:int, value:str):
    body={"schema":"test-event-v1","sequence":sequence,"value":value,"previous_hash":previous_hash}
    body["event_hash"]=hashlib.sha256(V.canonical_json(body)).hexdigest(); return body

def test_hash_chain_and_tamper_detection():
    a=_chain_event("0"*64,1,"a"); b=_chain_event(a["event_hash"],2,"b")
    assert V.verify_hash_chain([a,b])["valid"] is True
    bad=dict(b); bad["value"]="tampered"
    assert V.verify_hash_chain([a,bad])["valid"] is False


def test_merkle_proof_and_payment_assurance():
    left=hashlib.sha256(b"left").hexdigest(); right=hashlib.sha256(b"right").hexdigest()
    root=hashlib.sha256(bytes.fromhex(left)+bytes.fromhex(right)).hexdigest()
    assert V.verify_merkle_proof(left,[{"side":"right","hash":right}],root)
    assert not V.verify_merkle_proof(left,[{"side":"right","hash":"00"*32}],root)
    assert V.classify_external_payment({"level":"PROVIDER_CONFIRMED"})["external_money_movement_verified"] is True
    assert V.classify_external_payment({"level":"MANUALLY_ENTERED"})["external_money_movement_verified"] is False


def test_sealed_evidence_and_file_inventory(tmp_path):
    body={"schema":"evidence-test-v1","status":"PASS"}
    body["evidence_sha256"]=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
    # hash must be over the document before the hash field is added
    expected_body={"schema":"evidence-test-v1","status":"PASS"}
    body["evidence_sha256"]=hashlib.sha256(json.dumps(expected_body,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
    assert V.verify_sealed_json(body)
    f=tmp_path/"artifact.bin"; f.write_bytes(b"artifact")
    inv=[{"path":"artifact.bin","sha256":hashlib.sha256(b"artifact").hexdigest()}]
    assert V.verify_file_inventory(tmp_path,inv)["valid"] is True

def test_release_manifest_signature_verifies_without_production_runtime(tmp_path):
    identity=I.EntityIdentityVault(tmp_path/"state")
    signer=identity.create("Release Signer","organization"); entity_id=signer["entity_id"]
    body={"schema":"entity-release-evidence-v1","release":"test-1","artifacts":[]}
    manifest=dict(body); manifest["signature"]=identity.sign(entity_id,body)
    assert V.verify_release_manifest(manifest,signer)
    tampered=dict(manifest); tampered["release"]="test-2"
    assert not V.verify_release_manifest(tampered,signer)
