from __future__ import annotations
from pathlib import Path
import hashlib,json,time

def _canon(v): return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,default=str).encode()
def _sha(v): return hashlib.sha256(v if isinstance(v,(bytes,bytearray)) else _canon(v)).hexdigest()
def _now(): return int(time.time()*1000)

class DomainPortabilityManager:
    """Documented sovereign-domain export independent of the source SQLite representation."""
    def __init__(self,identity,domain_authority): self.identity=identity; self.domain=domain_authority
    def export_domain(self,entity_id:str,domain_id:str,destination:str|Path,*,state_refs:dict|None=None,external_dependencies:list|None=None)->dict:
        domain=self.domain.get_domain(domain_id)
        if domain['entity_root']!=entity_id: raise PermissionError('domain controller mismatch')
        snapshot=self.domain.public_snapshot(domain_id); identity_manifest=self.identity.load_manifest(entity_id); now=_now()
        body={'schema':'entity-domain-export-manifest-v1','entity_root':entity_id,'domain_id':domain_id,
              'domain_snapshot_sha256':_sha(snapshot),'identity_manifest_sha256':_sha(identity_manifest),
              'schema_versions':['entity-domain-v1','entity-name-claim-v1','entity-node-authorization-v1','entity-node-revocation-v1','entity-service-manifest-v1'],
              'cryptographic_algorithms':['Ed25519','SHA-256'],'state_refs':dict(state_refs or {}),
              'known_external_dependencies':list(external_dependencies or []),'created_at_ms':now,
              'proprietary_btg_database_required':False,'dns_required_for_interpretation':False}
        signature=self.identity.sign(entity_id,body)
        package={'schema':'entity-domain-export-package-v1','identity_manifest':identity_manifest,'domain_snapshot':snapshot,
                 'export_manifest':{**body,'signature':signature}}
        package['package_sha256']=_sha({k:v for k,v in package.items() if k!='package_sha256'})
        path=Path(destination); path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(package,indent=2,sort_keys=True)+'\n',encoding='utf-8')
        return {'path':str(path),'entity_root':entity_id,'domain_id':domain_id,'package_sha256':package['package_sha256'],
                'source_database_required':False,'portable_interpretation':True}
    def verify_export(self,path:str|Path)->dict:
        package=json.loads(Path(path).read_text(encoding='utf-8'))
        if package.get('schema')!='entity-domain-export-package-v1': return {'valid':False,'reason':'schema'}
        expected=package.get('package_sha256'); material={k:v for k,v in package.items() if k!='package_sha256'}
        if expected!=_sha(material): return {'valid':False,'reason':'package_hash'}
        manifest=dict(package.get('export_manifest') or {}); signature=manifest.pop('signature',None)
        snapshot=dict(package.get('domain_snapshot') or {}); identity_manifest=dict(package.get('identity_manifest') or {})
        if manifest.get('domain_snapshot_sha256')!=_sha(snapshot) or manifest.get('identity_manifest_sha256')!=_sha(identity_manifest):
            return {'valid':False,'reason':'manifest_commitment'}
        if manifest.get('entity_root')!=identity_manifest.get('entity_id') or manifest.get('entity_root')!=(snapshot.get('domain') or {}).get('entity_root'):
            return {'valid':False,'reason':'root_binding'}
        if not self.identity.verify_manifest(identity_manifest): return {'valid':False,'reason':'identity_manifest'}
        if not self.identity.verify_signature(identity_manifest,manifest,signature or {}): return {'valid':False,'reason':'export_signature'}
        return {'valid':True,'entity_root':manifest['entity_root'],'domain_id':manifest['domain_id'],'package_sha256':expected,
                'proprietary_database_required':False,'dns_required':False}

    def restore_public_state(self,path:str|Path,target_domain)->dict:
        check=self.verify_export(path)
        if not check['valid']: raise PermissionError('domain export verification failed: '+str(check.get('reason')))
        package=json.loads(Path(path).read_text(encoding='utf-8')); snap=package['domain_snapshot']; d=snap['domain']
        with target_domain._connect() as db:
            exists=db.execute('SELECT 1 FROM domains WHERE domain_id=?',(d['domain_id'],)).fetchone()
            if not exists:
                db.execute('INSERT INTO domains VALUES(?,?,?,?,?,?,?,?)',(d['domain_id'],d['entity_root'],d['namespace'],d.get('current_name'),int(d['version']),d['status'],int(d['created_at_ms']),int(d.get('updated_at_ms') or d['created_at_ms'])))
        claim=snap.get('name_claim')
        if claim:
            with target_domain._connect() as db:
                if not db.execute('SELECT 1 FROM name_claims WHERE claim_id=?',(claim['claim_id'],)).fetchone():
                    db.execute('INSERT INTO name_claims VALUES(?,?,?,?,?,?,?,?,?,?)',(claim['claim_id'],claim['domain_id'],claim['entity_root'],claim['normalized_name'],claim['namespace'],claim['status'],claim['conflict_state'],json.dumps(claim.get('evidence') or {},sort_keys=True),json.dumps(claim['signature'],sort_keys=True),int(claim['created_at_ms'])))
        for node in snap.get('nodes') or []:
            with target_domain._connect() as db:
                if not db.execute('SELECT 1 FROM nodes WHERE node_id=?',(node['node_id'],)).fetchone():
                    db.execute('INSERT INTO nodes VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(node['node_id'],node['domain_id'],node['entity_root'],node['public_key_b64'],json.dumps(node['permitted_services']),json.dumps(node['network_scopes']),json.dumps(node['publication_scopes']),json.dumps(node['data_scopes']),int(node['not_before_ms']),node.get('expires_at_ms'),json.dumps(node.get('delegation') or {},sort_keys=True),node['status'],int(node['auth_version']),json.dumps(node['signature'],sort_keys=True),int(node['created_at_ms']),int(node['created_at_ms'])))
            rev=node.get('revocation')
            if rev:
                with target_domain._connect() as db:
                    if not db.execute('SELECT 1 FROM revocations WHERE revocation_id=?',(rev['revocation_id'],)).fetchone():
                        db.execute('INSERT INTO revocations VALUES(?,?,?,?,?,?,?,?)',(rev['revocation_id'],rev['domain_id'],rev['node_id'],rev['entity_root'],rev['reason'],int(rev['effective_at_ms']),json.dumps(rev['signature'],sort_keys=True),int(rev['created_at_ms'])))
        for svc in snap.get('services') or []:
            with target_domain._connect() as db:
                if not db.execute('SELECT 1 FROM services WHERE service_id=?',(svc['service_id'],)).fetchone():
                    db.execute('INSERT INTO services VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(svc['service_id'],svc['domain_id'],svc['node_id'],svc['service_type'],json.dumps(svc['endpoint'],sort_keys=True),svc['protocol_version'],json.dumps(svc['capabilities']),svc['access_class'],json.dumps(svc['required_credentials']),json.dumps(svc['policy_refs']),json.dumps(svc['data_classifications']),svc.get('economic_terms_ref'),json.dumps(svc.get('availability') or {},sort_keys=True),int(svc['manifest_version']),svc.get('expires_at_ms'),svc['status'],json.dumps(svc['signature'],sort_keys=True),int(svc['created_at_ms']),int(svc['created_at_ms'])))
        for mig in snap.get('migrations') or []:
            with target_domain._connect() as db:
                if not db.execute('SELECT 1 FROM migrations WHERE migration_id=?',(mig['migration_id'],)).fetchone():
                    db.execute('INSERT INTO migrations VALUES(?,?,?,?,?,?,?,?,?,?)',(mig['migration_id'],mig['domain_id'],mig.get('from_node'),mig.get('to_node'),mig.get('from_provider'),mig.get('to_provider'),mig['semantic_hash_before'],mig['semantic_hash_after'],json.dumps(mig['signature'],sort_keys=True),int(mig['created_at_ms'])))
        return {'restored':True,'entity_root':d['entity_root'],'domain_id':d['domain_id'],'same_identity':True,
                'same_domain':True,'proprietary_database_required_for_export_interpretation':False}
