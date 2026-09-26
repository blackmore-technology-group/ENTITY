from __future__ import annotations
from pathlib import Path
from contextlib import contextmanager
import base64,json,secrets,sqlite3,time
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey,Ed25519PublicKey
from cryptography.hazmat.primitives import serialization
try:
    from canonical_hardware_keys import WindowsTpmProtector,PortableRecoveryEscrow
except ModuleNotFoundError:
    import importlib.util
    _hp=Path(__file__).with_name('canonical_hardware_keys.py')
    _spec=importlib.util.spec_from_file_location('entity_canonical_hardware_keys',_hp)
    if _spec is None or _spec.loader is None: raise ImportError(str(_hp))
    _mod=importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_mod)
    WindowsTpmProtector=_mod.WindowsTpmProtector; PortableRecoveryEscrow=_mod.PortableRecoveryEscrow

PURPOSES={'IDENTITY_ASSERTION','AUTHENTICATION','CONTRACT','DEVICE','ENCRYPTION','PAYMENT','DELEGATION','SESSION'}
def _now(): return int(time.time()*1000)
def _id(p): return f'{p}-'+secrets.token_hex(20)
def _b64(v:bytes): return base64.urlsafe_b64encode(v).decode().rstrip('=')
def _unb64(v:str): return base64.urlsafe_b64decode(v+'='*(-len(v)%4))

class PurposeKeyManager:
    """Purpose-separated Ed25519 operational keys wrapped by a non-exportable TPM key."""
    def __init__(self,state_dir:str|Path,protector:WindowsTpmProtector):
        self.root=Path(state_dir)/'purpose_keys'; self.root.mkdir(parents=True,exist_ok=True); self.path=self.root/'keys.sqlite'; self.protector=protector; self._init_db()
    @contextmanager
    def _connect(self):
        db=sqlite3.connect(self.path,timeout=30); db.row_factory=sqlite3.Row
        try: yield db; db.commit()
        except Exception: db.rollback(); raise
        finally: db.close()
    def _init_db(self):
        with self._connect() as db: db.execute('CREATE TABLE IF NOT EXISTS keys(key_id TEXT PRIMARY KEY,controller_entity_id TEXT NOT NULL,purpose TEXT NOT NULL,public_key_b64 TEXT NOT NULL,wrapped_private_b64 TEXT NOT NULL,status TEXT NOT NULL,created_at_ms INTEGER NOT NULL,revoked_at_ms INTEGER)')
    def create(self,controller_entity_id:str,purpose:str)->dict:
        p=str(purpose).upper()
        if p not in PURPOSES: raise ValueError('unsupported key purpose')
        key=Ed25519PrivateKey.generate(); raw=key.private_bytes(serialization.Encoding.Raw,serialization.PrivateFormat.Raw,serialization.NoEncryption()); public=key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
        kid=_id('pkey1'); wrapped=self.protector.wrap(raw); now=_now()
        with self._connect() as db: db.execute('INSERT INTO keys VALUES(?,?,?,?,?,?,?,?)',(kid,controller_entity_id,p,_b64(public),_b64(wrapped),'ACTIVE',now,None))
        return {'key_id':kid,'controller_entity_id':controller_entity_id,'purpose':p,'public_key_b64':_b64(public),'status':'ACTIVE','hardware_wrapped':True,'private_key_exported':False}
    def sign(self,key_id:str,purpose:str,payload:bytes)->dict:
        with self._connect() as db: row=db.execute('SELECT * FROM keys WHERE key_id=?',(key_id,)).fetchone()
        if not row or row['status']!='ACTIVE': raise PermissionError('purpose key unavailable')
        if row['purpose']!=str(purpose).upper(): raise PermissionError('purpose-key mismatch')
        raw=self.protector.unwrap(_unb64(row['wrapped_private_b64'])); sig=Ed25519PrivateKey.from_private_bytes(raw).sign(bytes(payload))
        return {'key_id':key_id,'purpose':row['purpose'],'signature_b64':_b64(sig),'hardware_wrapped':True}
    def verify(self,key_id:str,purpose:str,payload:bytes,signature_b64:str)->bool:
        with self._connect() as db: row=db.execute('SELECT * FROM keys WHERE key_id=?',(key_id,)).fetchone()
        if not row or row['purpose']!=str(purpose).upper(): return False
        try: Ed25519PublicKey.from_public_bytes(_unb64(row['public_key_b64'])).verify(_unb64(signature_b64),bytes(payload)); return True
        except Exception: return False
    def revoke(self,controller_entity_id:str,key_id:str)->dict:
        with self._connect() as db: row=db.execute('SELECT * FROM keys WHERE key_id=?',(key_id,)).fetchone()
        if not row: raise KeyError('purpose key not found')
        if row['controller_entity_id']!=controller_entity_id: raise PermissionError('key controller mismatch')
        now=_now()
        with self._connect() as db: db.execute("UPDATE keys SET status='REVOKED',revoked_at_ms=? WHERE key_id=?",(now,key_id))
        return {'key_id':key_id,'status':'REVOKED','revoked_at_ms':now}
    def status(self):
        with self._connect() as db: active=int(db.execute("SELECT COUNT(*) FROM keys WHERE status='ACTIVE'").fetchone()[0])
        return {'ready':True,'active_keys':active,'purpose_separation':True,'hardware_wrapped':True,'private_keys_on_ledger':False}

