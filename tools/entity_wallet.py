from __future__ import annotations
from pathlib import Path
import argparse, importlib.util, json, sys, webbrowser

def load_wallet(core:Path):
    path=core/"src"/"42_ENTITY_Wallet"/"canonical_wallet.py"
    spec=importlib.util.spec_from_file_location("entity_wallet_runtime",path)
    mod=importlib.util.module_from_spec(spec); sys.modules[spec.name]=mod; spec.loader.exec_module(mod)
    return mod

def main():
    ap=argparse.ArgumentParser(description="ENTITY economic wallet")
    ap.add_argument("--core",default=".")
    ap.add_argument("--state",required=True)
    ap.add_argument("--wallet-id",required=True)
    ap.add_argument("--treasury",action="store_true")
    ap.add_argument("--json-out")
    ap.add_argument("--html-out")
    ap.add_argument("--open",action="store_true")
    args=ap.parse_args()
    mod=load_wallet(Path(args.core).resolve())
    wallet=mod.EntityEconomicWallet(Path(args.state).resolve())
    snap=wallet.treasury_snapshot(args.wallet_id) if args.treasury else wallet.snapshot(args.wallet_id)
    if args.json_out:
        p=Path(args.json_out); p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps(snap,indent=2,sort_keys=True),encoding="utf-8")
    if args.html_out:
        p=Path(args.html_out); p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(mod.render_stock_style_html(snap),encoding="utf-8")
        if args.open: webbrowser.open(p.resolve().as_uri())
    if not args.json_out and not args.html_out:
        print(json.dumps(snap,indent=2,sort_keys=True))

if __name__=="__main__":
    main()
