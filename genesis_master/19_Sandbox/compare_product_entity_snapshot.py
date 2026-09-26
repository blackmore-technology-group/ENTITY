from pathlib import Path
import argparse, json, fnmatch

ap=argparse.ArgumentParser()
ap.add_argument("--pre",required=True); ap.add_argument("--post",required=True)
ap.add_argument("--allow",action="append",default=[]); ap.add_argument("--output",required=True)
a=ap.parse_args()
pre=json.loads(Path(a.pre).read_text(encoding="utf-8")); post=json.loads(Path(a.post).read_text(encoding="utf-8"))
p={x["path"]:x for x in pre.get("files",[])}; q={x["path"]:x for x in post.get("files",[])}
changed=sorted(k for k in p.keys()&q.keys() if p[k]["sha256"]!=q[k]["sha256"])
new=sorted(q.keys()-p.keys()); deleted=sorted(p.keys()-q.keys())
allowed=lambda path:any(fnmatch.fnmatch(path,pat) for pat in a.allow)
unexpected=sorted([x for x in changed+new if not allowed(x)]+deleted)
record={"schema":"btg-product-entity-source-diff-v1","product":post.get("product"),
        "pre_aggregate_sha256":pre.get("aggregate_sha256"),"post_aggregate_sha256":post.get("aggregate_sha256"),
        "changed_existing":changed,"new_files":new,"deleted_files":deleted,"allowed_patterns":a.allow,
        "unexpected_changes":unexpected,"pass":not unexpected,"artifact_before":pre.get("artifact"),"artifact_after":post.get("artifact")}
Path(a.output).write_text(json.dumps(record,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps(record,indent=2)); raise SystemExit(0 if record["pass"] else 2)
