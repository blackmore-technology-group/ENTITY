from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import argparse, hashlib, json, time, urllib.request
ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
EVID=ROOT/"16_Test_Qualification"/"evidence"
def post(url,obj,timeout=1800):
    raw=json.dumps(obj).encode(); req=urllib.request.Request(url,data=raw,headers={'Content-Type':'application/json'},method='POST')
    with urllib.request.urlopen(req,timeout=timeout) as r: return json.loads(r.read())
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--target',required=True); ap.add_argument('--workers',nargs='+',required=True); ap.add_argument('--clients',type=int,default=10000); ap.add_argument('--requests-per-client',type=int,default=1); ap.add_argument('--concurrency-per-worker',type=int,default=128); ap.add_argument('--out',default=str(EVID/'ENTITY_DISTRIBUTED_STORM_CURRENT.json')); args=ap.parse_args()
    target=json.loads(Path(args.target).read_text(encoding='utf-8')); proof=target['resolution_proof']; workers=list(dict.fromkeys(args.workers)); per=[]; left=args.clients
    for i,w in enumerate(workers):
        n=left if i==len(workers)-1 else args.clients//len(workers); left-=n
        per.append((w,{'resolution_proof':proof,'clients':n,'requests_per_client':args.requests_per_client,'concurrency':args.concurrency_per_worker,'timeout':15}))
    started=time.perf_counter(); results=[]
    with ThreadPoolExecutor(max_workers=len(per)) as pool:
        futs={pool.submit(post,w.rstrip('/')+'/run',cfg):w for w,cfg in per}
        for f in as_completed(futs):
            try: results.append(f.result())
            except Exception as exc: results.append({'worker_url':futs[f],'error':type(exc).__name__,'message':str(exc),'logical_clients':0,'requests':0,'successes':0,'failures':1})
    machines=sorted({r.get('machine_id') for r in results if r.get('machine_id')}); clients=sum(int(r.get('logical_clients',0)) for r in results); requests=sum(int(r.get('requests',0)) for r in results); failures=sum(int(r.get('failures',0)) for r in results); successes=sum(int(r.get('successes',0)) for r in results)
    crypto_ok=all(r.get('crypto_required') is True and r.get('dns_forbidden') is True for r in results if not r.get('error'))
    multi=(len(machines)>=2 and clients>=10000 and failures==0 and crypto_ok)
    shakedown=(clients>=10000 and failures==0 and crypto_ok)
    status='PASS_MULTI_MACHINE' if multi else ('PASS_SINGLE_HOST_SHAKEDOWN' if shakedown else 'FAIL')
    record={'schema':'entity-distributed-storm-v1','status':status,'qualification_complete':multi,'target_clients':args.clients,'observed_clients':clients,'requests':requests,'successes':successes,'failures':failures,'unique_machine_ids':machines,'machine_count':len(machines),'multi_machine_requirement_met':multi,'single_host_shakedown_pass':shakedown,'encrypted_entity_direct_protocol_required':True,'dns_forbidden':True,'worker_results':results,'elapsed_seconds':round(time.perf_counter()-started,3),'limitations':[] if multi else ['multi-machine qualification requires at least two distinct physical/authorized host IDs']}
    body=dict(record); record['evidence_sha256']=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':')).encode()).hexdigest(); out=Path(args.out); out.write_text(json.dumps(record,indent=2,sort_keys=True)+'\n',encoding='utf-8'); print(json.dumps({'status':status,'clients':clients,'requests':requests,'failures':failures,'machines':machines,'output':str(out)},indent=2)); return 0 if shakedown else 2
if __name__=='__main__': raise SystemExit(main())
