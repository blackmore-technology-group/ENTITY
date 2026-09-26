from pathlib import Path
import argparse, hashlib, json, time

ap=argparse.ArgumentParser()
ap.add_argument("--product",required=True)
ap.add_argument("--root",required=True)
ap.add_argument("--artifact")
ap.add_argument("--output",required=True)
a=ap.parse_args(); root=Path(a.root).resolve()
EXCLUDE={"build",".gradle",".cxx",".kotlin","__pycache__",".pytest_cache"}

def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

rows=[]
for p in sorted(root.rglob("*")):
    if not p.is_file() or any(x in EXCLUDE for x in p.relative_to(root).parts): continue
    rows.append({"path":p.relative_to(root).as_posix(),"bytes":p.stat().st_size,"sha256":sha(p)})
aggregate=hashlib.sha256("\n".join(f"{x['path']}:{x['sha256']}" for x in rows).encode()).hexdigest()
record={"schema":"btg-product-entity-integration-snapshot-v1","generated_at_ms":int(time.time()*1000),
        "product":a.product,"source_root":str(root),"file_count":len(rows),"aggregate_sha256":aggregate,"files":rows}
if a.artifact:
    art=Path(a.artifact)
    record["artifact"]={"path":str(art),"exists":art.is_file()}
    if art.is_file():
        record["artifact"].update({"bytes":art.stat().st_size,"sha256":sha(art)})
out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(record,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps({"product":a.product,"file_count":len(rows),"aggregate_sha256":aggregate,
                  "artifact":record.get("artifact"),"output":str(out)},indent=2))
