from pathlib import Path
import hashlib,json,time,sys
ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
EV=ROOT/"16_Test_Qualification"/"evidence"
MODE=(sys.argv[1] if len(sys.argv)>1 else "pre").lower()
ROOTS=["01_Core_Runtime","04_Entity_Registry","13_Security","15_Operations","21_Corporate_Capital","22_Sovereign_Domain"]
EXCLUDE=("__pycache__","runtime_state","software_inventory")
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
    return h.hexdigest()
files={}
for rel in ROOTS:
    for p in (ROOT/rel).rglob("*.py"):
        r=str(p.relative_to(ROOT)).replace('\\','/')
        if any(x in r for x in EXCLUDE): continue
        files[r]=sha(p)
aggregate=hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()
payload={"schema":"entity-sdk-core-invariance-snapshot-v1","mode":MODE,"generated_at_ms":int(time.time()*1000),"file_count":len(files),"aggregate_sha256":aggregate,"files":files}
out=EV/("ENTITY_SDK_PRE_ADAPTATION_CORE_HASHES.json" if MODE=="pre" else "ENTITY_SDK_POST_ADAPTATION_CORE_HASHES.json")
out.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps({"mode":MODE,"file_count":len(files),"aggregate_sha256":aggregate,"output":str(out)},indent=2))