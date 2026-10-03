from __future__ import annotations
from pathlib import Path
import argparse, importlib.util, json, os, sqlite3, sys, uuid
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APP_NAME="ENTITY Wallet"

def repo_root()->Path:
    if getattr(sys,"frozen",False) and hasattr(sys,"_MEIPASS"): return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[1]

def load_module(name:str,relative:str):
    path=repo_root()/relative
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise RuntimeError(f"Cannot load {path}")
    mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod

CLI=load_module("entity_wallet_v343_cli","tools/entity_v3_4_cli.py")
WALLET=load_module("entity_wallet_model","src/42_ENTITY_Wallet/canonical_wallet.py")
INGEST=load_module("entity_wallet_ingest","src/42_ENTITY_Wallet/asset_ingest.py")
EXCHANGE=load_module("entity_wallet_exchange","src/31_Profiles/exchange_protocol.py")
MARKET=load_module("entity_wallet_market","src/45_ENTITY_Market/canonical_market_registry.py")
INTEL=load_module("entity_wallet_intelligence","src/45_ENTITY_Market/economic_intelligence.py")

def default_state()->Path:
    env=os.environ.get("ENTITY_STATE_DIR")
    if env: return Path(env).expanduser()
    if sys.platform=="win32": return Path(os.environ.get("LOCALAPPDATA",Path.home()))/"Blackmore Technology Group"/"ENTITY"
    if sys.platform=="darwin": return Path.home()/"Library"/"Application Support"/"Blackmore Technology Group"/"ENTITY"
    return Path.home()/".local"/"share"/"blackmore-technology-group"/"entity"

def manifests(state:Path)->list[dict]:
    out=[]; root=state/"identity"/"manifests"
    if not root.is_dir(): return out
    for p in sorted(root.glob("*.json")):
        try:
            d=json.loads(p.read_text(encoding="utf-8"))
            out.append({"entity_id":d.get("entity_id"),"display_name":d.get("display_name") or d.get("entity_id")})
        except Exception: pass
    return [x for x in out if x["entity_id"]]

class Backend:
    def __init__(self,state:Path,entity_id:str):
        self.state=state; self.entity_id=entity_id
        identity,fabric,profiles,origin,passports,packages,sdk,origin_status=CLI.runtime(state)
        self.identity=identity; self.fabric=fabric; self.profiles=profiles; self.origin=origin
        self.passports=passports; self.packages=packages; self.sdk=sdk; self.origin_status=origin_status
        self.rights=self.sdk.ingestion.rights
        self.identity_manifest=self.identity.load_manifest(entity_id)
        self.wallet=WALLET.EntityEconomicWallet(state)
        self.exchange=EXCHANGE.ExchangeProtocol(state,self.identity,self.fabric)
        self.market_registry=MARKET.EntityEconomicMarketRegistry(
            state,self.identity,self.fabric,self.exchange,self.rights,self.passports)
        self.intelligence=INTEL.EntityEconomicIntelligence(
            state,self.market_registry,self.fabric,self.passports)
        self.ingestor=INGEST.WalletAssetIngestor(state,CLI)
        self.wallet_record=self.wallet.ensure_wallet(entity_id,self.identity_manifest.get("display_name","ENTITY")+" Wallet")

    def snapshot(self): return self.wallet.snapshot(self.wallet_record["wallet_id"])
    def domains(self): return ["general"]+self.packages.list_packages()
    def asset_kinds(self,domain): return self.ingestor.asset_kinds(domain)

    def latest_global_passport(self,object_id:str)->dict:
        dbp=self.state/"entity_v3_4_global_passports.sqlite"
        db=sqlite3.connect(dbp); db.row_factory=sqlite3.Row
        try:
            row=db.execute("""SELECT passport_id FROM global_passports WHERE object_id=?
                              ORDER BY created_at_ms DESC,passport_id DESC LIMIT 1""",(str(object_id),)).fetchone()
        finally: db.close()
        if not row: raise KeyError("asset has no Global Passport")
        return self.passports.get(row["passport_id"])

    def instruments(self)->list[dict]:
        if not self.market_registry.path.exists(): return []
        db=sqlite3.connect(self.market_registry.path); db.row_factory=sqlite3.Row
        try:
            rows=db.execute("""SELECT * FROM instrument_packages
                               WHERE issuer_entity_id=? AND status='ACTIVE'
                               ORDER BY created_at_ms,instrument_id""",(self.entity_id,)).fetchall()
        finally: db.close()
        return [self.market_registry.instrument(r["instrument_id"]) for r in rows]

    def venues(self)->list[dict]:
        if not self.exchange.path.exists(): return []
        db=sqlite3.connect(self.exchange.path); db.row_factory=sqlite3.Row
        try: rows=db.execute("SELECT venue_id,name,jurisdiction,status FROM venues WHERE status='ACTIVE' ORDER BY name").fetchall()
        finally: db.close()
        return [dict(r) for r in rows]

    def market(self)->list[dict]:
        rows=self.market_registry.active_market()
        if not rows: return []
        db=sqlite3.connect(self.exchange.path); db.row_factory=sqlite3.Row
        try:
            out=[]
            for row in rows:
                e=db.execute("SELECT settlement_currency FROM instruments WHERE instrument_id=? AND status='ACTIVE'",
                             (row["instrument_id"],)).fetchone()
                if not e: continue
                d=dict(row); d["settlement_currency"]=e["settlement_currency"]
                d["market"]=self.wallet._market(db,d["instrument_id"])
                d["intelligence"]=self.intelligence.instrument_metrics(d["instrument_id"])
                out.append(d)
            return out
        finally: db.close()

    def economy_rollup(self,group_by:str):
        return self.intelligence.economy_rollup(group_by=group_by)

    def rights_demand(self,dco_id:str):
        return self.intelligence.dco_rights_demand(dco_id)

    def ingest(self,path,options):
        return self.ingestor.ingest_file(
            self.entity_id,path,title=options["title"],package=options["domain"],
            asset_kind=options.get("asset_kind") or None,jurisdiction=options.get("jurisdiction",""),
            authority_basis=options["authority"],commodity_class=options["class"],
            measurement_unit=options["unit"],version=options.get("version") or "1.0",
            previous_object_id=options.get("parent_object_id") or None)

    def create_instrument(self,object_id:str,options:dict)->dict:
        gp=self.latest_global_passport(object_id)
        return self.market_registry.create_instrument(
            self.entity_id,object_id,instrument_name=options["name"],display_symbol=options["symbol"],
            instrument_class=options["instrument_class"],rights_class=options["rights_class"],
            rights={"actions":options["actions"]},supply=options["supply"],
            rights_passport_id=gp["rights_passport_id"],global_passport_id=gp["passport_id"],
            settlement_currency=options["currency"],jurisdiction=options["jurisdiction"],
            series=options["series"],fungibility=options["fungibility"],divisibility=options["divisibility"],
            transferable=options["transferable"],duration_ms=options.get("duration_ms"),
            transfer_rules={"wallet_defined":True},economic_terms={"market_value_created_by_issuance":False},
            royalty_terms={"automatic_protocol_royalty_bps":0},
            buyer_receives=options["buyer_receives"],buyer_does_not_receive=options["buyer_does_not_receive"],
            evidence_refs=gp.get("evidence_refs") or [],namespace=options.get("namespace") or None)

    def create_listing(self,instrument_id:str,options:dict)->dict:
        return self.market_registry.create_listing(
            self.entity_id,instrument_id,options["venue_id"],market_id=options["market_id"],
            quote_unit=options["quote_unit"],trade_mode=options["trade_mode"],
            settlement_method=options["settlement_method"],minimum_quantity=options["minimum_quantity"],
            quantity_precision=options["quantity_precision"],price_precision=options["price_precision"],
            pricing_method=options["pricing_method"],listing_series=options["listing_series"],
            tick_size=options["tick_size"])

    def submit_order(self,row:dict,side:str,quantity:int,limit_price:int):
        venue=row.get("venue_id")
        if not venue: raise ValueError("This instrument has no active market listing.")
        order=self.exchange.submit_order(venue,row["instrument_id"],self.entity_id,side,quantity,limit_price,
                                         nonce="wallet-"+uuid.uuid4().hex,tif="GTC")
        return {"order":order,"trades":self.exchange.match_order_book(venue,row["instrument_id"])}

