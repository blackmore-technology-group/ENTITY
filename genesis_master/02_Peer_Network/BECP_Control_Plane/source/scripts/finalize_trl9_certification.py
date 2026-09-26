from __future__ import annotations
import hashlib, hmac, json, os, shutil, subprocess
from datetime import datetime, timezone
from pathlib import Path
import httpx

ROOT=Path(r"<LOCAL_DRIVE>/Blackmore_Technology_Group\Software Development\BECP")
TRL=ROOT/'runtime'/'trl9'/'BECP_0.2.1_TRL9_20260912'
OUT=ROOT/'qa_evidence'/'BECP_0.2.1_TRL9_CERTIFICATION_20260913'
QUAL=ROOT/'runtime'/'qualification'/'becp_0.2.1'
QAKEY=ROOT/'runtime'/'secrets'/'qa_seal.key'
DEVICE='56d7ed92-c5b4-4cca-addd-02ab1384ca74'

def sha(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def wj(p:Path,x): p.write_text(json.dumps(x,indent=2,sort_keys=True),encoding='utf-8')
def run(cmd,cwd=ROOT):
    p=subprocess.run(cmd,cwd=cwd,capture_output=True,text=True,check=False)
    return {'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr}

def verify_audit(p:Path):
    prev='GENESIS'; errs=[]; n=0
    for i,line in enumerate(p.read_text(encoding='utf-8').splitlines(),1):
        if not line.strip(): continue
        n+=1; r=json.loads(line); stored=str(r.get('record_hash',''))
        if r.get('previous_hash')!=prev: errs.append(f'{i}: previous hash')
        base=dict(r); base.pop('record_hash',None); base.pop('record_hmac',None)
        calc=hashlib.sha256(json.dumps(base,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        if calc!=stored: errs.append(f'{i}: record hash')
        prev=stored
    return {'ok':n>0 and not errs,'records':n,'final_hash':prev,'file_sha256':sha(p),'errors':errs}

def copy_evidence():
    for p in TRL.iterdir():
        if p.is_file() and p.suffix.lower() in {'.json','.txt','.sha256'}:
            shutil.copy2(p,OUT/p.name)
    live=ROOT/'runtime'/'qualification'/'LIVE_RESULTS.json'
    if live.exists(): shutil.copy2(live,OUT/'DEEP_LIVE_QUALIFICATION_RESULTS.json')

def current_state():
    ca=ROOT/'runtime'/'pki'/'ca'/'ca.cert.pem'
    with httpx.Client(verify=str(ca),timeout=10) as c:
        health=c.get('https://127.0.0.1:8765/health').json()
        meta=c.get('https://127.0.0.1:8765/openapi.json').json()['info']
    reg=json.loads((ROOT/'runtime'/'registry'/'devices.json').read_text(encoding='utf-8-sig'))
    btg=next(d for d in reg['devices'] if d['device_id']==DEVICE)
    return {'health':health,'api_version':meta.get('version'),'btg':btg}

def main():
    if OUT.exists(): shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    copy_evidence()
    py=os.fspath(Path(os.sys.executable))
    core=run([py,'-m','pytest','-q'])
    comp=run([py,'-m','compileall','-q','blackmore_ecp','api','adapters','agents','scripts'])
    roots={
      'NIKI':Path(r'<LOCAL_DRIVE>/Blackmore_Technology_Group\NIKI\Blackmore_Central_Intelligence_Advanced_NIKI_ADAM_BSIE_v0.6.1_AR_INTELLIGENCE_COMPLETE'),
      'HIKEAR':Path(r'<LOCAL_DRIVE>/Blackmore_Technology_Group\Software Development\HIKE_AR\HikeAR_v0.1.0'),
      'HUNTAR':Path(r'<LOCAL_DRIVE>/Blackmore_Technology_Group\Software Development\HUNT_AR\HuntAR_v4.3.0'),
      'SEARCHAR':Path(r'<LOCAL_DRIVE>/Blackmore_Technology_Group\Software Development\SAR\SearchAR_v0.12.0')}
    prod={k:run([py,'-m','pytest','integrations/becp/tests','-q'],v) for k,v in roots.items()}
    wj(OUT/'FINAL_REGRESSION_RESULTS.json',{'core':core,'compileall':comp,'product_integrations':prod})
    audits={'gateway':verify_audit(ROOT/'runtime'/'audit'/'gateway_audit.jsonl'),'btg_agent':verify_audit(ROOT/'runtime'/'audit'/f'{DEVICE}.jsonl')}
    wj(OUT/'FINAL_AUDIT_CHAIN_VERIFICATION.json',audits)
    state=current_state(); wj(OUT/'FINAL_PRODUCTION_STATE.json',state)

    expected=json.loads((QUAL/'FINAL_BUILD_HASHES.json').read_text(encoding='utf-8-sig'))
    arts=[]
    for item in expected:
        p=ROOT/item['path']; ok=p.exists() and p.stat().st_size==item['bytes'] and sha(p)==item['sha256']
        arts.append({**item,'exists':p.exists(),'actual_bytes':p.stat().st_size if p.exists() else None,'actual_sha256':sha(p) if p.exists() else None,'ok':ok})
    wj(OUT/'FINAL_ARTIFACT_HASH_VERIFICATION.json',arts)
    support=[ROOT/'config'/'GATEWAY_LOCAL_QUALIFICATION.json',ROOT/'config'/'BTG_ENGINEERING_WORKSTATION.json',ROOT/'scripts'/'START_BECP_PRODUCTION_GATEWAY_021.ps1',ROOT/'scripts'/'START_BECP_PRODUCTION_AGENT_021.ps1',ROOT/'scripts'/'STOP_BECP_PRODUCTION_021.ps1',ROOT/'scripts'/'VERIFY_BECP_PRODUCTION_021.ps1']
    support += [ROOT/'docs'/n for n in ['OPERATIONS_AND_USER_GUIDE.md','SECURITY_ADMINISTRATION_GUIDE.md','MAINTENANCE_RECOVERY_ROLLBACK_GUIDE.md','OPERATOR_TRAINING_GUIDE.md','SUSTAINING_ENGINEERING_PLAN.md','TRL9_CERTIFICATION_BASIS.md']]
    wj(OUT/'FINAL_SUPPORT_HASHES.json',[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in support])
    trlsec=json.loads((OUT/'PRODUCTION_API_SECURITY_RESULTS.json').read_text(encoding='utf-8-sig'))
    mcp=json.loads((OUT/'PRODUCTION_MCP_RESULTS.json').read_text(encoding='utf-8-sig'))
    products=json.loads((OUT/'PRODUCT_INTEGRATION_LIVE_RESULTS.json').read_text(encoding='utf-8-sig'))
    live=json.loads((OUT/'DEEP_LIVE_QUALIFICATION_RESULTS.json').read_text(encoding='utf-8-sig'))
    rdc=json.loads((OUT/'RDC_DUAL_PATH_FINAL_RESULTS.json').read_text(encoding='utf-8-sig'))
    agentrec=json.loads((OUT/'AGENT_RESTART_RECOVERY.json').read_text(encoding='utf-8-sig'))

    gatewayrec=json.loads((OUT/'GATEWAY_RESTART_RECOVERY.json').read_text(encoding='utf-8-sig'))
    gates={
      'core_regression':core['returncode']==0 and '8 passed' in core['stdout'],
      'compileall':comp['returncode']==0,
      'product_regressions':all(v['returncode']==0 for v in prod.values()),
      'artifact_hashes':all(x['ok'] for x in arts),
      'audit_chains':all(v['ok'] for v in audits.values()),
      'production_state':state['health'].get('ok') is True and state['api_version']=='0.2.1' and state['btg'].get('online') is True and state['btg'].get('agent_version')=='0.2.1',
      'api_security_26':trlsec.get('status')=='PASS' and trlsec.get('check_count')==26,
      'mcp_v2':mcp.get('status')=='PASS' and mcp.get('tool_count')==8,
      'rdc_dual_path':rdc.get('status')=='PASS',
      'product_live':products.get('status')=='PASS',
      'deep_live':live.get('status')=='PASS',
      'gateway_recovery':gatewayrec.get('status')=='PASS',
      'agent_recovery':agentrec.get('status')=='PASS',
      'documentation_support':all(p.exists() and p.stat().st_size>0 for p in support)}
    disposition='TRL9_CERTIFIED_PASS' if all(gates.values()) else 'TRL9_CERTIFICATION_FAIL'
    cert={'product':'Blackmore Engineering Control Plane','product_id':'BTG-PLAT-010','version':'0.2.1','technology_readiness_level':9 if disposition.endswith('PASS') else None,'disposition':disposition,'certification_scope':'BTG internal engineering TRL assessment; not third-party regulatory/accredited certification','operational_environment':'BTG Windows engineering workstation','issued_utc':datetime.now(timezone.utc).isoformat(),'gates':gates}
    wj(OUT/'TRL9_CERTIFICATE.json',cert)
    report=['# BECP 0.2.1 — BTG Internal TRL-9 Certification','','**Product ID:** BTG-PLAT-010','**Disposition:** '+disposition,'','This is an internal Blackmore Technology Group engineering readiness certification, not an external regulatory or accredited certification.','','## Final Gates']+[f'- {k}: {"PASS" if v else "FAIL"}' for k,v in gates.items()]
    (OUT/'TRL9_CERTIFICATE.md').write_text('\n'.join(report)+'\n',encoding='utf-8')

    files=[]
    for p in sorted(OUT.iterdir()):
        if p.is_file() and p.name not in {'TRL9_MANIFEST.json','TRL9_SEAL.json','TRL9_SEAL.sha256','TRL9_SEAL.hmac','VERIFY_TRL9_EVIDENCE.py'}:
            files.append({'name':p.name,'bytes':p.stat().st_size,'sha256':sha(p)})
    manifest={'product_id':'BTG-PLAT-010','version':'0.2.1','disposition':disposition,'generated_utc':datetime.now(timezone.utc).isoformat(),'files':files,'gates':gates}
    wj(OUT/'TRL9_MANIFEST.json',manifest)
    mbytes=(OUT/'TRL9_MANIFEST.json').read_bytes(); msha=hashlib.sha256(mbytes).hexdigest()
    key=QAKEY.read_bytes(); mh=hmac.new(key,mbytes,hashlib.sha256).hexdigest()
    (OUT/'TRL9_SEAL.sha256').write_text(msha+'  TRL9_MANIFEST.json\n',encoding='utf-8')
    (OUT/'TRL9_SEAL.hmac').write_text(mh+'  TRL9_MANIFEST.json\n',encoding='utf-8')
    wj(OUT/'TRL9_SEAL.json',{'manifest_sha256':msha,'manifest_hmac_sha256':mh,'algorithm':'HMAC-SHA256','key_location':'external runtime secret; not included in evidence package'})
    verifier="""import hashlib,hmac,json,sys\nfrom pathlib import Path\nout=Path(__file__).resolve().parent\nkey=Path(sys.argv[1]).read_bytes()\nm=(out/'TRL9_MANIFEST.json').read_bytes(); man=json.loads(m.decode('utf-8'))\nseal=json.loads((out/'TRL9_SEAL.json').read_text(encoding='utf-8'))\nerrs=[]\nif hashlib.sha256(m).hexdigest()!=seal['manifest_sha256']: errs.append('manifest sha256')\nif not hmac.compare_digest(hmac.new(key,m,hashlib.sha256).hexdigest(),seal['manifest_hmac_sha256']): errs.append('manifest hmac')\nfor f in man['files']:\n p=out/f['name']\n if not p.exists(): errs.append('missing '+f['name']); continue\n if p.stat().st_size!=f['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=f['sha256']: errs.append('hash '+f['name'])\nprint(json.dumps({'ok':not errs,'errors':errs},indent=2)); raise SystemExit(0 if not errs else 2)\n"""
    (OUT/'VERIFY_TRL9_EVIDENCE.py').write_text(verifier,encoding='utf-8')
    print(json.dumps({'disposition':disposition,'output':str(OUT),'manifest_sha256':msha,'manifest_hmac_sha256':mh,'gate_count':len(gates),'all_gates':all(gates.values())},indent=2))
    return 0 if disposition=='TRL9_CERTIFIED_PASS' else 2

if __name__=='__main__': raise SystemExit(main())
