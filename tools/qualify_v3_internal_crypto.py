from __future__ import annotations
import importlib.util,sys,pathlib,tempfile,hashlib,time,json,random
REPO=pathlib.Path(__file__).resolve().parents[1]; CASES=500; PAY_CASES=200; SEED=305031
OUT=REPO/'docs/qualification/ENTITY_V3_INTERNAL_CRYPTO_ASSURANCE_2026-09-23.json'
def load(name,p):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
q=load('qrel',REPO/'tools/qualify_v3_release.py'); identity,fabric_mod,ref_mod,mirror_mod=q.setup_modules(); rng=random.Random(SEED)
def expect_fail(fn):
 try: fn(); return False
 except Exception: return True
def campaign(label,cls,root):
 vault=identity.EntityIdentityVault(root); fabric=fabric_mod.UniversalTransactionFabric(root,vault);owner=vault.create(label+' Owner','business')['entity_id'];buyer=vault.create(label+' Buyer','business')['entity_id'];attacker=vault.create(label+' Attacker','business')['entity_id'];dco=fabric.register_digital_commodity(owner,label+' Corpus',hashlib.sha256(label.encode()).hexdigest());eep,venue,inst=q.build_exchange(cls,root/'eep',vault,fabric,owner,dco,label)
 counts={k:0 for k in ('tamper_rejected','wrong_signer_rejected','noncanonical_rejected','replay_rejected','duplicate_nonce_rejected','payment_tamper_rejected')};created=int(time.time()*1000)
 for i in range(CASES):
  base={'schema':'entity-eep-order-v1','order_id':f'order3-fuzz-{label}-{i}','venue_id':venue['venue_id'],'instrument_id':inst['instrument_id'],'participant':buyer,'side':'BUY','quantity':1,'limit_price':0,'tif':'GTC','nonce':f'{label}-replay-{i}','created_at_ms':created+i}
  sig=vault.sign(buyer,base); bad=dict(base);bad['quantity']=2
  counts['tamper_rejected']+=expect_fail(lambda b=bad,s=sig:eep.submit_signed_order(b,s))
  ws=vault.sign(attacker,base);counts['wrong_signer_rejected']+=expect_fail(lambda b=base,s=ws:eep.submit_signed_order(b,s))
  nc=dict(base);nc['order_id']=f'order3-noncanon-{label}-{i}';nc['nonce']=f'{label}-nc-{i}';nc['side']='buy';ncs=vault.sign(buyer,nc);counts['noncanonical_rejected']+=expect_fail(lambda b=nc,s=ncs:eep.submit_signed_order(b,s))
  eep.submit_signed_order(base,sig);counts['replay_rejected']+=expect_fail(lambda b=base,s=sig:eep.submit_signed_order(b,s))
  one=dict(base);one['order_id']=f'order3-nonce-a-{label}-{i}';one['nonce']=f'{label}-dup-{i}';one['created_at_ms']=created+100000+i;osig=vault.sign(buyer,one);eep.submit_signed_order(one,osig);two=dict(one);two['order_id']=f'order3-nonce-b-{label}-{i}';tsig=vault.sign(buyer,two);counts['duplicate_nonce_rejected']+=expect_fail(lambda b=two,s=tsig:eep.submit_signed_order(b,s))
 # create a real trade for payment-attestation tamper cases
 eep.submit_order(venue['venue_id'],inst['instrument_id'],owner,'SELL',1,100,nonce=f'{label}-pay-sell');eep.submit_order(venue['venue_id'],inst['instrument_id'],buyer,'BUY',1,100,nonce=f'{label}-pay-buy');trade=eep.match_order_book(venue['venue_id'],inst['instrument_id'])[0]
 for i in range(PAY_CASES):
  body={'schema':'entity-eep-payment-attestation-v1','attestation_id':f'payatt3-fuzz-{label}-{i}','trade_id':trade['trade_id'],'verifier_entity_id':buyer,'settlement_ref':f'{label}-settle-{i}','evidence_sha256':hashlib.sha256(f'evidence-{i}'.encode()).hexdigest(),'nonce':f'{label}-payatt-{i}','created_at_ms':created+200000+i,'verification_is_attestation_not_absolute_truth':True}
  sig=vault.sign(buyer,body);bad=dict(body);bad['evidence_sha256']=hashlib.sha256(f'tampered-{i}'.encode()).hexdigest();counts['payment_tamper_rejected']+=expect_fail(lambda b=bad,s=sig:eep.submit_signed_payment_attestation(b,s))
 expected={'tamper_rejected':CASES,'wrong_signer_rejected':CASES,'noncanonical_rejected':CASES,'replay_rejected':CASES,'duplicate_nonce_rejected':CASES,'payment_tamper_rejected':PAY_CASES};return {'pass':counts==expected,'counts':counts,'expected':expected}
with tempfile.TemporaryDirectory() as t:
 root=pathlib.Path(t);results={'reference':campaign('reference',ref_mod.ExchangeProtocol,root/'reference'),'mirror':campaign('mirror',mirror_mod.ExchangeProtocol,root/'mirror')}
 # existing destructive recovery/tamper suite remains part of assurance evidence
 payload={'schema':'entity-v3-internal-crypto-assurance-v1','classification':'BTG_INTERNAL','seed':SEED,'implementations':results,'total_adversarial_cases':sum(sum(v['counts'].values()) for v in results.values()),'pass':all(v['pass'] for v in results.values()),'covered':['post-signature field mutation','wrong-signer substitution','noncanonical signed wire','exact replay','nonce replay with new id','payment-attestation mutation'],'additional_release_evidence':'market recovery suite includes controller-signature tamper after recomputing bundle/table hashes','scope':'Internal cryptographic misuse/red-team assurance; not an independent external cryptographic audit.'};OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n');print(json.dumps(payload,indent=2,sort_keys=True));raise SystemExit(0 if payload['pass'] else 2)
