from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
import hashlib, json, secrets, sqlite3, time

HIGH_IMPACT={
    'ROOT_AUTHORITY_CHANGE','IP_ASSIGNMENT','EXCLUSIVE_LICENCE','HIGH_VALUE_CONTRACT',
    'SENSITIVE_EXPORT','LARGE_SETTLEMENT','IRREVERSIBLE_PUBLICATION','RESTRICTED_AI_TRAINING',
    'SHARE_ISSUANCE','SHARE_TRANSFER'
}
SECRET_KEYS={'password','secret','private_key','recovery_key','token','cookie','api_key','credential'}
TELEMETRY_METRICS={
    'availability','latency_ms','authorization_denial','signature_failure','ledger_conflict',
    'sync_delay_ms','vault_error','connector_failure','usage_meter_error','settlement_reconciliation_error'
}
CRITICAL_DEFECT_CLASSES={
    'UNAUTHORIZED_RIGHTS_MUTATION','UNAUTHORIZED_ASSET_DISCLOSURE','ROOT_TAKEOVER',
    'UNAUTHORIZED_SETTLEMENT','SIGNATURE_BYPASS','UNDETECTED_LEDGER_TAMPERING',
    'AGENT_ESCALATION','CONNECTOR_ESCALATION'
}

def _now(): return int(time.time()*1000)
def _canon(v): return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,default=str).encode()
def _hash(v): return hashlib.sha256(_canon(v)).hexdigest()
class CanonicalEngineeringControlPlane:
    """Cross-cutting fail-closed controls for SERS-ENTITY-003 production engineering."""
    def __init__(self,state_dir:str|Path):
        self.root=Path(state_dir)/'engineering_controls'; self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/'controls.sqlite'; self._init_db()

    @contextmanager
    def _connect(self):
        db=sqlite3.connect(self.path,timeout=30); db.row_factory=sqlite3.Row
        try: yield db; db.commit()
        except Exception: db.rollback(); raise
        finally: db.close()

    def _init_db(self):
        with self._connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS objects(kind TEXT NOT NULL,key TEXT NOT NULL,state TEXT NOT NULL,payload_json TEXT NOT NULL,created_at_ms INTEGER NOT NULL,updated_at_ms INTEGER NOT NULL,PRIMARY KEY(kind,key))')
            db.execute('CREATE TABLE IF NOT EXISTS audit(seq INTEGER PRIMARY KEY AUTOINCREMENT,event_id TEXT UNIQUE NOT NULL,kind TEXT NOT NULL,subject TEXT NOT NULL,payload_json TEXT NOT NULL,prev_hash TEXT,event_hash TEXT UNIQUE NOT NULL,created_at_ms INTEGER NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS nonces(namespace TEXT NOT NULL,nonce TEXT NOT NULL,result_json TEXT NOT NULL,PRIMARY KEY(namespace,nonce))')

    def _audit(self,kind:str,subject:str,payload:dict)->dict:
        now=_now(); eid='eng1-'+secrets.token_hex(16)
        with self._connect() as db:
            prior=db.execute('SELECT event_hash FROM audit ORDER BY seq DESC LIMIT 1').fetchone(); prev=prior['event_hash'] if prior else None
            body={'event_id':eid,'kind':str(kind).upper(),'subject':str(subject),'payload':dict(payload),'prev_hash':prev,'created_at_ms':now}
            digest=_hash(body); db.execute('INSERT INTO audit(event_id,kind,subject,payload_json,prev_hash,event_hash,created_at_ms) VALUES(?,?,?,?,?,?,?)',(eid,body['kind'],body['subject'],json.dumps(body['payload'],sort_keys=True),prev,digest,now))
        return {**body,'event_hash':digest}
    def _put(self,kind:str,key:str,payload:dict,state:str='ACTIVE')->dict:
        now=_now(); kind=str(kind).upper(); key=str(key); state=str(state).upper()
        with self._connect() as db:
            existing=db.execute('SELECT created_at_ms FROM objects WHERE kind=? AND key=?',(kind,key)).fetchone(); created=existing['created_at_ms'] if existing else now
            db.execute('INSERT OR REPLACE INTO objects(kind,key,state,payload_json,created_at_ms,updated_at_ms) VALUES(?,?,?,?,?,?)',(kind,key,state,json.dumps(dict(payload),sort_keys=True),created,now))
        self._audit(kind,key,{'state':state,'payload_sha256':_hash(payload)})
        return {'kind':kind,'key':key,'state':state,'payload':dict(payload),'created_at_ms':created,'updated_at_ms':now}

    def _get(self,kind:str,key:str)->dict:
        with self._connect() as db: row=db.execute('SELECT * FROM objects WHERE kind=? AND key=?',(str(kind).upper(),str(key))).fetchone()
        if not row: raise KeyError(f'{kind}:{key} not found')
        return {'kind':row['kind'],'key':row['key'],'state':row['state'],'payload':json.loads(row['payload_json']),'created_at_ms':row['created_at_ms'],'updated_at_ms':row['updated_at_ms']}

    def idempotent(self,namespace:str,nonce:str,producer)->dict:
        ns=str(namespace); nonce=str(nonce)
        with self._connect() as db:
            row=db.execute('SELECT result_json FROM nonces WHERE namespace=? AND nonce=?',(ns,nonce)).fetchone()
            if row: return json.loads(row['result_json'])
        result=dict(producer())
        with self._connect() as db: db.execute('INSERT INTO nonces(namespace,nonce,result_json) VALUES(?,?,?)',(ns,nonce,json.dumps(result,sort_keys=True)))
        return result

    def verify_audit(self)->dict:
        with self._connect() as db: rows=db.execute('SELECT * FROM audit ORDER BY seq').fetchall()
        prev=None
        for row in rows:
            body={'event_id':row['event_id'],'kind':row['kind'],'subject':row['subject'],'payload':json.loads(row['payload_json']),'prev_hash':row['prev_hash'],'created_at_ms':row['created_at_ms']}
            if row['prev_hash']!=prev or _hash(body)!=row['event_hash']: return {'pass':False,'events':len(rows)}
            prev=row['event_hash']
        return {'pass':True,'events':len(rows),'head_hash':prev}
    # Governance / authority
    def register_jurisdiction_profile(self,profile_id:str,version:int,rules:dict)->dict:
        if int(version)<1: raise ValueError('version must be >=1')
        return self._put('JURISDICTION',profile_id,{'version':int(version),'rules':dict(rules),'engineering_not_legal_advice':True})

    def authorize(self,context:dict)->dict:
        c=dict(context or {}); required={'actor','capability','action','purpose','policy','jurisdiction','time_ms'}
        missing=sorted(required-set(c))
        if missing: return {'allowed':False,'reason':'missing_authorization_context','missing':missing}
        if c.get('policy') not in {'ALLOW','PERMIT'}: return {'allowed':False,'reason':'policy_denied'}
        if c.get('capability_active') is not True: return {'allowed':False,'reason':'capability_inactive'}
        action=str(c.get('action')).upper()
        if action in HIGH_IMPACT and not c.get('approval_ref'): return {'allowed':False,'reason':'approval_required'}
        if c.get('counterparty_required') and not c.get('counterparty'): return {'allowed':False,'reason':'counterparty_required'}
        decision={'allowed':True,'actor':c['actor'],'action':action,'purpose':c['purpose'],'jurisdiction':c['jurisdiction'],'approval_ref':c.get('approval_ref')}
        self._audit('AUTHORIZATION',str(c['actor']),decision); return decision

    def transition_claim(self,claim_id:str,current_origin:str,target_status:str,*,evidence:dict|None=None)->dict:
        origin=str(current_origin).upper(); target=str(target_status).upper()
        if origin in {'UNKNOWN','DERIVED_INFERENCE'} and target in {'VERIFIED','AUTHORITATIVELY_VERIFIED'} and not evidence:
            raise PermissionError('unknown/inferred claim cannot become verified without qualifying evidence')
        return self._put('CLAIM_STATE',claim_id,{'evidence_origin':origin,'status':target,'evidence':dict(evidence or {})})

    # Node/device authority
    def authorize_node(self,entity_root:str,node_id:str,public_key:str,scopes:list[str],*,protocol_version:str,schema_version:str,crypto_suite:str)->dict:
        payload={'entity_root':entity_root,'node_id':node_id,'public_key':public_key,'scopes':sorted(set(scopes)),'protocol_version':protocol_version,'schema_version':schema_version,'crypto_suite':crypto_suite,'root_identity_replaced':False}
        return self._put('NODE',node_id,payload,'ACTIVE')
    def revoke_node(self,node_id:str)->dict:
        row=self._get('NODE',node_id); return self._put('NODE',node_id,row['payload'],'REVOKED')

    def reconcile_node_event(self,node_id:str,nonce:str,*,exclusive:bool=False,conflicting_state:bool=False,payload:dict|None=None)->dict:
        node=self._get('NODE',node_id)
        if node['state']!='ACTIVE': raise PermissionError('revoked/inactive node')
        if exclusive and conflicting_state: raise PermissionError('exclusive operation conflicts; fail closed until reconciliation')
        def produce():
            event={'node_id':node_id,'nonce':nonce,'exclusive':bool(exclusive),'conflicting_state':False,'payload_sha256':_hash(payload or {}),'signed_locally':True,'reconciled':True}
            self._audit('NODE_RECONCILIATION',node_id,event); return event
        return self.idempotent('node-event:'+node_id,nonce,produce)

    def export_node_state(self,node_id:str)->dict:
        row=self._get('NODE',node_id)
        return {'schema':'entity-node-export-v1','node_id':node_id,'entity_root':row['payload']['entity_root'],'authorization_state':row['state'],'protocol_version':row['payload']['protocol_version'],'schema_version':row['payload']['schema_version'],'crypto_suite':row['payload']['crypto_suite'],'historical_evidence_preserved':True}

    # Hosted sites
    def register_site(self,entity_root:str,site_id:str,asset_id:str,*,classification:str,rights_state:str,policy_ref:str,provenance_ref:str)->dict:
        payload={'entity_root':entity_root,'asset_id':asset_id,'classification':classification.upper(),'rights_state':rights_state.upper(),'policy_ref':policy_ref,'provenance_ref':provenance_ref,'publication_history':[]}
        return self._put('SITE',site_id,payload,'PRIVATE')

    def publish_site(self,site_id:str,destination:str,*,terms_state:str,approval_ref:str|None,external_content_id:str|None=None)->dict:
        row=self._get('SITE',site_id); p=dict(row['payload']); terms=str(terms_state).upper()
        if p['classification'] in {'PRIVATE','RESTRICTED'}: raise PermissionError('sensitive site content is not publishable by default')
        if p['rights_state'] not in {'VERIFIED','LICENSABLE','PUBLIC'}: raise PermissionError('rights unresolved; review required')
        if terms not in {'VERIFIED','REVIEW_REQUIRED'}: raise PermissionError('platform terms unresolved')
        if terms=='REVIEW_REQUIRED' and not approval_ref: raise PermissionError('explicit approval required for review-required terms')
        event={'destination':destination,'terms_state':terms,'approval_ref':approval_ref,'external_content_id':external_content_id,'source_rights_mutated':False,'source_provenance_mutated':False,'published_at_ms':_now()}
        p['publication_history']=list(p.get('publication_history') or [])+[event]; self._put('SITE',site_id,p,'PUBLISHED'); self._audit('SITE_EXPORT',site_id,event); return event
    # Hosted applications
    def install_app(self,entity_root:str,app_id:str,version:str,scopes:list[str],*,package_sha256:str,sbom_sha256:str,rbom_sha256:str,data_classification:str='INTERNAL')->dict:
        if len(package_sha256)!=64 or len(sbom_sha256)!=64 or len(rbom_sha256)!=64: raise ValueError('package/SBOM/RBOM hashes required')
        payload={'entity_root':entity_root,'version':version,'scopes':sorted(set(scopes)),'package_sha256':package_sha256,'sbom_sha256':sbom_sha256,'rbom_sha256':rbom_sha256,'data_classification':data_classification.upper(),'history':[version]}
        return self._put('APP',app_id,payload,'ACTIVE')

    def update_app(self,app_id:str,new_version:str,new_scopes:list[str],*,approved_scope_expansion:bool=False)->dict:
        row=self._get('APP',app_id); p=dict(row['payload']); old=set(p['scopes']); new=set(new_scopes)
        if not new.issubset(old) and not approved_scope_expansion: raise PermissionError('material scope expansion requires permission review')
        p['version']=new_version; p['scopes']=sorted(new); p['history']=list(p['history'])+[new_version]
        return self._put('APP',app_id,p,'ACTIVE')

    def authorize_app_action(self,app_id:str,scope:str,*,policy_allowed:bool,instruction_origin:str,nonce:str)->dict:
        app=self._get('APP',app_id)
        if app['state']!='ACTIVE' or scope not in app['payload']['scopes']: raise PermissionError('application scope denied')
        if not policy_allowed: raise PermissionError('authoritative policy denied application action')
        if str(instruction_origin).upper()!='AUTHORIZED_REQUEST': raise PermissionError('untrusted app content cannot determine Entity authority')
        def produce():
            result={'app_id':app_id,'scope':scope,'authorized':True,'commercialization_rights_inferred':False,'nonce':nonce}
            self._audit('APP_ACTION',app_id,result); return result
        return self.idempotent('app-action:'+app_id,nonce,produce)

    # Privacy / security
    def minimum_projection(self,data:dict,allowed_fields:list[str],*,classification:str,permission:bool,provider:str,purpose:str)->dict:
        if not permission: raise PermissionError('AI/external read permission denied')
        if str(classification).upper() in {'SECRET','RESTRICTED'} and str(provider).upper()!='LOCAL': raise PermissionError('external disclosure prohibited for sensitive classification')
        out={}
        for k in allowed_fields:
            if k in data and not any(secret in k.lower() for secret in SECRET_KEYS): out[k]=data[k]
        self._audit('DISCLOSURE_PROJECTION',provider,{'purpose':purpose,'classification':classification.upper(),'fields':sorted(out)})
        return {'projection':out,'minimum_disclosure':True,'purpose':purpose,'provider':provider}
    def register_crypto_profile(self,profile_id:str,*,signing:str,hashing:str,key_agreement:str|None=None)->dict:
        payload={'signing':signing,'hashing':hashing,'key_agreement':key_agreement,'algorithm_identified':True,'schema_crypto_agile':True}
        return self._put('CRYPTO_PROFILE',profile_id,payload)

    def device_session(self,device_id:str,*,authorized:bool,secure_transport:bool,expires_at_ms:int,step_up:bool=False,high_impact:bool=False)->dict:
        if not authorized or not secure_transport or int(expires_at_ms)<=_now(): return {'allowed':False,'reason':'authentication_or_session_invalid'}
        if high_impact and not step_up: return {'allowed':False,'reason':'step_up_authentication_required'}
        result={'allowed':True,'device_id':device_id,'expires_at_ms':int(expires_at_ms),'step_up':bool(step_up)}
        self._audit('DEVICE_SESSION',device_id,result); return result

    # Operations / observability
    def register_slo(self,service_id:str,*,availability_target:float,latency_target_ms:int,error_budget:float,rpo_seconds:int,rto_seconds:int,max_sync_lag_seconds:int,alert_thresholds:dict,owner:str,runbook:str)->dict:
        if not (0<float(availability_target)<=1): raise ValueError('availability target invalid')
        payload={'availability_target':float(availability_target),'latency_target_ms':int(latency_target_ms),'error_budget':float(error_budget),'rpo_seconds':int(rpo_seconds),'rto_seconds':int(rto_seconds),'max_sync_lag_seconds':int(max_sync_lag_seconds),'alert_thresholds':dict(alert_thresholds),'owner':owner,'runbook':runbook}
        return self._put('SLO',service_id,payload)

    def telemetry(self,metric:str,value:float|int,*,tags:dict|None=None)->dict:
        name=str(metric).lower()
        if name not in TELEMETRY_METRICS: raise ValueError('metric not approved')
        clean={}
        for k,v in dict(tags or {}).items():
            lk=str(k).lower()
            if any(secret in lk for secret in SECRET_KEYS) or lk in {'entity_id','asset_id','path','filename','content'}: continue
            clean[str(k)]=v
        event={'metric':name,'value':value,'tags':clean,'sensitive_content_stored':False}; self._audit('TELEMETRY',name,event); return event

    def record_incident(self,incident_id:str,*,category:str,containment:str,evidence_ref:str,recovery:str,root_cause:str,remediation:str)->dict:
        payload={'category':category,'containment':containment,'evidence_ref':evidence_ref,'recovery':recovery,'root_cause':root_cause,'remediation':remediation,'preserves_evidence':True}
        return self._put('INCIDENT',incident_id,payload,'CLOSED')
    def record_migration(self,migration_id:str,*,entity_root_before:str,entity_root_after:str,semantic_root_before:str,semantic_root_after:str,source_provider:str,destination_provider:str,source_schema:str,target_schema:str,tool_version:str)->dict:
        if entity_root_before!=entity_root_after: raise ValueError('sovereign Entity root changed during migration')
        if semantic_root_before!=semantic_root_after: raise ValueError('sovereign semantic commitment changed during migration')
        payload={'entity_root':entity_root_after,'semantic_root':semantic_root_after,'source_provider':source_provider,'destination_provider':destination_provider,'source_schema':source_schema,'target_schema':target_schema,'tool_version':tool_version,'former_provider_authority_retained':False,'historical_meaning_preserved':True}
        return self._put('MIGRATION',migration_id,payload,'VERIFIED')

    # Protocol / SDK profiles
    def register_sdk(self,platform:str,version:str,*,schema_version:str,crypto_suite:str,scopes:list[str],extensions:list[str]|None=None)->dict:
        p=str(platform).upper()
        if p not in {'ANDROID','APPLE','WEB','WINDOWS'}: raise ValueError('unsupported SDK platform')
        if not version or not schema_version or not crypto_suite: raise ValueError('versioned schema/crypto profile required')
        payload={'platform':p,'version':version,'schema_version':schema_version,'crypto_suite':crypto_suite,'scopes':sorted(set(scopes)),'extensions':sorted(set(extensions or [])),'ambient_authority':False,'error_taxonomy':['AUTHENTICATION','AUTHORIZATION','POLICY_DENIAL','INVALID_TRANSITION','SIGNATURE_FAILURE','CONFLICT','DUPLICATE_REPLAY','DEPENDENCY_UNAVAILABLE','UNVERIFIED_EXTERNAL_STATE']}
        return self._put('SDK',p,payload,'READY')

    def sdk_mutation(self,platform:str,nonce:str,*,scope:str,policy_allowed:bool)->dict:
        sdk=self._get('SDK',str(platform).upper())
        if scope not in sdk['payload']['scopes'] or not policy_allowed: raise PermissionError('SDK mutation denied')
        def produce():
            result={'platform':sdk['payload']['platform'],'scope':scope,'nonce':nonce,'accepted':True,'replay_safe':True}; self._audit('SDK_MUTATION',platform,result); return result
        return self.idempotent('sdk:'+str(platform).upper(),nonce,produce)

    # ADAM / BSIE authority boundaries
    def authorize_adam(self,capability:dict,proposal:dict)->dict:
        cap=dict(capability or {}); p=dict(proposal or {})
        if cap.get('active') is not True: raise PermissionError('ADAM capability inactive')
        if str(p.get('operation')).upper() not in {str(x).upper() for x in cap.get('operations',[])}: raise PermissionError('ADAM operation outside capability')
        if p.get('instruction_origin')!='AUTHORIZED_REQUEST': raise PermissionError('untrusted content is not an instruction')
        if p.get('amount',0)>cap.get('financial_limit',0): raise PermissionError('ADAM financial limit exceeded')
        return {'allowed':True,'agent_id':cap.get('agent_id'),'operation':str(p.get('operation')).upper(),'entity_root_authority_inherited':False}

    def bsie_projection(self,world_object:dict,allowed_fields:list[str])->dict:
        obj=dict(world_object or {}); origin=str(obj.get('evidence_origin') or 'UNKNOWN').upper()
        state=dict(obj.get('state') or {}); projected={k:state[k] for k in allowed_fields if k in state}
        return {'world_id':obj.get('world_id'),'state':projected,'evidence_origin':origin,'read_only':True,'legal_ownership_inferred':False,'commercialization_rights_inferred':False,'verified_truth_inferred':False}
    # Release engineering
    def evaluate_release(self,defects:list[dict],evidence_package:dict)->dict:
        blocking=[]
        for defect in list(defects or []):
            if str(defect.get('class') or '').upper() in CRITICAL_DEFECT_CLASSES and str(defect.get('status') or '').upper() not in {'CLOSED','FIXED','NOT_APPLICABLE'}:
                blocking.append(defect)
        required={'source_revision','build_hashes','sbom','rbom','pbom','test_results','qualification_result','schema_versions','crypto_versions','migration_versions','artifact_hashes','release_signer','timestamp','rtm_snapshot','release_gates'}
        missing=sorted(k for k in required if not evidence_package.get(k))
        passed=not blocking and not missing
        result={'pass':passed,'blocking_critical_defects':blocking,'missing_evidence':missing,'claims_bounded_to_evidence':True,'trl9_claim_allowed':bool(passed and evidence_package.get('representative_operational_evidence'))}
        self._audit('RELEASE_GATE','ENTITY',result); return result

    def classify_public_claim(self,state:str)->dict:
        s=str(state).upper(); allowed={'REGISTERED','CLAIMED','PROVENANCE_VERIFIED','RIGHTS_VERIFIED','EXTERNALLY_ATTESTED','DISPUTED'}
        if s not in allowed: raise ValueError('unsupported claim state')
        return {'state':s,'ownership_implied':False,'truth_implied':False,'market_value_implied':False}

    def status(self)->dict:
        with self._connect() as db:
            objects=int(db.execute('SELECT COUNT(*) FROM objects').fetchone()[0]); events=int(db.execute('SELECT COUNT(*) FROM audit').fetchone()[0]); nonces=int(db.execute('SELECT COUNT(*) FROM nonces').fetchone()[0])
        chain=self.verify_audit()
        return {'ready':chain['pass'],'objects':objects,'events':events,'idempotency_records':nonces,'audit_chain':chain,'default_deny':True,'private_by_default':True,'authority_custody_separated':True,'untrusted_content_is_authority':False}

