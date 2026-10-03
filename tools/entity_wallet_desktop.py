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

IDENTITY=load_module("entity_wallet_identity","src/01_Core_Runtime/identity/canonical_identity.py")
FABRIC=load_module("entity_wallet_fabric","src/30_Universal_Transaction_Fabric/canonical_universal_fabric.py")
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
    out=[]
    root=state/"identity"/"manifests"
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
        self.identity=IDENTITY.EntityIdentityVault(state)
        self.identity.load_manifest(entity_id)
        self.fabric=FABRIC.UniversalTransactionFabric(state,self.identity)
        self.wallet=WALLET.EntityEconomicWallet(state)
        self.exchange=EXCHANGE.ExchangeProtocol(state,self.identity,self.fabric)
        self.ingestor=INGEST.WalletAssetIngestor(state,self.fabric)
        manifest=self.identity.load_manifest(entity_id)
        self.wallet_record=self.wallet.ensure_wallet(entity_id,manifest.get("display_name","ENTITY")+" Wallet")

    def snapshot(self): return self.wallet.snapshot(self.wallet_record["wallet_id"])

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

    def ingest(self,path,title,commodity_class,measurement_unit,authority_basis):
        return self.ingestor.ingest_file(
            self.entity_id,path,title=title,commodity_class=commodity_class,
            measurement_unit=measurement_unit,authority_basis=authority_basis,
            copy_to_local_vault=True)

    def submit_order(self,row:dict,side:str,quantity:int,limit_price:int):
        venue=row.get("venue_id")
        if not venue: raise ValueError("This instrument has no active market listing.")
        order=self.exchange.submit_order(
            venue,row["instrument_id"],self.entity_id,side,quantity,limit_price,
            nonce="wallet-"+uuid.uuid4().hex,tif="GTC")
        trades=self.exchange.match_order_book(venue,row["instrument_id"])
        return {"order":order,"trades":trades}

class AssetDialog(tk.Toplevel):
    def __init__(self,parent,path:Path):
        super().__init__(parent); self.title("Ingest Digital Asset"); self.resizable(False,False)
        self.result=None; self.transient(parent); self.grab_set()
        self.vars={
            "title":tk.StringVar(value=path.name),
            "class":tk.StringVar(value="DATA"),
            "unit":tk.StringVar(value="USE"),
            "authority":tk.StringVar(value="CREATOR_CONTROLLED"),
        }
        ttk.Label(self,text="File").grid(row=0,column=0,sticky="w",padx=12,pady=(12,4))
        ttk.Label(self,text=str(path),wraplength=520).grid(row=0,column=1,sticky="w",padx=12,pady=(12,4))
        labels=[("Title","title"),("Commodity class","class"),("Measurement unit","unit"),("Authority basis","authority")]
        for i,(label,key) in enumerate(labels,1):
            ttk.Label(self,text=label).grid(row=i,column=0,sticky="w",padx=12,pady=5)
            ttk.Entry(self,textvariable=self.vars[key],width=48).grid(row=i,column=1,sticky="ew",padx=12,pady=5)
        self.attest=tk.BooleanVar(value=False)
        ttk.Checkbutton(self,text="I have authority to register this asset and its provenance.",
                        variable=self.attest).grid(row=5,column=0,columnspan=2,sticky="w",padx=12,pady=10)
        b=ttk.Frame(self); b.grid(row=6,column=0,columnspan=2,sticky="e",padx=12,pady=12)
        ttk.Button(b,text="Cancel",command=self.destroy).pack(side="right",padx=4)
        ttk.Button(b,text="Ingest Asset",command=self.ok).pack(side="right",padx=4)

    def ok(self):
        if not self.attest.get():
            messagebox.showerror("Authority required","Confirm authority before registering the digital asset.",parent=self); return
        if not self.vars["title"].get().strip():
            messagebox.showerror("Title required","Enter an asset title.",parent=self); return
        self.result={k:v.get().strip() for k,v in self.vars.items()}; self.destroy()

