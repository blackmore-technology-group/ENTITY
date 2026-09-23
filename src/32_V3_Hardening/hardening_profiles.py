from __future__ import annotations
from pathlib import Path
from contextlib import contextmanager
from typing import Any
import hashlib, json, secrets, sqlite3, time

CORE_VERSION='3.0.0'
CORE_PRIMITIVES=('ENTITY','AUTHORITY','RIGHT','EVENT','VALUE')
RIGHT_TERMS={'INSPECT':(), 'READ':('INSPECT',), 'QUERY':('INSPECT',), 'COPY':('READ',), 'DERIVE':('READ',), 'TRAIN':('READ',), 'INFER':('QUERY',), 'EXECUTE':(), 'MODIFY':('READ',), 'REDISTRIBUTE':('COPY',), 'COMMERCIALIZE':(), 'SUBLICENSE':(), 'CONTROL':(), 'TRANSFER':()}

def now_ms(): return int(time.time()*1000)
def canon(v): return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,default=str).encode()
def sha(v): return hashlib.sha256(v if isinstance(v,(bytes,bytearray)) else canon(v)).hexdigest()
def rid(prefix): return prefix+'-'+secrets.token_hex(12)
def require_sha256(value):
    s=str(value or '').lower()
    if len(s)!=64 or any(c not in '0123456789abcdef' for c in s): raise ValueError('SHA-256 hex required')
    return s

@contextmanager
def dbctx(path):
    db=sqlite3.connect(path); db.row_factory=sqlite3.Row
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback(); raise
    finally:
        db.close()

class ProfileRegistry:
    def __init__(self,root):
        self.path=Path(root)/'entity_v3_profiles.sqlite'; self.path.parent.mkdir(parents=True,exist_ok=True)
        with dbctx(self.path) as db:
            db.execute('CREATE TABLE IF NOT EXISTS profiles(profile_id TEXT,version TEXT,schema_sha256 TEXT,dependencies_json TEXT,mandatory INTEGER,status TEXT,created_at_ms INTEGER,PRIMARY KEY(profile_id,version))')
            db.execute('CREATE TABLE IF NOT EXISTS schemas(schema_id TEXT,version TEXT,document_sha256 TEXT,compatibility TEXT,created_at_ms INTEGER,PRIMARY KEY(schema_id,version))')
    def register_profile(self,profile_id,version,schema_sha256,dependencies=(),mandatory=False):
        digest=require_sha256(schema_sha256); deps=sorted(set(map(str,dependencies)))
        with dbctx(self.path) as db:
            db.row_factory=sqlite3.Row; old=db.execute('SELECT * FROM profiles WHERE profile_id=? AND version=?',(profile_id,version)).fetchone()
            if old:
                if old['schema_sha256']!=digest: raise ValueError('immutable profile version changed')
                return dict(old)
            for dep in deps:
                pid,sep,ver=dep.partition('@')
                if not sep or not db.execute("SELECT 1 FROM profiles WHERE profile_id=? AND version=? AND status='ACTIVE'",(pid,ver)).fetchone(): raise ValueError('missing profile dependency: '+dep)
            db.execute('INSERT INTO profiles VALUES(?,?,?,?,?,?,?)',(profile_id,version,digest,json.dumps(deps),int(bool(mandatory)),'ACTIVE',now_ms()))
        return {'profile_id':profile_id,'version':version,'schema_sha256':digest,'dependencies':deps,'mandatory':bool(mandatory),'status':'ACTIVE'}
    def register_schema(self,schema_id,version,document,compatibility='IMMUTABLE'):
        compatibility=str(compatibility).upper()
        if compatibility not in {'IMMUTABLE','BACKWARD','FORWARD','BIDIRECTIONAL'}: raise ValueError('invalid compatibility')
        digest=sha(document)
        with dbctx(self.path) as db:
            db.row_factory=sqlite3.Row; old=db.execute('SELECT * FROM schemas WHERE schema_id=? AND version=?',(schema_id,version)).fetchone()
            if old:
                if old['document_sha256']!=digest: raise ValueError('immutable historical schema changed')
                return dict(old)
            db.execute('INSERT INTO schemas VALUES(?,?,?,?,?)',(schema_id,version,digest,compatibility,now_ms()))
        return {'schema_id':schema_id,'version':version,'document_sha256':digest,'compatibility':compatibility}
    def negotiate(self,local,remote):
        selected={}; incompatible=[]
        for pid in sorted(set(local)|set(remote)):
            common=sorted(set(local.get(pid,()))&set(remote.get(pid,())))
            if common: selected[pid]=common[-1]
            elif pid in local and pid in remote: incompatible.append(pid)
        return {'core_version':CORE_VERSION,'selected_profiles':selected,'incompatible_profiles':incompatible,'core_interop_preserved':True}