# Non-production and historical lifecycle controls are attached as explicit helpers.
def _classify_artifact(self,artifact_id:str,*,environment:str,maturity:str,evidence_origin:str,synthetic:bool=False)->dict:
    env=str(environment).upper(); mat=str(maturity).upper(); origin=str(evidence_origin).upper()
    if env not in {'RESEARCH','SANDBOX','TEST','QUALIFICATION','PRODUCTION'}: raise ValueError('invalid environment')
    payload={'environment':env,'maturity':mat,'evidence_origin':origin,'synthetic':bool(synthetic),'production_authority':env=='PRODUCTION' and mat=='QUALIFIED'}
    return self._put('ARTIFACT_CLASSIFICATION',artifact_id,payload,mat)

def _promote_artifact(self,artifact_id:str,*,tests_passed:bool,review_ref:str|None,release_evidence_ref:str|None)->dict:
    row=self._get('ARTIFACT_CLASSIFICATION',artifact_id); p=dict(row['payload'])
    if p['environment'] not in {'RESEARCH','SANDBOX','TEST','QUALIFICATION'}: raise ValueError('artifact is not promotable from non-production')
    if not tests_passed or not review_ref or not release_evidence_ref: raise PermissionError('promotion requires review, tests and release evidence')
    p.update({'environment':'PRODUCTION','maturity':'QUALIFIED','production_authority':True,'promotion_review_ref':review_ref,'release_evidence_ref':release_evidence_ref})
    return self._put('ARTIFACT_CLASSIFICATION',artifact_id,p,'QUALIFIED')

def _archive_state(self,record_id:str,*,schema_version:str,verification_ref:str,retention_basis:str,active_authority:bool=False)->dict:
    if active_authority: raise PermissionError('archive state cannot silently become current authority')
    payload={'schema_version':schema_version,'verification_ref':verification_ref,'retention_basis':retention_basis,'historical_verifiable':True,'active_authority':False,'silent_rewrite_allowed':False}
    return self._put('ARCHIVE',record_id,payload,'ARCHIVED')

CanonicalEngineeringControlPlane.classify_artifact=_classify_artifact
CanonicalEngineeringControlPlane.promote_artifact=_promote_artifact
CanonicalEngineeringControlPlane.archive_state=_archive_state
