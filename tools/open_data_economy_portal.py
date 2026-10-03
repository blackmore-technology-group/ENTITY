from __future__ import annotations
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import argparse, html, importlib.util, json, sys, threading, webbrowser

ROOT=Path(__file__).resolve().parents[1]
STATE_DEFAULT=Path.home()/".entity"/"state"

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec); sys.modules[name]=m; spec.loader.exec_module(m); return m

open_mod=load("entity_open_economy_portal_mod",ROOT/"src"/"45_Open_Data_Economy"/"open_data_economy.py")
wallet_mod=load("entity_wallet_portal_mod",ROOT/"src"/"42_ENTITY_Wallet"/"canonical_wallet.py")

CSS="""
:root{font-family:Inter,Segoe UI,Arial,sans-serif;color:#1d232b;background:#f4f6f8}
body{margin:0}.top{background:#111820;color:white;padding:18px 24px}.top b{font-size:20px}
.wrap{max-width:1180px;margin:22px auto;padding:0 18px}.hero,.card{background:white;border:1px solid #dce2e7;border-radius:12px;padding:20px;margin-bottom:16px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px}
h1,h2,h3{margin-top:0}label{display:block;font-size:13px;font-weight:600;margin:9px 0 4px}
input,select,textarea{width:100%;box-sizing:border-box;padding:9px;border:1px solid #c6ced6;border-radius:7px}
textarea{min-height:76px}.btn{background:#111820;color:white;border:0;padding:10px 14px;border-radius:7px;cursor:pointer;margin-top:10px}
.small{color:#58636e;font-size:13px}.ok{background:#eaf8ee;border:1px solid #a8d8b3;padding:10px;border-radius:8px}
.err{background:#fff0f0;border:1px solid #e5abab;padding:10px;border-radius:8px}
pre{white-space:pre-wrap;word-break:break-word;background:#f6f8fa;padding:12px;border-radius:8px;max-height:500px;overflow:auto}
.tag{display:inline-block;padding:4px 8px;background:#eef2f6;border-radius:999px;margin:2px;font-size:12px}
"""

HTML="""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>ENTITY Open Data Economy</title><style>__CSS__</style></head>
<body><div class='top'><b>ENTITY Open Data Economy</b><div class='small' style='color:#cbd3db'>Rights—not copies. No token. No gas. No protocol tax.</div></div>
<div class='wrap'>
<div class='hero'><h1>Your Data Economy</h1><p>Bring data or another legitimate information asset, prove your authority, choose what you keep private, choose which rights you retain and which rights you offer. ENTITY handles the underlying DCO/passport/economic machinery.</p>
<span class='tag'>issuer neutral</span><span class='tag'>provider neutral</span><span class='tag'>fiat supported</span><span class='tag'>protocol tax 0</span></div>
<div class='grid'>
<div class='card'><h2>Create My DCO</h2><p class='small'>Creates an issuance draft only. Registration does not create ownership.</p>
<form id='dco'>
<label>Your ENTITY ID</label><input name='issuer_entity_id' required>
<label>Name</label><input name='name' required>
<label>Asset class</label><select name='asset_class'><option>DATASET</option><option>ALGORITHM</option><option>MODEL</option><option>BENCHMARK</option><option>CREATIVE_WORK</option><option>OTHER</option></select>
<label>Content SHA-256</label><input name='content_sha256' required>
<label>Provenance root SHA-256</label><input name='provenance_root' required>
<label>Authority evidence SHA-256</label><input name='authority_evidence_sha256' required>
<label>Privacy</label><select name='privacy_profile'><option>SELECTIVE_DISCLOSURE</option><option>PUBLIC_PROVENANCE</option><option>CONFIDENTIAL_PROVENANCE</option><option>RESTRICTED_DISCLOSURE</option></select>
<label>Rights you keep (comma separated)</label><input name='retained' value='CONTROL'>
<label>Rights to offer (ACTION:QUANTITY, ...)</label><input name='offered' placeholder='TRAIN:100, QUERY:1000'>
<button class='btn'>Create draft</button></form><div id='dcoout'></div></div>

<div class='card'><h2>My Data Portfolio</h2><p class='small'>Normal participant portfolio—not a treasury-only view.</p>
<form id='portfolio'><label>Your ENTITY ID</label><input name='entity_id' required><label>Portfolio name</label><input name='name' value='My Data Economy'><button class='btn'>Open portfolio</button></form><div id='portfolioout'></div></div>

<div class='card'><h2>Find Data Rights</h2><p class='small'>Search by the rights you need. Issuer is not a ranking factor.</p>
<form id='search'><label>Required actions</label><input name='actions' placeholder='TRAIN, DERIVE'>
<label>Region</label><input name='region' placeholder='CA-BC'>
<label><input style='width:auto' type='checkbox' name='commercial_use_required'> Commercial use required</label>
<label><input style='width:auto' type='checkbox' name='derivative_models_required'> Derivative models required</label>
<label>Raw data transfer</label><select name='raw'><option value='either'>Either</option><option value='no'>Not required</option><option value='yes'>Required</option></select>
<button class='btn'>Search rights</button></form><div id='searchout'></div></div>

<div class='card'><h2>Data Pools</h2><p class='small'>Aggregate small contributions while preserving provenance and deterministic allocation.</p>
<form id='pool'><label>Controller ENTITY ID</label><input name='controller_entity_id' required>
<label>Pool name</label><input name='name' required><label>Purpose</label><textarea name='purpose' required></textarea>
<label>Terms SHA-256</label><input name='terms_sha256' required><button class='btn'>Create pool</button></form><div id='poolout'></div></div>
</div>
<div class='card'><h2>Constitution</h2><pre id='constitution'></pre></div>
</div>
<script>
async function api(path,data){let r=await fetch(path,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(data)});let j=await r.json();if(!r.ok)throw new Error(j.error||'request failed');return j}
function obj(form){return Object.fromEntries(new FormData(form).entries())}
function show(id,v,err=false){document.getElementById(id).innerHTML="<div class='"+(err?"err":"ok")+"'><pre>"+esc(JSON.stringify(v,null,2))+"</pre></div>"}
function esc(s){return s.replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]))}
document.getElementById('dco').onsubmit=async e=>{e.preventDefault();let d=obj(e.target);try{show('dcoout',await api('/api/create-dco',d))}catch(x){show('dcoout',{error:x.message},true)}}
document.getElementById('portfolio').onsubmit=async e=>{e.preventDefault();try{show('portfolioout',await api('/api/portfolio',obj(e.target)))}catch(x){show('portfolioout',{error:x.message},true)}}
document.getElementById('search').onsubmit=async e=>{e.preventDefault();let d=obj(e.target);d.commercial_use_required=e.target.commercial_use_required.checked;d.derivative_models_required=e.target.derivative_models_required.checked;try{show('searchout',await api('/api/search',d))}catch(x){show('searchout',{error:x.message},true)}}
document.getElementById('pool').onsubmit=async e=>{e.preventDefault();try{show('poolout',await api('/api/create-pool',obj(e.target)))}catch(x){show('poolout',{error:x.message},true)}}
fetch('/api/constitution').then(r=>r.json()).then(j=>document.getElementById('constitution').textContent=JSON.stringify(j,null,2))
</script></body></html>""".replace("__CSS__",CSS)

