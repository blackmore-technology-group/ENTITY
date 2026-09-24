from __future__ import annotations
import importlib.util, json, pathlib, sys

ROOT=pathlib.Path(__file__).resolve().parents[1]
SRC=ROOT/"src/39_Implementation_Packages/industry_packages.py"
spec=importlib.util.spec_from_file_location("industry_packages",SRC)
mod=importlib.util.module_from_spec(spec); sys.modules["industry_packages"]=mod; spec.loader.exec_module(mod)
registry=mod.IndustryImplementationPackageRegistry()
out_root=ROOT/"profiles"; out_root.mkdir(parents=True,exist_ok=True)

def dump(path:pathlib.Path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n",encoding="utf-8")

def example_config(name:str)->dict:
    base={"organization":"Example Organization","jurisdiction":"CONFIGURE-ME","authority_source":"CONFIGURE-ME"}
    extra={"healthcare":{"privacy_policy":"CONFIGURE-ME"},"finance":{"settlement_policy":"CONFIGURE-ME"},
           "manufacturing":{"asset_namespace":"CONFIGURE-ME"},"ai":{"model_governance_policy":"CONFIGURE-ME"},
           "robotics":{"safety_policy":"CONFIGURE-ME"},"defence-public":{"release_policy":"PUBLIC-UNCLASSIFIED","classification":"UNCLASSIFIED"}}
    return dict(base,**extra[name])

index={"schema":"entity-v3-industry-package-registry-v1","version":"3.4.0","packages":[],
       "one_global_passport":True,"profiles_are_executable_implementation_assets":True}
for name in registry.list_packages():
    package=registry.get(name); target=out_root/name; target.mkdir(parents=True,exist_ok=True)
    dump(target/"package.json",package)
    dump(target/"mappings.json",{"package":name,"mappings":package["mappings"],"external_standards_are_mapped_not_redefined":True})
    templates={kind:registry.template(name,kind) for kind in package["object_types"]}
    dump(target/"templates.json",{"package":name,"templates":templates})
    cfg=example_config(name)
    sample_kind=next(iter(package["object_types"]))
    dump(target/"deployment.example.json",{"package":name,"configuration":cfg,"asset_kind":sample_kind,
         "note":"Replace CONFIGURE-ME values with organization-specific facts before deployment."})
    dump(target/"deployment.schema.json",{
        "$schema":"https://json-schema.org/draft/2020-12/schema","type":"object",
        "required":package["required_config"],"properties":{k:{"type":"string","minLength":1} for k in package["required_config"]},
        "additionalProperties":True,"x-entity-profile-is-not-regulatory-compliance":True})
    valid={"configuration":cfg,"asset_kind":sample_kind,"expected_valid":True}
    invalid={"configuration":{},"asset_kind":sample_kind,"expected_valid":False}
    dump(target/"conformance.json",{"schema":"entity-v3-industry-package-conformance-v1","valid":[valid],"invalid":[invalid],
         "profile_stack":package["profile_refs"],"core_semantics_changed":False})
    quick=f"""# ENTITY {name} Implementation Package

This package configures the one ENTITY Global Passport; it does not define a separate passport.

1. Copy `deployment.example.json` and replace every `CONFIGURE-ME` value.
2. Validate organization authority, jurisdiction and package-specific policy inputs.
3. Use `EntityGlobalPassportSDK.package_plan()` to resolve the executable profile stack.
4. Connect the source system and use `ingest_package_file()` for continuous provenance.
5. Verify the resulting Global Passport and run the package conformance vectors.

External standards are mappings only. ENTITY does not redefine them, and package validation does not establish regulatory compliance.
"""
    (target/"QUICKSTART.md").write_text(quick,encoding="utf-8")
    index["packages"].append({"name":name,"version":package["version"],"package_sha256":package["package_sha256"],"profile_refs":package["profile_refs"]})
dump(out_root/"registry.json",index)
print(json.dumps({"packages":len(index["packages"]),"names":[x["name"] for x in index["packages"]]},indent=2))

bundle={"schema":"entity-v3-4-implementation-package-bundle-v1","version":"3.4.0","registry":index,"packages":{},
        "one_global_passport":True,"profiles_are_executable_implementation_assets":True}
for name in registry.list_packages():
    target=out_root/name
    bundle["packages"][name]={}
    for filename in ["package.json","mappings.json","templates.json","deployment.example.json","deployment.schema.json","conformance.json"]:
        bundle["packages"][name][filename]=json.loads((target/filename).read_text(encoding="utf-8"))
    bundle["packages"][name]["QUICKSTART.md"]=(target/"QUICKSTART.md").read_text(encoding="utf-8")
dump(out_root/"ENTITY_V3_4_IMPLEMENTATION_PACKAGES.json",bundle)
