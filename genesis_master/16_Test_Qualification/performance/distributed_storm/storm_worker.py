from __future__ import annotations
import argparse, asyncio, hashlib, json, os, platform, socket, time
from pathlib import Path
import httpx


def seal(obj: dict) -> dict:
    body=dict(obj); body.pop("evidence_sha256",None)
    obj["evidence_sha256"]=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
    return obj


async def one(client,http_method,url,payload,sem):
    async with sem:
        started=time.perf_counter()
        try:
            if http_method=="POST": r=await client.post(url,json=payload)
            else: r=await client.get(url)
            return r.status_code, time.perf_counter()-started, None
        except Exception as exc:
            return 0, time.perf_counter()-started, type(exc).__name__


async def run(args):
    sem=asyncio.Semaphore(args.concurrency)
    limits=httpx.Limits(max_connections=args.concurrency,max_keepalive_connections=min(args.concurrency,1000))
    timeout=httpx.Timeout(args.timeout)
    payload={"query":"storm qualification","domain":"ENTITY_CORE","runtime_profile":"AR_FIELD"} if args.method=="POST" else None
    async with httpx.AsyncClient(limits=limits,timeout=timeout,verify=not args.insecure) as client:
        tasks=[]
        for client_id in range(args.clients):
            for request_index in range(args.requests_per_client):
                tasks.append(one(client,args.method,args.target,payload,sem))
        started=time.perf_counter(); results=await asyncio.gather(*tasks); elapsed=time.perf_counter()-started
    codes={}; errors={}; latencies=[]
    for code,latency,error in results:
        codes[str(code)]=codes.get(str(code),0)+1
        if error: errors[error]=errors.get(error,0)+1
        latencies.append(latency)
    latencies.sort(); total=len(results); failures=sum(v for k,v in codes.items() if not k.startswith("2"))
    def pct(p):
        if not latencies: return None
        return round(latencies[min(len(latencies)-1,int((len(latencies)-1)*p))]*1000,3)
    out=seal({"schema":"entity-distributed-storm-worker-v1","generated_at_ms":int(time.time()*1000),"status":"PASS" if failures==0 else "FAIL","machine_id":args.machine_id,"host":socket.gethostname(),"platform":platform.platform(),"target":args.target,"method":args.method,"clients":args.clients,"requests_per_client":args.requests_per_client,"requests":total,"concurrency":args.concurrency,"elapsed_seconds":round(elapsed,3),"requests_per_second":round(total/elapsed,2) if elapsed else None,"status_codes":codes,"errors":errors,"failed_requests":failures,"latency_ms":{"p50":pct(.50),"p95":pct(.95),"p99":pct(.99),"max":round(max(latencies)*1000,3) if latencies else None}})
    Path(args.output).write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(out,indent=2)); return 0 if out["status"]=="PASS" else 2


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--target",required=True)
    p.add_argument("--machine-id",required=True)
    p.add_argument("--clients",type=int,required=True)
    p.add_argument("--requests-per-client",type=int,default=1)
    p.add_argument("--concurrency",type=int,default=500)
    p.add_argument("--timeout",type=float,default=30.0)
    p.add_argument("--method",choices=["GET","POST"],default="GET")
    p.add_argument("--insecure",action="store_true")
    p.add_argument("--output",required=True)
    args=p.parse_args()
    if args.clients<1 or args.requests_per_client<1 or args.concurrency<1:
        raise SystemExit("clients, requests-per-client and concurrency must be positive")
    raise SystemExit(asyncio.run(run(args)))


if __name__=="__main__":
    main()