class AssetDialog(tk.Toplevel):
    def __init__(self,parent,path:Path,backend:Backend):
        super().__init__(parent); self.title("Canonical ENTITY Asset Ingest"); self.resizable(False,False)
        self.result=None; self.backend=backend; self.transient(parent); self.grab_set()
        self.vars={k:tk.StringVar(value=v) for k,v in {
            "title":path.name,"domain":"general","asset_kind":"","jurisdiction":"","class":"DIGITAL_ASSET",
            "unit":"ASSET","authority":f"CONTROLLER_ENTITY:{backend.entity_id}","version":"1.0","parent_object_id":""}.items()}
        ttk.Label(self,text="File").grid(row=0,column=0,sticky="w",padx=12,pady=(12,4))
        ttk.Label(self,text=str(path),wraplength=560).grid(row=0,column=1,sticky="w",padx=12,pady=(12,4))
        ttk.Label(self,text="Domain profile").grid(row=1,column=0,sticky="w",padx=12,pady=5)
        self.domain=ttk.Combobox(self,textvariable=self.vars["domain"],values=backend.domains(),state="readonly",width=48)
        self.domain.grid(row=1,column=1,sticky="ew",padx=12,pady=5); self.domain.bind("<<ComboboxSelected>>",self._domain_changed)
        ttk.Label(self,text="Asset kind").grid(row=2,column=0,sticky="w",padx=12,pady=5)
        self.kind=ttk.Combobox(self,textvariable=self.vars["asset_kind"],values=[],width=48); self.kind.grid(row=2,column=1,sticky="ew",padx=12,pady=5)
        labels=[("Title","title"),("Jurisdiction (domain assets)","jurisdiction"),("Commodity class","class"),
                ("Measurement unit","unit"),("Authority basis","authority"),("Passport version","version"),
                ("Parent object ID (optional)","parent_object_id")]
        for i,(label,key) in enumerate(labels,3):
            ttk.Label(self,text=label).grid(row=i,column=0,sticky="w",padx=12,pady=5)
            ttk.Entry(self,textvariable=self.vars[key],width=50).grid(row=i,column=1,sticky="ew",padx=12,pady=5)
        self.attest=tk.BooleanVar(value=False)
        ttk.Checkbutton(self,text="I have authority to register this asset and attest its provenance.",variable=self.attest).grid(row=10,column=0,columnspan=2,sticky="w",padx=12,pady=(10,4))
        ttk.Label(self,text="Creates DCO + evidence + Rights Passport + Global Passport + BTDU binding. It does not create an instrument, listing, or price.",wraplength=650).grid(row=11,column=0,columnspan=2,sticky="w",padx=12,pady=4)
        b=ttk.Frame(self); b.grid(row=12,column=0,columnspan=2,sticky="e",padx=12,pady=12)
        ttk.Button(b,text="Cancel",command=self.destroy).pack(side="right",padx=4); ttk.Button(b,text="Ingest Asset",command=self.ok).pack(side="right",padx=4)
    def _domain_changed(self,event=None):
        domain=self.vars["domain"].get(); kinds=self.backend.asset_kinds(domain); self.kind["values"]=kinds
        self.vars["asset_kind"].set(kinds[0] if kinds else "")
        self.vars["class"].set("DIGITAL_ASSET" if domain=="general" else domain.upper().replace("-","_")+"_ASSET")
    def ok(self):
        if not self.attest.get(): messagebox.showerror("Authority required","Confirm authority before registering the digital asset.",parent=self); return
        if not self.vars["title"].get().strip(): messagebox.showerror("Title required","Enter an asset title.",parent=self); return
        domain=self.vars["domain"].get()
        if domain!="general" and not self.vars["jurisdiction"].get().strip(): messagebox.showerror("Jurisdiction required","Domain package ingest requires an explicit jurisdiction.",parent=self); return
        if domain!="general" and not self.vars["asset_kind"].get().strip(): messagebox.showerror("Asset kind required","Choose an asset kind for this domain.",parent=self); return
        self.result={k:v.get().strip() for k,v in self.vars.items()}; self.destroy()

