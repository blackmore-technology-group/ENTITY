from pathlib import Path
p=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network\16_Test_Qualification\sovereign_domain\qualify_sovereign_domain.py")
s=p.read_text(encoding='utf-8')
old="""def vector(path,name,expected_valid,material,reason=None):
    write_json(path/f'{name}.json',{'schema':'entity-domain-test-vector-v1','name':name,
        'expected_valid':bool(expected_valid),'expected_reason':reason,'material':material})
"""
new="""def vector(path,name,expected_valid,material,reason=None,trust_material=None):
    record={'schema':'entity-domain-test-vector-v1','name':name,'expected_valid':bool(expected_valid),'expected_reason':reason,'material':material}
    if trust_material is not None: record['trust_material']=trust_material
    write_json(path/f'{name}.json',record)
"""
if old not in s: raise RuntimeError('vector function marker missing')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
print('vector function patched')