class OrderDialog(tk.Toplevel):
    def __init__(self,parent,row,side):
        super().__init__(parent); self.title(f"{side.title()} {row['instrument_id']}"); self.resizable(False,False)
        self.result=None; self.transient(parent); self.grab_set(); m=row["market"]
        self.qty=tk.StringVar(value="1")
        default=m.get("ask") if side=="BUY" else m.get("bid")
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
        super().__init__(); self.title(APP_NAME); self.geometry("1180x760"); self.minsize(920,620)
        self.backend=None; self.market_rows=[]
        self.state_var=tk.StringVar(value=str(state or default_state()))
        self.entity_var=tk.StringVar()
        self.entity_map={}
        self._style(); self._layout()
        self.load_state(preselect=entity)

    def _style(self):
        style=ttk.Style(self)
        if sys.platform=="win32":
            try: style.theme_use("vista")
            except Exception: pass
        style.configure("Title.TLabel",font=("Segoe UI",18,"bold"))
        style.configure("Sub.TLabel",foreground="#666")

    def _layout(self):
        top=ttk.Frame(self,padding=12); top.pack(fill="x")
        ttk.Label(top,text="ENTITY Wallet",style="Title.TLabel").grid(row=0,column=0,sticky="w")
        ttk.Label(top,text="Digital assets first. Markets optional.",style="Sub.TLabel").grid(row=1,column=0,sticky="w")
        ttk.Label(top,text="State").grid(row=0,column=1,padx=(30,5))
        ttk.Entry(top,textvariable=self.state_var,width=45).grid(row=0,column=2,sticky="ew")
        ttk.Button(top,text="Browse",command=self.browse_state).grid(row=0,column=3,padx=4)
        ttk.Button(top,text="Load",command=self.load_state).grid(row=0,column=4,padx=4)
        ttk.Label(top,text="Identity").grid(row=1,column=1,padx=(30,5))
        self.entity_box=ttk.Combobox(top,textvariable=self.entity_var,state="readonly",width=42)
        self.entity_box.grid(row=1,column=2,sticky="ew"); self.entity_box.bind("<<ComboboxSelected>>",lambda e:self.activate())
        ttk.Button(top,text="Refresh",command=self.refresh).grid(row=1,column=3,padx=4)
        top.columnconfigure(2,weight=1)

        self.tabs=ttk.Notebook(self); self.tabs.pack(fill="both",expand=True,padx=12,pady=(0,12))
        self.assets_tab=ttk.Frame(self.tabs,padding=10); self.market_tab=ttk.Frame(self.tabs,padding=10)
        self.positions_tab=ttk.Frame(self.tabs,padding=10); self.orders_tab=ttk.Frame(self.tabs,padding=10)
        self.tabs.add(self.assets_tab,text="My Digital Assets"); self.tabs.add(self.market_tab,text="Market")
        self.tabs.add(self.positions_tab,text="Market Positions"); self.tabs.add(self.orders_tab,text="Orders")

        bar=ttk.Frame(self.assets_tab); bar.pack(fill="x",pady=(0,8))
        ttk.Button(bar,text="Upload / Ingest Digital Asset",command=self.ingest_asset).pack(side="left")
        ttk.Label(bar,text="Uploading creates a DCO asset only — no licence, listing or price is created.",style="Sub.TLabel").pack(side="left",padx=12)
        self.assets=self._tree(self.assets_tab,["Title","Class","Unit","SHA-256","Object ID"],[220,100,90,240,290])

        mbar=ttk.Frame(self.market_tab); mbar.pack(fill="x",pady=(0,8))
        ttk.Button(mbar,text="Buy",command=lambda:self.order("BUY")).pack(side="left")
        ttk.Button(mbar,text="Sell",command=lambda:self.order("SELL")).pack(side="left",padx=4)
        ttk.Label(mbar,text="Orders match automatically by price/time. Paid matches remain subject to settlement evidence.",style="Sub.TLabel").pack(side="left",padx=12)
        self.market=self._tree(self.market_tab,["Instrument","Class","Currency","Bid","Ask","Last","Venue"],[240,140,80,90,90,90,220])

        self.positions=self._tree(self.positions_tab,["Instrument","Units","Currency","Last","Bid","Ask","Indicative Value"],[260,90,80,90,90,90,140])
        self.orders=self._tree(self.orders_tab,["Instrument","Side","Remaining","Limit","Status"],[280,80,100,100,120])
        self.status=tk.StringVar(value="Ready")
        ttk.Label(self,textvariable=self.status,relief="sunken",anchor="w",padding=5).pack(fill="x",side="bottom")

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
        state=Path(self.state_var.get()).expanduser()
        state.mkdir(parents=True,exist_ok=True)
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
            snap=self.backend.snapshot(); self.market_rows=self.backend.market()
            self.clear(self.assets)
            for a in snap.get("assets",[]):
                self.assets.insert("", "end", values=(a["title"],a.get("commodity_class"),a.get("measurement_unit"),
                    a.get("content_sha256") or "",a["object_id"]))
            self.clear(self.positions)
            for p in snap.get("positions",[]):
                m=p["market"]; self.positions.insert("", "end",values=(p["instrument_id"],p["units"],p["settlement_currency"],
                    m.get("last"),m.get("bid"),m.get("ask"),p.get("market_value_amount_units")))
            self.clear(self.orders)
            for o in snap.get("orders",[]):
                self.orders.insert("", "end",values=(o["instrument_id"],o["side"],o["remaining"],o["limit_price"],o["status"]))
            self.clear(self.market)
            for i,row in enumerate(self.market_rows):
                m=row["market"]; self.market.insert("", "end",iid=str(i),values=(row["instrument_id"],row["instrument_class"],
                    row["settlement_currency"],m.get("bid"),m.get("ask"),m.get("last"),row.get("venue_id") or "UNLISTED"))
            self.status.set(f"{len(snap.get('assets',[]))} digital assets · {len(snap.get('positions',[]))} market positions · protocol tax 0 · crypto not required")
        except Exception as e:
            messagebox.showerror("Refresh failed",str(e)); self.status.set(str(e))

    def ingest_asset(self):
        if not self.backend: messagebox.showwarning("Wallet","Load an ENTITY identity first."); return
        f=filedialog.askopenfilename(title="Choose data or digital asset to ingest")
        if not f: return
        d=AssetDialog(self,Path(f)); self.wait_window(d)
        if not d.result: return
        try:
            r=self.backend.ingest(f,d.result["title"],d.result["class"],d.result["unit"],d.result["authority"])
            a=r["digital_asset"]; self.refresh()
            messagebox.showinfo("Digital asset created",
                f"Registered as {a['object_id']}\n\nSHA-256:\n{r['content_sha256']}\n\nNo market instrument or price was created.")
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
            n=len(result["trades"])
            messagebox.showinfo("Order submitted",
                f"Order accepted.\nImmediate matches: {n}\n\nMatched paid trades remain pending until settlement requirements are satisfied.")
        except Exception as e: messagebox.showerror("Order failed",str(e))

def main():
    ap=argparse.ArgumentParser(description="Native ENTITY economic wallet")
    ap.add_argument("--state"); ap.add_argument("--entity")
    args=ap.parse_args(); App(Path(args.state) if args.state else None,args.entity).mainloop()

if __name__=="__main__": main()
