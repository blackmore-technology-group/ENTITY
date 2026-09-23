import base64, copy, hashlib, importlib.util, pathlib, random, sys, tempfile, unittest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT=pathlib.Path(__file__).resolve().parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec)
    sys.modules[name]=mod; assert spec.loader is not None; spec.loader.exec_module(mod); return mod
identity=load('crypto_identity',ROOT/'src/01_Core_Runtime/identity/canonical_identity.py')

def forge_record(entity_id,key_id,suite,private_raw,payload,signed_at):
    rec={'signature_schema':'entity-signature-record-v2','entity_id':entity_id,'key_id':key_id,
         'suite':suite,'signed_at_ms':int(signed_at),
         'payload_sha256':hashlib.sha256(identity.canonical_json(payload)).hexdigest()}
    key=Ed25519PrivateKey.from_private_bytes(private_raw)
    rec['signature']=base64.b64encode(key.sign(identity.canonical_json(rec))).decode()
    return rec

class CryptoLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.vault=identity.EntityIdentityVault(self.tmp.name)
        self.a=self.vault.create('A','business')['entity_id']; self.b=self.vault.create('B','business')['entity_id']
    def tearDown(self): self.tmp.cleanup()
    def test_retired_key_cutoff_and_cleanup(self):
        payload={'kind':'historical','n':1}; before=self.vault.sign(self.a,payload)
        old_manifest=self.vault.load_manifest(self.a); old=old_manifest['active_signing_key_id']
        raw=self.vault._read_private_key_bytes(self.a,old); rotated=self.vault.rotate_signing_key(self.a)
        method=next(x for x in rotated['verification_methods'] if x['key_id']==old)
        self.assertTrue(self.vault.verify_signature(rotated,payload,before))
        forged_payload={'kind':'post-retirement','n':2}
        forged=forge_record(self.a,old,method['suite'],raw,forged_payload,int(method['retired_at_ms'])+1)
        self.assertFalse(self.vault.verify_signature(rotated,forged_payload,forged))
        kd=pathlib.Path(self.tmp.name)/'identity'/'keys'/self.a
        self.assertFalse((kd/f'{old}.key').exists()); self.assertFalse((kd/f'{old}.key.tpm').exists())

    def test_recovery_revocation_cutoff_and_cleanup(self):
        payload={'kind':'before-recovery'}; before=self.vault.sign(self.a,payload)
        old_manifest=self.vault.load_manifest(self.a); old=old_manifest['active_signing_key_id']
        raw=self.vault._read_private_key_bytes(self.a,old); recovered=self.vault.recover_signing_key(self.a)
        method=next(x for x in recovered['verification_methods'] if x['key_id']==old)
        self.assertTrue(self.vault.verify_signature(recovered,payload,before))
        forged_payload={'kind':'post-revocation'}
        forged=forge_record(self.a,old,method['suite'],raw,forged_payload,int(method['revoked_at_ms'])+1)
        self.assertFalse(self.vault.verify_signature(recovered,forged_payload,forged))
        kd=pathlib.Path(self.tmp.name)/'identity'/'keys'/self.a
        self.assertFalse((kd/f'{old}.key').exists()); self.assertFalse((kd/f'{old}.key.tpm').exists())
    def test_signature_and_payload_mutations_fail_closed(self):
        payload={'alpha':1,'beta':['x',2],'nested':{'ok':True}}
        sig=self.vault.sign(self.a,payload); manifest=self.vault.load_manifest(self.a)
        self.assertTrue(self.vault.verify_signature(manifest,payload,sig))
        changed=copy.deepcopy(payload); changed['alpha']=2
        self.assertFalse(self.vault.verify_signature(manifest,changed,sig))
        wrong=self.vault.load_manifest(self.b)
        self.assertFalse(self.vault.verify_signature(wrong,payload,sig))
        bad=copy.deepcopy(sig); raw=bytearray(identity._unb64(bad['signature'])); raw[0]^=1; bad['signature']=identity._b64(bytes(raw))
        self.assertFalse(self.vault.verify_signature(manifest,payload,bad))
        bad=copy.deepcopy(sig); bad['payload_sha256']='0'*64
        self.assertFalse(self.vault.verify_signature(manifest,payload,bad))
        bad=copy.deepcopy(sig); bad['signature_schema']='entity-signature-record-v999'
        self.assertFalse(self.vault.verify_signature(manifest,payload,bad))

    def test_canonical_order_independence_and_random_mutations(self):
        rng=random.Random(3000); manifest=self.vault.load_manifest(self.a)
        a={'z':3,'a':1,'m':{'y':2,'x':1}}; b={'m':{'x':1,'y':2},'a':1,'z':3}
        self.assertEqual(identity.canonical_json(a),identity.canonical_json(b))
        for i in range(250):
            payload={'i':i,'n':rng.randrange(1,10**9),'flag':bool(rng.randrange(2)),'text':f'case-{rng.randrange(10**9)}'}
            sig=self.vault.sign(self.a,payload); self.assertTrue(self.vault.verify_signature(manifest,payload,sig))
            mutated=dict(payload); mutated['n']+=1
            self.assertFalse(self.vault.verify_signature(manifest,mutated,sig))

if __name__=='__main__': unittest.main()

