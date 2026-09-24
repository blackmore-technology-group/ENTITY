from __future__ import annotations
import hashlib, importlib.util, json, pathlib, sys

ROOT=pathlib.Path(__file__).resolve().parents[1]
REG=ROOT/"profiles/registry.json"; BUNDLE=ROOT/"profiles/ENTITY_V3_4_IMPLEMENTATION_PACKAGES.json"
SRC=ROOT/"src/39_Implementation_Packages/industry_packages.py"
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
spec=importlib.util.spec_from_file_location("pkg34_verify",SRC); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
runtime=mod.IndustryImplementationPackageRegistry(); reg=json.loads(REG.read_text(encoding="utf-8")); bundle=json.loads(BUNDLE.read_text(encoding="utf-8"))
errors=[]; expected_names=runtime.list_packages(); actual_names=[x["name"] for x in reg.get("packages",[])]
if actual_names!=expected_names: errors.append("package_names")
if bundle.get("schema")!="entity-v3-4-implementation-package-bundle-v1" or bundle.get("version")!="3.4.0": errors.append("bundle_schema")
if bundle.get("one_global_passport") is not True or bundle.get("profiles_are_executable_implementation_assets") is not True: errors.append("bundle_boundaries")
for row in reg.get("packages",[]):
    pkg=runtime.get(row["name"])
    if pkg["package_sha256"]!=row.get("package_sha256"): errors.append("package_hash:"+row["name"])
    if row["name"] not in bundle.get("packages",{}): errors.append("bundle_missing:"+row["name"])
result={"valid":not errors,"version":"3.4.0","packages":len(actual_names),"registry_sha256":sha(REG),"bundle_sha256":sha(BUNDLE),"errors":errors}
print(json.dumps(result,indent=2,sort_keys=True)); sys.exit(0 if not errors else 2)
