from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import argparse, importlib.util, json, os, socket, sys, time, urllib.parse
ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(spec); sys.modules[name]=m; spec.loader.exec_module(m); return m
N=load('storm_client',ROOT/'22_Sovereign_Domain/node_runtime/canonical_node_runtime.py')
MACHINE_ID=f"{socket.gethostname()}:{os.getpid()}"
def run_job(cfg):
    proof=cfg['resolution_proof']; clients=int(cfg.get('clients',1000)); rpc=int(cfg.get('requests_per_client',1)); concurrency=int(cfg.get('concurrency',128)); timeout=float(cfg.get('timeout',10))
    started=time.perf_counter(); ok=0; failed=0; lat=[]; errors={}
    def one(seq):
        cid=f"{MACHINE_ID}:{seq//rpc}"; t=time.perf_counter()
        out=N.EntityDirectClient.request(proof,'svc-storm',{'client_id':cid,'value':seq},timeout=timeout)
        good=(out.get('status')==200 and out.get('result',{}).get('echo')==seq and out.get('direct_encrypted_session') is True and out.get('dns_used') is False)
        return good,(time.perf_counter()-t)*1000
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures=[pool.submit(one,i) for i in range(clients*rpc)]
        for f in as_completed(futures):
            try:
                good,ms=f.result(); lat.append(ms); ok+=1 if good else 0; failed+=0 if good else 1
            except Exception as exc:
                failed+=1; name=type(exc).__name__; errors[name]=errors.get(name,0)+1
    elapsed=time.perf_counter()-started; lat.sort()
    q=lambda p: lat[min(len(lat)-1,int(len(lat)*p))] if lat else None
    return {'machine_id':MACHINE_ID,'logical_clients':clients,'requests':clients*rpc,'successes':ok,'failures':failed,'elapsed_seconds':round(elapsed,3),'requests_per_second':round((clients*rpc)/elapsed,2),'latency_ms':{'p50':round(q(.5),3) if lat else None,'p95':round(q(.95),3) if lat else None,'p99':round(q(.99),3) if lat else None},'errors':errors,'crypto_required':True,'dns_forbidden':True}
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def reply(self,code,obj):
        raw=json.dumps(obj,sort_keys=True).encode(); self.send_response(code); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def do_GET(self):
        if self.path=='/health': return self.reply(200,{'ready':True,'machine_id':MACHINE_ID})
        return self.reply(404,{'error':'not_found'})
    def do_POST(self):
        if self.path!='/run': return self.reply(404,{'error':'not_found'})
        try:
            n=int(self.headers.get('Content-Length','0')); cfg=json.loads(self.rfile.read(n)); return self.reply(200,run_job(cfg))
        except Exception as exc: return self.reply(500,{'error':type(exc).__name__,'message':str(exc)[:1000],'machine_id':MACHINE_ID})

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--host',default='127.0.0.1'); ap.add_argument('--port',type=int,default=8765); args=ap.parse_args()
    srv=ThreadingHTTPServer((args.host,args.port),Handler); print(json.dumps({'ready':True,'machine_id':MACHINE_ID,'listen':[args.host,args.port]}),flush=True)
    try: srv.serve_forever()
    except KeyboardInterrupt: pass
    finally: srv.server_close()
if __name__=='__main__': main()
