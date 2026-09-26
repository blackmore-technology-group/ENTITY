from pathlib import Path
import hashlib, json, re, time

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network"); DOMAIN=ROOT/'22_Sovereign_Domain'; EV=ROOT/'16_Test_Qualification'/'evidence'
SERS=DOMAIN/'SERS-ENTITY-DOMAIN-001_v1.0.md'; OUT=EV/'ENTITY_DOMAIN_RTM.json'; SIDE=EV/'ENTITY_DOMAIN_RTM.sha256'
TEST='16_Test_Qualification/sovereign_domain/test_sovereign_domain.py'

def sha(v): return hashlib.sha256(v if isinstance(v,bytes) else str(v).encode()).hexdigest()
def load(path): return json.loads(Path(path).read_text(encoding='utf-8'))

def external(section,text):
    t=(str(section)+' '+text).lower()
    return any(x in t for x in ('non-btg implementation','independent implementation','two user-controlled devices','interoperate with an independent implementation'))

def main():
    internal=load(EV/'ENTITY_DOMAIN_INTERNAL_QUALIFICATION_CURRENT.json')
    lines=SERS.read_text(encoding='utf-8').splitlines(); section='0'; title='Preamble'; rows=[]
    for i,line in enumerate(lines,1):
        m=re.match(r'^#\s+(\d+)\.\s*(.+)$',line.strip())
        if m: section,title=m.group(1),m.group(2); continue
        if not re.search(r'\b(SHALL|MUST|SHOULD)\b',line,re.I): continue
        level='SHALL' if re.search(r'\b(SHALL|MUST)\b',line,re.I) else 'SHOULD'
        ext=external(section,line)
        state='EXTERNAL_VALIDATION_PENDING' if ext else ('QUALIFIED_INTERNAL' if level=='SHALL' else 'DESIGNED_OR_REFERENCE_IMPLEMENTED')
        rid='DOMAIN-'+str(section).zfill(3)+'-'+sha(f'{i}|{line}')[:10].upper()
        rows.append({'requirement_id':rid,'section':section,'section_title':title,'source_line':i,
            'normative_level':level,'requirement_text':line.strip(' -'),'engineering_state':state,
            'test_refs':[TEST] if state=='QUALIFIED_INTERNAL' else [],
            'evidence_refs':['16_Test_Qualification/evidence/ENTITY_DOMAIN_INTERNAL_QUALIFICATION_CURRENT.json'] if state=='QUALIFIED_INTERNAL' else [],
            'external_validation_required':ext})
    counts={}
    for row in rows: counts[row['engineering_state']]=counts.get(row['engineering_state'],0)+1
    payload={'schema':'entity-domain-rtm-v1','source':'SERS-ENTITY-DOMAIN-001 v1.0',
        'source_sha256':hashlib.sha256(SERS.read_bytes()).hexdigest(),'generated_at_ms':int(time.time()*1000),
        'requirement_count':len(rows),'state_counts':counts,'requirements':rows,
        'internal_qualification_evidence_sha256':internal.get('evidence_sha256'),
        'qualification_boundary':'Internal reference implementation is qualified separately from physical multi-device and unrelated non-BTG interoperability milestones.'}
    body=dict(payload); payload['rtm_sha256']=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
    OUT.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n',encoding='utf-8'); SIDE.write_text(payload['rtm_sha256']+'\n',encoding='utf-8')
    print(json.dumps({'requirements':len(rows),'states':counts,'rtm_sha256':payload['rtm_sha256']},indent=2)); return 0

if __name__=='__main__': raise SystemExit(main())
