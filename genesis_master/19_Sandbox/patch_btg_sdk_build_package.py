from pathlib import Path
root=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
p=root/"17_Release"/"builds"/"seal_build_manifest.py"; s=p.read_text(encoding="utf-8")
needle="post=ROOT/'16_Test_Qualification/evidence/ENTITY_POST_CHAOS_CLOSURE_CURRENT.json'\n"
if "ENTITY_BTG_APPLICATION_SDK_CURRENT.json" not in s:
    s=s.replace(needle,needle+"sdk=ROOT/'16_Test_Qualification/evidence/ENTITY_BTG_APPLICATION_SDK_CURRENT.json'\n",1)
    s=s.replace("(ready,gate,chaos,reg,post)","(ready,gate,chaos,reg,post,sdk)",1); p.write_text(s,encoding="utf-8")
p=root/"17_Release"/"builds"/"build_qualified_source_package.py"; s=p.read_text(encoding="utf-8")
needle2="    '16_Test_Qualification/evidence/ENTITY_ENGINEERING_REQUIREMENTS_CLOSURE_CURRENT.json']:\n"
if "ENTITY_BTG_APPLICATION_SDK_CURRENT.json" not in s:
    s=s.replace(needle2,"    '16_Test_Qualification/evidence/ENTITY_ENGINEERING_REQUIREMENTS_CLOSURE_CURRENT.json',\n    '16_Test_Qualification/evidence/ENTITY_BTG_APPLICATION_SDK_CURRENT.json']:\n",1); p.write_text(s,encoding="utf-8")
print('SDK evidence bound into build manifest/package')