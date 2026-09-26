from pathlib import Path
import json
ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
H01="6d91311bf117a6150a907d2000e5ccaac5ee6b1a13a3176580126ec936fdf586"; H04="243bf14e6c2b9ba0d8296cadac5af2635a39e761bc0efde6f66536234dfa07fa"; H15="73e494fac0e6b89c2952827fe17521a5cfa47f85386958fb541f63b4f74263c3"; H16="c36a04d05dab9bf862c6a77065c7d19f7ae88ba04d2897de2bec7d992074c5ac"
CU="e260c1a2a45e8efac189041045f1ed1dbf04223e1fb9d2bfcf4fada14cb382df"; CM="2d32d896e6652d1da02fd0cec80823a6e613498bc7575e2cde11663a2415fc6d"; ST="634dcef2f6895626c5754cc8532e1acef9e0e58e37b5611184ab304c2d5d0ef1"; IV="3754a8f64d114996f8f16c50f7ccd7db49fb0664c02bc52a2418146126571427"
def dump(path,obj): path.write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def binding(authority,version,py,exports,req,evidence):
    return {"schema":"entity-runtime-binding-v1","authority":authority,"status":"READY","abi_version":"1","implementation_version":version,"python_file":py,"exports":exports,"requirements_sha256":req,"qualification_evidence":[evidence]}

dump(ROOT/"01_Core_Runtime"/"contracts"/"ENTITY_RUNTIME_BINDING.json",binding("contracts","2.0.0-canonical","canonical_contracts.py",["ContractLicensingEngine"],H01,{"path":"16_Test_Qualification/evidence/ENTITY_CONTRACTS_USAGE_CURRENT.json","sha256":CU}))
dump(ROOT/"01_Core_Runtime"/"usage_control"/"ENTITY_RUNTIME_BINDING.json",binding("usage_control","2.0.0-canonical","canonical_usage_control.py",["UsageControlEngine"],H01,{"path":"16_Test_Qualification/evidence/ENTITY_CONTRACTS_USAGE_CURRENT.json","sha256":CU}))
dump(ROOT/"04_Entity_Registry"/"credentials"/"ENTITY_RUNTIME_BINDING.json",binding("credentials","1.0.0-canonical","canonical_credentials.py",["CredentialTrustStore"],H04,{"path":"16_Test_Qualification/evidence/ENTITY_CREDENTIALS_MIGRATION_CURRENT.json","sha256":CM}))
dump(ROOT/"15_Operations"/"migration"/"ENTITY_RUNTIME_BINDING.json",binding("migration_config","1.0.0-canonical","canonical_migration_config.py",["MigrationConfiguration"],H15,{"path":"16_Test_Qualification/evidence/ENTITY_CREDENTIALS_MIGRATION_CURRENT.json","sha256":CM}))
vault_path=ROOT/"08_Data_Vaults"/"ENTITY_RUNTIME_BINDING.json"; vault=json.loads(vault_path.read_text(encoding="utf-8"))
for name in ("data_sources","data_vault"): vault["authorities"][name]["qualification_evidence"]=[{"path":"16_Test_Qualification/evidence/ENTITY_PHASE1_STORAGE_PORTABILITY_CURRENT.json","sha256":ST}]
dump(vault_path,vault)
portable_path=ROOT/"15_Operations"/"backups"/"ENTITY_RUNTIME_BINDING.json"; portable=json.loads(portable_path.read_text(encoding="utf-8")); portable["qualification_evidence"]=[{"path":"16_Test_Qualification/evidence/ENTITY_PHASE1_STORAGE_PORTABILITY_CURRENT.json","sha256":ST}]; dump(portable_path,portable)
ver_path=ROOT/"16_Test_Qualification"/"verifier"/"ENTITY_RUNTIME_BINDING.json"; ver=json.loads(ver_path.read_text(encoding="utf-8")); ver["implementation_version"]="1.2.0-licence-usage"; ver["implementation_sha256"]="235c2a573e87f95679055616afa207240ad3b4936eea6d223622fefa00ed4e1f"; ver["qualification_evidence"][0]["sha256"]=IV
for symbol in ("verify_licence_record","verify_usage_receipt"):
    if symbol not in ver["exports"]: ver["exports"].append(symbol)
dump(ver_path,ver)
manifest_path=ROOT/"10_NIKI"/"ENTITY_PLATFORM_BINDINGS.json"; m=json.loads(manifest_path.read_text(encoding="utf-8"))
m["bindings"]["contracts"]["owner"]="01_Core_Runtime\\contracts"; m["bindings"]["credentials"]["owner"]="04_Entity_Registry\\credentials"
m["bindings"]["usage_control"]={"embedded":"blackmore_ci.controlled_access","owner":"01_Core_Runtime\\usage_control"}
m["bindings"]["migration_config"]={"embedded":"blackmore_ci.portable_state","owner":"15_Operations\\migration"}
dump(manifest_path,m); print("published phase1 bindings and authority mappings")
