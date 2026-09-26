from pathlib import Path
import argparse, hashlib, importlib.util, json, os, signal, sys, time
ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(spec); sys.modules[name]=m; spec.loader.exec_module(m); return m
N=load('storm_node',ROOT/'22_Sovereign_Domain/node_runtime/canonical_node_runtime.py')
ap=argparse.ArgumentParser(); ap.add_argument('--host',default='127.0.0.1'); ap.add_argument('--port',type=int,default=0); ap.add_argument('--out',default=str(ROOT/'16_Test_Qualification/evidence/ENTITY_STORM_TARGET_CURRENT.json')); args=ap.parse_args()
state=ROOT/'16_Test_Qualification/evidence/_STORM_TARGET_STATE'; state.mkdir(parents=True,exist_ok=True)
node=N.EntityNodeRuntime(state,'storm-node-a'); node.add_api_service('svc-storm',lambda req:{'echo':req.get('value'),'client_id':req.get('client_id'),'server_pid':os.getpid()})
ep=node.start(args.host,args.port)
proof={'schema':'entity-resolution-proof-v1','verified':True,'entity_root':'storm-entity-root','services':[{'service':{'service_id':'svc-storm','endpoint':{'host':ep['host'],'port':ep['port']}},'node':{'node_id':'storm-node-a','public_key_b64':node.public_key_b64,'status':'ACTIVE','effective_status':'ACTIVE'}}]}
payload={'endpoint':ep,'resolution_proof':proof}; payload['evidence_sha256']=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest(); out=Path(args.out); out.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n',encoding='utf-8'); out.with_suffix('.json.sha256').write_text(hashlib.sha256(out.read_bytes()).hexdigest()+'  '+out.name+'\n',encoding='utf-8'); print(json.dumps({'ready':True,'target':str(out),'endpoint':ep,'evidence_sha256':payload['evidence_sha256']}),flush=True)
try:
    while True: time.sleep(1)
except KeyboardInterrupt: pass
finally: node.stop()
