from pathlib import Path
import importlib.util,json,hashlib,time
P=Path(r'<LOCAL_DRIVE>/Sovereign_Entity_Network\16_Test_Qualification\ecosystem\integrate_btg_engineering_tools.py')
s=importlib.util.spec_from_file_location('eco',P); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
rows=[]
for name,(rel,alias) in m.SYSTEMS.items():
    print('START',name,flush=True)
    try:
        r=m.integrate(name,rel,alias); r['status']='PASS'; rows.append(r); print('PASS',name,len(r['registered_software_artifacts']),flush=True)
    except Exception as exc:
        rows.append({'product':name,'status':'FAIL','error':str(exc)}); print('FAIL',name,repr(exc),flush=True)
record={'schema':'btg-engineering-tools-entity-integration-qualification-v1','generated_at_ms':int(time.time()*1000),'products':rows,'passed':sum(x['status']=='PASS' for x in rows),'total':len(rows),'registration_not_ownership':True,'economic_value_not_inferred':True}
record['status']='PASS' if record['passed']==record['total'] else 'FAIL'; record['evidence_sha256']=hashlib.sha256(json.dumps(record,sort_keys=True,separators=(',',':')).encode()).hexdigest()
out=m.EVID/'BTG_ENGINEERING_TOOLS_ENTITY_INTEGRATION_CURRENT.json'; out.write_text(json.dumps(record,indent=2,sort_keys=True)+'\n',encoding='utf-8'); (m.EVID/(out.name+'.sha256')).write_text(m.sha(out)+'  '+out.name+'\n',encoding='utf-8')
print(json.dumps({'status':record['status'],'passed':record['passed'],'total':record['total'],'evidence_sha256':record['evidence_sha256']},indent=2),flush=True)
raise SystemExit(0 if record['status']=='PASS' else 2)
