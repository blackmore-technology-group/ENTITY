from __future__ import annotations
from pathlib import Path
import argparse, hashlib, importlib.util, json, sqlite3, sys

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod)
    return mod

def main():
    ap=argparse.ArgumentParser(description="Provision BTG ENTITY participant and treasury wallets")
    ap.add_argument("--core",default=".")
    ap.add_argument("--state",required=True)
    ap.add_argument("--btg-entity",required=True,help="Verified Blackmore Technology Group legal ENTITY ID")
    ap.add_argument("--treasury-entity",help="Existing distinct BTG Treasury ENTITY ID; creates one when omitted")
    ap.add_argument("--output-dir")
    args=ap.parse_args()
    core=Path(args.core).resolve(); state=Path(args.state).resolve()
    identity=load("wallet_identity",core/"src"/"01_Core_Runtime"/"identity"/"canonical_identity.py")
    econ=load("wallet_econ",core/"src"/"33_Economic_Participation"/"economic_participation.py")
    btg=load("wallet_btg",core/"src"/"33_Economic_Participation"/"btg_deployment.py")
    wallet_mod=load("wallet_runtime",core/"src"/"42_ENTITY_Wallet"/"canonical_wallet.py")

    vault=identity.EntityIdentityVault(state)
    legal=vault.load_manifest(args.btg_entity)
    if legal.get("display_name")!="Blackmore Technology Group Limited":
        raise SystemExit("Supplied legal ENTITY is not named Blackmore Technology Group Limited")

    treasury_manifest=None
    if args.treasury_entity:
        treasury_manifest=vault.load_manifest(args.treasury_entity)
    else:
        for p in sorted((state/"identity"/"manifests").glob("*.json")):
            try: candidate=json.loads(p.read_text(encoding="utf-8-sig"))
            except Exception: continue
            if candidate.get("display_name")=="Blackmore Technology Group ENTITY Treasury":
                treasury_manifest=vault.load_manifest(candidate["entity_id"]); break
        if treasury_manifest is None:
            treasury_manifest=vault.create(
                "Blackmore Technology Group ENTITY Treasury","business",
                aliases=["BTG ENTITY Treasury","BTG Treasury"],
                metadata={"role":"entity_economic_treasury","owner_entity_id":args.btg_entity,
                          "fiat_custody":"external_bank_or_payment_service",
                          "protocol_tax_bps":0,"cryptocurrency_required":False})

    treasury_entity=treasury_manifest["entity_id"]
    if treasury_entity==args.btg_entity:
        raise SystemExit("BTG Treasury ENTITY must be distinct from the BTG legal ENTITY")

    out=Path(args.output_dir).resolve() if args.output_dir else state/"wallet"
    out.mkdir(parents=True,exist_ok=True)
    policy={
      "schema":"entity-btg-treasury-wallet-governance-v1",
      "owner_entity_id":args.btg_entity,"treasury_entity_id":treasury_entity,
      "purpose":"Hold ENTITY rights reserves, receive contractual economic obligations, and present stock-style market positions.",
      "fiat_custody":{"model":"EXTERNAL_BANK_OR_PAYMENT_SERVICE","wallet_custodies_fiat":False,
                       "payment_credentials_stored_in_entity":False},
      "market_marking":{"last_settled_trade_only":True,"offers_are_not_value":True,
                        "bid_ask_are_quotes":True,"indicative_only":True,"not_accounting_fair_value":True},
      "stock_style_interface":{"enabled":True,"rights_are_not_declared_corporate_shares":True,
                               "legal_classification_not_inferred":True},
      "protocol_tax_bps":0,"cryptocurrency_required":False
    }
    policy_path=out/"BTG_TREASURY_WALLET_GOVERNANCE_POLICY.json"
    policy_path.write_text(json.dumps(policy,indent=2,sort_keys=True),encoding="utf-8")

    profile=econ.EconomicParticipationProfile(state,vault)
    with sqlite3.connect(profile.path) as db:
        db.row_factory=sqlite3.Row
        row=db.execute("""SELECT * FROM treasuries WHERE owner_entity_id=? AND treasury_entity_id=?
                          AND status='ACTIVE'""",(args.btg_entity,treasury_entity)).fetchone()
    treasury=btg.provision_btg_treasury(profile,args.btg_entity,treasury_entity,policy) if row is None else dict(row)

    wallet=wallet_mod.EntityEconomicWallet(state)
    participant=wallet.ensure_wallet(args.btg_entity,"BTG Participant Wallet",wallet_type="PARTICIPANT",
                                     config={"portfolio_role":"ISSUER_AND_PARTICIPANT"})
    treasury_wallet=wallet.ensure_wallet(treasury_entity,"BTG ENTITY Treasury Wallet",wallet_type="TREASURY",
                                         treasury_id=treasury["treasury_id"],
                                         config={"portfolio_role":"BTG_TREASURY"})
    ps=wallet.snapshot(participant["wallet_id"]); ts=wallet.treasury_snapshot(treasury_wallet["wallet_id"])
    (out/"BTG_PARTICIPANT_WALLET_SNAPSHOT.json").write_text(json.dumps(ps,indent=2,sort_keys=True),encoding="utf-8")
    (out/"BTG_TREASURY_WALLET_SNAPSHOT.json").write_text(json.dumps(ts,indent=2,sort_keys=True),encoding="utf-8")
    (out/"BTG_PARTICIPANT_WALLET.html").write_text(wallet_mod.render_stock_style_html(ps),encoding="utf-8")
    (out/"BTG_TREASURY_WALLET.html").write_text(wallet_mod.render_stock_style_html(ts),encoding="utf-8")

    receipt={"schema":"entity-v343-wallet-provision-receipt-v1","entity_display_version":"3.4.3",
             "wallet_version":"1.0.0","btg_legal_entity_id":args.btg_entity,
             "treasury_entity_id":treasury_entity,"treasury_id":treasury["treasury_id"],
             "participant_wallet_id":participant["wallet_id"],"treasury_wallet_id":treasury_wallet["wallet_id"],
             "fiat_custody":"EXTERNAL_BANK_OR_PAYMENT_SERVICE","wallet_custodies_fiat":False,
             "protocol_tax_bps":0,"cryptocurrency_required":False,
             "policy_sha256":hashlib.sha256(policy_path.read_bytes()).hexdigest()}
    (out/"ENTITY_V343_WALLET_PROVISION_RECEIPT.json").write_text(json.dumps(receipt,indent=2,sort_keys=True),encoding="utf-8")
    print(json.dumps(receipt,indent=2,sort_keys=True))

if __name__=="__main__":
    main()
