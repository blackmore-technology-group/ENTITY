from pathlib import Path
import hashlib, json, time, os

ROOTS={
  "BTG_FINAL_BUILDS_2026_09_14":Path(r"<LOCAL_DRIVE>/BTG_BUILT_SYSTEMS_2026-09-14"),
  "BOUNDARYSBEST":Path(r"<LOCAL_DRIVE>/Blackmore_Technology_Group\BoundarysBest"),
}
OUT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network\15_Operations\software_inventory\BTG_SOFTWARE_DISCOVERY_INDEX_CURRENT.json")
EXCLUDE_DIRS={"__pycache__",".pytest_cache","node_modules","cache","caches","temp","tmp","obj",".git",".cxx","corpus","runtime_data","runtime_data_prequalification_no_install"}
SECRET_TOKENS=(".env","private","secret","password","token","credential","keystore","recovery.key","signing.key","id_rsa","id_ed25519")

def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(4*1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def classify(path:Path)->str:
    s=path.suffix.lower()
    if s in {".exe",".apk",".msi",".dll"}: return "BINARY_OR_RUNTIME"
    if s in {".json",".md",".txt",".csv",".log",".sha256",".sig"}: return "EVIDENCE_OR_METADATA"
    if s in {".py",".ps1",".cs",".cpp",".h",".kt",".java",".swift",".sh"}: return "SOURCE_OR_SCRIPT"
    return "DATA_OR_ASSET"
def scan_root(label:str, root:Path)->dict:
    files=[]; excluded=[]; errors=[]
    def walk_error(exc):
        errors.append({"path":str(getattr(exc,"filename",root)),"error":f"{type(exc).__name__}: {exc}"})
    for base, dirs, names in os.walk(root,topdown=True,onerror=walk_error):
        dirs[:] = [d for d in dirs if d.lower() not in {x.lower() for x in EXCLUDE_DIRS}]
        basep=Path(base)
        for name in names:
            p=basep/name
            try:
                rel=p.relative_to(root); low=name.lower()
                if any(t in low for t in SECRET_TOKENS):
                    excluded.append({"path":str(rel),"reason":"possible_secret_or_private_key"}); continue
                st=p.stat()
                files.append({"path":str(rel),"bytes":st.st_size,"mtime_ns":st.st_mtime_ns,
                              "sha256":sha256(p),"classification":classify(p)})
            except Exception as exc:
                errors.append({"path":str(p),"error":f"{type(exc).__name__}: {exc}"})
    by_hash={}
    for item in files: by_hash.setdefault(item["sha256"],[]).append(item["path"])
    duplicates={h:v for h,v in by_hash.items() if len(v)>1}
    return {"label":label,"root":str(root),"files":files,"file_count":len(files),
            "total_bytes":sum(x["bytes"] for x in files),"excluded":excluded,"errors":errors,
            "duplicate_hash_groups":duplicates}
record={"schema":"entity-btg-software-discovery-index-v1","generated_at_ms":int(time.time()*1000),
        "mode":"READ_ONLY_DISCOVERY_HASH_CLASSIFICATION","ledger_committed":False,
        "roots":{k:scan_root(k,v) for k,v in ROOTS.items()},
        "policy":{"secrets_excluded":True,"content_copied_into_ledger":False,
                  "rights_status":"BTG_CONTROL_ASSERTION_PENDING_EVIDENCE_REVIEW"}}
summary={k:{"file_count":v["file_count"],"total_bytes":v["total_bytes"],
            "excluded_count":len(v["excluded"]),"errors":len(v["errors"]),
            "duplicate_hash_groups":len(v["duplicate_hash_groups"])} for k,v in record["roots"].items()}
record["summary"]=summary
body=json.dumps(record,sort_keys=True,separators=(",",":"),default=str).encode()
record["index_sha256"]=hashlib.sha256(body).hexdigest()
OUT.write_text(json.dumps(record,indent=2,sort_keys=True)+"\n",encoding="utf-8")
OUT.with_suffix(".json.sha256").write_text(hashlib.sha256(OUT.read_bytes()).hexdigest()+"  "+OUT.name+"\n",encoding="utf-8")
status="PASS" if all(not x["errors"] for x in record["roots"].values()) else "PASS_WITH_READ_ERRORS"
print(json.dumps({"status":status,"summary":summary,"index_sha256":record["index_sha256"],"output":str(OUT)},indent=2))

