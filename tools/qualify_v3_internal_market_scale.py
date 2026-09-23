from __future__ import annotations
import importlib.util,sys,pathlib,tempfile,hashlib,time,json
REPO=pathlib.Path(__file__).resolve().parents[1]; N=2000
OUT=REPO/'docs/qualification/ENTITY_V3_INTERNAL_MARKET_SCALE_QUALIFICATION_2026-09-23.json'
def load(name,p):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
q=load('qscale_release',REPO/'tools/qualify_v3_release.py');q.TRADES_PER_IMPLEMENTATION=N;identity,fabric_mod,ref_mod,mirror_mod=q.setup_modules()
with tempfile.TemporaryDirectory() as tmp:
 root=pathlib.Path(tmp);vault=identity.EntityIdentityVault(root);fabric=fabric_mod.UniversalTransactionFabric(root,vault);owner=vault.create('Scale Owner','business')['entity_id'];buyer=vault.create('Scale Buyer','business')['entity_id'];dco=fabric.register_digital_commodity(owner,'Scale Corpus',hashlib.sha256(b'scale-corpus').hexdigest());results={}
 for label,cls in (('reference',ref_mod.ExchangeProtocol),('mirror',mirror_mod.ExchangeProtocol)):
  eep,venue,inst=q.build_exchange(cls,root/label,vault,fabric,owner,dco,label+'-scale');results[label]=q.exercise(eep,venue,inst,owner,buyer,label+'-scale')
 payload={'schema':'entity-v3-internal-market-scale-qualification-v1','classification':'BTG_INTERNAL','pass':all(v['trades']==N for v in results.values()),'trades_per_implementation':N,'total_fully_settled_trades':sum(v['trades'] for v in results.values()),'implementations':results,'scope':'Sustained signed-order/matching/clearing/settlement/entitlement execution on local hardware; BTG internal operational qualification, not third-party capacity certification or SLA.'};OUT.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n');print(json.dumps(payload,indent=2,sort_keys=True));raise SystemExit(0 if payload['pass'] else 2)