class RightsOntology:
    @classmethod
    def closure(cls,actions):
        out={str(a).upper() for a in actions}; unknown=out-set(RIGHT_TERMS)
        if unknown: raise ValueError('unknown rights terms: '+','.join(sorted(unknown)))
        changed=True
        while changed:
            changed=False
            for action in list(out):
                for implied in RIGHT_TERMS[action]:
                    if implied not in out: out.add(implied); changed=True
        return out
    @classmethod
    def evaluate(cls,rules,action,context=None):
        action=str(action).upper(); context=dict(context or {})
        if action not in RIGHT_TERMS: raise ValueError('unknown right action')
        applicable=[]; requested_closure=cls.closure([action])
        for rule in rules:
            effect=str(rule.get('effect') or '').upper()
            if effect not in {'ALLOW','REQUIRE','PROHIBIT'}: raise ValueError('invalid effect')
            rule_actions={str(a).upper() for a in (rule.get('actions') or [])}; rule_closure=cls.closure(rule_actions)
            if effect=='PROHIBIT':
                if not (rule_actions & requested_closure): continue
            elif action not in rule_closure: continue
            if any(context.get(k)!=v for k,v in dict(rule.get('conditions') or {}).items()): continue
            applicable.append(rule)
        effects={str(x['effect']).upper() for x in applicable}
        decision='DENY' if 'PROHIBIT' in effects else 'CONDITIONAL' if 'REQUIRE' in effects else 'ALLOW' if 'ALLOW' in effects else 'DENY'
        return {'action':action,'decision':decision,'obligations':[o for r in applicable for o in r.get('obligations',[])],'deny_by_default':True}

class SelectiveDisclosure:
    @staticmethod
    def commit(claims):
        commitments={}; openings={}
        for key in sorted(claims):
            salt=secrets.token_hex(24); commitments[key]=sha({'key':key,'value':claims[key],'salt':salt}); openings[key]={'value':claims[key],'salt':salt}
        return {'schema':'entity-v3-private-claims-v1','root':sha({'claims':commitments}),'commitments':commitments,'private_openings':openings}
    @staticmethod
    def disclose(package,keys):
        openings=package.get('private_openings') or {}; revealed={}
        for key in sorted(set(keys)):
            if key not in openings: raise KeyError(key)
            revealed[key]=openings[key]
        return {'schema':'entity-v3-selective-disclosure-v1','root':package['root'],'commitments':dict(package['commitments']),'revealed':revealed}
    @staticmethod
    def verify(proof):
        commitments=dict(proof.get('commitments') or {}); bad=[]
        root_ok=sha({'claims':commitments})==proof.get('root')
        for key,opening in dict(proof.get('revealed') or {}).items():
            if commitments.get(key)!=sha({'key':key,'value':opening.get('value'),'salt':opening.get('salt')}): bad.append(key)
        return {'valid':root_ok and not bad,'root_valid':root_ok,'invalid_reveals':bad,'revealed_keys':sorted((proof.get('revealed') or {}).keys())}

class DisputeLedger:
    KINDS={'CLAIM','CHALLENGE','EVIDENCE','RULING','SUPERSESSION','CONSEQUENCE'}
    def __init__(self,root,identity):
        self.path=Path(root)/'entity_v3_disputes.sqlite'; self.identity=identity
        with dbctx(self.path) as db: db.execute('CREATE TABLE IF NOT EXISTS records(record_id TEXT PRIMARY KEY,kind TEXT,actor TEXT,subject_ref TEXT,target_ref TEXT,payload_json TEXT,authority_basis TEXT,created_at_ms INTEGER,signature_json TEXT)')
    def record(self,kind,actor,subject_ref,payload,target_ref=None,authority_basis=None):
        kind=str(kind).upper()
        if kind not in self.KINDS: raise ValueError('invalid dispute kind')
        if kind in {'CHALLENGE','RULING','SUPERSESSION','CONSEQUENCE'} and not target_ref: raise ValueError('target_ref required')
        self.identity.load_manifest(actor); body={'schema':'entity-v3-dispute-record-v1','record_id':rid('disp3'),'kind':kind,'actor_entity_id':actor,'subject_ref':str(subject_ref),'target_ref':target_ref,'payload':dict(payload),'authority_basis':authority_basis,'created_at_ms':now_ms(),'history_rewrite_prohibited':True}
        sig=self.identity.sign(actor,body)
        with dbctx(self.path) as db: db.execute('INSERT INTO records VALUES(?,?,?,?,?,?,?,?,?)',(body['record_id'],kind,actor,body['subject_ref'],target_ref,json.dumps(body['payload'],sort_keys=True),authority_basis,body['created_at_ms'],json.dumps(sig,sort_keys=True)))
        return dict(body,signature=sig)
    def state(self,subject_ref):
        with dbctx(self.path) as db:
            rows=db.execute('SELECT kind FROM records WHERE subject_ref=? ORDER BY created_at_ms,record_id',(subject_ref,)).fetchall()
        kinds=[r[0] for r in rows]; state='UNCONTESTED'
        if 'CHALLENGE' in kinds: state='CONTESTED'
        if 'RULING' in kinds: state='RULED'
        if 'SUPERSESSION' in kinds: state='SUPERSEDED'
        return {'subject_ref':subject_ref,'state':state,'record_count':len(rows),'history_preserved':True,'cryptographic_validity_is_not_legal_truth':True}