class RecoveryCustodyManager:
    """TPM local recovery custody plus user-held portable escrow independent of one device/provider."""
    def __init__(self,state_dir:str|Path,identity,protector:WindowsTpmProtector):
        self.state=Path(state_dir); self.identity=identity; self.protector=protector; self.root=self.state/'recovery_custody'; self.root.mkdir(parents=True,exist_ok=True)
    def commission_entity(self,entity_id:str,recovery_secret:bytes)->dict:
        manifest=self.identity.load_manifest(entity_id); authorities=list((manifest.get('recovery_policy') or {}).get('authorities') or [])
        if not authorities: raise RuntimeError('no recovery authority configured')
        escrow=[]
        for key_id in authorities:
            raw=self.identity._read_private_key_bytes(entity_id,str(key_id)); env=PortableRecoveryEscrow.seal(raw,recovery_secret,context=f'{entity_id}:{key_id}')
            ep=self.root/f'{entity_id}__{key_id}.escrow.json'; ep.write_text(json.dumps(env,indent=2,sort_keys=True),encoding='utf-8'); escrow.append(str(ep))
        protected=self.identity.hardware_protect_recovery(entity_id,self.protector)
        return {'entity_id':entity_id,'hardware_protected':all(x.get('hardware_protected') for x in protected),'raw_recovery_keys_removed':all(x.get('raw_private_key_removed',True) for x in protected),'portable_escrow_paths':escrow,'recovery_secret_stored':False,'provider_dependency_for_sovereign_recovery':False}
    def restore_portable(self,entity_id:str,key_id:str,recovery_secret:bytes,target_identity=None)->dict:
        identity=target_identity or self.identity; ep=self.root/f'{entity_id}__{key_id}.escrow.json'
        if not ep.is_file(): raise FileNotFoundError(str(ep))
        raw=PortableRecoveryEscrow.open(json.loads(ep.read_text(encoding='utf-8')),recovery_secret); path=identity._entity_key_dir(entity_id)/f'{key_id}.key'; identity._write_private(path,raw)
        return {'entity_id':entity_id,'key_id':key_id,'portable_recovery_restored':True,'source_tpm_required':False}
    def status(self): return {'ready':True,'tpm_local_custody':True,'portable_escrow':True,'recovery_secret_stored':False}

