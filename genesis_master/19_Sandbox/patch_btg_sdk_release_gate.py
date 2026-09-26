from pathlib import Path
root=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
rel=root/"17_Release"/"ten_of_ten"/"evaluate_release.py"
s=rel.read_text(encoding="utf-8")
needle='        "genesis_proof":"ENTITY_GENESIS_PROOF_CURRENT.json",\n'
insert=needle+'        "btg_application_sdk":"ENTITY_BTG_APPLICATION_SDK_CURRENT.json",\n'
if '"btg_application_sdk":"ENTITY_BTG_APPLICATION_SDK_CURRENT.json"' not in s:
    if needle not in s: raise SystemExit("release gate anchor missing")
    rel.write_text(s.replace(needle,insert,1),encoding="utf-8")
build=root/"17_Release"/"builds"/"evaluate_build_readiness.py"
b=build.read_text(encoding="utf-8")
needle2="    'engineering_requirements_closure':'ENTITY_ENGINEERING_REQUIREMENTS_CLOSURE_CURRENT.json','genesis_proof':'ENTITY_GENESIS_PROOF_CURRENT.json',\n"
insert2=needle2+"    'btg_application_sdk':'ENTITY_BTG_APPLICATION_SDK_CURRENT.json',\n"
if "'btg_application_sdk':'ENTITY_BTG_APPLICATION_SDK_CURRENT.json'" not in b:
    if needle2 not in b: raise SystemExit("build gate anchor missing")
    build.write_text(b.replace(needle2,insert2,1),encoding="utf-8")
print("BTG Application SDK added to release and build gates")