class StatusTimeProfile:
    STATES={'ACTIVE','SUSPENDED','REVOKED','COMPROMISED','RETIRED'}
    POLICIES={'FAIL_CLOSED','READ_ONLY_GRACE','ALLOW_UNTIL_EXPIRY'}
    def __init__(self,root,identity):
        self.path=Path(root)/'entity_v3_status_time.sqlite'; self.identity=identity
        with dbctx(self.path) as db: db.execute('CREATE TABLE IF NOT EXISTS statuses(status_id TEXT PRIMARY KEY,subject_ref TEXT,issuer TEXT,state TEXT,epoch INTEGER,effective_at_ms INTEGER,expires_at_ms INTEGER,stale_policy TEXT,created_at_ms INTEGER,signature_json TEXT)')
    def timestamp(self,authority,payload_sha256,uncertainty_ms=0):
        body={'schema':'entity-v3-time-attestation-v1','authority_entity_id':authority,'payload_sha256':require_sha256(payload_sha256),'timestamp_ms':now_ms(),'uncertainty_ms':max(0,int(uncertainty_ms))}; return dict(body,signature=self.identity.sign(authority,body))
    def publish(self,issuer,subject_ref,state,epoch,ttl_ms,stale_policy='FAIL_CLOSED',effective_at_ms=None):
        state=str(state).upper(); stale_policy=str(stale_policy).upper()
        if state not in self.STATES or stale_policy not in self.POLICIES: raise ValueError('invalid status/policy')
        effective=int(effective_at_ms or now_ms()); expires=effective+max(1,int(ttl_ms))
        with dbctx(self.path) as db:
            latest=db.execute('SELECT COALESCE(MAX(epoch),-1) FROM statuses WHERE subject_ref=?',(subject_ref,)).fetchone()[0]
            if int(epoch)<=int(latest): raise ValueError('status epoch must increase')
        body={'schema':'entity-v3-status-v1','status_id':rid('status3'),'subject_ref':subject_ref,'issuer':issuer,'state':state,'epoch':int(epoch),'effective_at_ms':effective,'expires_at_ms':expires,'stale_policy':stale_policy,'created_at_ms':now_ms()}; sig=self.identity.sign(issuer,body)
        with dbctx(self.path) as db: db.execute('INSERT INTO statuses VALUES(?,?,?,?,?,?,?,?,?,?)',(body['status_id'],subject_ref,issuer,state,int(epoch),effective,expires,stale_policy,body['created_at_ms'],json.dumps(sig,sort_keys=True)))
        return dict(body,signature=sig)
    def evaluate(self,subject_ref,at_ms=None):
        at=int(at_ms or now_ms())
        with dbctx(self.path) as db:
            db.row_factory=sqlite3.Row; row=db.execute('SELECT * FROM statuses WHERE subject_ref=? AND effective_at_ms<=? ORDER BY epoch DESC LIMIT 1',(subject_ref,at)).fetchone()
        if not row: return {'subject_ref':subject_ref,'decision':'DENY','reason':'NO_STATUS'}
        stale=at>int(row['expires_at_ms']); state=row['state']
        decision='DENY' if state in {'REVOKED','COMPROMISED'} else 'DENY' if stale and row['stale_policy']=='FAIL_CLOSED' else 'READ_ONLY' if stale and row['stale_policy']=='READ_ONLY_GRACE' else 'ALLOW'
        return {'subject_ref':subject_ref,'state':state,'epoch':row['epoch'],'stale':stale,'stale_policy':row['stale_policy'],'decision':decision}

