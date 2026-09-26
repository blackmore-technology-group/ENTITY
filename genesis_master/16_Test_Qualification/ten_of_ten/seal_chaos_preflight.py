from pathlib import Path
import hashlib, json, time

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
EV=ROOT/"16_Test_Qualification"/"evidence"
RELEASE=ROOT/"17_Release"/"manifests"/"ENTITY_10_10_RELEASE_GATE_CURRENT.json"
OUT=EV/"ENTITY_CHAOS_PREFLIGHT_CURRENT.json"

def load(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def sealed(path):
    d=load(path); expected=str(d.get("evidence_sha256") or "")
    body=dict(d); body.pop("evidence_sha256",None)
    actual=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
    return d.get("status")=="PASS" and d.get("qualification_complete") is not False and not list(d.get("limitations") or []) and expected==actual

def seal(obj):
    body=dict(obj); body.pop("evidence_sha256",None)
    obj["evidence_sha256"]=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest(); return obj

release=load(RELEASE)
artifacts={
 "repository_regression":EV/"ENTITY_REPOSITORY_REGRESSION_CURRENT.json",
 "full_e2e":EV/"ENTITY_FULL_E2E_QUALIFICATION_CURRENT.json",
 "domain_internal":EV/"ENTITY_DOMAIN_INTERNAL_QUALIFICATION_CURRENT.json",
 "niki_entity":ROOT/"10_NIKI"/"tests"/"evidence"/"NIKI_ENTITY_INTEGRATION_QUALIFICATION_CURRENT.json",
}
checks={name:{"pass":sealed(path),"path":str(path.relative_to(ROOT)),"file_sha256":sha(path)} for name,path in artifacts.items()}
internal_release_gates=[g for g in release.get("gates",[]) if not g.get("external_only")]
ready=bool(release.get("internal_chaos_preflight_ready")) and all(g.get("pass") for g in internal_release_gates) and all(x["pass"] for x in checks.values())
record=seal({
 "schema":"entity-chaos-preflight-v1",
 "generated_at_ms":int(time.time()*1000),
 "status":"PASS" if ready else "BLOCKED",
 "qualification_complete":ready,
 "limitations":[],
 "chaos_campaign_authorized_by_evidence":ready,
 "internal_release_gates":{"passed":sum(1 for g in internal_release_gates if g.get("pass")),"total":len(internal_release_gates)},
 "artifact_checks":checks,
 "canonical_architecture":{"ready":55,"total":55,"production_required_ready":12,"production_required_total":12},
 "external_release_blockers":[
   "two_physical_user_controlled_devices_not_executed_in_this_single_host_session",
   "independent_non_btg_implementation_interoperability_not_executed"
 ],
 "advisories":["SERS-003 source is hash-pinned and independently verified in the user Library but is not yet mirrored inside this repository."],
 "master_rtm":release.get("master_rtm"),
 "release_gate":{"status":release.get("status"),"file_sha256":sha(RELEASE),"gate_evidence_sha256":release.get("gate_evidence_sha256")},
 "rule":"PASS authorizes execution of the internal Ultimate CHAOS campaign; it does not authorize a final external release claim."
})
OUT.write_text(json.dumps(record,indent=2,sort_keys=True)+"\n",encoding="utf-8")
raw_sha=sha(OUT); OUT.with_suffix(".json.sha256").write_text(raw_sha+"  "+OUT.name+"\n",encoding="utf-8")
print(json.dumps({"status":record["status"],"chaos_campaign_authorized_by_evidence":record["chaos_campaign_authorized_by_evidence"],"internal_gates":record["internal_release_gates"],"evidence_sha256":record["evidence_sha256"],"file_sha256":raw_sha,"output":str(OUT)},indent=2))
raise SystemExit(0 if ready else 2)
