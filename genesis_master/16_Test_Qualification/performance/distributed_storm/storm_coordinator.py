from __future__ import annotations
import argparse, hashlib, json, time
from pathlib import Path


def verify_seal(data: dict) -> bool:
    expected=str(data.get("evidence_sha256") or "")
    body=dict(data); body.pop("evidence_sha256",None)
    actual=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
    return bool(expected and expected==actual)


def seal(obj: dict) -> dict:
    body=dict(obj); body.pop("evidence_sha256",None)
    obj["evidence_sha256"]=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
    return obj


def main():
    p=argparse.ArgumentParser()
    p.add_argument("evidence",nargs="+")
    p.add_argument("--output",required=True)
    p.add_argument("--min-machines",type=int,default=2)
    p.add_argument("--min-clients",type=int,default=10000)
    args=p.parse_args()
    workers=[]; failures=[]
    for item in args.evidence:
        path=Path(item); data=json.loads(path.read_text(encoding="utf-8"))
        if not verify_seal(data): failures.append(f"invalid_seal:{path}")
        if data.get("status")!="PASS": failures.append(f"worker_not_pass:{path}")
        workers.append({"path":str(path),"data":data})
    machine_ids={w["data"].get("machine_id") for w in workers if w["data"].get("machine_id")}
    total_clients=sum(int(w["data"].get("clients") or 0) for w in workers)
    total_requests=sum(int(w["data"].get("requests") or 0) for w in workers)
    failed_requests=sum(int(w["data"].get("failed_requests") or 0) for w in workers)
    if len(machine_ids)<args.min_machines: failures.append(f"machine_count:{len(machine_ids)}<{args.min_machines}")
    if total_clients<args.min_clients: failures.append(f"client_count:{total_clients}<{args.min_clients}")
    if failed_requests: failures.append(f"failed_requests:{failed_requests}")
    targets={w["data"].get("target") for w in workers}
    if len(targets)!=1: failures.append("workers_target_different_endpoints")
    payload=seal({"schema":"entity-distributed-storm-qualification-v1","generated_at_ms":int(time.time()*1000),"status":"PASS" if not failures else "BLOCKED","qualification_complete":not failures,"requirements":{"min_distinct_machines":args.min_machines,"min_clients":args.min_clients},"observed":{"distinct_machines":len(machine_ids),"machine_ids":sorted(machine_ids),"clients":total_clients,"requests":total_requests,"failed_requests":failed_requests,"targets":sorted(str(x) for x in targets)},"workers":[{"path":w["path"],"evidence_sha256":w["data"].get("evidence_sha256"),"machine_id":w["data"].get("machine_id"),"clients":w["data"].get("clients"),"requests":w["data"].get("requests"),"requests_per_second":w["data"].get("requests_per_second")} for w in workers],"failures":failures})
    Path(args.output).write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2)); return 0 if payload["status"]=="PASS" else 2


if __name__=="__main__":
    raise SystemExit(main())