class RecoveryQuorum:
    def __init__(self,root,identity):
        self.path=Path(root)/'entity_v3_recovery_quorum.sqlite'; self.identity=identity
        with dbctx(self.path) as db:
            db.execute('CREATE TABLE IF NOT EXISTS policies(entity_id TEXT PRIMARY KEY,approvers_json TEXT,threshold INTEGER)'); db.execute('CREATE TABLE IF NOT EXISTS requests(request_id TEXT PRIMARY KEY,entity_id TEXT,reason_sha256 TEXT,status TEXT,created_at_ms INTEGER)'); db.execute('CREATE TABLE IF NOT EXISTS approvals(request_id TEXT,approver TEXT,created_at_ms INTEGER,signature_json TEXT,PRIMARY KEY(request_id,approver))')
    def set_policy(self,entity_id,approvers,threshold):
        unique=sorted(set(approvers)); threshold=int(threshold)
        if threshold<1 or threshold>len(unique): raise ValueError('invalid threshold')
        for a in unique: self.identity.load_manifest(a)
        with dbctx(self.path) as db: db.execute('INSERT OR REPLACE INTO policies VALUES(?,?,?)',(entity_id,json.dumps(unique),threshold))
        return {'entity_id':entity_id,'approvers':unique,'threshold':threshold}
    def request(self,entity_id,reason):
        request_id=rid('recovery3')
        with dbctx(self.path) as db:
            if not db.execute('SELECT 1 FROM policies WHERE entity_id=?',(entity_id,)).fetchone(): raise KeyError('policy missing')
            db.execute('INSERT INTO requests VALUES(?,?,?,?,?)',(request_id,entity_id,sha(reason),'OPEN',now_ms()))
        return {'request_id':request_id,'entity_id':entity_id,'status':'OPEN'}
    def approve(self,request_id,approver):
        with dbctx(self.path) as db:
            db.row_factory=sqlite3.Row; req=db.execute("SELECT * FROM requests WHERE request_id=? AND status='OPEN'",(request_id,)).fetchone();
            if not req: raise KeyError('open request missing')
            pol=db.execute('SELECT * FROM policies WHERE entity_id=?',(req['entity_id'],)).fetchone()
        if approver not in set(json.loads(pol['approvers_json'])): raise PermissionError('not approver')
        body={'schema':'entity-v3-recovery-approval-v1','request_id':request_id,'entity_id':req['entity_id'],'approver':approver,'created_at_ms':now_ms()}; sig=self.identity.sign(approver,body)
        with dbctx(self.path) as db:
            db.execute('INSERT OR REPLACE INTO approvals VALUES(?,?,?,?)',(request_id,approver,body['created_at_ms'],json.dumps(sig,sort_keys=True))); count=db.execute('SELECT COUNT(*) FROM approvals WHERE request_id=?',(request_id,)).fetchone()[0]
        return dict(body,signature=sig,approval_count=count,threshold=int(pol['threshold']))
    def ready(self,request_id):
        with dbctx(self.path) as db:
            db.row_factory=sqlite3.Row; req=db.execute("SELECT * FROM requests WHERE request_id=? AND status='OPEN'",(request_id,)).fetchone();
            if not req: raise KeyError('open request missing')
            pol=db.execute('SELECT * FROM policies WHERE entity_id=?',(req['entity_id'],)).fetchone(); approvals=db.execute('SELECT COUNT(*) FROM approvals WHERE request_id=?',(request_id,)).fetchone()[0]
        return {'request_id':request_id,'ready':approvals>=int(pol['threshold']),'approval_count':approvals,'threshold':int(pol['threshold'])}

class FederatedResolution:
    def __init__(self,root,identity):
        self.path=Path(root)/'entity_v3_federated_resolution.sqlite'; self.identity=identity
        with dbctx(self.path) as db: db.execute('CREATE TABLE IF NOT EXISTS views(view_id TEXT PRIMARY KEY,object_id TEXT,resolver TEXT,version INTEGER,epoch INTEGER,resolution_sha256 TEXT,expires_at_ms INTEGER,created_at_ms INTEGER,signature_json TEXT)')
    def observe(self,resolver,object_id,resolution_record,epoch,ttl_ms):
        version=int(resolution_record.get('version') or 0)
        if version<1: raise ValueError('version required')
        digest=sha(resolution_record)
        with dbctx(self.path) as db:
            prior={r[0] for r in db.execute('SELECT resolution_sha256 FROM views WHERE object_id=? AND resolver=? AND version=? AND epoch=?',(object_id,resolver,version,int(epoch))).fetchall()}
        if prior and digest not in prior: raise ValueError('resolver equivocation detected')
        body={'schema':'entity-v3-resolver-view-v1','view_id':rid('view3'),'object_id':object_id,'resolver':resolver,'version':version,'epoch':int(epoch),'resolution_sha256':digest,'expires_at_ms':now_ms()+max(1,int(ttl_ms)),'created_at_ms':now_ms()}; sig=self.identity.sign(resolver,body)
        with dbctx(self.path) as db: db.execute('INSERT INTO views VALUES(?,?,?,?,?,?,?,?,?)',(body['view_id'],object_id,resolver,version,int(epoch),digest,body['expires_at_ms'],body['created_at_ms'],json.dumps(sig,sort_keys=True)))
        return dict(body,signature=sig)
    def quorum(self,object_id,minimum_resolvers=2,at_ms=None):
        at=int(at_ms or now_ms())
        with dbctx(self.path) as db:
            db.row_factory=sqlite3.Row; rows=db.execute('SELECT * FROM views WHERE object_id=? AND expires_at_ms>=?',(object_id,at)).fetchall()
        grouped={}
        for r in rows: grouped.setdefault((r['version'],r['epoch'],r['resolution_sha256']),set()).add(r['resolver'])
        choices=sorted(((len(v),k,v) for k,v in grouped.items()),key=lambda x:(-x[0],-x[1][0],-x[1][1],x[1][2]))
        if not choices or choices[0][0]<int(minimum_resolvers): return {'object_id':object_id,'resolved':False,'reason':'QUORUM_NOT_MET'}
        count,(version,epoch,digest),resolvers=choices[0]; return {'object_id':object_id,'resolved':True,'version':version,'epoch':epoch,'resolution_sha256':digest,'resolver_count':count,'resolvers':sorted(resolvers),'resolver_is_not_authority':True}