class Portal:
    def __init__(self,state):
        self.state=Path(state)
        self.creator=open_mod.CreateMyDCOService(self.state)
        self.wallet=wallet_mod.EntityEconomicWallet(self.state)
        self.market=open_mod.RightsMarketDiscovery(self.state/"entity_v3_exchange.sqlite")
        self.pools=open_mod.DataPoolManager(self.state)

    def create_dco(self,d):
        retained=[{"action":x.strip()} for x in str(d.get("retained","")).split(",") if x.strip()]
        offered=[]
        for item in str(d.get("offered","")).split(","):
            item=item.strip()
            if not item: continue
            if ":" not in item: raise ValueError("offered rights use ACTION:QUANTITY")
            action,qty=item.split(":",1)
            offered.append({"action":action.strip(),"quantity":int(qty.strip()),"raw_transfer_allowed":False})
        return self.creator.create_draft(
            issuer_entity_id=d.get("issuer_entity_id"),name=d.get("name"),asset_class=d.get("asset_class"),
            content_sha256=d.get("content_sha256"),provenance_root=d.get("provenance_root"),
            authority_evidence_sha256=d.get("authority_evidence_sha256"),privacy_profile=d.get("privacy_profile"),
            retained_rights=retained,offered_rights=offered)

    def portfolio(self,d):
        wid=self.wallet.ensure_wallet(d.get("entity_id"),d.get("name") or "My Data Economy",wallet_type="PARTICIPANT")
        return open_mod.ParticipantPortfolioView.simplify(self.wallet.snapshot(wid["wallet_id"]))

    def search(self,d):
        raw=d.get("raw")
        rawcrit=None if raw=="either" else raw=="yes"
        return self.market.search({
            "actions":[x.strip() for x in str(d.get("actions","")).split(",") if x.strip()],
            "region":d.get("region") or None,
            "commercial_use_required":bool(d.get("commercial_use_required")),
            "derivative_models_required":bool(d.get("derivative_models_required")),
            "raw_transfer_required":rawcrit,
        })

    def create_pool(self,d):
        return self.pools.create_pool(d.get("controller_entity_id"),d.get("name"),d.get("purpose"),d.get("terms_sha256"))

def handler(portal):
    class H(BaseHTTPRequestHandler):
        def log_message(self,*args): return
        def send(self,status,body,ctype="application/json; charset=utf-8"):
            data=body if isinstance(body,bytes) else body.encode()
            self.send_response(status); self.send_header("content-type",ctype); self.send_header("content-length",str(len(data))); self.end_headers(); self.wfile.write(data)
        def do_GET(self):
            if self.path=="/": return self.send(200,HTML,"text/html; charset=utf-8")
            if self.path=="/api/constitution": return self.send(200,json.dumps(open_mod.OpenEconomyConstitution.status()))
            return self.send(404,json.dumps({"error":"not found"}))
        def do_POST(self):
            try:
                n=int(self.headers.get("content-length","0")); data=json.loads(self.rfile.read(n) or b"{}")
                if self.path=="/api/create-dco": out=portal.create_dco(data)
                elif self.path=="/api/portfolio": out=portal.portfolio(data)
                elif self.path=="/api/search": out=portal.search(data)
                elif self.path=="/api/create-pool": out=portal.create_pool(data)
                else: return self.send(404,json.dumps({"error":"not found"}))
                return self.send(200,json.dumps(out,default=str))
            except Exception as exc:
                return self.send(400,json.dumps({"error":str(exc)}))
    return H

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--state",default=str(STATE_DEFAULT)); ap.add_argument("--port",type=int,default=8765); ap.add_argument("--no-browser",action="store_true")
    a=ap.parse_args(); portal=Portal(a.state); server=ThreadingHTTPServer(("127.0.0.1",a.port),handler(portal))
    url=f"http://127.0.0.1:{a.port}/"
    print(f"ENTITY Open Data Economy: {url}",flush=True)
    if not a.no_browser: threading.Timer(.6,lambda:webbrowser.open(url)).start()
    server.serve_forever()

if __name__=="__main__": main()
