from __future__ import annotations
from pathlib import Path
import argparse, importlib.util, json, os, sqlite3, sys, uuid
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APP_NAME="ENTITY Wallet"

def repo_root()->Path:
    if getattr(sys,"frozen",False) and hasattr(sys,"_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[1]

def load_module(name:str,relative:str):
    path=repo_root()/relative
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise RuntimeError(f"Cannot load {path}")
    mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod)
    return mod

CLI=load_module("entity_wallet_v343_cli","tools/entity_v3_4_cli.py")
WALLET=load_module("entity_wallet_model","src/42_ENTITY_Wallet/canonical_wallet.py")
INGEST=load_module("entity_wallet_ingest","src/42_ENTITY_Wallet/asset_ingest.py")
EXCHANGE=load_module("entity_wallet_exchange","src/31_Profiles/exchange_protocol.py")

def default_state()->Path:
    env=os.environ.get("ENTITY_STATE_DIR")
    if env: return Path(env).expanduser()
    if sys.platform=="win32":
        return Path(os.environ.get("LOCALAPPDATA",Path.home()))/"Blackmore Technology Group"/"ENTITY"
    if sys.platform=="darwin":
        return Path.home()/"Library"/"Application Support"/"Blackmore Technology Group"/"ENTITY"
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
        self.identity_manifest=self.identity.load_manifest(entity_id)
        self.wallet=WALLET.EntityEconomicWallet(state)
        self.exchange=EXCHANGE.ExchangeProtocol(state,self.identity,self.fabric)
        self.ingestor=INGEST.WalletAssetIngestor(state,CLI)
        self.wallet_record=self.wallet.ensure_wallet(
            entity_id,self.identity_manifest.get("display_name","ENTITY")+" Wallet")

    def snapshot(self): return self.wallet.snapshot(self.wallet_record["wallet_id"])
    def domains(self): return ["general"]+self.packages.list_packages()
    def asset_kinds(self,domain): return self.ingestor.asset_kinds(domain)

    def market(self)->list[dict]:
        if not self.wallet.exchange_path.exists(): return []
        with sqlite3.connect(self.wallet.exchange_path) as db:
            db.row_factory=sqlite3.Row
            rows=db.execute("""SELECT i.instrument_id,i.instrument_class,i.settlement_currency,
                                      i.underlying_object_id,
                                      (SELECT ll.venue_id FROM listings ll
                                       WHERE ll.instrument_id=i.instrument_id AND ll.status='ACTIVE'
                                       ORDER BY ll.created_at_ms DESC LIMIT 1) venue_id
                               FROM instruments i WHERE i.status='ACTIVE'
                               ORDER BY i.instrument_id""").fetchall()
            out=[]
            for r in rows:
                d=dict(r); d["market"]=self.wallet._market(db,d["instrument_id"]); out.append(d)
            return out

    def ingest(self,path,options):
        return self.ingestor.ingest_file(
            self.entity_id,path,title=options["title"],package=options["domain"],
            asset_kind=options.get("asset_kind") or None,jurisdiction=options.get("jurisdiction",""),
            authority_basis=options["authority"],commodity_class=options["class"],
            measurement_unit=options["unit"],version=options.get("version") or "1.0",
            previous_object_id=options.get("parent_object_id") or None)

    def submit_order(self,row:dict,side:str,quantity:int,limit_price:int):
        venue=row.get("venue_id")
        if not venue: raise ValueError("This instrument has no active market listing.")
        order=self.exchange.submit_order(
            venue,row["instrument_id"],self.entity_id,side,quantity,limit_price,
            nonce="wallet-"+uuid.uuid4().hex,tif="GTC")
        trades=self.exchange.match_order_book(venue,row["instrument_id"])
        return {"order":order,"trades":trades}