class AgentDelegation:
    def __init__(self,root,identity):
        self.path=Path(root)/'entity_v3_agent_delegation.sqlite'; self.identity=identity
        with dbctx(self.path) as db: db.execute('CREATE TABLE IF NOT EXISTS grants(grant_id TEXT PRIMARY KEY,principal TEXT,grantor TEXT,grantee TEXT,parent_grant_id TEXT,depth INTEGER,max_depth INTEGER,capabilities_json TEXT,budget_units INTEGER,spent_units INTEGER,expires_at_ms INTEGER,policy_sha256 TEXT,status TEXT,created_at_ms INTEGER,signature_json TEXT)')
    def grant(self,principal,grantor,grantee,capabilities,max_depth,budget_units,expires_at_ms,policy_sha256,parent_grant_id=None):
        caps=sorted({str(c).upper() for c in capabilities}); depth=0
        with dbctx(self.path) as db:
            db.row_factory=sqlite3.Row
            if parent_grant_id:
                p=db.execute("SELECT * FROM grants WHERE grant_id=? AND status='ACTIVE'",(parent_grant_id,)).fetchone()
                if not p or p['grantee']!=grantor or p['principal']!=principal: raise PermissionError('delegation chain mismatch')
                depth=int(p['depth'])+1
                if depth>int(p['max_depth']) or not set(caps).issubset(set(json.loads(p['capabilities_json']))): raise PermissionError('delegation escalation prohibited')
                if int(budget_units)>int(p['budget_units'])-int(p['spent_units']) or int(expires_at_ms)>int(p['expires_at_ms']): raise PermissionError('budget/time escalation prohibited')
        body={'schema':'entity-v3-agent-delegation-v1','grant_id':rid('agentgrant3'),'principal':principal,'grantor':grantor,'grantee':grantee,'parent_grant_id':parent_grant_id,'depth':depth,'max_depth':int(max_depth),'capabilities':caps,'budget_units':max(0,int(budget_units)),'expires_at_ms':int(expires_at_ms),'policy_sha256':require_sha256(policy_sha256),'status':'ACTIVE','created_at_ms':now_ms()}; sig=self.identity.sign(grantor,body)
        with dbctx(self.path) as db: db.execute('INSERT INTO grants VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(body['grant_id'],principal,grantor,grantee,parent_grant_id,depth,int(max_depth),json.dumps(caps),body['budget_units'],0,body['expires_at_ms'],body['policy_sha256'],'ACTIVE',body['created_at_ms'],json.dumps(sig,sort_keys=True)))
        return dict(body,signature=sig)
    def consume(self,grant_id,capability,units=1,at_ms=None):
        at=int(at_ms or now_ms()); units=max(0,int(units)); capability=str(capability).upper()
        with dbctx(self.path) as db:
            db.row_factory=sqlite3.Row; row=db.execute('SELECT * FROM grants WHERE grant_id=?',(grant_id,)).fetchone()
            if not row or row['status']!='ACTIVE' or at>int(row['expires_at_ms']): raise PermissionError('inactive/expired grant')
            if capability not in set(json.loads(row['capabilities_json'])): raise PermissionError('capability not delegated')
            if int(row['spent_units'])+units>int(row['budget_units']): raise PermissionError('budget exhausted')
            spent=int(row['spent_units'])+units; db.execute('UPDATE grants SET spent_units=? WHERE grant_id=?',(spent,grant_id))
        return {'grant_id':grant_id,'authorized':True,'spent_units':spent,'remaining_units':int(row['budget_units'])-spent}
    def kill(self,grant_id):
        with dbctx(self.path) as db:
            q=[grant_id]; revoked=[]
            while q:
                cur=q.pop(0); db.execute("UPDATE grants SET status='REVOKED' WHERE grant_id=?",(cur,)); revoked.append(cur); q.extend(r[0] for r in db.execute("SELECT grant_id FROM grants WHERE parent_grant_id=? AND status='ACTIVE'",(cur,)).fetchall())
        return {'root_grant_id':grant_id,'revoked_grants':revoked,'kill_propagated':True}

class PhysicalBinding:
    def __init__(self,root,identity):
        self.path=Path(root)/'entity_v3_physical_binding.sqlite'; self.identity=identity
        with dbctx(self.path) as db: db.execute('CREATE TABLE IF NOT EXISTS bindings(binding_id TEXT PRIMARY KEY,object_id TEXT,actor TEXT,hardware_fingerprint TEXT,evidence_sha256 TEXT,status TEXT,created_at_ms INTEGER,signature_json TEXT)')
    def bind(self,actor,object_id,hardware_fingerprint,evidence_sha256):
        with dbctx(self.path) as db: conflicts=[r[0] for r in db.execute("SELECT object_id FROM bindings WHERE hardware_fingerprint=? AND status='ACTIVE' AND object_id<>?",(hardware_fingerprint,object_id)).fetchall()]
        if conflicts: return {'bound':False,'clone_suspected':True,'conflicting_object_ids':sorted(set(conflicts))}
        body={'schema':'entity-v3-physical-binding-v1','binding_id':rid('bind3'),'object_id':object_id,'actor':actor,'hardware_fingerprint':hardware_fingerprint,'evidence_sha256':require_sha256(evidence_sha256),'status':'ACTIVE','created_at_ms':now_ms()}; sig=self.identity.sign(actor,body)
        with dbctx(self.path) as db: db.execute('INSERT INTO bindings VALUES(?,?,?,?,?,?,?,?)',(body['binding_id'],object_id,actor,hardware_fingerprint,body['evidence_sha256'],'ACTIVE',body['created_at_ms'],json.dumps(sig,sort_keys=True)))
        return dict(body,signature=sig,bound=True,clone_suspected=False)

class SettlementAdapters:
    KINDS={'FIAT_BANK','INTERNAL_ACCOUNTING','CREDIT','TOKEN','INVOICE','GOVERNMENT_RAIL','ZERO_VALUE'}
    def __init__(self): self.adapters={}
    def register(self,name,kind,capabilities=()):
        kind=str(kind).upper()
        if kind not in self.KINDS: raise ValueError('unsupported adapter kind')
        self.adapters[name]={'name':name,'kind':kind,'capabilities':sorted(set(capabilities))}; return dict(self.adapters[name])
    def route(self,kind): return [dict(v) for v in self.adapters.values() if v['kind']==str(kind).upper()]

class AdmissionController:
    def __init__(self,limit,window_ms): self.limit=max(1,int(limit)); self.window_ms=max(1,int(window_ms)); self.counters={}
    def admit(self,subject,cost=1,at_ms=None):
        at=int(at_ms or now_ms()); cost=max(1,int(cost)); key=(subject,at//self.window_ms); used=self.counters.get(key,0); allowed=used+cost<=self.limit
        if allowed: self.counters[key]=used+cost
        return {'subject':subject,'allowed':allowed,'used':self.counters.get(key,used),'limit':self.limit,'reputation_used':False}

class DegradationStateMachine:
    RULES={'NORMAL':{'VERIFY','WRITE','RESOLVE','SETTLE','TRADE'},'OFFLINE_VERIFY':{'VERIFY'},'STALE_READ':{'VERIFY','RESOLVE'},'READ_ONLY':{'VERIFY','RESOLVE'},'RECOVERY':{'VERIFY','RECOVER'}}
    def __init__(self): self.state='NORMAL'
    def transition(self,state):
        state=str(state).upper()
        if state not in self.RULES: raise ValueError('invalid degradation state')
        self.state=state; return {'state':state,'allowed_operations':sorted(self.RULES[state])}
    def permits(self,operation): return str(operation).upper() in self.RULES[self.state]

class MerkleBatcher:
    @staticmethod
    def leaf(v): return hashlib.sha256(canon(v)).digest()
    @classmethod
    def root(cls,values):
        nodes=[cls.leaf(v) for v in values]
        if not nodes: return hashlib.sha256(b'').hexdigest()
        while len(nodes)>1:
            if len(nodes)%2: nodes.append(nodes[-1])
            nodes=[hashlib.sha256(nodes[i]+nodes[i+1]).digest() for i in range(0,len(nodes),2)]
        return nodes[0].hex()
    @classmethod
    def proof(cls,values,index):
        if index<0 or index>=len(values): raise IndexError(index)
        nodes=[cls.leaf(v) for v in values]; idx=index; siblings=[]
        while len(nodes)>1:
            if len(nodes)%2: nodes.append(nodes[-1])
            sib=idx-1 if idx%2 else idx+1; siblings.append({'side':'LEFT' if idx%2 else 'RIGHT','hash':nodes[sib].hex()}); nodes=[hashlib.sha256(nodes[i]+nodes[i+1]).digest() for i in range(0,len(nodes),2)]; idx//=2
        return {'leaf':cls.leaf(values[index]).hex(),'siblings':siblings,'root':nodes[0].hex()}
    @staticmethod
    def verify(proof):
        node=bytes.fromhex(proof['leaf'])
        for s in proof['siblings']:
            other=bytes.fromhex(s['hash']); node=hashlib.sha256(other+node if s['side']=='LEFT' else node+other).digest()
        return node.hex()==proof['root']

class LegacyBridge:
    SUPPORTED={'OAUTH','OIDC','X509','DID_VC','DNS','C2PA','ERP','PKI','SUPPLY_CHAIN','DATABASE'}
    @classmethod
    def map(cls,external_system,external_id,entity_ref,evidence_sha256,verifier=None):
        system=str(external_system).upper()
        if system not in cls.SUPPORTED: raise ValueError('unsupported bridge')
        return {'schema':'entity-v3-legacy-bridge-v1','external_system':system,'external_id':external_id,'entity_ref':entity_ref,'evidence_sha256':require_sha256(evidence_sha256),'verifier':verifier,'legacy_identifier_is_not_entity_authority':True}

def capability_status():
    return {'core_primitives':list(CORE_PRIMITIVES),'extensions_optional':True,'privacy_selective_disclosure':True,'dispute_semantics':True,'threshold_recovery':True,'bounded_status_ttl':True,'federated_resolution':True,'rights_ontology':True,'ai_attenuated_delegation':True,'physical_binding':True,'settlement_adapters':True,'anti_abuse_quota':True,'degradation_states':True,'merkle_batching':True,'legacy_bridges':sorted(LegacyBridge.SUPPORTED)}
class PrivacyEnvelope:
    @staticmethod
    def pseudonym(secret: bytes, relationship: str) -> str:
        import hmac, base64
        raw=hmac.new(secret,str(relationship).encode(),hashlib.sha256).digest()
        return 'pse3-'+base64.b32encode(raw).decode().lower().rstrip('=')
    @staticmethod
    def encrypt(key: bytes, claims: dict, aad: dict | None=None) -> dict:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        if len(key) not in {16,24,32}: raise ValueError('AES-GCM key must be 128/192/256 bits')
        nonce=secrets.token_bytes(12); associated=canon(aad or {}); ciphertext=AESGCM(key).encrypt(nonce,canon(claims),associated)
        import base64
        return {'schema':'entity-v3-encrypted-claims-v1','algorithm':'AES-GCM','nonce':base64.urlsafe_b64encode(nonce).decode(),'ciphertext':base64.urlsafe_b64encode(ciphertext).decode(),'aad_sha256':hashlib.sha256(associated).hexdigest(),'plaintext_sha256':sha(claims),'minimum_disclosure':True}
    @staticmethod
    def decrypt(key: bytes, envelope: dict, aad: dict | None=None) -> dict:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        import base64
        associated=canon(aad or {})
        if hashlib.sha256(associated).hexdigest()!=envelope.get('aad_sha256'): raise ValueError('AAD mismatch')
        raw=AESGCM(key).decrypt(base64.urlsafe_b64decode(envelope['nonce']),base64.urlsafe_b64decode(envelope['ciphertext']),associated); value=json.loads(raw.decode())
        if sha(value)!=envelope.get('plaintext_sha256'): raise ValueError('plaintext digest mismatch')
        return value

class SuccessionRegistry:
    def __init__(self,root,identity):
        self.path=Path(root)/'entity_v3_succession.sqlite'; self.identity=identity
        with dbctx(self.path) as db: db.execute('CREATE TABLE IF NOT EXISTS designations(designation_id TEXT PRIMARY KEY,entity_id TEXT,successor TEXT,trigger_type TEXT,evidence_sha256 TEXT,status TEXT,created_at_ms INTEGER,signature_json TEXT)')
    def designate(self,entity_id,successor,trigger_type,evidence_sha256):
        self.identity.load_manifest(entity_id); self.identity.load_manifest(successor); trigger=str(trigger_type).upper()
        if trigger not in {'INCAPACITY','DISSOLUTION','DEATH','ADMINISTRATIVE_TRANSFER','EMERGENCY_CONTINUITY'}: raise ValueError('invalid succession trigger')
        body={'schema':'entity-v3-succession-designation-v1','designation_id':rid('succ3'),'entity_id':entity_id,'successor':successor,'trigger_type':trigger,'evidence_sha256':require_sha256(evidence_sha256),'status':'ACTIVE','created_at_ms':now_ms(),'designation_is_not_trigger_proof':True}; sig=self.identity.sign(entity_id,body)
        with dbctx(self.path) as db: db.execute('INSERT INTO designations VALUES(?,?,?,?,?,?,?,?)',(body['designation_id'],entity_id,successor,trigger,body['evidence_sha256'],'ACTIVE',body['created_at_ms'],json.dumps(sig,sort_keys=True)))
        return dict(body,signature=sig)

class AttributionMethodology:
    @staticmethod
    def receipt(object_id,evaluator,methodology,version,allocations_bps,confidence_bps,evidence_refs=()):
        allocations={str(k):int(v) for k,v in allocations_bps.items()}
        if any(v<0 for v in allocations.values()) or sum(allocations.values())>10000: raise ValueError('invalid attribution allocation')
        return {'schema':'entity-v3-attribution-methodology-v1','object_id':object_id,'evaluator':evaluator,'methodology':str(methodology),'methodology_version':str(version),'allocations_bps':dict(sorted(allocations.items())),'confidence_bps':max(0,min(10000,int(confidence_bps))),'evidence_refs':sorted(map(str,evidence_refs)),'methodology_is_not_universal_truth':True}

class PhysicalCustody:
    def __init__(self,root,identity):
        self.path=Path(root)/'entity_v3_physical_custody.sqlite'; self.identity=identity
        with dbctx(self.path) as db: db.execute('CREATE TABLE IF NOT EXISTS events(event_id TEXT PRIMARY KEY,object_id TEXT,actor TEXT,from_entity TEXT,to_entity TEXT,event_type TEXT,evidence_sha256 TEXT,created_at_ms INTEGER,signature_json TEXT)')
    def record(self,actor,object_id,from_entity,to_entity,event_type,evidence_sha256):
        event_type=str(event_type).upper()
        if event_type not in {'CUSTODY_TRANSFER','INSPECTION','REBIND','TAMPER_EVENT'}: raise ValueError('invalid physical event')
        body={'schema':'entity-v3-physical-custody-v1','event_id':rid('phys3'),'object_id':object_id,'actor':actor,'from_entity':from_entity,'to_entity':to_entity,'event_type':event_type,'evidence_sha256':require_sha256(evidence_sha256),'created_at_ms':now_ms(),'custody_is_not_ownership':True}; sig=self.identity.sign(actor,body)
        with dbctx(self.path) as db: db.execute('INSERT INTO events VALUES(?,?,?,?,?,?,?,?,?)',(body['event_id'],object_id,actor,from_entity,to_entity,event_type,body['evidence_sha256'],body['created_at_ms'],json.dumps(sig,sort_keys=True)))
        return dict(body,signature=sig)

class StandardsGovernance:
    def __init__(self,root,identity):
        self.path=Path(root)/'entity_v3_standards_governance.sqlite'; self.identity=identity
        with dbctx(self.path) as db:
            db.execute('CREATE TABLE IF NOT EXISTS rfcs(rfc_id TEXT PRIMARY KEY,proposer TEXT,body_sha256 TEXT,change_class TEXT,threshold INTEGER,status TEXT,created_at_ms INTEGER,signature_json TEXT)'); db.execute('CREATE TABLE IF NOT EXISTS votes(rfc_id TEXT,voter TEXT,decision TEXT,created_at_ms INTEGER,signature_json TEXT,PRIMARY KEY(rfc_id,voter))')
    def propose(self,proposer,body,change_class='PROFILE',threshold=2):
        change_class=str(change_class).upper()
        if change_class not in {'CORE','PROFILE','SCHEMA','TEST'}: raise ValueError('invalid change class')
        record={'schema':'entity-v3-rfc-v1','rfc_id':rid('rfc3'),'proposer':proposer,'body_sha256':sha(body),'change_class':change_class,'threshold':max(1,int(threshold)),'status':'OPEN','created_at_ms':now_ms()}; sig=self.identity.sign(proposer,record)
        with dbctx(self.path) as db: db.execute('INSERT INTO rfcs VALUES(?,?,?,?,?,?,?,?)',(record['rfc_id'],proposer,record['body_sha256'],change_class,record['threshold'],'OPEN',record['created_at_ms'],json.dumps(sig,sort_keys=True)))
        return dict(record,signature=sig)
    def vote(self,rfc_id,voter,decision):
        decision=str(decision).upper()
        if decision not in {'APPROVE','REJECT'}: raise ValueError('invalid decision')
        with dbctx(self.path) as db:
            db.row_factory=sqlite3.Row; rfc=db.execute("SELECT * FROM rfcs WHERE rfc_id=? AND status='OPEN'",(rfc_id,)).fetchone()
            if not rfc: raise KeyError('open RFC missing')
            body={'schema':'entity-v3-rfc-vote-v1','rfc_id':rfc_id,'voter':voter,'decision':decision,'created_at_ms':now_ms()}; sig=self.identity.sign(voter,body); db.execute('INSERT OR REPLACE INTO votes VALUES(?,?,?,?,?)',(rfc_id,voter,decision,body['created_at_ms'],json.dumps(sig,sort_keys=True))); approvals=db.execute("SELECT COUNT(*) FROM votes WHERE rfc_id=? AND decision='APPROVE'",(rfc_id,)).fetchone()[0]; rejects=db.execute("SELECT COUNT(*) FROM votes WHERE rfc_id=? AND decision='REJECT'",(rfc_id,)).fetchone()[0]; status='ACCEPTED' if approvals>=int(rfc['threshold']) else 'REJECTED' if rejects>=int(rfc['threshold']) else 'OPEN'; db.execute('UPDATE rfcs SET status=? WHERE rfc_id=?',(status,rfc_id))
        return dict(body,signature=sig,rfc_status=status)

class ArchivalSnapshot:
    @staticmethod
    def create(events,first_sequence,last_sequence):
        if int(first_sequence)<0 or int(last_sequence)<int(first_sequence): raise ValueError('invalid sequence range')
        return {'schema':'entity-v3-archival-snapshot-v1','first_sequence':int(first_sequence),'last_sequence':int(last_sequence),'event_count':len(events),'merkle_root':MerkleBatcher.root(events),'pruning_preserves_proof':True,'partial_verification_supported':True,'created_at_ms':now_ms()}
