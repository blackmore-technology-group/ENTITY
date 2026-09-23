from __future__ import annotations
import importlib.util, json, pathlib, sys, tempfile

REPO=pathlib.Path(__file__).resolve().parents[1]
IDENTITY=REPO/"src"/"01_Core_Runtime"/"identity"/"canonical_identity.py"
FABRIC=REPO/"src"/"30_Universal_Transaction_Fabric"/"canonical_universal_fabric.py"

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module

def main(argv):
    if len(argv)!=2:
        print("usage: verify_v3_bundle.py <bundle.json>",file=sys.stderr); return 2
    bundle=json.loads(pathlib.Path(argv[1]).read_text(encoding="utf-8"))
    identity_mod=load("entity_v3_portable_identity",IDENTITY)
    fabric_mod=load("entity_v3_portable_fabric",FABRIC)
    with tempfile.TemporaryDirectory() as tmp:
        identity=identity_mod.EntityIdentityVault(tmp)
        fabric=fabric_mod.UniversalTransactionFabric(tmp,identity)
        result=fabric.verify_bundle(bundle)
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0 if result.get("valid") else 1

if __name__=="__main__": raise SystemExit(main(sys.argv))
