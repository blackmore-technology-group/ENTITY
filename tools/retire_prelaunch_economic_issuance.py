from __future__ import annotations
from pathlib import Path
import argparse, importlib.util, json, sys

ROOT=Path(__file__).resolve().parents[1]

def load(name:str,path:Path):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise RuntimeError(f"cannot load {path}")
    mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod

IDENT=load("entity_prelaunch_identity",ROOT/"src"/"01_Core_Runtime"/"identity"/"canonical_identity.py")
MIG=load("entity_prelaunch_withdrawal",ROOT/"src"/"45_ENTITY_Market"/"prelaunch_withdrawal.py")

def main():
    ap=argparse.ArgumentParser(description="Audit or withdraw unused prelaunch ENTITY economic issuance without changing EEP 3.0.")
    ap.add_argument("--state",required=True,help="ENTITY state directory")
    ap.add_argument("--object-id",action="append",default=[],help="Underlying ENTITY object ID; repeatable")
    ap.add_argument("--dco-id",action="append",default=[],help="DCO Factory ID; repeatable")
    ap.add_argument("--reason",default="Superseded unused prelaunch economic experiment; asset remains active.")
    ap.add_argument("--apply",action="store_true",help="Apply withdrawal. Omit for fail-safe audit only.")
    args=ap.parse_args()
    state=Path(args.state).expanduser().resolve()
    vault=IDENT.EntityIdentityVault(state)
    migration=MIG.PrelaunchEconomicWithdrawal(state,vault)
    if args.apply:
        result=migration.apply(args.object_id,args.dco_id,args.reason)
    else:
        result=migration.audit(args.object_id,args.dco_id)
    print(json.dumps(result,indent=2,sort_keys=True,default=str))
    if not args.apply and not result.get("safe_to_withdraw",False):
        raise SystemExit(2)

if __name__=="__main__":
    main()
