from pathlib import Path
import hashlib,json
ROOT=Path(r'<LOCAL_DRIVE>/Sovereign_Entity_Network'); EV=ROOT/'16_Test_Qualification'/'evidence'/'ENTITY_ENGINEERING_REQUIREMENTS_CLOSURE_CURRENT.json'
TARGETS=['00_Governance','01_Core_Runtime','03_Public_Internet_Bridge','05_Entity_Nodes','06_Hosted_Sites','07_Hosted_Apps','11_ADAM','12_BSIE','13_Security','14_Protocols_SDK','15_Operations','16_Test_Qualification','17_Release','18_Research_Design','19_Sandbox','20_Archive']
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
facade="""from pathlib import Path\nimport importlib.util,sys\nROOT=Path(__file__).resolve().parents[1]\np=ROOT/'01_Core_Runtime'/'engineering_controls'/'canonical_engineering_controls.py'\ns=importlib.util.spec_from_file_location('entity_engineering_controls_shared',p); m=importlib.util.module_from_spec(s); sys.modules[s.name]=m; s.loader.exec_module(m)\nCanonicalEngineeringControlPlane=m.CanonicalEngineeringControlPlane\n"""
for top in TARGETS:
    folder=ROOT/top; req=folder/'ENTITY_REQUIREMENTS.md'; out=folder/'ENTITY_ENGINEERING_CLOSURE.py'; out.write_text(facade,encoding='utf-8')
    evidence=[{'path':'16_Test_Qualification/evidence/ENTITY_ENGINEERING_REQUIREMENTS_CLOSURE_CURRENT.json','sha256':sha(EV)}]
    binding={'schema':'entity-runtime-binding-v1','authority':'engineering_closure_'+top.lower(),'abi_version':'1','implementation_version':'2.2.0-engineering-closure','python_file':out.name,'exports':['CanonicalEngineeringControlPlane'],'implementation_sha256':sha(out),'requirements_sha256':sha(req),'qualification_evidence':evidence,'status':'READY'}
    (folder/'ENTITY_RUNTIME_BINDING.json').write_text(json.dumps(binding,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps({'published':len(TARGETS),'targets':TARGETS,'evidence_file_sha256':sha(EV)},indent=2))
