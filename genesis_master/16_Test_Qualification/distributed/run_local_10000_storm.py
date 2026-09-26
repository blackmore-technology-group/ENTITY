from __future__ import annotations
from pathlib import Path
import copy, hashlib, importlib.util, json, sys, tempfile, time
ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod
I=load("storm_identity",ROOT/"01_Core_Runtime"/"identity"/"canonical_identity.py")
D=load("storm_domain",ROOT/"22_Sovereign_Domain"/"core"/"canonical_domain.py")
R=load("storm_resolution",ROOT/"22_Sovereign_Domain"/"resolution"/"canonical_resolution.py")
N=load("storm_runtime",ROOT/"22_Sovereign_Domain"/"node_runtime"/"canonical_node_runtime.py")
W=load("storm_worker_impl",ROOT/"16_Test_Qualification"/"distributed"/"storm_worker.py")

def main():
    lab=Path(r"<LOCAL_DRIVE>/ENTITY_STORM_LAB"); lab.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=lab) as td:
        root=Path(td); state=root/"state"; ids=I.EntityIdentityVault(state); owner=ids.create("ENTITY Storm Target","organization")["entity_id"]
        domain=D.EntityDomainAuthority(state,ids); created=domain.create_domain(owner,requested_name="storm.entity"); did=created["domain_id"]
        node=N.EntityNodeRuntime(root/"node","storm-node"); node.add_api_service("svc-api",lambda req:{"echo":req.get("value"),"owner_controlled":True}); started=node.start("127.0.0.1",0)
        try:
            domain.authorize_node(owner,did,node.public_key_b64,permitted_services=["API"],node_id="storm-node")
            domain.publish_service(owner,did,"storm-node","API",{"host":started["host"],"port":started["port"]},capabilities=["ECHO"],access_class="PUBLIC",policy_refs=["policy:storm"],data_classifications=["PUBLIC"],service_id="svc-api")
            resolver=R.EntityNativeResolver(ids); resolver.add_snapshot("storm-local",domain.public_snapshot(did)); proof=resolver.resolve(did,service_id="svc-api")
            result=W.run_storm(proof,"svc-api",10000,128,"BTG-LOCAL-10000")
            bad=copy.deepcopy(proof); bad["services"][0]["node"]["public_key_b64"]="A"*43; rejected=0
            for i in range(100):
                try: N.EntityDirectClient.request(bad,"svc-api",{"value":i},timeout=2)
                except Exception: rejected+=1
            failures=list(result.get("failures") or [])
            if rejected!=100: failures.append({"reason":f"malicious_proof_rejections={rejected}/100"})
            payload={"schema":"entity-10000-client-storm-local-v1","generated_at_ms":int(time.time()*1000),"status":"PASS" if not failures else "FAIL","qualification_complete":not failures,"scope_status":"PASS_10000_CLIENT_SINGLE_HOST" if not failures else "FAIL","logical_clients":10000,"peak_concurrency":128,"worker_hosts":1,"multi_machine_demonstrated":False,"worker_result":result,"malicious_proof_rejected":rejected,"failures":failures,"limitations":["10,000-client storm executed on one physical workstation; real multi-machine distribution requires additional worker hosts"]}
            body=dict(payload); payload["evidence_sha256"]=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
            out=ROOT/"16_Test_Qualification"/"evidence"/"ENTITY_10000_CLIENT_STORM_LOCAL_CURRENT.json"; out.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8"); out.with_suffix(".json.sha256").write_text(hashlib.sha256(out.read_bytes()).hexdigest()+"  "+out.name+"\n")
            print(json.dumps({"status":payload["status"],"scope_status":payload["scope_status"],"success":result["success"],"failure_count":result["failure_count"],"requests_per_second":result["requests_per_second"],"latency_ms":result["latency_ms"],"malicious_proof_rejected":rejected,"evidence_sha256":payload["evidence_sha256"]},indent=2)); return 0 if not failures else 2
        finally: node.stop()

if __name__=="__main__": raise SystemExit(main())