class AssetDialog(tk.Toplevel):
    def __init__(self,parent,path:Path,backend:Backend):
        super().__init__(parent); self.title("Canonical ENTITY Asset Ingest"); self.resizable(False,False)
        self.result=None; self.backend=backend; self.transient(parent); self.grab_set()
        self.vars={
            "title":tk.StringVar(value=path.name),
            "domain":tk.StringVar(value="general"),
            "asset_kind":tk.StringVar(value=""),
            "jurisdiction":tk.StringVar(value=""),
            "class":tk.StringVar(value="DIGITAL_ASSET"),
            "unit":tk.StringVar(value="ASSET"),
            "authority":tk.StringVar(value=f"CONTROLLER_ENTITY:{backend.entity_id}"),
            "version":tk.StringVar(value="1.0"),
            "parent_object_id":tk.StringVar(value=""),
        }
        ttk.Label(self,text="File").grid(row=0,column=0,sticky="w",padx=12,pady=(12,4))
        ttk.Label(self,text=str(path),wraplength=560).grid(row=0,column=1,sticky="w",padx=12,pady=(12,4))
        ttk.Label(self,text="Domain profile").grid(row=1,column=0,sticky="w",padx=12,pady=5)
        self.domain=ttk.Combobox(self,textvariable=self.vars["domain"],values=backend.domains(),state="readonly",width=48)
        self.domain.grid(row=1,column=1,sticky="ew",padx=12,pady=5); self.domain.bind("<<ComboboxSelected>>",self._domain_changed)
        ttk.Label(self,text="Asset kind").grid(row=2,column=0,sticky="w",padx=12,pady=5)
        self.kind=ttk.Combobox(self,textvariable=self.vars["asset_kind"],values=[],width=48)
        self.kind.grid(row=2,column=1,sticky="ew",padx=12,pady=5)
        labels=[
            ("Title","title"),("Jurisdiction (domain assets)","jurisdiction"),
            ("Commodity class","class"),("Measurement unit","unit"),
            ("Authority basis","authority"),("Passport version","version"),
            ("Parent object ID (optional)","parent_object_id"),
        ]
        for i,(label,key) in enumerate(labels,3):
            ttk.Label(self,text=label).grid(row=i,column=0,sticky="w",padx=12,pady=5)
            ttk.Entry(self,textvariable=self.vars[key],width=50).grid(row=i,column=1,sticky="ew",padx=12,pady=5)
        self.attest=tk.BooleanVar(value=False)
        ttk.Checkbutton(self,text="I have authority to register this asset and attest its provenance.",
                        variable=self.attest).grid(row=10,column=0,columnspan=2,sticky="w",padx=12,pady=(10,4))
        ttk.Label(self,text="Ingest creates the governed DCO + evidence + rights passport + Global Passport + BTDU binding. It does not list or price the asset.",
                  wraplength=650).grid(row=11,column=0,columnspan=2,sticky="w",padx=12,pady=4)
        b=ttk.Frame(self); b.grid(row=12,column=0,columnspan=2,sticky="e",padx=12,pady=12)
        ttk.Button(b,text="Cancel",command=self.destroy).pack(side="right",padx=4)
        ttk.Button(b,text="Ingest Asset",command=self.ok).pack(side="right",padx=4)

    def _domain_changed(self,event=None):
        domain=self.vars["domain"].get()
        kinds=self.backend.asset_kinds(domain)
        self.kind["values"]=kinds
        self.vars["asset_kind"].set(kinds[0] if kinds else "")
        self.vars["class"].set("DIGITAL_ASSET" if domain=="general" else domain.upper().replace("-","_")+"_ASSET")

    def ok(self):
        if not self.attest.get():
            messagebox.showerror("Authority required","Confirm authority before registering the digital asset.",parent=self); return
        if not self.vars["title"].get().strip():
            messagebox.showerror("Title required","Enter an asset title.",parent=self); return
        domain=self.vars["domain"].get()
        if domain!="general" and not self.vars["jurisdiction"].get().strip():
            messagebox.showerror("Jurisdiction required","Domain package ingest requires an explicit jurisdiction.",parent=self); return
        if domain!="general" and not self.vars["asset_kind"].get().strip():
            messagebox.showerror("Asset kind required","Choose an asset kind for this domain.",parent=self); return
        self.result={k:v.get().strip() for k,v in self.vars.items()}; self.destroy()

