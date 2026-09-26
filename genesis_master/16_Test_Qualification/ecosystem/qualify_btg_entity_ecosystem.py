from pathlib import Path
import json,hashlib,time
ROOT=Path(r'<LOCAL_DRIVE>/Sovereign_Entity_Network'); EV=ROOT/'16_Test_Qualification'/'evidence'; STATE=Path(r'<LOCAL_DRIVE>/BTG_ENTITY_PRODUCTION_STATE')
REQUIRED={
 'ENTITY':('entity.entity',None),
 'HUNTAR':('huntar.entity','HUNTAR_ENTITY_INTEGRATION_CURRENT.json'),
 'SEARCHAR':('searchar.entity','SEARCHAR_ENTITY_INTEGRATION_CURRENT.json'),
 'HIKEAR':('hikear.entity','HIKEAR_ENTITY_INTEGRATION_CURRENT.json'),
 'BOUNDARYS_BEST':('boundarys.best.entity','BOUNDARYS_BEST_ENTITY_NATIVE_RELEASE_CURRENT.json'),
 'NIKI':('niki.entity','NIKI_ENTITY_BRIDGE_FULL_CURRENT.json'),
 'BSIE':('bsie.entity','BSIE_ENTITY_INTEGRATION_CURRENT.json'),
 'ADAM':('adam.entity','ADAM_ENTITY_INTEGRATION_CURRENT.json'),
 'BECP':('becp.entity','BECP_ENTITY_INTEGRATION_CURRENT.json'),
}
def load(p):
 try:return json.loads(Path(p).read_text(encoding='utf-8-sig'))
 except:return None
def status_ok(d):
 if not d:return False
 if d.get('status') in {'PASS','BUILD_READY','BUILT'}:return True
 if d.get('qualification_complete') is True:return True
 if d.get('schema')=='btg-niki-entity-bridge-run-v1' and d.get('full_files') is True and d.get('raw_content_sent_to_entity') is False:return True
 return False
def main():
 graph=load(STATE/'BTG_ENTITY_GRAPH.json') or {}; ents=graph.get('entities') or {}; byalias={v.get('alias'):v for v in ents.values() if isinstance(v,dict)}
 rows={}
 for name,(alias,evidence) in REQUIRED.items():
  identity=byalias.get(alias); edata=load(EV/evidence) if evidence else None
  if name=='ENTITY':
   core=load(EV/'ENTITY_CORE_INVARIANCE_CURRENT.json'); sdk=load(EV/'ENTITY_OPEN_SDK_CURRENT.json'); pb=load(EV/'ENTITY_PRINCIPAL_BINDING_CURRENT.json')
   ok=bool(identity and core and core.get('critical_core_unchanged') and sdk and sdk.get('status')=='PASS' and pb and pb.get('status')=='PASS')
   details={'core':bool(core and core.get('critical_core_unchanged')),'open_sdk':None if not sdk else sdk.get('status'),'principal_binding':None if not pb else pb.get('status')}
  else:
   ok=bool(identity and status_ok(edata)); details={'evidence_status':None if not edata else edata.get('status'),'qualification_complete':None if not edata else edata.get('qualification_complete')}
  rows[name]={'alias':alias,'entity_id':None if not identity else identity.get('entity_id'),'identity_present':bool(identity),'evidence':evidence,'integrated_qualified':ok,'details':details}
 internal=all(x['integrated_qualified'] for x in rows.values())
 rec={'schema':'btg-entity-ecosystem-qualification-v1','generated_at_ms':int(time.time()*1000),'status':'PASS_INTERNAL_ECOSYSTEM' if internal else 'INCOMPLETE','internal_ecosystem_complete':internal,'components':rows,'authority_invariants':{'user_generated_app_data_defaults_to_user_entity':True,'niki_preserves_source_controller_through_derivation':True,'registration_not_ownership':True,'economic_value_not_inferred_from_creation':True,'open_protocol_not_dependent_on_btg_hosting':True},'external_protocol_status':'PENDING_EXTERNAL_VALIDATION','external_pending':['two independent physical user-controlled devices','multi-host independent-machine storm','independently authored non-BTG implementation/interoperability'],'claim_boundary':'Internal BTG ecosystem qualification does not constitute independent external protocol validation.'}
 out=EV/'BTG_ENTITY_ECOSYSTEM_CURRENT.json';out.write_text(json.dumps(rec,indent=2,sort_keys=True)+'\n',encoding='utf-8'); sha=hashlib.sha256(out.read_bytes()).hexdigest(); Path(str(out)+'.sha256').write_text(sha+'  '+out.name+'\n',encoding='ascii'); print(json.dumps({'status':rec['status'],'complete':internal,'pending':[k for k,v in rows.items() if not v['integrated_qualified']],'sha256':sha},indent=2)); return 0 if internal else 2
if __name__=='__main__':raise SystemExit(main())
