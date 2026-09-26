from pathlib import Path
import importlib.util, json, shutil, tempfile

MODULE=Path(r'<LOCAL_DRIVE>/Sovereign_Entity_Network\11_ADAM\full_runtime\canonical_full_adam_runtime.py')
s=importlib.util.spec_from_file_location('entity_full_adam_runtime',MODULE)
m=importlib.util.module_from_spec(s); s.loader.exec_module(m)

with tempfile.TemporaryDirectory(prefix='entity-adam-int-') as td:
    verifier=lambda r: bool(r.get('authorized')) and r.get('authority_root')=='ENTITY'
    with m.EntityFullAdamRuntime(td,authorization_verifier=verifier) as rt:
        r1=rt.record_authorized_transition(
            entity_id='ent2-testentity0000000000000000000000000000000000000000000000',
            entity_kind='TEST_ENTITY',
            event_type='ASSET_REGISTERED',
            event={'asset_id':'asset-test-1','kind':'DATA'},
            authorization_receipt={'authorized':True,'authority_root':'ENTITY','capability_id':'cap-test-1','policy_id':'policy-test-1'},
            result={'status':'RECORDED'},
        )
        assert r1['committed'] is True
        raw=rt.reconstruct_evidence(r1['exact_evidence_object_id'])
        doc=json.loads(raw.decode('utf-8'))
        assert doc['event']['asset_id']=='asset-test-1'
        r2=rt.record_authorized_transition(
            entity_id=doc['entity_id'], event_type='RIGHTS_ASSERTED',
            event={'claim':'CONTROL'},
            authorization_receipt={'authorized':True,'authority_root':'ENTITY','capability_id':'cap-test-2'},
            result={'status':'RECORDED'},
        )
        assert r2['sequence_after']>r1['sequence_after']
        ctx=rt.project_reasoning_context(doc['entity_id'])
        assert ctx['authority_transferred_to_niki'] is False
        assert ctx['state']['last_event_type']=='RIGHTS_ASSERTED'
        hist=rt.entity_history(doc['entity_id'])
        assert any(x['value']=='ASSET_REGISTERED' for x in hist)
        assert any(x['value']=='RIGHTS_ASSERTED' for x in hist)
        v=rt.verify(); assert v['pass'] is True
        denied=False
        try:
            rt.record_authorized_transition(entity_id=doc['entity_id'],event_type='DENIED',event={},authorization_receipt={'authorized':False,'authority_root':'ENTITY'})
        except PermissionError:
            denied=True
        assert denied
        print(json.dumps({'PASS':True,'first':r1,'second':r2,'context':ctx,'history_rows':len(hist),'verification':{'pass':v['pass'],'aligned_transition_claims':v['aligned_transition_claims'],'atomic_sequence':v['atomic_universe']['sequence']}},indent=2,default=str))
