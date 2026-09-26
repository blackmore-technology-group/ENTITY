from __future__ import annotations
from pathlib import Path
import hashlib, importlib.util, json, shutil, time

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
PRIVATE=Path(r"<LOCAL_DRIVE>/BTG_PRIVATE_RELEASE_TRUST")
RELEASE_ID="ENTITY_INTERNAL_QUALIFIED_SIGNED_2026-09-17"
OUT=ROOT/"17_Release"/"packages"/RELEASE_ID

def loadmod(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path): return json.loads(Path(path).read_text(encoding="utf-8"))

ID=loadmod("signed_dist_identity",ROOT/"01_Core_Runtime"/"identity"/"canonical_identity.py")
ATT=loadmod("signed_dist_attestation",ROOT/"17_Release"/"supply_chain"/"canonical_release_attestation.py")
VERIFY=loadmod("signed_dist_verifier",ROOT/"17_Release"/"trust"/"verify_signed_distribution.py")

REQUIRED=[
 "ROOT_MANIFEST.json","CANONICAL_STATE_CURRENT.json",
 "00_Governance/protocol/ENTITY_PROTOCOL_1_0_FREEZE.json",
 "00_Governance/protocol/ENTITY_PROTOCOL_GOVERNANCE_v1.md",
 "17_Release/manifests/ENTITY_BUILD_MANIFEST_CURRENT.json",
 "17_Release/manifests/ENTITY_BUILD_READINESS_CURRENT.json",
 "17_Release/manifests/ENTITY_10_10_RELEASE_GATE_CURRENT.json",
 "16_Test_Qualification/traceability/MASTER_RTM.json",
 "16_Test_Qualification/evidence/ENTITY_GENESIS_PROOF_CURRENT.json",
 "16_Test_Qualification/evidence/ENTITY_REPOSITORY_REGRESSION_CURRENT.json",
 "16_Test_Qualification/evidence/ENTITY_ULTIMATE_CHAOS_QUALIFICATION_CURRENT.json",
 "16_Test_Qualification/evidence/ENTITY_ENGINEERING_REQUIREMENTS_CLOSURE_CURRENT.json",
 "16_Test_Qualification/evidence/ENTITY_OPEN_SDK_CURRENT.json",
 "16_Test_Qualification/evidence/ENTITY_PRINCIPAL_BINDING_CURRENT.json",
 "16_Test_Qualification/evidence/ENTITY_SIMPLE_SDK_CURRENT.json",
 "16_Test_Qualification/evidence/ENTITY_BTG_APPLICATION_SDK_CURRENT.json",
 "16_Test_Qualification/evidence/HUNTAR_ENTITY_INTEGRATION_CURRENT.json",
 "16_Test_Qualification/evidence/HIKEAR_ENTITY_INTEGRATION_CURRENT.json",
 "16_Test_Qualification/evidence/SEARCHAR_ENTITY_INTEGRATION_CURRENT.json",
 "16_Test_Qualification/evidence/BOUNDARYS_BEST_ENTITY_PRINCIPAL_BINDING_CURRENT.json",
 "10_NIKI/tests/evidence/NIKI_ENTITY_INTEGRATION_QUALIFICATION_CURRENT.json",
]
SOURCE_ROOTS=["00_Governance","01_Core_Runtime","02_Peer_Network","03_Public_Internet_Bridge",
 "04_Entity_Registry","05_Entity_Nodes","06_Hosted_Sites","07_Hosted_Apps","08_Data_Vaults",
 "09_Spatial_AR_Dashboard","11_ADAM","12_BSIE","13_Security","14_Protocols_SDK","15_Operations",
 "16_Test_Qualification","17_Release","18_Research_Design","19_Sandbox","20_Archive","21_Corporate_Capital","22_Sovereign_Domain"]

