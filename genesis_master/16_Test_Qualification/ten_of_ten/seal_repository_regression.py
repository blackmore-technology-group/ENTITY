from pathlib import Path
import hashlib, json, re, time

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
EV=ROOT/"16_Test_Qualification"/"evidence"
OUT=EV/"ENTITY_REPOSITORY_REGRESSION_CURRENT.json"

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read_text(p):
    raw=Path(p).read_bytes()
    return raw.decode("utf-16") if raw.startswith((b"\xff\xfe",b"\xfe\xff")) else raw.decode("utf-8",errors="replace")
def parse(p):
    text=read_text(p); lines=[x.strip() for x in text.splitlines() if " passed" in x and " in " in x]
    if not lines: raise RuntimeError(f"no pytest summary: {p}")
    line=lines[-1]
    def n(label):
        m=re.search(rf"(\d+)\s+{label}",line); return int(m.group(1)) if m else 0
    return {"passed":n("passed"),"failed":n("failed"),"skipped":n("skipped"),"warnings":n("warnings?"),"summary":line}
def seal(obj):
    body=dict(obj); body.pop("evidence_sha256",None)
    obj["evidence_sha256"]=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest(); return obj
legs={
 "entity_qualification":EV/"ENTITY_BUILD_REGRESSION_PYTEST.txt",
 "niki_entity_unified":ROOT/"10_NIKI"/"sovereign_adapted"/"Blackmore_Central_Intelligence_Advanced_NIKI_ADAM_BSIE_v0.6.1_AR_INTELLIGENCE_COMPLETE"/"central_runtime"/"tests"/"evidence"/"FULL_PYTEST_NIKI_POST_SERS_HARNESS.txt",
 "becp_core":EV/"BECP_CORE_REGRESSION_POST_NIKI_DOMAIN.txt",
}
results={name:dict(parse(path),path=str(path.relative_to(ROOT)),file_sha256=sha(path)) for name,path in legs.items()}
failed=sum(x["failed"] for x in results.values()); passed=sum(x["passed"] for x in results.values()); skipped=sum(x["skipped"] for x in results.values())
record=seal({
 "schema":"entity-repository-regression-v1",
 "generated_at_ms":int(time.time()*1000),
 "scope":"AUTHORITATIVE_ENTITY_NIKI_BECP_REGRESSION_LEGS",
 "status":"PASS" if failed==0 else "FAIL",
 "qualification_complete":failed==0,
 "limitations":[],
 "totals":{"passed":passed,"failed":failed,"skipped":skipped},
 "legs":results,
 "non_authoritative_collection_diagnostic":{
   "path":str((EV/"FULL_REPOSITORY_REGRESSION_POST_NIKI_DOMAIN.txt").relative_to(ROOT)),
   "file_sha256":sha(EV/"FULL_REPOSITORY_REGRESSION_POST_NIKI_DOMAIN.txt"),
   "result":"COLLECTION_CONTEXT_INVALID",
   "reason":"recursive root collection mixes compatibility baseline, embedded ADAM/BSIE self-tests and BECP tests without their native import/runtime contexts"
 },
 "excluded_duplicate_or_native_context_trees":["10_NIKI/compatibility_baseline","embedded ADAM component self-test trees","embedded BSIE component self-test trees"],
 "regression_rule":"Each authoritative subsystem test leg executes in its declared runtime context; duplicate archived/bundled component test trees are not reclassified as independent ENTITY release tests."
})
OUT.write_text(json.dumps(record,indent=2,sort_keys=True)+"\n",encoding="utf-8")
file_sha=sha(OUT); OUT.with_suffix(".json.sha256").write_text(file_sha+"  "+OUT.name+"\n",encoding="utf-8")
print(json.dumps({"status":record["status"],"totals":record["totals"],"evidence_sha256":record["evidence_sha256"],"file_sha256":file_sha,"output":str(OUT)},indent=2))
raise SystemExit(0 if record["status"]=="PASS" else 1)