class OrderDialog(tk.Toplevel):
    def __init__(self,parent,row,side):
        super().__init__(parent); self.title(f"{side.title()} {row['instrument_id']}"); self.resizable(False,False)
        self.result=None; self.transient(parent); self.grab_set(); m=row["market"]
        self.qty=tk.StringVar(value="1"); default=m.get("ask") if side=="BUY" else m.get("bid")
        self.price=tk.StringVar(value="" if default is None else str(default))
        ttk.Label(self,text=f"{side} {row['instrument_id']}").grid(row=0,column=0,columnspan=2,sticky="w",padx=12,pady=12)
        ttk.Label(self,text="Quantity").grid(row=1,column=0,sticky="w",padx=12,pady=5)
        ttk.Entry(self,textvariable=self.qty,width=22).grid(row=1,column=1,padx=12,pady=5)
        ttk.Label(self,text=f"Limit price ({row['settlement_currency']})").grid(row=2,column=0,sticky="w",padx=12,pady=5)
        ttk.Entry(self,textvariable=self.price,width=22).grid(row=2,column=1,padx=12,pady=5)
        ttk.Label(self,text=f"Bid: {m.get('bid')}   Ask: {m.get('ask')}   Last: {m.get('last')}").grid(row=3,column=0,columnspan=2,sticky="w",padx=12,pady=8)
        ttk.Button(self,text="Submit",command=self.ok).grid(row=4,column=1,sticky="e",padx=12,pady=12)
    def ok(self):
        try:
            q=int(self.qty.get()); p=int(self.price.get())
            if q<1 or p<0: raise ValueError
        except Exception:
            messagebox.showerror("Invalid order","Quantity must be positive and price must be a non-negative integer.",parent=self); return
        self.result=(q,p); self.destroy()

