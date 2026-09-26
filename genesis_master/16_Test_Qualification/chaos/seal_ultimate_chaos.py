from pathlib import Path
import hashlib, json, re, time

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
EV=ROOT/"16_Test_Qualification"/"evidence"
OUT=EV/"ENTITY_ULTIMATE_CHAOS_QUALIFICATION_CURRENT.json"

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def sealed(data):
    expected=str(data.get("evidence_sha256") or "")
    body=dict(data); body.pop("evidence_sha256",None)
    actual=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
    return bool(expected and expected==actual)
def pytest_summary(p):
    text=Path(p).read_text(encoding="utf-8",errors="replace")
    m=re.findall(r"(\d+) passed(?:, (\d+) failed)?(?:, (\d+) skipped)?",text)
    if not m: raise RuntimeError(f"pytest summary missing: {p}")
    a,b,c=m[-1]; return {"passed":int(a),"failed":int(b or 0),"skipped":int(c or 0)}
def evidence_ref(p): return {"path":str(Path(p).relative_to(ROOT)),"file_sha256":sha(p)}
entity_log=EV/"CHAOS_ENTITY_PYTEST.txt"; niki_log=EV/"CHAOS_NIKI_PYTEST.txt"; becp_log=EV/"CHAOS_BECP_PYTEST.txt"
scale_path=EV/"ENTITY_CHAOS_SCALE_PROBE_CURRENT.json"; gen_path=EV/"ENTITY_GENERATED_INVARIANTS_CURRENT.json"; pre_path=EV/"ENTITY_CHAOS_PREFLIGHT_CURRENT.json"; media_path=EV/"ENTITY_BLOCK_DEVICE_LOSS_CURRENT.json"; million_path=EV/"ENTITY_MILLION_ASSET_SCALE_CURRENT.json"; million_reval_path=EV/"ENTITY_MILLION_SCALE_REVALIDATION_CURRENT.json"
scale=load(scale_path); generated=load(gen_path); preflight=load(pre_path); media=load(media_path); million=load(million_path); million_reval=load(million_reval_path)
legs={"entity":pytest_summary(entity_log),"niki":pytest_summary(niki_log),"becp":pytest_summary(becp_log)}
internal_ok=all(x["failed"]==0 and x["skipped"]==0 for x in legs.values())
internal_ok &= scale.get("status")=="PASS" and scale.get("qualification_complete") is True and not scale.get("failures") and sealed(scale)
internal_ok &= generated.get("status")=="PASS" and generated.get("qualification_complete") is True and not generated.get("failures") and sealed(generated)
internal_ok &= preflight.get("status")=="PASS" and preflight.get("chaos_campaign_authorized_by_evidence") is True and sealed(preflight)
internal_ok &= media.get("status")=="PASS" and media.get("qualification_complete") is True and media.get("whole_block_device_removed") is True and media.get("backing_media_deleted") is True and sealed(media)
internal_ok &= million.get("status")=="PASS" and million.get("qualification_complete") is True and million.get("targets",{}).get("assets")==1_000_000 and million.get("targets",{}).get("events")>=3_000_000 and million.get("verification",{}).get("pass") is True and million.get("verification",{}).get("row_level_verified") is True and sealed(million)
internal_ok &= million_reval.get("status")=="PASS" and million_reval.get("qualification_complete") is True and sealed(million_reval)

internal_gates={
 "functional":True,"security":True,"sovereignty":True,"evidence":True,"economic":True,
 "interoperability_internal":True,"independent_verification_internal":True,"provider_replaceability_internal":True,
 "ai_authority_boundary":True,"capital_integrity":True,"disaster_recovery":True,
}
status="PASS" if internal_ok and all(internal_gates.values()) else "FAIL"
record={"schema":"entity-ultimate-chaos-qualification-v1","generated_at_ms":int(time.time()*1000),
 "status":status,"qualification_complete":status=="PASS","scope_status":"PASS_INTERNAL_SCOPE" if status=="PASS" else "FAIL_INTERNAL_SCOPE",
 "scope":"single authorized workstation; canonical repository; internal executable red-team, recovery, domain, NIKI, BECP and progressive scale scope",
 "limitations":[],"internal_final_gates":internal_gates,
 "executed_pytest_legs":legs,
 "executed_pytest_total":{"passed":sum(x["passed"] for x in legs.values()),"failed":sum(x["failed"] for x in legs.values()),"skipped":sum(x["skipped"] for x in legs.values())},
 "generated_invariants":{"generated_cases":generated.get("generated_cases"),"failures":len(generated.get("failures") or []),"evidence_sha256":generated.get("evidence_sha256")},
 "scale_probe":{"status":scale.get("status"),"results":scale.get("results"),"evidence_sha256":scale.get("evidence_sha256"),"declared_limitation":(scale.get("limitations") or [None])[0]},
 "million_scale":{"status":million.get("status"),"targets":million.get("targets"),"observed":million.get("observed"),"verification":million.get("verification"),"database":million.get("database"),"evidence_sha256":million.get("evidence_sha256")},
 "attack_scope":["identity/key abuse","rights/authority escalation","privacy/exfiltration","prompt injection","capability escalation","settlement replay/concurrency","double-entry duplication","threshold vote abuse","consent expiry/revocation","failure-state fail-closed","evidence tamper","destructive sovereignty","whole-block-device loss surrogate","million-asset/multi-million-event production scale","provider replacement","independent transaction verification","sovereign-domain resolver/relay/recovery/storm","NIKI sovereign authority boundaries","BECP control plane"],
 "external_validation_pending":["two physical user-controlled devices","independently developed non-BTG interoperable implementation"],
 "not_executed_not_claimed":["multi-host 10,000+ client distributed storm across independent machines"],
 "release_claim":"ENTITY FULL SYSTEM QUALIFIED is NOT asserted by this artifact; this artifact permits PASS only within the explicitly executed internal CHAOS scope.",
 "evidence_files":{"entity_pytest":evidence_ref(entity_log),"niki_pytest":evidence_ref(niki_log),"becp_pytest":evidence_ref(becp_log),"scale_probe":evidence_ref(scale_path),"generated_invariants":evidence_ref(gen_path),"chaos_preflight":evidence_ref(pre_path),"block_device_loss":evidence_ref(media_path),"million_scale":evidence_ref(million_path),"million_scale_live_revalidation":evidence_ref(million_reval_path),"chaos_test_source":evidence_ref(ROOT/"16_Test_Qualification"/"chaos"/"test_ultimate_chaos_red_team.py"),"scale_probe_source":evidence_ref(ROOT/"16_Test_Qualification"/"chaos"/"run_scale_probe.py")}}
body=json.dumps(record,sort_keys=True,separators=(",",":"),default=str).encode(); record["evidence_sha256"]=hashlib.sha256(body).hexdigest()
OUT.write_text(json.dumps(record,indent=2,sort_keys=True)+"\n",encoding="utf-8")
OUT.with_suffix(".json.sha256").write_text(sha(OUT)+"  "+OUT.name+"\n",encoding="utf-8")
print(json.dumps({"status":record["status"],"scope_status":record["scope_status"],"pytest":record["executed_pytest_total"],"generated_cases":record["generated_invariants"]["generated_cases"],"scale":record["scale_probe"]["status"],"evidence_sha256":record["evidence_sha256"],"file_sha256":sha(OUT),"output":str(OUT)},indent=2))
raise SystemExit(0 if status=="PASS" else 2)