def build():
    missing=[rel for rel in REQUIRED if not (ROOT/rel).is_file()]
    if missing: raise RuntimeError("required release artifacts missing: "+", ".join(missing))
    release=load(ROOT/"17_Release/manifests/ENTITY_10_10_RELEASE_GATE_CURRENT.json")
    if release.get("internal_gates_passed")!=release.get("internal_gates_total"):
        raise RuntimeError("internal release gates are not fully green")
    if OUT.exists(): shutil.rmtree(OUT)
    OUT.mkdir(parents=True); (OUT/"artifacts").mkdir(); (OUT/"supply_chain").mkdir()
    artifacts=[]
    for rel in REQUIRED:
        src=ROOT/rel; name=rel.replace("/","__").replace("\\","__"); dst=OUT/"artifacts"/name
        shutil.copy2(src,dst); artifacts.append({"path":str(dst.relative_to(OUT)).replace("\\","/"),"sha256":sha(dst),"bytes":dst.stat().st_size,"source":rel})
    trust_src=ROOT/"17_Release/trust/ENTITY_RELEASE_SIGNER_PUBLIC.json"
    trust_dst=OUT/"ENTITY_RELEASE_SIGNER_PUBLIC.json"; shutil.copy2(trust_src,trust_dst)
    verifier_src=ROOT/"17_Release/trust/verify_signed_distribution.py"
    verifier_dst=OUT/"verify_signed_distribution.py"; shutil.copy2(verifier_src,verifier_dst)
    artifacts.extend([{"path":"ENTITY_RELEASE_SIGNER_PUBLIC.json","sha256":sha(trust_dst),"bytes":trust_dst.stat().st_size,"source":"public_trust_root"},
                      {"path":"verify_signed_distribution.py","sha256":sha(verifier_dst),"bytes":verifier_dst.stat().st_size,"source":"offline_verifier"}])
    files=ATT.source_files(ROOT,SOURCE_ROOTS); sbom=ATT.build_sbom(ROOT,files); rbom=ATT.build_rbom(sbom); pbom=ATT.build_pbom(ROOT,files,ROOT/"16_Test_Qualification/evidence")
    for name,data in [("SBOM.json",sbom),("RBOM.json",rbom),("PBOM.json",pbom)]:
        p=OUT/"supply_chain"/name; p.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        artifacts.append({"path":str(p.relative_to(OUT)).replace("\\","/"),"sha256":sha(p),"bytes":p.stat().st_size,"source":"generated_supply_chain"})
    signer_cfg=load(PRIVATE/"RELEASE_SIGNER.json"); signer_id=signer_cfg["entity_id"]
    vault=ID.EntityIdentityVault(PRIVATE/"state"); signer_manifest=vault.load_manifest(signer_id)
    if sha(trust_src)!=sha(trust_dst): raise RuntimeError("public trust-root copy mismatch")
    manifest={"schema":"entity-signed-distribution-v1","release_id":RELEASE_ID,"generated_at_ms":int(time.time()*1000),
              "status":"INTERNALLY_QUALIFIED_SIGNED_EXTERNAL_VALIDATION_PENDING","signed":True,
              "release_signer_entity_id":signer_id,"public_trust_root_sha256":sha(trust_dst),
              "artifacts":artifacts,"source_roots_covered":SOURCE_ROOTS,
              "internal_release_gates":{"passed":release["internal_gates_passed"],"total":release["internal_gates_total"]},
              "external_release_status":"BLOCKED_PENDING_SOVEREIGN_DOMAIN_EXTERNAL",
              "trust_boundary":"Signature proves package integrity and signer-key possession. External organizational trust in the signer still requires an independently distributed/pinned trust root.",
              "claim":"Signed internally qualified ENTITY distribution. External physical-device and independent non-BTG interoperability milestones are not claimed as passed."}
    manifest["signature"]=vault.sign(signer_id,dict(manifest))
    mp=OUT/"SIGNED_RELEASE_MANIFEST.json"; mp.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    (OUT/"SIGNED_RELEASE_MANIFEST.json.sha256").write_text(sha(mp)+"  SIGNED_RELEASE_MANIFEST.json\n",encoding="utf-8")
    result=VERIFY.verify_distribution(OUT)
    evidence={"schema":"entity-signed-distribution-qualification-v1","generated_at_ms":int(time.time()*1000),"status":"PASS" if result.get("valid") else "FAIL",
              "release_id":RELEASE_ID,"distribution":str(OUT),"manifest_sha256":sha(mp),"verification":result,
              "public_trust_root_sha256":sha(trust_dst),"private_signer_state_distributed":False}
    ep=ROOT/"16_Test_Qualification/evidence/ENTITY_SIGNED_DISTRIBUTION_CURRENT.json"; ep.write_text(json.dumps(evidence,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    ep.with_suffix('.json.sha256').write_text(sha(ep)+"  "+ep.name+"\n",encoding="utf-8")
    return evidence

if __name__=="__main__":
    result=build(); print(json.dumps(result,indent=2,sort_keys=True)); raise SystemExit(0 if result["status"]=="PASS" else 2)