class InstrumentDialog(tk.Toplevel):
    def __init__(self,parent,asset:dict):
        super().__init__(parent); self.title("Create Economic Instrument"); self.resizable(False,False)
        self.result=None; self.transient(parent); self.grab_set()
        short=(asset.get("title") or "ASSET").upper().replace(" ","")[:12]
        self.vars={k:tk.StringVar(value=v) for k,v in {
            "name":f"{asset.get('title')} Commercial Rights","symbol":(short+"-COM")[:24],"namespace":"",
            "instrument_class":"SPOT_LICENSE","rights_class":"COMMERCIAL","actions":"COMMERCIALIZE",
            "supply":"1","currency":"CAD","jurisdiction":"CA","series":"1","fungibility":"FUNGIBLE",
            "divisibility":"0","duration_ms":"","buyer_receives":"defined commercial-use right",
            "buyer_does_not_receive":"ownership of the underlying DCO,copyright ownership,rights not stated in the Rights Passport"}.items()}
        fields=[("Instrument name","name"),("Display symbol","symbol"),("Issuer namespace (optional)","namespace"),
                ("EEP instrument class","instrument_class"),("Rights class","rights_class"),("Rights actions (comma separated)","actions"),
                ("Supply","supply"),("Settlement currency","currency"),("Jurisdiction","jurisdiction"),("Series","series"),
                ("Fungibility","fungibility"),("Divisibility precision","divisibility"),("Duration ms (optional)","duration_ms"),
                ("Buyer receives (comma separated)","buyer_receives"),("Buyer does NOT receive","buyer_does_not_receive")]
        for i,(label,key) in enumerate(fields):
            ttk.Label(self,text=label).grid(row=i,column=0,sticky="w",padx=12,pady=4)
            if key=="instrument_class":
                w=ttk.Combobox(self,textvariable=self.vars[key],state="readonly",
                    values=["SPOT_LICENSE","SUBSCRIPTION","COMPUTE_TO_DATA","PROCUREMENT","CONTRIBUTION","SECONDARY_LICENSE"],width=50)
            else: w=ttk.Entry(self,textvariable=self.vars[key],width=54)
            w.grid(row=i,column=1,sticky="ew",padx=12,pady=4)
        self.transferable=tk.BooleanVar(value=False)
        ttk.Checkbutton(self,text="Transferable / secondary sale allowed",variable=self.transferable).grid(row=len(fields),column=0,columnspan=2,sticky="w",padx=12,pady=8)
        ttk.Label(self,text="Instrument creation issues rights units but does not list them or establish market value.",wraplength=650).grid(row=len(fields)+1,column=0,columnspan=2,sticky="w",padx=12,pady=4)
        b=ttk.Frame(self); b.grid(row=len(fields)+2,column=0,columnspan=2,sticky="e",padx=12,pady=12)
        ttk.Button(b,text="Cancel",command=self.destroy).pack(side="right",padx=4); ttk.Button(b,text="Create Instrument",command=self.ok).pack(side="right",padx=4)
    def ok(self):
        try:
            supply=int(self.vars["supply"].get()); series=int(self.vars["series"].get()); div=int(self.vars["divisibility"].get())
            duration=int(self.vars["duration_ms"].get()) if self.vars["duration_ms"].get().strip() else None
            if supply<1 or series<1 or div<0: raise ValueError
        except Exception:
            messagebox.showerror("Invalid instrument","Supply/series must be positive integers and divisibility non-negative.",parent=self); return
        self.result={k:v.get().strip() for k,v in self.vars.items()}
        self.result.update({"supply":supply,"series":series,"divisibility":div,"duration_ms":duration,
                            "transferable":self.transferable.get(),
                            "actions":[x.strip().upper() for x in self.vars["actions"].get().split(",") if x.strip()],
                            "buyer_receives":[x.strip() for x in self.vars["buyer_receives"].get().split(",") if x.strip()],
                            "buyer_does_not_receive":[x.strip() for x in self.vars["buyer_does_not_receive"].get().split(",") if x.strip()]})
        self.destroy()

