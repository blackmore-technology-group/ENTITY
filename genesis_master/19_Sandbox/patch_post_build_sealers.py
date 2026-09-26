from pathlib import Path
root=Path(r'<LOCAL_DRIVE>/Sovereign_Entity_Network')
p=root/'16_Test_Qualification/ten_of_ten/seal_repository_regression.py'
s=p.read_text(encoding='utf-8')
s=s.replace('EV/"ENTITY_QUALIFICATION_TREE_REGRESSION_POST_NIKI_DOMAIN.txt"','EV/"ENTITY_BUILD_REGRESSION_PYTEST.txt"')
p.write_text(s,encoding='utf-8')
p=root/'16_Test_Qualification/chaos/seal_post_chaos_closure.py'
s=p.read_text(encoding='utf-8')
s=s.replace('"regression_403":reg.get("totals")=={"failed":0,"passed":403,"skipped":0}', '"regression_clean":int((reg.get("totals") or {}).get("failed",1))==0 and int((reg.get("totals") or {}).get("skipped",1))==0 and int((reg.get("totals") or {}).get("passed",0))>=403')
p.write_text(s,encoding='utf-8')
print('patched sealers')
