from pathlib import Path
import hashlib, json, time
ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
BASE=ROOT/"16_Test_Qualification"/"evidence"/"ENTITY_SDK_PRE_ADAPTATION_CORE_HASHES.json"
base=json.loads(BASE.read_text(encoding="utf-8")); current={}; mismatches=[]
for rel,expected in sorted((base.get("files") or {}).items()):
    p=ROOT/rel
    actual=hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
    current[rel]=actual
    if actual!=expected: mismatches.append({"path":rel,"expected":expected,"actual":actual})
aggregate=hashlib.sha256(json.dumps(current,sort_keys=True,separators=(",",":")).encode()).hexdigest()
record={"schema":"entity-core-invariance-verification-v1","generated_at_ms":int(time.time()*1000),
        "status":"PASS" if not mismatches else "FAIL","file_count":len(current),
        "baseline_aggregate_sha256":base.get("aggregate_sha256"),"current_aggregate_sha256":aggregate,
        "mismatches":mismatches,"critical_core_unchanged":not mismatches}
out=ROOT/"16_Test_Qualification"/"evidence"/"ENTITY_CORE_INVARIANCE_CURRENT.json"
out.write_text(json.dumps(record,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(record,indent=2)); raise SystemExit(0 if not mismatches else 2)
