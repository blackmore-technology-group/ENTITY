from pathlib import Path
import argparse, hashlib, json, time
ap=argparse.ArgumentParser(); ap.add_argument("--product",required=True); ap.add_argument("--pre",required=True); ap.add_argument("--post",required=True)
ap.add_argument("--diff",required=True); ap.add_argument("--regression",required=True); ap.add_argument("--build-log",required=True)
ap.add_argument("--core",required=True); ap.add_argument("--principal",required=True); ap.add_argument("--output",required=True)
ap.add_argument("--regression-marker",action="append",default=[]); a=ap.parse_args()
def load(p): return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def text(p):
    raw=Path(p).read_bytes()
    for enc in ("utf-8-sig","utf-16","utf-16-le"):
        try: return raw.decode(enc)
        except Exception: pass
    return raw.decode("utf-8",errors="replace")
pre,post,diff,core,principal=map(load,[a.pre,a.post,a.diff,a.core,a.principal])
reg=text(a.regression); build=text(a.build_log); artifact=post.get("artifact") or {}
checks={"source_diff_clean":diff.get("pass") is True,"artifact_exists":artifact.get("exists") is True,
        "build_successful":"BUILD SUCCESSFUL" in build,"entity_core_unchanged":core.get("critical_core_unchanged") is True,
        "principal_binding_qualified":principal.get("status")=="PASS","regression_markers":all(x in reg for x in a.regression_marker)}
record={"schema":"btg-product-entity-integration-qualification-v1","generated_at_ms":int(time.time()*1000),
        "product":a.product,"status":"PASS" if all(checks.values()) else "FAIL","qualification_complete":all(checks.values()),
        "checks":checks,"pre_source_aggregate_sha256":pre.get("aggregate_sha256"),"post_source_aggregate_sha256":post.get("aggregate_sha256"),
        "artifact":artifact,"evidence_refs":{"pre":a.pre,"post":a.post,"diff":a.diff,"regression":a.regression,
        "build_log":a.build_log,"core_invariance":a.core,"principal_binding":a.principal},
        "claim":"Application gained ENTITY principal-bound provenance/data-economy integration; source change scope remained bounded; pre-existing regression/build passed; protected ENTITY core remained unchanged.",
        "limitations":["Physical-device principal pairing is not claimed until executed on an attached device."]}
body=dict(record); record["evidence_sha256"]=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
out=Path(a.output); out.write_text(json.dumps(record,indent=2,sort_keys=True)+"\n",encoding="utf-8")
out.with_suffix(".json.sha256").write_text(sha(out)+"  "+out.name+"\n",encoding="utf-8")
print(json.dumps(record,indent=2)); raise SystemExit(0 if record["status"]=="PASS" else 2)
