from __future__ import annotations
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse, hashlib, importlib.util, json, platform, socket, statistics, sys, time

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod
N=load("storm_node",ROOT/"22_Sovereign_Domain"/"node_runtime"/"canonical_node_runtime.py")

def percentile(values,p):
    if not values: return None
    s=sorted(values); return s[min(len(s)-1,max(0,int((len(s)-1)*p)))]

def run_storm(proof, service_id, clients, concurrency, worker_id):
    started=time.perf_counter(); lat=[]; failures=[]
    def one(i):
        t=time.perf_counter(); out=N.EntityDirectClient.request(proof,service_id,{"value":f"{worker_id}:{i}"},timeout=10)
        ok=out.get("status")==200 and out.get("result",{}).get("echo")==f"{worker_id}:{i}" and out.get("direct_encrypted_session") is True and out.get("dns_used") is False
        return ok,(time.perf_counter()-t)*1000
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures={pool.submit(one,i):i for i in range(clients)}
        for future in as_completed(futures):
            i=futures[future]
            try:
                ok,ms=future.result(); lat.append(ms)
                if not ok: failures.append({"client":i,"reason":"response_validation"})
            except Exception as exc: failures.append({"client":i,"reason":type(exc).__name__+":"+str(exc)[:160]})
    elapsed=time.perf_counter()-started; success=clients-len(failures)
    result={"schema":"entity-distributed-storm-worker-v1","worker_id":worker_id,"hostname":platform.node(),"resolved_host":socket.gethostbyname(socket.gethostname()),"clients":clients,"concurrency":concurrency,"success":success,"failures":failures[:100],"failure_count":len(failures),"elapsed_seconds":elapsed,"requests_per_second":success/elapsed if elapsed else None,"latency_ms":{"p50":percentile(lat,.50),"p95":percentile(lat,.95),"p99":percentile(lat,.99),"max":max(lat) if lat else None},"security_expectations":{"dns_used":False,"encrypted_session":True,"node_verified":True}}
    body=dict(result); result["result_sha256"]=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest(); return result

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--proof",required=True); ap.add_argument("--service-id",default="svc-api"); ap.add_argument("--clients",type=int,default=10000); ap.add_argument("--concurrency",type=int,default=128); ap.add_argument("--worker-id",default=platform.node()); ap.add_argument("--out",required=True); args=ap.parse_args()
    proof=json.loads(Path(args.proof).read_text(encoding="utf-8")); result=run_storm(proof,args.service_id,args.clients,args.concurrency,args.worker_id); out=Path(args.out); out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8"); print(json.dumps(result,indent=2)); return 0 if result["failure_count"]==0 else 2

if __name__=="__main__": raise SystemExit(main())
