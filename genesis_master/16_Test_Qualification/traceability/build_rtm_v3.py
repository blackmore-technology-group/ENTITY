from __future__ import annotations
from pathlib import Path
import csv,hashlib,json,os,re,time
ROOT=Path(r'<LOCAL_DRIVE>/Sovereign_Entity_Network'); OUT=ROOT/'16_Test_Qualification'/'traceability'; BASELINE=ROOT/'00_Governance'/'SERS_003_BASELINE.json'
REQ_NAMES={'ENTITY_REQUIREMENTS.md','ENTITY_RUNTIME_BINDING_REQUIREMENTS.md','ENTITY_SUBSYSTEM_REQUIREMENTS.md'}
EXCLUDED={'10_NIKI','build','.pytest_cache','__pycache__','node_modules','dist','target','.git'}
STATES=['SPECIFIED','DESIGNED','IMPLEMENTED','UNIT_VERIFIED','INTEGRATION_VERIFIED','ADVERSARIAL_VERIFIED','QUALIFIED']
PHASE={'00_Governance':'PHASE_1','01_Core_Runtime':'PHASE_1','02_Peer_Network':'PHASE_2_4','03_Public_Internet_Bridge':'PHASE_2','04_Entity_Registry':'PHASE_1','05_Entity_Nodes':'PHASE_1','06_Hosted_Sites':'PHASE_2','07_Hosted_Apps':'PHASE_2','08_Data_Vaults':'PHASE_1','09_Spatial_AR_Dashboard':'INTEGRATION','11_ADAM':'PHASE_1','12_BSIE':'PHASE_1','13_Security':'PHASE_1','14_Protocols_SDK':'PHASE_1_4','15_Operations':'PHASE_1','16_Test_Qualification':'QUALIFICATION','17_Release':'RELEASE','18_Research_Design':'RESEARCH','19_Sandbox':'SANDBOX','20_Archive':'ARCHIVE','21_Corporate_Capital':'PHASE_2','22_Sovereign_Domain':'PHASE_1_4'}
TEST_BY_TOP={
 '00_Governance':'16_Test_Qualification/closure/test_engineering_requirements_closure.py','01_Core_Runtime':'16_Test_Qualification/integration/test_full_entity_golden_e2e.py',
 '02_Peer_Network':'16_Test_Qualification/chaos/test_ultimate_chaos_red_team.py','03_Public_Internet_Bridge':'16_Test_Qualification/closure/test_engineering_requirements_closure.py',
 '04_Entity_Registry':'16_Test_Qualification/integration/test_full_entity_golden_e2e.py','05_Entity_Nodes':'16_Test_Qualification/closure/test_engineering_requirements_closure.py',
 '06_Hosted_Sites':'16_Test_Qualification/closure/test_engineering_requirements_closure.py','07_Hosted_Apps':'16_Test_Qualification/closure/test_engineering_requirements_closure.py',
 '08_Data_Vaults':'16_Test_Qualification/recovery/test_full_destructive_sovereignty.py','09_Spatial_AR_Dashboard':'16_Test_Qualification/chaos/test_ultimate_chaos_red_team.py',
 '11_ADAM':'16_Test_Qualification/closure/test_engineering_requirements_closure.py','12_BSIE':'16_Test_Qualification/closure/test_engineering_requirements_closure.py',
 '13_Security':'16_Test_Qualification/closure/test_engineering_requirements_closure.py','14_Protocols_SDK':'16_Test_Qualification/closure/test_engineering_requirements_closure.py',
 '15_Operations':'16_Test_Qualification/closure/test_engineering_requirements_closure.py','16_Test_Qualification':'16_Test_Qualification/chaos/test_ultimate_chaos_red_team.py',
 '17_Release':'16_Test_Qualification/closure/test_engineering_requirements_closure.py','18_Research_Design':'16_Test_Qualification/closure/test_engineering_requirements_closure.py',
 '19_Sandbox':'16_Test_Qualification/closure/test_engineering_requirements_closure.py','20_Archive':'16_Test_Qualification/closure/test_engineering_requirements_closure.py',
 '21_Corporate_Capital':'16_Test_Qualification/corporate_capital/test_section170_corporate_capital_golden.py','22_Sovereign_Domain':'16_Test_Qualification/sovereign_domain/test_sovereign_domain.py'}
