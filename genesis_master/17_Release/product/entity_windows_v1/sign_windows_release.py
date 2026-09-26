from __future__ import annotations
from pathlib import Path
import hashlib, importlib.util, json, time
ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
REL=ROOT/"17_Release"/"packages"/"ENTITY_1.0.0_RC1_WINDOWS_SIGNED"
PRIVATE=Path(r"<LOCAL_DRIVE>/BTG_PRIVATE_RELEASE_TRUST")

def loadmod(name,path):
    spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def main():
    ID=loadmod("entity_windows_release_identity",ROOT/"01_Core_Runtime"/"identity"/"canonical_identity.py")
    VERIFY=loadmod("entity_windows_release_verify",ROOT/"17_Release"/"trust"/"verify_signed_distribution.py")
    signer=json.loads((PRIVATE/"RELEASE_SIGNER.json").read_text(encoding="utf-8")); signer_id=signer["entity_id"]
    vault=ID.EntityIdentityVault(PRIVATE/"state"); vault.load_manifest(signer_id)
    artifacts=[]
    for p in sorted(REL.iterdir()):
        if not p.is_file() or p.name.startswith("SIGNED_RELEASE_MANIFEST"): continue
        artifacts.append({"path":p.name,"sha256":sha(p),"bytes":p.stat().st_size})
    manifest={
      "schema":"entity-signed-distribution-v1","release_id":"ENTITY_1.0.0_RC1_WINDOWS_SIGNED",
      "generated_at_ms":int(time.time()*1000),"status":"ENTITY_1_0_RC1_WINDOWS_INTERNAL_QUALIFIED_EXTERNAL_VALIDATION_PENDING",
      "signed":True,"release_signer_entity_id":signer_id,
      "public_trust_root_sha256":sha(REL/"ENTITY_RELEASE_SIGNER_PUBLIC.json"),"artifacts":artifacts,
      "product":{"name":"ENTITY","version":"1.0.0-rc1","platform":"Windows x64","installer":"ENTITY_Setup.exe"},
      "qualification":{"lifecycle":"PASS","clean_install_scope":"isolated install on BTG PC","two_physical_devices":"PENDING","independent_non_btg_interoperability":"PENDING"},
      "claim":"Frozen ENTITY 1.0 RC1 Windows product build. Internally qualified and signed; external physical-device and independent non-BTG interoperability gates are not claimed as passed."
    }
    manifest["signature"]=vault.sign(signer_id,dict(manifest))
    mp=REL/"SIGNED_RELEASE_MANIFEST.json"; mp.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    (REL/"SIGNED_RELEASE_MANIFEST.json.sha256").write_text(sha(mp)+"  SIGNED_RELEASE_MANIFEST.json\n",encoding="ascii")
    result=VERIFY.verify_distribution(REL)
    evidence={"schema":"entity-windows-rc1-release-qualification-v1","generated_at_ms":int(time.time()*1000),
      "status":"PASS" if result.get("valid") else "FAIL","release_dir":str(REL),"manifest_sha256":sha(mp),
      "installer_sha256":sha(REL/"ENTITY_Setup.exe"),"product_manifest_sha256":sha(REL/"PRODUCT_MANIFEST.json"),
      "lifecycle_evidence_sha256":sha(REL/"ENTITY_WINDOWS_PRODUCT_LIFECYCLE_CURRENT.json"),"offline_verification":result,
      "private_release_signing_state_distributed":False}
    ep=ROOT/"16_Test_Qualification"/"evidence"/"ENTITY_WINDOWS_RC1_RELEASE_CURRENT.json"
    ep.write_text(json.dumps(evidence,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    ep.with_suffix('.json.sha256').write_text(sha(ep)+"  "+ep.name+"\n",encoding="ascii")
    print(json.dumps(evidence,indent=2,sort_keys=True)); return 0 if evidence["status"]=="PASS" else 2
if __name__=="__main__": raise SystemExit(main())
