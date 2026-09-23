from __future__ import annotations
import importlib.util,sys,pathlib,hashlib,json,secrets,base64,copy
REPO=pathlib.Path(__file__).resolve().parents[1];N=300
OUT=REPO/'docs/qualification/ENTITY_V3_INTERNAL_PRIVACY_CRYPTO_ASSURANCE_2026-09-23.json'
def load(name,p):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
ref=load('priv_ref',REPO/'src/31_Profiles/governance_privacy.py'); hard=load('priv_hard',REPO/'src/32_V3_Hardening/hardening_profiles.py')
def fails(fn):
 try:fn();return False
 except Exception:return True
c={'ref_valid':0,'hard_valid':0,'ref_reveal_tamper_rejected':0,'hard_reveal_tamper_rejected':0,'ref_commitment_tamper_rejected':0,'hard_commitment_tamper_rejected':0,'aes_roundtrip':0,'aes_wrong_key_rejected':0,'aes_aad_tamper_rejected':0,'aes_ciphertext_tamper_rejected':0}
for i in range(N):
 claims={'subject':f'entity-{i}','age_band':20+(i%5),'region':'CA','secret_note':hashlib.sha256(str(i).encode()).hexdigest()}
 for prefix,cls in [('ref',ref.SelectiveDisclosure),('hard',hard.SelectiveDisclosure)]:
  pkg=cls.commit(claims);proof=cls.disclose(pkg,['subject','region']);c[prefix+'_valid']+=int(cls.verify(proof)['valid'])
  bad=copy.deepcopy(proof);bad['revealed']['subject']['value']='tampered';c[prefix+'_reveal_tamper_rejected']+=int(not cls.verify(bad)['valid'])
  bad2=copy.deepcopy(proof);bad2['commitments']['secret_note']='0'*64;c[prefix+'_commitment_tamper_rejected']+=int(not cls.verify(bad2)['valid'])
 key=hashlib.sha256(f'key-{i}'.encode()).digest();aad={'entity':f'ent3-{i}','purpose':'MIN_DISCLOSURE'};env=hard.PrivacyEnvelope.encrypt(key,claims,aad);c['aes_roundtrip']+=int(hard.PrivacyEnvelope.decrypt(key,env,aad)==claims)
 c['aes_wrong_key_rejected']+=int(fails(lambda e=env,a=aad:hard.PrivacyEnvelope.decrypt(hashlib.sha256(f'wrong-{i}'.encode()).digest(),e,a)))
 c['aes_aad_tamper_rejected']+=int(fails(lambda e=env,k=key:hard.PrivacyEnvelope.decrypt(k,e,{'entity':'other','purpose':'MIN_DISCLOSURE'})))
 tam=copy.deepcopy(env);raw=bytearray(base64.urlsafe_b64decode(tam['ciphertext']));raw[len(raw)//2]^=1;tam['ciphertext']=base64.urlsafe_b64encode(bytes(raw)).decode();c['aes_ciphertext_tamper_rejected']+=int(fails(lambda e=tam,k=key,a=aad:hard.PrivacyEnvelope.decrypt(k,e,a)))
expected={k:N for k in c};payload={'schema':'entity-v3-internal-privacy-crypto-assurance-v1','classification':'BTG_INTERNAL','iterations':N,'counts':c,'expected':expected,'total_assertions':sum(c.values()),'pass':c==expected,'scope':'Internal privacy-primitive misuse/tamper assurance for selective disclosure convergence and AES-GCM envelopes; not independent cryptographic review.'};OUT.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n');print(json.dumps(payload,indent=2,sort_keys=True));raise SystemExit(0 if payload['pass'] else 2)