class ListingDialog(tk.Toplevel):
    def __init__(self,parent,backend:Backend,instrument:dict):
        super().__init__(parent); self.title("Create Listing"); self.resizable(False,False)
        self.result=None; self.backend=backend; self.transient(parent); self.grab_set()
        venues=backend.venues(); self.venue_map={f"{v['name']} — {v['venue_id']}":v["venue_id"] for v in venues}
        self.vars={k:tk.StringVar(value=v) for k,v in {
            "venue":next(iter(self.venue_map),""),
            "market_id":"ENTITY-MARKET","quote_unit":"CAD","trade_mode":"ORDER_BOOK",
            "settlement_method":"PAYMENT_VERSUS_RIGHT","minimum_quantity":"1","quantity_precision":"0",
            "price_precision":"0","pricing_method":"ORDER_BOOK","listing_series":"1","tick_size":"1"}.items()}
        fields=[("Venue","venue"),("Market ID","market_id"),("Quote unit","quote_unit"),("Trade mode","trade_mode"),
                ("Settlement method","settlement_method"),("Minimum quantity","minimum_quantity"),
                ("Quantity precision","quantity_precision"),("Price precision","price_precision"),
                ("Pricing method","pricing_method"),("Listing series","listing_series"),("Tick size","tick_size")]
        for i,(label,key) in enumerate(fields):
            ttk.Label(self,text=label).grid(row=i,column=0,sticky="w",padx=12,pady=5)
            if key=="venue": w=ttk.Combobox(self,textvariable=self.vars[key],values=list(self.venue_map),state="readonly",width=54)
            else: w=ttk.Entry(self,textvariable=self.vars[key],width=56)
            w.grid(row=i,column=1,sticky="ew",padx=12,pady=5)
        ttk.Label(self,text=f"Listing {instrument['market_identifier']} creates a required Listing Information Sheet and machine manifest.",wraplength=650).grid(row=len(fields),column=0,columnspan=2,sticky="w",padx=12,pady=6)
        b=ttk.Frame(self); b.grid(row=len(fields)+1,column=0,columnspan=2,sticky="e",padx=12,pady=12)
        ttk.Button(b,text="Cancel",command=self.destroy).pack(side="right",padx=4); ttk.Button(b,text="Create Listing",command=self.ok).pack(side="right",padx=4)
    def ok(self):
        if not self.venue_map: messagebox.showerror("No venue","No active ENTITY-compatible venue exists.",parent=self); return
        try:
            ints={k:int(self.vars[k].get()) for k in ("minimum_quantity","quantity_precision","price_precision","listing_series","tick_size")}
            if ints["minimum_quantity"]<1 or ints["listing_series"]<1 or ints["tick_size"]<1: raise ValueError
        except Exception:
            messagebox.showerror("Invalid listing","Listing quantities/series/tick must be valid integers.",parent=self); return
        self.result={k:v.get().strip() for k,v in self.vars.items()}
        self.result["venue_id"]=self.venue_map[self.result.pop("venue")]; self.result.update(ints); self.destroy()

class OrderDialog(tk.Toplevel):
    def __init__(self,parent,row,side):
        super().__init__(parent); self.title(f"{side.title()} {row.get('market_identifier') or row['instrument_id']}"); self.resizable(False,False)
        self.result=None; self.transient(parent); self.grab_set(); m=row["market"]
        self.qty=tk.StringVar(value="1"); default=m.get("ask") if side=="BUY" else m.get("bid")
        self.price=tk.StringVar(value="" if default is None else str(default))
        ttk.Label(self,text=f"{side} {row.get('market_identifier') or row['instrument_id']}").grid(row=0,column=0,columnspan=2,sticky="w",padx=12,pady=12)
        ttk.Label(self,text="Quantity").grid(row=1,column=0,sticky="w",padx=12,pady=5); ttk.Entry(self,textvariable=self.qty,width=22).grid(row=1,column=1,padx=12,pady=5)
        ttk.Label(self,text=f"Limit price ({row['settlement_currency']})").grid(row=2,column=0,sticky="w",padx=12,pady=5); ttk.Entry(self,textvariable=self.price,width=22).grid(row=2,column=1,padx=12,pady=5)
        ttk.Label(self,text=f"Bid: {m.get('bid')}   Ask: {m.get('ask')}   Last: {m.get('last')}").grid(row=3,column=0,columnspan=2,sticky="w",padx=12,pady=8)
        ttk.Button(self,text="Submit",command=self.ok).grid(row=4,column=1,sticky="e",padx=12,pady=12)
    def ok(self):
        try:
            q=int(self.qty.get()); p=int(self.price.get())
            if q<1 or p<0: raise ValueError
        except Exception: messagebox.showerror("Invalid order","Quantity must be positive and price non-negative.",parent=self); return
        self.result=(q,p); self.destroy()

