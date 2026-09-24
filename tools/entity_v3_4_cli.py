from __future__ import annotations
import argparse, importlib.util, json, pathlib, sys

ROOT=pathlib.Path(__file__).resolve().parents[1]
def load(name,rel):
    spec=importlib.util.spec_from_file_location(name,ROOT/rel); mod=importlib.util.module_from_spec(spec)
    sys.modules[name]=mod; spec.loader.exec_module(mod); return mod

identity_mod=load("cli_v34_identity","src/01_Core_Runtime/identity/canonical_identity.py")
fabric_mod=load("cli_v34_fabric","src/30_Universal_Transaction_Fabric/canonical_universal_fabric.py")
rights_mod=load("cli_v34_rights","src/36_Adoption_Layer/rights_passport.py")
reality_profile=load("reality_profile","src/37_Verifiable_Reality/reality_profile.py")
evidence_mod=load("cli_v34_evidence","src/37_Verifiable_Reality/evidence_objects.py")
profile_mod=load("cli_v34_profiles","src/38_Global_Passports/profile_registry.py")
industry_mod=load("cli_v34_industry","src/38_Global_Passports/industry_profiles.py")
global_mod=load("cli_v34_global","src/38_Global_Passports/global_passport.py")
ingest_mod=load("cli_v34_ingest","src/38_Global_Passports/continuous_ingestion.py")
package_mod=load("cli_v34_packages","src/39_Implementation_Packages/industry_packages.py")
sdk_mod=load("cli_v34_sdk","sdk/global_passport_sdk/canonical_global_passport_sdk.py")

def runtime(state):
    identity=identity_mod.EntityIdentityVault(state); fabric=fabric_mod.UniversalTransactionFabric(state,identity)
    evidence=evidence_mod.EvidenceRegistry(state,identity); rights=rights_mod.RightsPassportRegistry(state,identity,fabric)
    profiles=profile_mod.GlobalProfileRegistry(state,identity); passports=global_mod.GlobalPassportRegistry(state,identity,fabric,rights,profiles)
    ingestion=ingest_mod.ContinuousProvenanceEngine(state,identity,fabric,evidence,rights,passports)
    packages=package_mod.IndustryImplementationPackageRegistry(); sdk=sdk_mod.EntityGlobalPassportSDK(profiles,passports,ingestion,packages)
    return identity,fabric,profiles,passports,packages,sdk
def read_json(path): return json.loads(pathlib.Path(path).read_text(encoding="utf-8-sig"))
def emit(value): print(json.dumps(value,indent=2,sort_keys=True))

def cmd_init(a):
    identity,_,profiles,_,_,_=runtime(a.state)
    controller=identity.create(a.name,"organization")["entity_id"]
    installed=industry_mod.install_builtin_profiles(profiles,controller)
    emit({"state":str(pathlib.Path(a.state).resolve()),"controller_entity_id":controller,
          "profiles":sorted(installed),"authority_must_be_configured_by_deployer":True})

def cmd_packages(a):
    *_,packages,_=runtime(a.state)
    emit({"packages":[packages.get(name) for name in packages.list_packages()]})

def cmd_plan(a):
    *_,packages,sdk=runtime(a.state)
    emit(sdk.package_plan(a.package,read_json(a.config),a.asset_kind))

def cmd_map(a):
    *_,sdk=runtime(a.state)
    emit(sdk.map_external(a.package,a.standard,read_json(a.input)))

def cmd_ingest(a):
    _,_,profiles,_,_,sdk=runtime(a.state)
    try: profiles.get("entity-profile:global@1.0")
    except KeyError: raise SystemExit("state has no installed v3.4 profiles; run init first")
    out=sdk.ingest_package_file(a.file,a.controller,a.package,read_json(a.config),a.asset_kind,
                                logical_path=a.logical_path,version=a.version)
    emit(out)

def cmd_verify(a):
    *_,sdk=runtime(a.state)
    emit(sdk.verify_passport(a.passport_id))
def parser():
    p=argparse.ArgumentParser(prog="entity-v3.4",description="ENTITY v3.4 Global Passport deployment CLI")
    p.add_argument("--state",required=True,help="ENTITY state directory")
    sub=p.add_subparsers(dest="command",required=True)
    x=sub.add_parser("init"); x.add_argument("--name",required=True); x.set_defaults(func=cmd_init)
    x=sub.add_parser("packages"); x.set_defaults(func=cmd_packages)
    x=sub.add_parser("plan"); x.add_argument("--package",required=True); x.add_argument("--config",required=True); x.add_argument("--asset-kind",required=True); x.set_defaults(func=cmd_plan)
    x=sub.add_parser("map"); x.add_argument("--package",required=True); x.add_argument("--standard",required=True); x.add_argument("--input",required=True); x.set_defaults(func=cmd_map)
    x=sub.add_parser("ingest"); x.add_argument("--controller",required=True); x.add_argument("--package",required=True); x.add_argument("--config",required=True)
    x.add_argument("--asset-kind",required=True); x.add_argument("--file",required=True); x.add_argument("--logical-path"); x.add_argument("--version",default="1.0"); x.set_defaults(func=cmd_ingest)
    x=sub.add_parser("verify"); x.add_argument("--passport-id",required=True); x.set_defaults(func=cmd_verify)
    return p

def main(argv=None):
    args=parser().parse_args(argv); args.func(args); return 0

if __name__=="__main__": raise SystemExit(main())