class App(tk.Tk):
    def __init__(self,state:Path|None=None,entity:str|None=None):
        super().__init__(); self.title(APP_NAME); self.geometry("1380x800"); self.minsize(1000,650)
        self.backend=None; self.market_rows=[]; self.asset_rows={}
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
        ttk.Label(top,text="Sovereign digital assets · canonical lineage · open rights market",style="Sub.TLabel").grid(row=1,column=0,sticky="w")
        ttk.Label(top,text="State").grid(row=0,column=1,padx=(30,5)); ttk.Entry(top,textvariable=self.state_var,width=45).grid(row=0,column=2,sticky="ew")
        ttk.Button(top,text="Browse",command=self.browse_state).grid(row=0,column=3,padx=4); ttk.Button(top,text="Load",command=self.load_state).grid(row=0,column=4,padx=4)
        ttk.Label(top,text="Identity").grid(row=1,column=1,padx=(30,5))
        self.entity_box=ttk.Combobox(top,textvariable=self.entity_var,state="readonly",width=42)
        self.entity_box.grid(row=1,column=2,sticky="ew"); self.entity_box.bind("<<ComboboxSelected>>",lambda e:self.activate())
        ttk.Button(top,text="Refresh",command=self.refresh).grid(row=1,column=3,padx=4); top.columnconfigure(2,weight=1)

        self.tabs=ttk.Notebook(self); self.tabs.pack(fill="both",expand=True,padx=12,pady=(0,12))
        self.assets_tab=ttk.Frame(self.tabs,padding=10); self.market_tab=ttk.Frame(self.tabs,padding=10)
        self.positions_tab=ttk.Frame(self.tabs,padding=10); self.orders_tab=ttk.Frame(self.tabs,padding=10)
        self.tabs.add(self.assets_tab,text="My Digital Assets"); self.tabs.add(self.market_tab,text="Market")
        self.tabs.add(self.positions_tab,text="Market Positions"); self.tabs.add(self.orders_tab,text="Orders")

        bar=ttk.Frame(self.assets_tab); bar.pack(fill="x",pady=(0,8))
        ttk.Button(bar,text="Upload / Ingest Digital Asset",command=self.ingest_asset).pack(side="left")
        ttk.Button(bar,text="View Lineage",command=self.view_lineage).pack(side="left",padx=4)
        ttk.Label(bar,text="Assets are separate from market instruments. Ingest never creates a price.",style="Sub.TLabel").pack(side="left",padx=12)
        self.assets=self._tree(self.assets_tab,["Title","Class","Type","Canonical lineage","Controller","Passport","BTDU","Object ID"],
                               [210,145,90,330,160,110,60,260])

        mbar=ttk.Frame(self.market_tab); mbar.pack(fill="x",pady=(0,8))
        ttk.Button(mbar,text="Buy",command=lambda:self.order("BUY")).pack(side="left")
        ttk.Button(mbar,text="Sell",command=lambda:self.order("SELL")).pack(side="left",padx=4)
        ttk.Label(mbar,text="Price/time matching uses existing EEP. Settlement evidence remains required.",style="Sub.TLabel").pack(side="left",padx=12)
        self.market=self._tree(self.market_tab,["Instrument","Class","Currency","Bid","Ask","Last","Venue"],[240,140,80,90,90,90,220])
        self.positions=self._tree(self.positions_tab,["Instrument","Units","Currency","Last","Bid","Ask","Indicative Value"],[260,90,80,90,90,90,140])
        self.orders=self._tree(self.orders_tab,["Instrument","Side","Remaining","Limit","Status"],[280,80,100,100,120])
        self.status=tk.StringVar(value="Ready"); ttk.Label(self,textvariable=self.status,relief="sunken",anchor="w",padding=5).pack(fill="x",side="bottom")

    def _tree(self,parent,columns,widths):
        f=ttk.Frame(parent); f.pack(fill="both",expand=True)
        t=ttk.Treeview(f,columns=columns,show="headings",selectmode="browse")
        for c,w in zip(columns,widths): t.heading(c,text=c); t.column(c,width=w,anchor="w")
        y=ttk.Scrollbar(f,orient="vertical",command=t.yview); t.configure(yscrollcommand=y.set)
        t.pack(side="left",fill="both",expand=True); y.pack(side="right",fill="y"); return t

    def browse_state(self):
        p=filedialog.askdirectory(title="Select ENTITY state folder",initialdir=self.state_var.get())
        if p: self.state_var.set(p); self.load_state()

    def load_state(self,preselect=None):
        state=Path(self.state_var.get()).expanduser(); state.mkdir(parents=True,exist_ok=True)
        items=manifests(state); self.entity_map={f"{x['display_name']} — {x['entity_id']}":x["entity_id"] for x in items}
        self.entity_box["values"]=list(self.entity_map)
        if preselect:
            for label,eid in self.entity_map.items():
                if eid==preselect: self.entity_var.set(label); break
        elif items and not self.entity_var.get(): self.entity_var.set(next(iter(self.entity_map)))
        if self.entity_var.get(): self.activate()
        else: self.status.set("No ENTITY identity found in this state folder.")

    def activate(self):
        try:
            eid=self.entity_map.get(self.entity_var.get(),self.entity_var.get())
            self.backend=Backend(Path(self.state_var.get()),eid); self.refresh()
        except Exception as e:
            self.backend=None; messagebox.showerror("Cannot load wallet",str(e)); self.status.set(str(e))

    @staticmethod
    def clear(tree):
        for x in tree.get_children(): tree.delete(x)

    def refresh(self):
        if not self.backend: return
        try:
            snap=self.backend.snapshot(); self.market_rows=self.backend.market(); self.asset_rows={}
            self.clear(self.assets)
            for a in snap.get("assets",[]):
                lin=a.get("lineage",{}); prot=lin.get("protocol_lineage",{}); al=lin.get("asset_lineage",{})
                gp=lin.get("global_passport") or {}; btdu=lin.get("capability_bindings",{}).get("BTDU",{}).get("bound",False)
                self.asset_rows[a["object_id"]]=a
                self.assets.insert("", "end",iid=a["object_id"],values=(
                    a["title"],a.get("commodity_class"),a.get("object_type"),prot.get("display_path") or "UNRESOLVED",
                    al.get("controller_name") or a["controller_entity_id"],
                    (gp.get("version") or "—"),"YES" if btdu else "NO",a["object_id"]))
            self.clear(self.positions)
            for p in snap.get("positions",[]):
                m=p["market"]; self.positions.insert("", "end",values=(p["instrument_id"],p["units"],p["settlement_currency"],
                    m.get("last"),m.get("bid"),m.get("ask"),p.get("market_value_amount_units")))
            self.clear(self.orders)
            for o in snap.get("orders",[]): self.orders.insert("", "end",values=(o["instrument_id"],o["side"],o["remaining"],o["limit_price"],o["status"]))
            self.clear(self.market)
            for i,row in enumerate(self.market_rows):
                m=row["market"]; self.market.insert("", "end",iid=str(i),values=(row["instrument_id"],row["instrument_class"],
                    row["settlement_currency"],m.get("bid"),m.get("ask"),m.get("last"),row.get("venue_id") or "UNLISTED"))
            self.status.set(f"{len(snap.get('assets',[]))} digital assets · {len(snap.get('positions',[]))} market positions · protocol tax 0 · crypto not required")
        except Exception as e:
            messagebox.showerror("Refresh failed",str(e)); self.status.set(str(e))

    def view_lineage(self):
        sel=self.assets.selection()
        if not sel: messagebox.showwarning("Lineage","Select a digital asset."); return
        a=self.asset_rows.get(sel[0]); lin=(a or {}).get("lineage",{})
        p=lin.get("protocol_lineage",{}); al=lin.get("asset_lineage",{}); cap=lin.get("capability_bindings",{}); gp=lin.get("global_passport") or {}
        parents="\n".join(f"  {x.get('relation')}: {x.get('title') or x.get('parent_object_id')}" for x in al.get("parents",[])) or "  None recorded"
        msg=(
            f"CANONICAL PROTOCOL / DOMAIN LINEAGE\n{p.get('display_path') or 'Unresolved'}\n\n"
            f"Passport: {gp.get('passport_id') or 'None'}  version {gp.get('version') or '—'}\n"
            f"Origin embedded in passport: {p.get('passport_protocol_origin_embedded')}\n"
            f"Needs lineage supersession: {p.get('needs_passport_lineage_supersession')}\n\n"
            f"ASSET PROVENANCE\nController: {al.get('controller_name')}\nParents:\n{parents}\n\n"
            f"SYSTEM BINDINGS\nBTDU bound: {cap.get('BTDU',{}).get('bound')}\n"
            f"ADAM: deterministic execution/evidence; not sovereign authority\n"
            f"NIKI: bounded reasoning/proposals; not sovereign authority\n\n"
            f"Protocol ancestry does not transfer ownership or create economic entitlement."
        )
        messagebox.showinfo("ENTITY Lineage",msg)

    def ingest_asset(self):
        if not self.backend: messagebox.showwarning("Wallet","Load an ENTITY identity first."); return
        f=filedialog.askopenfilename(title="Choose data or digital asset to ingest")
        if not f: return
        d=AssetDialog(self,Path(f),self.backend); self.wait_window(d)
        if not d.result: return
        try:
            r=self.backend.ingest(f,d.result); self.refresh()
            a=r["digital_asset"]; origin=r["protocol_origin"]; refs=r["profile_refs"]
            messagebox.showinfo("Canonical digital asset created",
                f"DCO: {a['object_id']}\n\nProfiles: {', '.join(refs)}\n"
                f"Origin: {origin['origin_lineage_id']} → {origin['release_ref']}\n"
                f"Global Passport verified: {r['global_passport_verified']}\nBTDU bound: {bool(r['btdu_binding'])}\n\n"
                "No market instrument, listing, or price was created.")
        except Exception as e: messagebox.showerror("Ingest failed",str(e))

    def order(self,side):
        if not self.backend: return
        sel=self.market.selection()
        if not sel: messagebox.showwarning("Market","Select a market instrument."); return
        row=self.market_rows[int(sel[0])]
        if not row.get("venue_id"): messagebox.showwarning("Market","This asset has no active market listing."); return
        d=OrderDialog(self,row,side); self.wait_window(d)
        if not d.result: return
        try:
            q,p=d.result; result=self.backend.submit_order(row,side,q,p); self.refresh()
            messagebox.showinfo("Order submitted",f"Order accepted.\nImmediate matches: {len(result['trades'])}\n\nPaid matches remain subject to settlement requirements.")
        except Exception as e: messagebox.showerror("Order failed",str(e))

def main():
    ap=argparse.ArgumentParser(description="Native ENTITY economic wallet")
    ap.add_argument("--state"); ap.add_argument("--entity")
    args=ap.parse_args(); App(Path(args.state) if args.state else None,args.entity).mainloop()

if __name__=="__main__": main()