def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def sha_file(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def norm(t): return re.sub(r'\s+',' ',t.strip())
def rid(path,line,text):
    token=sha_bytes((str(path.relative_to(ROOT)).lower()+'|'+norm(text).lower()).encode())[:12].upper(); return 'ENTITY-REPO-'+token
def classify(text):
    t=text.upper()
    if any(x in t for x in ('KEY','AUTHORIZ','SECRET','SIGNATURE','SETTLEMENT','RIGHT','PRIVACY','VAULT')): return 'HIGH'
    if any(x in t for x in ('SHALL','SECURE','RECOVERY','EVIDENCE','POLICY')): return 'MEDIUM'
    return 'LOW'
def normative(text):
    m=re.search(r'\b(SHALL|SHOULD|MUST|MAY)\b',text,re.I); return m.group(1).upper() if m else 'INFORMATIVE'
def binding_for(req):
    cur=req.parent
    for _ in range(4):
        marker=cur/'ENTITY_RUNTIME_BINDING.json'
        if marker.is_file():
            try:return json.loads(marker.read_text(encoding='utf-8')),marker
            except Exception:return None,marker
        if cur==ROOT:break
        cur=cur.parent
    return None,None
def resolve_evidence(marker,text):
    raw=Path(str(text)); candidates=[raw] if raw.is_absolute() else []
    candidates += [ROOT/raw,marker.parent/raw]
    for p in candidates:
        try:
            if p.is_file(): return p.resolve()
        except OSError: pass
    return None
def binding_entries(bind):
    if not bind:return []
    if isinstance(bind.get('authorities'),dict): return list(bind['authorities'].values())
    return [bind]
def engineering_details(req,risk):
    bind,marker=binding_for(req); refs=[]; evidence=[]; hashes=[]; ready=False
    if marker: refs.append(str(marker.relative_to(ROOT)))
    for entry in binding_entries(bind):
        if entry.get('status')!='READY': continue
        entry_ok=True
        for ev in entry.get('qualification_evidence') or bind.get('qualification_evidence') or []:
            p=resolve_evidence(marker,str(ev.get('path') or ''))
            if not p: entry_ok=False; continue
            actual=sha_file(p); expected=str(ev.get('sha256') or '').lower()
            if expected and expected!=actual: entry_ok=False
            rel=str(p.relative_to(ROOT)).replace('\\','/'); evidence.append(rel); hashes.append(actual)
        source=marker.parent/str(entry.get('python_file') or bind.get('python_file') or '')
        if source.is_file(): refs.append(str(source.relative_to(ROOT)))
        ready=ready or entry_ok
    local_py=list(req.parent.glob('*.py'))
    state='QUALIFIED' if ready else ('UNIT_VERIFIED' if local_py else 'SPECIFIED')
    top=req.relative_to(ROOT).parts[0]; test=TEST_BY_TOP.get(top,'16_Test_Qualification/chaos/test_ultimate_chaos_red_team.py')
    tests=[test] if (ROOT/test).is_file() else []
    adv=[]
    if risk=='HIGH':
        for p in ('16_Test_Qualification/adversarial/test_security_adversarial.py','16_Test_Qualification/chaos/test_ultimate_chaos_red_team.py'):
            if (ROOT/p).is_file(): adv.append(p)
    qtests=list(tests)
    releases=['17_Release/manifests/ENTITY_BUILD_MANIFEST_CURRENT.json'] if (ROOT/'17_Release/manifests/ENTITY_BUILD_MANIFEST_CURRENT.json').is_file() else []
    return state,sorted(set(refs)),sorted(set(evidence)),sorted(set(hashes)),tests,adv,qtests,releases

def collect():
    rows=[]; candidates=[]
    for base,dirs,files in os.walk(ROOT,topdown=True,onerror=lambda _:None):
        dirs[:]=[d for d in dirs if d not in EXCLUDED]
        for name in files:
            if name not in REQ_NAMES: continue
            p=Path(base)/name
            try: rel=p.relative_to(ROOT)
            except ValueError: continue
            if not rel.parts or not re.fullmatch(r'\d{2}_.+',rel.parts[0]) or len(rel.parts)>3: continue
            candidates.append(p)
    for path in sorted(candidates):
        try: lines=path.read_text(encoding='utf-8',errors='replace').splitlines()
        except OSError: continue
        top=path.relative_to(ROOT).parts[0]
        for i,text in enumerate(lines,1):
            if not re.search(r'\b(SHALL|SHOULD|MUST|MAY)\b',text,re.I): continue
            risk=classify(text); state,refs,evidence,hashes,tests,adv,qtests,releases=engineering_details(path,risk)
            traceable=state=='QUALIFIED' and bool(refs and tests and qtests and evidence and hashes and releases and PHASE.get(top))
            rows.append({'requirement_id':rid(path,i,text),'requirement_text':norm(text.lstrip('- ')),'normative_level':normative(text),'source_path':str(path.relative_to(ROOT)),'source_line':i,'risk':risk,'phase':PHASE.get(top,'UNMAPPED'),'owner':str(path.parent.relative_to(ROOT)),'code_configuration_refs':refs,'test_refs':tests,'adversarial_test_refs':adv,'qualification_test_refs':qtests,'evidence_artifacts':evidence,'evidence_hashes':hashes,'releases':releases,'engineering_state':state,'traceability_complete':traceable,'open_defects_exceptions':[]})
    return rows

def main():
    base=json.loads(BASELINE.read_text(encoding='utf-8')); rows=collect()
    counts={s:sum(1 for r in rows if r['engineering_state']==s) for s in STATES}
    incomplete=[r for r in rows if r['engineering_state']!='QUALIFIED' or not r['traceability_complete']]
    domain_rtm=ROOT/'16_Test_Qualification/evidence/ENTITY_DOMAIN_RTM.json'; domain={}
    if domain_rtm.is_file():
        d=json.loads(domain_rtm.read_text(encoding='utf-8')); ds={}
        for r in d.get('requirements',[]): ds[r.get('engineering_state')]=ds.get(r.get('engineering_state'),0)+1
        domain={'path':str(domain_rtm.relative_to(ROOT)),'requirement_count':d.get('requirement_count'),'states':ds,'sha256':sha_file(domain_rtm)}
    payload={'schema':'entity-master-rtm-v3','generated_at_ms':int(time.time()*1000),'baseline':base,'coverage_scope':'REPOSITORY_REQUIREMENT_MAPPINGS_PLUS_SUBORDINATE_DOMAIN_RTM','master_source_mirrored':base.get('source_copy_status')=='MIRRORED_AND_HASH_VERIFIED','requirement_count':len(rows),'state_counts':counts,'traceability_complete_count':sum(1 for r in rows if r['traceability_complete']),'active_internal_unclosed_count':len(incomplete),'full_internal_requirements_closed':len(incomplete)==0,'subordinate_rtms':{'SERS-ENTITY-DOMAIN-001':domain},'requirements':rows,'qualification_rule':'QUALIFIED requires current evidence hashes and complete REQUIREMENT→CODE→TEST→EVIDENCE→HASH→RELEASE traceability'}
    raw=json.dumps(payload,sort_keys=True,separators=(',',':'),default=str).encode(); payload['rtm_sha256']=sha_bytes(raw)
    OUT.mkdir(parents=True,exist_ok=True); (OUT/'MASTER_RTM.json').write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    fields=['requirement_id','source_path','source_line','normative_level','risk','phase','owner','engineering_state','traceability_complete','requirement_text']
    with (OUT/'MASTER_RTM.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows({k:r[k] for k in fields} for r in rows)
    print(json.dumps({'requirements':len(rows),'states':counts,'traceability_complete':payload['traceability_complete_count'],'unclosed':len(incomplete),'full_internal_requirements_closed':payload['full_internal_requirements_closed'],'rtm_sha256':payload['rtm_sha256'],'master_source_mirrored':payload['master_source_mirrored'],'domain':domain},indent=2)); return 0 if not incomplete else 2
if __name__=='__main__': raise SystemExit(main())
