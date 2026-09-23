from __future__ import annotations
import importlib.util,sys,pathlib,tempfile,hashlib,time,json
REPO=pathlib.Path(__file__).resolve().parents[1]; DURATION=900; REOPEN_EVERY=100
OUT=REPO/'docs/qualification/ENTITY_V3_INTERNAL_OPERATIONAL_SOAK_2026-09-23.json'
def load(name,p):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
q=load('qsoak',REPO/'tools/qualify_v3_release.py');q.TRADES_PER_IMPLEMENTATION=100000;identity,fabric_mod,ref_mod,mirror_mod=q.setup_modules()
with tempfile.TemporaryDirectory() as tmp:
 root=pathlib.Path(tmp);vault=identity.EntityIdentityVault(root);fabric=fabric_mod.UniversalTransactionFabric(root,vault);owner=vault.create('Soak Owner','business')['entity_id'];buyer=vault.create('Soak Buyer','business')['entity_id'];dco=fabric.register_digital_commodity(owner,'Soak Corpus',hashlib.sha256(b'soak-corpus').hexdigest());results={}
 for label,cls in (('reference',ref_mod.ExchangeProtocol),('mirror',mirror_mod.ExchangeProtocol)):
  eroot=root/label;eep,venue,inst=q.build_exchange(cls,eroot,vault,fabric,owner,dco,label+'-soak');start=time.monotonic();trades=0;reopens=0
  # Split total wall-clock evenly between the two implementations.
  until=start+(DURATION/2)
  while time.monotonic()<until:
   if trades and trades%REOPEN_EVERY==0:
    eep=cls(eroot,vault,fabric);reopens+=1
   eep.submit_order(venue['venue_id'],inst['instrument_id'],owner,'SELL',1,100+(trades%7),nonce=f'{label}-soak-s-{trades}')
   eep.submit_order(venue['venue_id'],inst['instrument_id'],buyer,'BUY',1,106,nonce=f'{label}-soak-b-{trades}')
   ts=eep.match_order_book(venue['venue_id'],inst['instrument_id']);
   if len(ts)!=1: raise AssertionError(f'{label}: expected one trade, got {len(ts)}')
   eep.settle_trade(ts[0]['trade_id'],payment_ref=f'{label}-soak-pay-{trades}');trades+=1
  bal=eep.balance(inst['instrument_id'],buyer); elapsed=time.monotonic()-start
  results[label]={'pass':bal==trades,'trades':trades,'reopens':reopens,'buyer_balance':bal,'elapsed_seconds':round(elapsed,3),'trades_per_second':round(trades/elapsed,3)}
 payload={'schema':'entity-v3-internal-operational-soak-v1','classification':'BTG_INTERNAL','pass':all(v['pass'] for v in results.values()),'target_total_wall_seconds':DURATION,'reopen_every_trades':REOPEN_EVERY,'implementations':results,'total_settled_trades':sum(v['trades'] for v in results.values()),'scope':'15-minute bounded continuous EEP execution with periodic implementation reopen on local hardware; combined with destructive recovery/concurrency/failure-injection release evidence. Not an external SLA or independent production certification.'};OUT.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n');print(json.dumps(payload,indent=2,sort_keys=True));raise SystemExit(0 if payload['pass'] else 2)

