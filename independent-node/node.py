#!/usr/bin/env python3
"""ENTITY Independent Node Program v1 — minimal test transport and lineage harness.

Standard-library only. This is not a production network service or a replacement
for ENTITY protocol qualification. It records reproducible transport/hash lineage.
"""
from __future__ import annotations
import argparse, hashlib, json, os, sys, uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen

SCHEMA="entity-independent-node/envelope/v1"
STATE=Path(os.environ.get("ENTITY_INP_HOME", ".entity-independent-node"))
MAX_BODY=2*1024*1024

def now(): return datetime.now(timezone.utc).isoformat()
def canon(v): return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
def sha(v): return hashlib.sha256(v if isinstance(v,bytes) else canon(v)).hexdigest()
def paths():
    STATE.mkdir(parents=True,exist_ok=True); (STATE/"receipts").mkdir(exist_ok=True)
    return STATE/"node.json", STATE/"receipts"
def load_node():
    p,_=paths()
    if not p.exists(): raise SystemExit("Node not initialized. Run: node.py init")
    return json.loads(p.read_text(encoding="utf-8"))
def init():
    p,_=paths()
    if p.exists():
        n=json.loads(p.read_text(encoding="utf-8")); print(n["node_id"]); return
    n={"schema":"entity-independent-node/node/v1","node_id":"ent-test-"+uuid.uuid4().hex[:16],"created_at":now()}
    p.write_text(json.dumps(n,indent=2)+"\n",encoding="utf-8"); print(n["node_id"])
def make_envelope(obj,node_id):
    h=sha(obj)
    return {"schema":SCHEMA,"origin_sha256":h,"object_sha256":h,"object":obj,"lineage":[],"sender_node_id":node_id,"created_at":now()}
def verify_env(e):
    if e.get("schema")!=SCHEMA: return False,"wrong schema"
    actual=sha(e.get("object"))
    if actual!=e.get("object_sha256"): return False,"object hash mismatch"
    if not e.get("origin_sha256"): return False,"missing origin hash"
    lineage=e.get("lineage")
    if not isinstance(lineage,list): return False,"lineage is not a list"
    return True,"verified"
def receipt(event,env,receiver,result):
    r={"schema":"entity-independent-node/receipt/v1","receipt_id":"inp-"+uuid.uuid4().hex,
       "event":event,"timestamp":now(),"receiver_node_id":receiver,
       "sender_node_id":env.get("sender_node_id"),"object_sha256":env.get("object_sha256"),
       "origin_sha256":env.get("origin_sha256"),"lineage_depth":len(env.get("lineage",[])),
       "result":result}
    r["receipt_sha256"]=sha(r)
    _,d=paths(); (d/(r["receipt_id"]+".json")).write_text(json.dumps(r,indent=2)+"\n",encoding="utf-8")
    return r
def receive(env,node_id):
    ok,msg=verify_env(env)
    if not ok: return 400,receipt("REJECT",env,node_id,"FAIL: "+msg),None
    hop={"from_node_id":env.get("sender_node_id"),"to_node_id":node_id,"received_at":now(),
         "object_sha256":env["object_sha256"],"origin_sha256":env["origin_sha256"]}
    out=dict(env); out["lineage"]=list(env["lineage"])+[hop]; out["sender_node_id"]=node_id
    r=receipt("RECEIVE",out,node_id,"PASS")
    out["last_receipt_sha256"]=r["receipt_sha256"]
    return 200,r,out

class Handler(BaseHTTPRequestHandler):
    server_version="ENTITY-INP/1"
    def do_POST(self):
        if self.path!="/entity-test/v1/receive": self.send_error(404); return
        try:
            n=int(self.headers.get("Content-Length","0"))
            if n<=0 or n>MAX_BODY: self.send_error(413); return
            env=json.loads(self.rfile.read(n).decode("utf-8"))
            status,r,out=receive(env,self.server.node_id)
            body=canon({"receipt":r,"envelope":out})
            self.send_response(status); self.send_header("Content-Type","application/json")
            self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)
        except Exception as ex:
            body=canon({"error":type(ex).__name__})
            self.send_response(400); self.send_header("Content-Type","application/json")
            self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self,fmt,*args): sys.stderr.write("%s - %s\n"%(self.address_string(),fmt%args))

def serve(host,port):
    node=load_node(); srv=ThreadingHTTPServer((host,port),Handler); srv.node_id=node["node_id"]
    print(f"ENTITY INP node {srv.node_id} listening on http://{host}:{port}")
    try: srv.serve_forever()
    except KeyboardInterrupt: pass
def read_obj(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def cmd_make(file,out):
    e=make_envelope(read_obj(file),load_node()["node_id"])
    Path(out).write_text(json.dumps(e,indent=2)+"\n",encoding="utf-8"); print(out)
def cmd_verify(path):
    ok,msg=verify_env(read_obj(path)); print(("PASS: " if ok else "FAIL: ")+msg); raise SystemExit(0 if ok else 2)
def cmd_send(target,file):
    node=load_node(); raw=read_obj(file)
    env=raw if isinstance(raw,dict) and raw.get("schema")==SCHEMA else make_envelope(raw,node["node_id"])
    ok,msg=verify_env(env)
    if not ok: raise SystemExit("Refusing invalid envelope: "+msg)
    env["sender_node_id"]=node["node_id"]
    req=Request(target.rstrip("/")+"/entity-test/v1/receive",data=canon(env),headers={"Content-Type":"application/json"},method="POST")
    with urlopen(req,timeout=10) as res: reply=json.loads(res.read().decode())
    r=reply["receipt"]; _,d=paths(); (d/(r["receipt_id"]+"-remote.json")).write_text(json.dumps(r,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(reply,indent=2))
def status():
    n=load_node(); _,d=paths(); print(json.dumps({**n,"local_receipts":len(list(d.glob("*.json")))},indent=2))
def main():
    p=argparse.ArgumentParser(description="ENTITY Independent Node Program v1")
    s=p.add_subparsers(dest="cmd",required=True)
    s.add_parser("init"); s.add_parser("status")
    q=s.add_parser("serve"); q.add_argument("--host",default="127.0.0.1"); q.add_argument("--port",type=int,default=8343)
    q=s.add_parser("send"); q.add_argument("--to",required=True); q.add_argument("--file",required=True)
    q=s.add_parser("verify"); q.add_argument("--envelope",required=True)
    q=s.add_parser("make-envelope"); q.add_argument("--file",required=True); q.add_argument("--out",required=True)
    a=p.parse_args()
    if a.cmd=="init": init()
    elif a.cmd=="status": status()
    elif a.cmd=="serve": serve(a.host,a.port)
    elif a.cmd=="send": cmd_send(a.to,a.file)
    elif a.cmd=="verify": cmd_verify(a.envelope)
    elif a.cmd=="make-envelope": cmd_make(a.file,a.out)
if __name__=="__main__": main()
