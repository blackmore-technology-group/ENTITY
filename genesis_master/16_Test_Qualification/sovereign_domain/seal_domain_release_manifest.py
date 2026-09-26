from pathlib import Path
import hashlib, json, time

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
EV=ROOT/"16_Test_Qualification"/"evidence"
DOMAIN=ROOT/"22_Sovereign_Domain"
OUT=ROOT/"17_Release"/"manifests"/"ENTITY_DOMAIN_RELEASE_MANIFEST.json"

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def seal(obj):
    body=dict(obj); body.pop("evidence_sha256",None)
    obj["evidence_sha256"]=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
    return obj

internal=load(EV/"ENTITY_DOMAIN_INTERNAL_QUALIFICATION_CURRENT.json")
overall=load(EV/"ENTITY_DOMAIN_QUALIFICATION_CURRENT.json")
rtm=load(EV/"ENTITY_DOMAIN_RTM.json")
binding=load(DOMAIN/"ENTITY_RUNTIME_BINDING.json")
manifest=seal({
 "schema":"entity-domain-release-manifest-v1",
 "generated_at_ms":int(time.time()*1000),
 "scope":"SERS-ENTITY-DOMAIN-001_v1.0",
 "internal_reference_status":"PASS" if internal.get("status")=="PASS" else "FAIL",
 "full_release_status":overall.get("status"),
 "release_claim_allowed":bool(overall.get("release_claim_allowed")),
 "qualification_complete":bool(overall.get("qualification_complete")),
 "external_validation_pending":list(overall.get("limitations") or []),
 "internal_evidence":{
   "path":str((EV/"ENTITY_DOMAIN_INTERNAL_QUALIFICATION_CURRENT.json").relative_to(ROOT)),
   "file_sha256":sha(EV/"ENTITY_DOMAIN_INTERNAL_QUALIFICATION_CURRENT.json"),
   "evidence_sha256":internal.get("evidence_sha256")},
 "overall_evidence":{
   "path":str((EV/"ENTITY_DOMAIN_QUALIFICATION_CURRENT.json").relative_to(ROOT)),
   "file_sha256":sha(EV/"ENTITY_DOMAIN_QUALIFICATION_CURRENT.json"),
   "evidence_sha256":overall.get("evidence_sha256")},
 "rtm":{"path":str((EV/"ENTITY_DOMAIN_RTM.json").relative_to(ROOT)),"file_sha256":sha(EV/"ENTITY_DOMAIN_RTM.json"),"rtm_sha256":rtm.get("rtm_sha256")},
 "runtime_binding":{"path":str((DOMAIN/"ENTITY_RUNTIME_BINDING.json").relative_to(ROOT)),"file_sha256":sha(DOMAIN/"ENTITY_RUNTIME_BINDING.json"),"status":binding.get("status")},
 "protocol_sha256":sha(DOMAIN/"protocols"/"ENTITY_DOMAIN_PROTOCOLS_v1.md"),
 "sers_sha256":sha(DOMAIN/"SERS-ENTITY-DOMAIN-001_v1.0.md"),
 "qualification_boundary":"Internal reference implementation is release-candidate evidence; full SERS release claim remains blocked until external physical-device and non-BTG interoperability milestones are demonstrated."
})
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8")
raw_sha=sha(OUT)
side=OUT.with_suffix(".json.sha256")
side.write_text(raw_sha+"  "+OUT.name+"\n",encoding="utf-8")
print(json.dumps({"manifest":str(OUT),"file_sha256":raw_sha,"evidence_sha256":manifest["evidence_sha256"],"internal":manifest["internal_reference_status"],"full_release":manifest["full_release_status"],"release_claim_allowed":manifest["release_claim_allowed"],"external_validation_pending":manifest["external_validation_pending"]},indent=2))
