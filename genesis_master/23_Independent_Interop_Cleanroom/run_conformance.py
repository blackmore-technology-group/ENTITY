from pathlib import Path
import hashlib, importlib.util, json, sys, time
ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network"); HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('cleanroom',HERE/'independent_domain.py'); C=importlib.util.module_from_spec(spec); spec.loader.exec_module(C)
EVID=ROOT/'16_Test_Qualification/evidence'; VALID=EVID/'ENTITY_DOMAIN_VALID_VECTORS'; INVALID=EVID/'ENTITY_DOMAIN_INVALID_VECTORS'; OUT=EVID/'ENTITY_CLEANROOM_INTEROP_CURRENT.json'
identity=json.loads((VALID/'entity_root.json').read_text(encoding='utf-8'))['material']; results=[]
for folder,expected in ((VALID,True),(INVALID,False)):
    for p in sorted(folder.glob('*.json')):
        v=json.loads(p.read_text(encoding='utf-8')); trust=v.get('trust_material') or identity; ok,reason=C.validate(v['name'],v['material'],trust)
        passed=(ok is expected); results.append({'vector':p.name,'set':folder.name,'expected_valid':expected,'observed_valid':ok,'reason':reason,'pass':passed})
source=(HERE/'independent_domain.py').read_text(encoding='utf-8'); forbidden=['blackmore_ci','canonical_domain','Sovereign_Entity_Network\\01_Core_Runtime','Sovereign_Entity_Network\\22_Sovereign_Domain']
independent=all(x not in source for x in forbidden); all_ok=all(x['pass'] for x in results) and independent
record={'schema':'entity-cleanroom-interop-v1','status':'PASS_INTERNAL_CLEANROOM' if all_ok else 'FAIL','qualification_complete':all_ok,'valid_vectors':sum(1 for x in results if x['set']==VALID.name and x['pass']),'invalid_vectors':sum(1 for x in results if x['set']==INVALID.name and x['pass']),'total_vectors':len(results),'results':results,'implementation_source_sha256':hashlib.sha256(source.encode()).hexdigest(),'runtime_import_independence':independent,'forbidden_runtime_imports':forbidden,'external_non_btg_organization_claimed':False,'limitations':['BTG/ChatGPT-authored clean-room implementation; independent external organization authorship/run remains a separate milestone']}
body=dict(record); record['evidence_sha256']=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':')).encode()).hexdigest(); OUT.write_text(json.dumps(record,indent=2,sort_keys=True)+'\n',encoding='utf-8'); print(json.dumps({'status':record['status'],'valid':record['valid_vectors'],'invalid':record['invalid_vectors'],'total':len(results),'failed':[x for x in results if not x['pass']],'output':str(OUT)},indent=2)); raise SystemExit(0 if all_ok else 2)
