from __future__ import annotations
from pathlib import Path
from typing import Any, Callable
import importlib.util, json

HERE=Path(__file__).resolve().parent
SRC=HERE.parent
REPO=SRC.parent

def _load(name:str,path:Path):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise ImportError(str(path))
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

PB=_load('entity_ecosystem_pb',REPO/'sdk'/'principal_binding'/'canonical_principal_binding.py')
DOMAIN=_load('entity_ecosystem_domain',SRC/'22_Sovereign_Domain'/'core'/'canonical_domain.py')
NODE=_load('entity_ecosystem_node',SRC/'22_Sovereign_Domain'/'node_runtime'/'canonical_node_runtime.py')
RESOLUTION=_load('entity_ecosystem_resolution',SRC/'22_Sovereign_Domain'/'resolution'/'canonical_resolution.py')
PRESENCE=_load('entity_ecosystem_presence',SRC/'22_Sovereign_Domain'/'presence'/'canonical_presence.py')

REQUIRED_SUBSYSTEMS=('ADAM','NIKI','BSIE','BECP')

class EcosystemBindingRegistry:
    """Fail-closed verification of separately executable BTG subsystems bound to ENTITY."""
    def __init__(self,state_dir:str|Path,binding_dir:str|Path):
        self.state=Path(state_dir); self.binding_dir=Path(binding_dir)
    def verify_required(self)->dict[str,Any]:
        out={}
        for name in REQUIRED_SUBSYSTEMS:
            key=name.lower(); bp=self.binding_dir/f'{key}_local_principal_binding.json'; pp=self.binding_dir/f'{key}_entity_profile.json'
            if not bp.is_file() or not pp.is_file():
                out[name]={'valid':False,'reason':'binding_or_profile_missing'}; continue
            binding=json.loads(bp.read_text(encoding='utf-8-sig')); profile=json.loads(pp.read_text(encoding='utf-8-sig'))
            result=PB.validate_bound_installation(self.state,binding)
            subsystem=str(profile.get('subsystem') or ('NIKI' if key=='niki' else '')).upper()
            result['profile_matches']=subsystem==name or (name=='NIKI' and profile.get('schema')=='btg-niki-entity-profile-v1')
            result['profile_application_matches']=profile.get('application_entity_id')==binding.get('application_entity_id')
            result['profile_installation_matches']=profile.get('installation_entity_id')==binding.get('installation_entity_id')
            result['valid']=bool(result.get('valid') and result['profile_matches'] and result['profile_application_matches'] and result['profile_installation_matches'])
            out[name]=result
        return {'schema':'entity-ecosystem-binding-verification-v1','pass':all(v.get('valid') for v in out.values()),'subsystems':out}

class FederatedEntityNode:
    """Commissioned sovereign node: signed domain + services + encrypted direct sessions."""
    def __init__(self,state_dir:str|Path,identity,entity_root:str,*,node_id:str):
        self.state=Path(state_dir); self.state.mkdir(parents=True,exist_ok=True)
        self.identity=identity; self.entity_root=str(entity_root)
        self.domain=DOMAIN.EntityDomainAuthority(self.state,identity)
        self.resolver=RESOLUTION.EntityNativeResolver(identity)
        self.presence=PRESENCE.PresenceAdvertisementManager()
        self.node=NODE.EntityNodeRuntime(self.state/'node',str(node_id))
        self.domain_record=None; self.node_authorization=None; self.service_manifests={}; self.endpoint=None

    def commission(self,*,name:str,services:dict[str,Callable[[dict],dict]],host:str='127.0.0.1',port:int=0)->dict:
        if not services: raise ValueError('at least one service required')
        domain=self.domain.create_domain(self.entity_root,requested_name=name)
        endpoint=self.node.start(host,port); permitted=['API']
        auth=self.domain.authorize_node(self.entity_root,domain['domain_id'],self.node.public_key_b64,permitted_services=permitted,node_id=self.node.node_id)
        manifests={}
        for service_id,handler in sorted(services.items()):
            self.node.add_api_service(service_id,handler)
            manifests[service_id]=self.domain.publish_service(
                self.entity_root,domain['domain_id'],self.node.node_id,'API',
                {'host':endpoint['host'],'port':endpoint['port']},protocol_version='ENTITY-DIRECT-v1',
                capabilities=[service_id],access_class='PUBLIC',service_id=service_id)
        self.domain_record=domain; self.node_authorization=auth; self.service_manifests=manifests; self.endpoint=endpoint
        return {'schema':'entity-federated-node-commission-v1','entity_root':self.entity_root,
                'domain_id':domain['domain_id'],'node_id':self.node.node_id,'endpoint':endpoint,
                'services':sorted(manifests),'offline_sovereignty_preserved':True,
                'network_participation_requires_owner_commissioning':True}

    def snapshot(self)->dict:
        if not self.domain_record: raise RuntimeError('node is not commissioned')
        return self.domain.public_snapshot(self.domain_record['domain_id'])

    def accept_snapshot(self,source_id:str,snapshot:dict,public_manifest:dict)->dict:
        self.identity.import_public_manifest(public_manifest)
        return self.resolver.add_snapshot(source_id,snapshot)

    def request(self,identifier:str,service_id:str,request:dict)->dict:
        proof=self.resolver.resolve(identifier,service_id=service_id)
        return NODE.EntityDirectClient.request(proof,service_id,request)

    def advertise(self,*,scope:str='PUBLIC',sequence:int=1,ttl_ms:int=60000)->dict:
        if not self.node_authorization: raise RuntimeError('node is not commissioned')
        return self.presence.create(self.node,self.node_authorization,list(self.service_manifests),scope=scope,
                                    endpoint_hints=[self.endpoint],sequence=sequence,ttl_ms=ttl_ms)
    def stop(self): self.node.stop()

class EcosystemServiceGateway:
    """Network facade over existing authoritative BTDU and EEP engines; it creates no new authority."""
    def __init__(self,*,btdu=None,exchange=None): self.btdu=btdu; self.exchange=exchange
    def btdu_handler(self,request:dict)->dict:
        if self.btdu is None: raise RuntimeError('BTDU not configured')
        op=str(request.get('operation') or '').upper()
        if op=='STATUS': return self.btdu.verify(deep=False)
        if op=='CONTEXT': return self.btdu.project_object_context(str(request['object_ref']))
        raise ValueError('unsupported BTDU network operation')
    def market_handler(self,request:dict)->dict:
        if self.exchange is None: raise RuntimeError('exchange not configured')
        op=str(request.get('operation') or '').upper()
        if op=='STATUS': return self.exchange.status()
        if op=='SUBMIT_SIGNED_ORDER': return self.exchange.submit_signed_order(dict(request['order']),dict(request['signature']))
        if op=='MARKET_DATA': return self.exchange.market_data(str(request['venue_id']),str(request['instrument_id']))
        if op=='BALANCE': return {'balance_units':self.exchange.balance(str(request['instrument_id']),str(request['holder']))}
        raise ValueError('unsupported market network operation')