class GuardianRecoveryManager:
    """Signed M-of-N guardian recovery approvals with replay-resistant recovery requests."""
    def __init__(self,state_dir:str|Path,identity):
        self.root=Path(state_dir)/'guardian_recovery'; self.root.mkdir(parents=True,exist_ok=True); self.path=self.root/'guardians.sqlite'; self.identity=identity; self._init_db()
    @contextmanager
    def _connect(self):
        db=sqlite3.connect(self.path,timeout=30); db.row_factory=sqlite3.Row
        try: yield db; db.commit()
        except Exception: db.rollback(); raise
        finally: db.close()
    def _init_db(self):
        with self._connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS policies(policy_id TEXT PRIMARY KEY,entity_id TEXT NOT NULL,guardians_json TEXT NOT NULL,threshold_n INTEGER NOT NULL,delay_ms INTEGER NOT NULL,status TEXT NOT NULL,created_at_ms INTEGER NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS requests(request_id TEXT PRIMARY KEY,policy_id TEXT NOT NULL,created_at_ms INTEGER NOT NULL,status TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS votes(request_id TEXT NOT NULL,guardian_entity_id TEXT NOT NULL,signature_json TEXT NOT NULL,created_at_ms INTEGER NOT NULL,PRIMARY KEY(request_id,guardian_entity_id))')
    def create_policy(self,entity_id:str,guardians:list[str],threshold:int,*,delay_ms:int=0)->dict:
        members=sorted({str(x) for x in guardians}); n=int(threshold)
        if not members or n<1 or n>len(members): raise ValueError('invalid guardian threshold')
        pid=_id('gpol1'); now=_now()
        with self._connect() as db: db.execute('INSERT INTO policies VALUES(?,?,?,?,?,?,?)',(pid,entity_id,json.dumps(members),n,max(0,int(delay_ms)),'ACTIVE',now))
        return {'policy_id':pid,'entity_id':entity_id,'guardians':members,'threshold':n,'delay_ms':max(0,int(delay_ms)),'status':'ACTIVE'}
    def request(self,policy_id:str,request_id:str)->dict:
        with self._connect() as db:
            if not db.execute("SELECT 1 FROM policies WHERE policy_id=? AND status='ACTIVE'",(policy_id,)).fetchone(): raise KeyError('active guardian policy not found')
            try: db.execute('INSERT INTO requests VALUES(?,?,?,?)',(str(request_id),policy_id,_now(),'PENDING'))
            except sqlite3.IntegrityError as exc: raise ValueError('duplicate/replayed recovery request') from exc
        return {'request_id':str(request_id),'policy_id':policy_id,'status':'PENDING'}
    def approve(self,request_id:str,guardian_entity_id:str)->dict:
        with self._connect() as db:
            req=db.execute('SELECT * FROM requests WHERE request_id=?',(str(request_id),)).fetchone(); policy=db.execute('SELECT * FROM policies WHERE policy_id=?',(req['policy_id'],)).fetchone() if req else None
        if not req or not policy or req['status']!='PENDING': raise PermissionError('active recovery request required')
        if guardian_entity_id not in set(json.loads(policy['guardians_json'])): raise PermissionError('guardian outside recovery policy')
        body={'schema':'entity-guardian-recovery-vote-v1','request_id':str(request_id),'policy_id':policy['policy_id'],'guardian_entity_id':guardian_entity_id,'created_at_ms':_now()}; sig=self.identity.sign(guardian_entity_id,body)
        try:
            with self._connect() as db: db.execute('INSERT INTO votes VALUES(?,?,?,?)',(str(request_id),guardian_entity_id,json.dumps(sig,sort_keys=True),body['created_at_ms']))
        except sqlite3.IntegrityError as exc: raise ValueError('duplicate guardian vote') from exc
        return {**body,'signature':sig}
    def authorize(self,request_id:str)->dict:
        with self._connect() as db:
            req=db.execute('SELECT * FROM requests WHERE request_id=?',(str(request_id),)).fetchone(); policy=db.execute('SELECT * FROM policies WHERE policy_id=?',(req['policy_id'],)).fetchone() if req else None
            votes=int(db.execute('SELECT COUNT(*) FROM votes WHERE request_id=?',(str(request_id),)).fetchone()[0]) if req else 0
        if not req or not policy: return {'allowed':False,'reason':'request_not_found'}
        if req['created_at_ms']+int(policy['delay_ms'])>_now(): return {'allowed':False,'reason':'recovery_delay_not_elapsed'}
        allowed=votes>=int(policy['threshold_n'])
        return {'allowed':allowed,'reason':'threshold_met' if allowed else 'threshold_not_met','approvals':votes,'threshold':int(policy['threshold_n']),'entity_id':policy['entity_id']}
    def status(self): return {'ready':True,'threshold_guardians':True,'delay_supported':True,'replay_protected':True,'historical_signatures_preserved':True}