class App(tk.Tk):
    def __init__(self,state:Path|None=None,entity:str|None=None):
        super().__init__(); self.title(APP_NAME); self.geometry("1450x820"); self.minsize(1050,680)
        self.backend=None; self.market_rows=[]; self.asset_rows={}; self.instrument_rows={}
        self.state_var=tk.StringVar(value=str(state or default_state())); self.entity_var=tk.StringVar(); self.entity_map={}
        self._style(); self._layout(); self.load_state(preselect=entity)

    def _style(self):
        style=ttk.Style(self)
        if sys.platform=="win32":
            try: style.theme_use("vista")
            except Exception: pass
        style.configure("Title.TLabel",font=("Segoe UI",18,"bold")); style.configure("Sub.TLabel",foreground="#666")

    def _layout(self):
        top=ttk.Frame(self,padding=12); top.pack(fill="x")
        ttk.Label(top,text="ENTITY Wallet",style="Title.TLabel").grid(row=0,column=0,sticky="w")
        ttk.Label(top,text="Sovereign digital assets · universal multi-issuer market · wallet-to-wallet rights",style="Sub.TLabel").grid(row=1,column=0,sticky="w")
        ttk.Label(top,text="State").grid(row=0,column=1,padx=(30,5)); ttk.Entry(top,textvariable=self.state_var,width=45).grid(row=0,column=2,sticky="ew")
        ttk.Button(top,text="Browse",command=self.browse_state).grid(row=0,column=3,padx=4); ttk.Button(top,text="Load",command=self.load_state).grid(row=0,column=4,padx=4)
        ttk.Label(top,text="Identity").grid(row=1,column=1,padx=(30,5))
        self.entity_box=ttk.Combobox(top,textvariable=self.entity_var,state="readonly",width=42); self.entity_box.grid(row=1,column=2,sticky="ew")
        self.entity_box.bind("<<ComboboxSelected>>",lambda e:self.activate()); ttk.Button(top,text="Refresh",command=self.refresh).grid(row=1,column=3,padx=4); top.columnconfigure(2,weight=1)

        self.tabs=ttk.Notebook(self); self.tabs.pack(fill="both",expand=True,padx=12,pady=(0,12))
        self.assets_tab=ttk.Frame(self.tabs,padding=10); self.instruments_tab=ttk.Frame(self.tabs,padding=10)
        self.market_tab=ttk.Frame(self.tabs,padding=10); self.intel_tab=ttk.Frame(self.tabs,padding=10)
        self.positions_tab=ttk.Frame(self.tabs,padding=10); self.orders_tab=ttk.Frame(self.tabs,padding=10)
        self.tabs.add(self.assets_tab,text="My Digital Assets"); self.tabs.add(self.instruments_tab,text="My Instruments")
        self.tabs.add(self.market_tab,text="ENTITY Market"); self.tabs.add(self.intel_tab,text="Data Value Discovery")
        self.tabs.add(self.positions_tab,text="Market Positions"); self.tabs.add(self.orders_tab,text="Orders")

        bar=ttk.Frame(self.assets_tab); bar.pack(fill="x",pady=(0,8))
        ttk.Button(bar,text="Upload / Ingest Digital Asset",command=self.ingest_asset).pack(side="left")
        ttk.Button(bar,text="View Lineage",command=self.view_lineage).pack(side="left",padx=4)
        ttk.Button(bar,text="Create Economic Instrument",command=self.create_instrument).pack(side="left",padx=4)
        ttk.Button(bar,text="Rights Demand",command=self.view_rights_demand).pack(side="left",padx=4)
        ttk.Label(bar,text="Asset creation never auto-issues or prices rights.",style="Sub.TLabel").pack(side="left",padx=12)
        self.assets=self._tree(self.assets_tab,["Title","Class","Type","Canonical lineage","Controller","Passport","BTDU","Object ID"],[210,145,90,330,160,100,55,250])

        ibar=ttk.Frame(self.instruments_tab); ibar.pack(fill="x",pady=(0,8))
        ttk.Button(ibar,text="Create Listing",command=self.create_listing).pack(side="left")
        ttk.Label(ibar,text="Canonical instruments are issuer-neutral; namespace:symbol is a display alias only.",style="Sub.TLabel").pack(side="left",padx=12)
        self.instruments=self._tree(self.instruments_tab,["Market ID","Instrument Name","Rights Class","Class","Supply","DCO","Status"],[170,310,130,130,80,300,90])

        mbar=ttk.Frame(self.market_tab); mbar.pack(fill="x",pady=(0,8))
        ttk.Button(mbar,text="Buy",command=lambda:self.order("BUY")).pack(side="left")
        ttk.Button(mbar,text="Sell",command=lambda:self.order("SELL")).pack(side="left",padx=4)
        ttk.Button(mbar,text="Listing Information",command=self.view_listing).pack(side="left",padx=4)
        ttk.Button(mbar,text="Market Intelligence",command=self.view_market_intelligence).pack(side="left",padx=4)
        ttk.Button(mbar,text="Export Portable Package",command=self.export_listing).pack(side="left",padx=4)
        ttk.Label(mbar,text="One canonical instrument can be published/listed on multiple venues.",style="Sub.TLabel").pack(side="left",padx=12)
        self.market=self._tree(self.market_tab,["Market ID","Instrument Name","Rights","Currency","Last","24h Vol","30d Vol","30d Buyers","Holders","Integrity","Venue"],
                               [155,245,105,70,75,85,85,85,70,180,200])

        ib=ttk.Frame(self.intel_tab); ib.pack(fill="x",pady=(0,8))
        self.rollup_dimension=tk.StringVar(value="asset_class")
        ttk.Label(ib,text="Roll up settled market activity by").pack(side="left")
        self.rollup_box=ttk.Combobox(ib,textvariable=self.rollup_dimension,state="readonly",width=22,
            values=["asset_class","asset_subtype","primary_domain","rights_class","issuer_entity_id","underlying_dco_id"])
        self.rollup_box.pack(side="left",padx=6); self.rollup_box.bind("<<ComboboxSelected>>",lambda e:self.refresh_intelligence())
        ttk.Button(ib,text="Refresh",command=self.refresh_intelligence).pack(side="left")
        ttk.Label(ib,text="Notional remains separated by currency.",style="Sub.TLabel").pack(side="left",padx=12)
        self.rollups=self._tree(self.intel_tab,["Group","Instruments","30d Trades","30d Units","30d Notional by Currency","Buyer Count*"],
                                [260,95,95,105,300,110])

        self.positions=self._tree(self.positions_tab,["Instrument","Units","Currency","Last","Bid","Ask","Indicative Value"],[320,90,80,90,90,90,140])
        self.orders=self._tree(self.orders_tab,["Instrument","Side","Remaining","Limit","Status"],[340,80,100,100,120])
        self.status=tk.StringVar(value="Ready"); ttk.Label(self,textvariable=self.status,relief="sunken",anchor="w",padding=5).pack(fill="x",side="bottom")

    def _tree(self,parent,columns,widths):
        f=ttk.Frame(parent); f.pack(fill="both",expand=True); t=ttk.Treeview(f,columns=columns,show="headings",selectmode="browse")
        for c,w in zip(columns,widths): t.heading(c,text=c); t.column(c,width=w,anchor="w")
        y=ttk.Scrollbar(f,orient="vertical",command=t.yview); t.configure(yscrollcommand=y.set)
        t.pack(side="left",fill="both",expand=True); y.pack(side="right",fill="y"); return t

    def browse_state(self):
        p=filedialog.askdirectory(title="Select ENTITY state folder",initialdir=self.state_var.get())
        if p: self.state_var.set(p); self.load_state()
    def load_state(self,preselect=None):
        state=Path(self.state_var.get()).expanduser(); state.mkdir(parents=True,exist_ok=True)
        items=manifests(state); self.entity_map={f"{x['display_name']} — {x['entity_id']}":x["entity_id"] for x in items}; self.entity_box["values"]=list(self.entity_map)
        if preselect:
            for label,eid in self.entity_map.items():
                if eid==preselect: self.entity_var.set(label); break
        elif items and not self.entity_var.get(): self.entity_var.set(next(iter(self.entity_map)))
        if self.entity_var.get(): self.activate()
        else: self.status.set("No ENTITY identity found in this state folder.")
    def activate(self):
        try:
            eid=self.entity_map.get(self.entity_var.get(),self.entity_var.get()); self.backend=Backend(Path(self.state_var.get()),eid); self.refresh()
        except Exception as e:
            self.backend=None; messagebox.showerror("Cannot load wallet",str(e)); self.status.set(str(e))
    @staticmethod
    def clear(tree):
        for x in tree.get_children(): tree.delete(x)

    def refresh(self):
        if not self.backend: return
        try:
            snap=self.backend.snapshot(); self.market_rows=self.backend.market(); instruments=self.backend.instruments()
            self.asset_rows={}; self.instrument_rows={}
            self.clear(self.assets)
            for a in snap.get("assets",[]):
                lin=a.get("lineage",{}); prot=lin.get("protocol_lineage",{}); al=lin.get("asset_lineage",{})
                gp=lin.get("global_passport") or {}; btdu=lin.get("capability_bindings",{}).get("BTDU",{}).get("bound",False)
                self.asset_rows[a["object_id"]]=a; self.assets.insert("", "end",iid=a["object_id"],values=(
                    a["title"],a.get("commodity_class"),a.get("object_type"),prot.get("display_path") or "UNRESOLVED",
                    al.get("controller_name") or a["controller_entity_id"],gp.get("version") or "—","YES" if btdu else "NO",a["object_id"]))
            self.clear(self.instruments)
            for x in instruments:
                self.instrument_rows[x["instrument_id"]]=x; self.instruments.insert("", "end",iid=x["instrument_id"],values=(
                    x["market_identifier"],x["instrument_name"],x["rights_class"],x["instrument_class"],x["supply"],x["underlying_dco_id"],x["status"]))
            self.clear(self.positions)
            for p in snap.get("positions",[]):
                m=p["market"]; self.positions.insert("", "end",values=(p["instrument_id"],p["units"],p["settlement_currency"],m.get("last"),m.get("bid"),m.get("ask"),p.get("market_value_amount_units")))
            self.clear(self.orders)
            for o in snap.get("orders",[]): self.orders.insert("", "end",values=(o["instrument_id"],o["side"],o["remaining"],o["limit_price"],o["status"]))
            self.clear(self.market)
            for i,row in enumerate(self.market_rows):
                intel=row.get("intelligence") or {}; w24=intel.get("window_24h") or {}; w30=intel.get("window_30d") or {}
                flags=(intel.get("market_integrity") or {}).get("flags") or []
                self.market.insert("", "end",iid=str(i),values=(
                    row["market_identifier"],row["instrument_name"],row["rights_class"],row["settlement_currency"],
                    intel.get("last_settled_price"),w24.get("volume_units"),w30.get("volume_units"),w30.get("unique_buyers"),
                    intel.get("active_holder_count"),", ".join(flags) if flags else "CLEAR",row["venue_id"]))
            self.refresh_intelligence()
            self.status.set(f"{len(snap.get('assets',[]))} assets · {len(instruments)} issued instruments · {len(self.market_rows)} active listings · protocol tax 0 · crypto not required")
        except Exception as e:
            messagebox.showerror("Refresh failed",str(e)); self.status.set(str(e))

    def refresh_intelligence(self):
        if not self.backend: return
        try:
            roll=self.backend.economy_rollup(self.rollup_dimension.get())
            self.clear(self.rollups)
            for row in roll.get("rows",[]):
                notional=", ".join(f"{cur} {amt:,}" for cur,amt in sorted(row.get("notional_30d_by_currency",{}).items())) or "—"
                self.rollups.insert("", "end",values=(row["group"],row["instrument_count"],row["settled_trades_30d"],
                    row["volume_units_30d"],notional,row["sum_instrument_unique_buyers_30d"]))
        except Exception as e:
            self.status.set("Economic intelligence: "+str(e))

    def view_market_intelligence(self):
        row=self._selected_market_row()
        if not row: messagebox.showwarning("Market Intelligence","Select a market listing."); return
        try:
            m=row.get("intelligence") or self.backend.intelligence.instrument_metrics(row["instrument_id"])
            w24=m["window_24h"]; w30=m["window_30d"]; roy=m["royalties_and_participation"]
            rpaid=", ".join(f"{k} {v:,}" for k,v in sorted(roy["externally_verified_amounts_by_currency"].items())) or "None verified"
            flags="\n".join("• "+x for x in m["market_integrity"]["flags"]) or "• No current integrity flags"
            messagebox.showinfo("ENTITY Market Intelligence",
                f"{m['market_identifier']}\n{m['instrument_name']}\n\n"
                f"Last settled price: {m['last_settled_price']} {m['settlement_currency']}\n"
                f"Last externally verified price: {m['last_externally_verified_price']} {m['settlement_currency']}\n\n"
                f"24h settled volume: {w24['volume_units']:,} units / {w24['notional_amount_units']:,} {m['settlement_currency']}\n"
                f"30d settled volume: {w30['volume_units']:,} units / {w30['notional_amount_units']:,} {m['settlement_currency']}\n"
                f"30d high / low: {w30['high_price']} / {w30['low_price']}\n30d trades: {w30['trade_count']:,}\n"
                f"Unique buyers: {w30['unique_buyers']:,}\nActive holders: {m['active_holder_count']:,}\n"
                f"Open sell offers: {m['open_sell_offer_units']:,} units\nExternally verified royalties/participation: {rpaid}\n\n"
                f"MARKET INTEGRITY\n{flags}\n\n"
                "These observations value the traded rights under their terms; they do not prove intrinsic or accounting value of the underlying DCO.")
        except Exception as e: messagebox.showerror("Market Intelligence",str(e))

    def view_rights_demand(self):
        if not self.backend: return
        sel=self.assets.selection()
        if not sel: messagebox.showwarning("Rights Demand","Select a digital asset."); return
        try:
            report=self.backend.rights_demand(sel[0]); lines=[]
            for rights,row in report.get("rights_class_rollup",{}).items():
                notion=", ".join(f"{cur} {amt:,}" for cur,amt in sorted(row["notional_30d_by_currency"].items())) or "—"
                lines.append(f"{rights}: {row['volume_units_30d']:,} units · {row['settled_trades']:,} trades · {notion}")
            messagebox.showinfo("DCO Rights Demand","\n".join(lines) if lines else "No active economic instruments or settled demand for this DCO yet.")
        except Exception as e: messagebox.showerror("Rights Demand",str(e))

    def view_lineage(self):
        sel=self.assets.selection()
        if not sel: messagebox.showwarning("Lineage","Select a digital asset."); return
        a=self.asset_rows.get(sel[0]); lin=(a or {}).get("lineage",{}); p=lin.get("protocol_lineage",{}); al=lin.get("asset_lineage",{}); cap=lin.get("capability_bindings",{}); gp=lin.get("global_passport") or {}
        parents="\n".join(f"  {x.get('relation')}: {x.get('title') or x.get('parent_object_id')}" for x in al.get("parents",[])) or "  None recorded"
        messagebox.showinfo("ENTITY Lineage",f"CANONICAL PROTOCOL / DOMAIN LINEAGE\n{p.get('display_path') or 'Unresolved'}\nAssociated profiles: {', '.join(p.get('associated_profiles') or []) or 'None'}\n\nPassport: {gp.get('passport_id') or 'None'}  version {gp.get('version') or '—'}\nOrigin embedded: {p.get('passport_protocol_origin_embedded')}\n\nASSET PROVENANCE\nController: {al.get('controller_name')}\nParents:\n{parents}\n\nSYSTEM BINDINGS\nBTDU bound: {cap.get('BTDU',{}).get('bound')}\nADAM: deterministic execution/evidence; not ownership\nNIKI: bounded reasoning; not ownership\n\nProtocol ancestry does not transfer ownership or create economic entitlement.")

    def ingest_asset(self):
        if not self.backend: return
        f=filedialog.askopenfilename(title="Choose data or digital asset to ingest")
        if not f: return
        d=AssetDialog(self,Path(f),self.backend); self.wait_window(d)
        if not d.result: return
        try:
            r=self.backend.ingest(f,d.result); self.refresh(); a=r["digital_asset"]; origin=r["protocol_origin"]
            messagebox.showinfo("Canonical digital asset created",f"DCO: {a['object_id']}\nOrigin: {origin['origin_lineage_id']} → {origin['release_ref']}\nGlobal Passport verified: {r['global_passport_verified']}\nBTDU bound: {bool(r['btdu_binding'])}\n\nNo instrument, listing, or price was created.")
        except Exception as e: messagebox.showerror("Ingest failed",str(e))

    def create_instrument(self):
        if not self.backend: return
        sel=self.assets.selection()
        if not sel: messagebox.showwarning("Instrument","Select a controlled digital asset first."); return
        asset=self.asset_rows[sel[0]]; d=InstrumentDialog(self,asset); self.wait_window(d)
        if not d.result: return
        try:
            result=self.backend.create_instrument(asset["object_id"],d.result); self.refresh()
            messagebox.showinfo("Instrument created",f"{result['market_identifier']}\n\nCanonical ID:\n{result['instrument_id']}\n\nNot listed. No market value was created.")
        except Exception as e: messagebox.showerror("Instrument creation failed",str(e))

    def create_listing(self):
        if not self.backend: return
        sel=self.instruments.selection()
        if not sel: messagebox.showwarning("Listing","Select one of your instruments."); return
        instrument=self.instrument_rows[sel[0]]; d=ListingDialog(self,self.backend,instrument); self.wait_window(d)
        if not d.result: return
        try:
            result=self.backend.create_listing(instrument["instrument_id"],d.result); self.refresh()
            messagebox.showinfo("Listing created",f"{instrument['market_identifier']} is listed.\n\nListing ID:\n{result['listing_id']}\n\nRequired Listing Information Sheet and machine manifest were bound by hash.")
        except Exception as e: messagebox.showerror("Listing creation failed",str(e))

    def _selected_market_row(self):
        sel=self.market.selection()
        if not sel: return None
        return self.market_rows[int(sel[0])]

    def view_listing(self):
        row=self._selected_market_row()
        if not row: messagebox.showwarning("Listing Information","Select a market listing."); return
        try:
            listing=self.backend.market_registry.listing(row["listing_id"]); info=listing["information"]
            receives="\n".join("• "+x for x in info["buyer_receives"]) or "• See Rights Passport"
            excludes="\n".join("• "+x for x in info["buyer_does_not_receive"]) or "• No unstated rights"
            messagebox.showinfo("Listing Information",f"WHAT IS THIS?\n\n{info['what_is_this']}\n\nIssuer: {info['issuer']}\nMarket ID: {info['market_identifier']}\nUnderlying DCO: {info['underlying_dco_id']}\n\nBUYER RECEIVES\n{receives}\n\nBUYER DOES NOT RECEIVE\n{excludes}\n\nSupply: {info['supply']}\nJurisdiction: {info['jurisdiction']}\nPricing: {info['pricing_method']}\nRights Passport: {info['rights_passport_id']}\nGlobal Passport: {info['global_passport_id']}\n\nInstrument: {info['instrument_id']}\nListing: {info['listing_id']}")
        except Exception as e: messagebox.showerror("Listing Information",str(e))

    def export_listing(self):
        row=self._selected_market_row()
        if not row: messagebox.showwarning("Portable package","Select a market listing."); return
        dest=filedialog.askdirectory(title="Choose folder for portable ENTITY instrument package")
        if not dest: return
        try:
            instrument=self.backend.market_registry.instrument(row["instrument_id"])
            folder=Path(dest)/(instrument["market_identifier"].replace(":","-")+".entity-instrument")
            result=self.backend.market_registry.export_portable_package(row["listing_id"],folder)
            messagebox.showinfo("Portable package created",f"{result['market_identifier']}\n\n{result['destination']}\n\nIncludes PDF, Markdown, JSON passports/manifests, verification and SHA256SUMS.")
        except Exception as e: messagebox.showerror("Portable package",str(e))

    def order(self,side):
        if not self.backend: return
        row=self._selected_market_row()
        if not row: messagebox.showwarning("Market","Select a market instrument."); return
        d=OrderDialog(self,row,side); self.wait_window(d)
        if not d.result: return
        try:
            q,p=d.result; result=self.backend.submit_order(row,side,q,p); self.refresh()
            messagebox.showinfo("Order submitted",f"Order accepted.\nImmediate matches: {len(result['trades'])}\n\nMatched trades remain subject to clearing and settlement requirements.")
        except Exception as e: messagebox.showerror("Order failed",str(e))

def main():
    ap=argparse.ArgumentParser(description="Native ENTITY economic wallet")
    ap.add_argument("--state"); ap.add_argument("--entity")
    args=ap.parse_args(); App(Path(args.state) if args.state else None,args.entity).mainloop()

if __name__=="__main__": main()
