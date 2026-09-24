from __future__ import annotations
import hashlib, importlib.util, json, pathlib, sys

ROOT=pathlib.Path(__file__).resolve().parents[1]
REG=ROOT/"profiles/registry.json"
SRC=ROOT/"src/39_Implementation_Packages/industry_packages.py"

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
spec=importlib.util.spec_from_file_location("pkg34_verify",SRC)
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
runtime=mod.IndustryImplementationPackageRegistry()
reg=json.loads(REG.read_text(encoding="utf-8"))
errors=[]
expected_names=runtime.list_packages()
actual_names=[x["name"] for x in reg.get("packages",[])]
if actual_names!=expected_names: errors.append("package_names")
if reg.get("schema")!="entity-v3-industry-package-registry-v1" or reg.get("version")!="3.4.0": errors.append("registry_schema")
if reg.get("one_global_passport") is not True or reg.get("profiles_are_executable_implementation_assets") is not True: errors.append("registry_boundaries")
package_hashes={}
for row in reg.get("packages",[]):
    pkg=runtime.get(row["name"]); package_hashes[row["name"]]=pkg["package_sha256"]
    if pkg["package_sha256"]!=row.get("package_sha256"): errors.append("package_hash:"+row["name"])
    if pkg.get("developer_configures_not_redesigns") is not True: errors.append("package_model:"+row["name"])
result={"valid":not errors,"version":"3.4.0","packages":len(actual_names),"registry_sha256":sha(REG),
        "package_sha256":package_hashes,"publication_model":"core registry plus six dedicated domain repositories","errors":errors}
print(json.dumps(result,indent=2,sort_keys=True)); sys.exit(0 if not errors else 2)
