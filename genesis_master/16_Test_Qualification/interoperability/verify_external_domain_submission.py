from __future__ import annotations
from pathlib import Path
import hashlib, json, subprocess, sys, time

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
KIT=ROOT/"16_Test_Qualification"/"interoperability"/"external_domain_kit"
REF=ROOT/"22_Sovereign_Domain"/"reference"/"verify_entity_domain.py"
OUT=ROOT/"16_Test_Qualification"/"evidence"/"ENTITY_DOMAIN_EXTERNAL_INTEROP_CURRENT.json"

def sha_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def seal(obj: dict) -> dict:
    body=dict(obj); body.pop("evidence_sha256",None)
    obj["evidence_sha256"]=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
    return obj

def vectors(folder: str):
    out={}
    for p in sorted((KIT/folder).glob("*.json")):
        v=json.loads(p.read_text(encoding="utf-8")); out[str(v["name"])]=v
    return out

def main(argv=None):
    args=list(argv or sys.argv[1:])
    if len(args)!=1:
        raise SystemExit("usage: verify_external_domain_submission.py <EXTERNAL_SUBMISSION.json>")
    submission_path=Path(args[0]).resolve()
    submission=json.loads(submission_path.read_text(encoding="utf-8"))
    failures=[]; checks={}
    kit_manifest=json.loads((KIT/"KIT_MANIFEST.json").read_text(encoding="utf-8"))
    checks["kit_hash_match"]=submission.get("kit_sha256")==kit_manifest.get("kit_sha256")
    if not checks["kit_hash_match"]: failures.append("kit_hash_mismatch")
    impl=dict(submission.get("implementer") or {})
    checks["non_btg_attested"]=impl.get("non_btg") is True
    checks["independent_development_attested"]=impl.get("independent_development_attestation") is True
    checks["source_hash_present"]=bool(impl.get("source_sha256"))
    checks["toolchain_declared"]=bool(impl.get("language") and impl.get("toolchain"))
    for name in ("non_btg_attested","independent_development_attested","source_hash_present","toolchain_declared"):
        if not checks[name]: failures.append(name)
    valid=vectors("valid_vectors"); invalid=vectors("invalid_vectors")
    vr=dict(submission.get("valid_results") or {}); ir=dict(submission.get("invalid_results") or {})
    checks["all_valid_vectors_accepted"]=set(vr)==set(valid) and all(bool((vr.get(k) or {}).get("accepted")) for k in valid)
    checks["all_invalid_vectors_rejected"]=set(ir)==set(invalid) and all((ir.get(k) or {}).get("accepted") is False for k in invalid)
    if not checks["all_valid_vectors_accepted"]: failures.append("valid_vector_conformance")
    if not checks["all_invalid_vectors_rejected"]: failures.append("invalid_vector_rejection")
    external_export_name=str(submission.get("external_export_file") or "")
    external_export=(submission_path.parent/external_export_name).resolve() if external_export_name else None
    checks["external_export_present"]=bool(external_export and external_export.is_file())
    if not checks["external_export_present"]:
        failures.append("external_export_missing")
        reference_result={"valid":False,"failures":["external_export_missing"]}; reference_exit=None
    else:
        run=subprocess.run([sys.executable,"-I",str(REF),str(external_export)],cwd=str(submission_path.parent),capture_output=True,text=True)
        reference_exit=run.returncode
        try: reference_result=json.loads(run.stdout)
        except Exception: reference_result={"valid":False,"failures":["reference_verifier_output_unreadable"],"stdout":run.stdout,"stderr":run.stderr}
        checks["btg_reference_accepts_external_export"]=run.returncode==0 and reference_result.get("valid") is True
        if not checks["btg_reference_accepts_external_export"]: failures.append("external_export_reference_verification")
    btg_result=dict(submission.get("btg_export_verification") or {})
    checks["external_impl_accepts_btg_export"]=btg_result.get("valid") is True and bool(btg_result.get("entity_root")) and bool(btg_result.get("domain_id"))
    if not checks["external_impl_accepts_btg_export"]: failures.append("btg_export_not_verified_by_external_impl")
    review=dict(submission.get("independence_review") or {})
    checks["external_independence_reviewed"]=review.get("reviewed") is True and str(review.get("reviewer_organization") or "").strip().upper() not in {"","BTG","BLACKMORE TECHNOLOGY GROUP"}
    if not checks["external_independence_reviewed"]: failures.append("external_independence_review_pending")
    payload=seal({"schema":"entity-domain-external-interoperability-v1","generated_at_ms":int(time.time()*1000),"status":"PASS" if not failures else "BLOCKED","qualification_complete":not failures,"submission_path":str(submission_path),"submission_sha256":sha_file(submission_path),"kit_sha256":kit_manifest.get("kit_sha256"),"checks":checks,"reference_verifier":{"exit_code":reference_exit,"result":reference_result},"failures":failures,"claim":"PASS requires both protocol conformance and externally reviewed non-BTG independence; BTG cannot self-certify this requirement."})
    OUT.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2))
    return 0 if payload["status"]=="PASS" else 2

if __name__=="__main__":
    raise SystemExit(main())
