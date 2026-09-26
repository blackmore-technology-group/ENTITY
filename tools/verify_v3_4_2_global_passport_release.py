from __future__ import annotations
import hashlib, importlib.util, json, pathlib, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
KIT=ROOT/'protocol/v3/ENTITY_V3_4_2_GLOBAL_PASSPORT_CLEANROOM_KIT.min.json'
SCHEMA=ROOT/'protocol/v3/ENTITY_GLOBAL_PASSPORT.schema.json'
EXPECTED_KIT='ced70113f1d153627eb972b11adbf20e502ed086e0b13e8abf1dc5adc4c2e716'
EXPECTED_SCHEMA='d3abb77eef52de516a26caa3d7ef16e9fe268b4f9da21b480aad1687f19e051d'
EXPECTED_RESULT='45af773554a7191c1b49a75c636a1106afb1de36d788bb00d7af56097b8d1b0e'
def sha(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def canonical(v): return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
errors=[]
if sha(KIT)!=EXPECTED_KIT: errors.append('kit_sha256')
if sha(SCHEMA)!=EXPECTED_SCHEMA: errors.append('schema_sha256')
kit=json.loads(KIT.read_text(encoding='utf-8'))
if kit.get('version')!='3.4.2' or kit.get('base_release')!='v3.4.1': errors.append('version_or_base')
if kit.get('valid_vectors')!=13 or kit.get('invalid_vectors')!=13 or len(kit.get('cases',[]))!=26: errors.append('vector_counts')
if kit.get('schema_sha256')!=EXPECTED_SCHEMA or kit.get('expected_result_sha256')!=EXPECTED_RESULT: errors.append('kit_commitments')
spec=importlib.util.spec_from_file_location('v342_conf',ROOT/'src/38_Global_Passports/passport_conformance.py')
conf=importlib.util.module_from_spec(spec); sys.modules['v342_conf']=conf; spec.loader.exec_module(conf)
rows=[]
for case in sorted(kit.get('cases',[]),key=lambda x:x.get('id','')):
    actual='VALID' if conf.validate_global_passport_record(case.get('record') or {}) else 'INVALID'
    if actual!=case.get('expect'): errors.append(f"case:{case.get('id')}:{actual}")
    rows.append({'id':case.get('id'),'actual':actual})
result_hash=hashlib.sha256(canonical(rows)).hexdigest()
if result_hash!=EXPECTED_RESULT: errors.append(f'result_sha256:{result_hash}')
print(json.dumps({'valid':not errors,'version':'3.4.2','vectors':len(rows),'valid_vectors':kit.get('valid_vectors'),'invalid_vectors':kit.get('invalid_vectors'),'kit_sha256':sha(KIT),'schema_sha256':sha(SCHEMA),'result_sha256':result_hash,'errors':errors},indent=2,sort_keys=True))
sys.exit(0 if not errors else 2)
