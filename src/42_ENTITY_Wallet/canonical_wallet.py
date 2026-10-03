from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
from typing import Any
import html, json, secrets, sqlite3, time

WALLET_PROFILE="ENTITY_ECONOMIC_WALLET"
WALLET_VERSION="1.0.0"
WALLET_TYPES={"PARTICIPANT","TREASURY"}

def now_ms()->int: return int(time.time()*1000)
def rid(prefix:str)->str: return prefix+"-"+secrets.token_hex(12)

class EntityEconomicWallet:
    """Identity-bound stock-style view over canonical ENTITY economic records."""
    def __init__(self,state_dir:str|Path):
        self.state=Path(state_dir)
        self.exchange_path=self.state/"entity_v3_exchange.sqlite"
        self.economic_path=self.state/"entity_v3_economic_participation.sqlite"
        self.root=self.state/"wallet"; self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/"entity_wallet.sqlite"; self._init()

    @contextmanager
    def _db(self,path:Path,*,write:bool=False):
        db=sqlite3.connect(path,timeout=30.0); db.row_factory=sqlite3.Row
        db.execute("PRAGMA busy_timeout=30000")
        try:
            yield db
            if write: db.commit()
        except Exception:
            if write: db.rollback()
            raise
        finally: db.close()

    def _init(self):
        with self._db(self.path,write=True) as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
            CREATE TABLE IF NOT EXISTS wallets(
              wallet_id TEXT PRIMARY KEY,owner_entity_id TEXT NOT NULL,
              wallet_type TEXT NOT NULL,name TEXT NOT NULL,treasury_id TEXT,
              status TEXT NOT NULL,config_json TEXT NOT NULL,created_at_ms INTEGER NOT NULL);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_wallet_identity_type
              ON wallets(owner_entity_id,wallet_type,COALESCE(treasury_id,''));
            CREATE TABLE IF NOT EXISTS watchlist(
              wallet_id TEXT NOT NULL,instrument_id TEXT NOT NULL,created_at_ms INTEGER NOT NULL,
              PRIMARY KEY(wallet_id,instrument_id));
            """)

    def ensure_wallet(self,owner_entity_id:str,name:str,*,wallet_type:str="PARTICIPANT",
                      treasury_id:str|None=None,config:dict|None=None)->dict:
        typ=str(wallet_type).upper()
        if typ not in WALLET_TYPES: raise ValueError("wallet_type must be PARTICIPANT or TREASURY")
        if typ=="TREASURY" and not treasury_id: raise ValueError("treasury_id required")
        owner=str(owner_entity_id)
        cfg={"fiat_custody":"EXTERNAL_BANK_OR_PAYMENT_SERVICE","wallet_custodies_fiat":False,
             "payment_credentials_stored":False,"cryptocurrency_required":False,"protocol_tax_bps":0,
             "stock_style_market_view":True,"legal_classification_not_inferred":True,**dict(config or {})}
        with self._db(self.path,write=True) as db:
            row=db.execute("""SELECT * FROM wallets WHERE owner_entity_id=? AND wallet_type=?
                              AND COALESCE(treasury_id,'')=COALESCE(?,'')""",(owner,typ,treasury_id)).fetchone()
            if row is None:
                wid=rid("wallet3"); created=now_ms()
                db.execute("INSERT INTO wallets VALUES(?,?,?,?,?,?,?,?)",
                    (wid,owner,typ,str(name)[:256],treasury_id,"ACTIVE",json.dumps(cfg,sort_keys=True),created))
                row=db.execute("SELECT * FROM wallets WHERE wallet_id=?",(wid,)).fetchone()
        return self._wallet_row(row)

    @staticmethod
    def _wallet_row(row)->dict:
        d=dict(row); d["config"]=json.loads(d.pop("config_json") or "{}"); return d

    def wallet(self,wallet_id:str)->dict:
        with self._db(self.path) as db:
            row=db.execute("SELECT * FROM wallets WHERE wallet_id=?",(wallet_id,)).fetchone()
        if not row: raise KeyError("wallet not found")
        return self._wallet_row(row)

    def add_watch(self,wallet_id:str,instrument_id:str):
        self.wallet(wallet_id)
        with self._db(self.path,write=True) as db:
            db.execute("INSERT OR IGNORE INTO watchlist VALUES(?,?,?)",(wallet_id,str(instrument_id),now_ms()))

    def _market(self,db,instrument_id:str)->dict:
        last=db.execute("""SELECT price,quantity,created_at_ms,trade_id FROM trades
                           WHERE instrument_id=? AND status='SETTLED'
                           ORDER BY created_at_ms DESC,trade_id DESC LIMIT 1""",(instrument_id,)).fetchone()
        bid=db.execute("""SELECT MAX(limit_price) price FROM orders WHERE instrument_id=? AND side='BUY'
                          AND status IN ('OPEN','PARTIAL')""",(instrument_id,)).fetchone()
        ask=db.execute("""SELECT MIN(limit_price) price FROM orders WHERE instrument_id=? AND side='SELL'
                          AND status IN ('OPEN','PARTIAL')""",(instrument_id,)).fetchone()
        return {"last":None if not last else int(last["price"]),
                "last_quantity":None if not last else int(last["quantity"]),
                "last_trade_id":None if not last else last["trade_id"],
                "last_at_ms":None if not last else int(last["created_at_ms"]),
                "bid":None if not bid or bid["price"] is None else int(bid["price"]),
                "ask":None if not ask or ask["price"] is None else int(ask["price"])}

    def _trade_basis(self,db,entity_id:str,instrument_id:str,current_units:int)->dict:
        rows=db.execute("""SELECT * FROM trades WHERE instrument_id=? AND status='SETTLED'
                           AND (buyer=? OR seller=?) ORDER BY created_at_ms,trade_id""",
                        (instrument_id,entity_id,entity_id)).fetchall()
        lots=[]; realized=0; unknown_sold=0; bought=0; sold=0
        for r in rows:
            qty=int(r["quantity"]); price=int(r["price"])
            if r["buyer"]==entity_id:
                lots.append([qty,price]); bought+=qty
            if r["seller"]==entity_id:
                sold+=qty; remaining=qty
                while remaining and lots:
                    use=min(remaining,lots[0][0]); realized += use*(price-lots[0][1])
                    lots[0][0]-=use; remaining-=use
                    if lots[0][0]==0: lots.pop(0)
                unknown_sold+=remaining
        known_units=sum(x[0] for x in lots); known_cost=sum(x[0]*x[1] for x in lots)
        unknown_basis_units=max(0,int(current_units)-known_units)
        return {"method":"FIFO_SETTLED_TRADES","known_basis_units":known_units,
                "unknown_basis_units":unknown_basis_units,
                "basis_complete":unknown_basis_units==0 and unknown_sold==0,
                "known_cost_amount_units":known_cost,
                "average_cost_per_unit":(known_cost/known_units) if known_units else None,
                "realized_change_amount_units":realized,"unknown_sold_units":unknown_sold,
                "bought_units":bought,"sold_units":sold}

    def _positions(self,entity_id:str)->list[dict]:
        if not self.exchange_path.exists(): return []
        with self._db(self.exchange_path) as db:
            rows=db.execute("""SELECT b.instrument_id,b.units,i.issuer,i.underlying_object_id,i.instrument_class,
                                      i.rights_json,i.total_units,i.transferable,i.duration_ms,
                                      i.settlement_currency,i.delivery_mode,i.status
                               FROM balances b JOIN instruments i ON i.instrument_id=b.instrument_id
                               WHERE b.holder=? AND b.units>0 ORDER BY b.instrument_id""",(entity_id,)).fetchall()
            out=[]
            for row in rows:
                p=dict(row); p["units"]=int(p["units"]); p["total_units"]=int(p["total_units"])
                p["transferable"]=bool(p["transferable"]); p["rights"]=json.loads(p.pop("rights_json") or "{}")
                p["market"]=self._market(db,p["instrument_id"])
                p["cost_basis"]=self._trade_basis(db,entity_id,p["instrument_id"],p["units"])
                last=p["market"]["last"]
                p["market_value_amount_units"]=None if last is None else p["units"]*last
                p["unrealized_change_amount_units"]=None
                avg=p["cost_basis"]["average_cost_per_unit"]
                if last is not None and avg is not None and p["cost_basis"]["basis_complete"]:
                    p["unrealized_change_amount_units"]=round((last-avg)*p["units"])
                p["usage_units_recorded"]=int(db.execute(
                    "SELECT COALESCE(SUM(units),0) FROM usage WHERE instrument_id=? AND holder=?",
                    (p["instrument_id"],entity_id)).fetchone()[0])
                p["mark_is_indicative"]=last is not None; p["not_accounting_fair_value"]=True
                out.append(p)
            return out

    def _orders(self,entity_id:str)->list[dict]:
        if not self.exchange_path.exists(): return []
        with self._db(self.exchange_path) as db:
            return [dict(r) for r in db.execute("""SELECT order_id,instrument_id,side,quantity,remaining,
                    limit_price,tif,status,created_at_ms FROM orders WHERE participant=?
                    ORDER BY created_at_ms DESC LIMIT 200""",(entity_id,)).fetchall()]

    def _entitlements(self,entity_id:str)->list[dict]:
        if not self.exchange_path.exists(): return []
        with self._db(self.exchange_path) as db:
            rows=db.execute("""SELECT entitlement_id,trade_id,instrument_id,quantity,rights_json,
                               expires_at_ms,created_at_ms FROM entitlements WHERE holder=?
                               ORDER BY created_at_ms DESC""",(entity_id,)).fetchall()
            out=[]
            for row in rows:
                d=dict(row); d["rights"]=json.loads(d.pop("rights_json") or "{}"); out.append(d)
            return out

    def _obligations(self,entity_id:str)->dict:
        if not self.economic_path.exists(): return {"receivable":[],"payable":[],"summary":{}}
        with self._db(self.economic_path) as db:
            rec=[dict(r) for r in db.execute("""SELECT obligation_id,event_id,payer_entity_id,amount_units,currency,
                    basis,bps,status,settlement_ref,external_verified,created_at_ms,settled_at_ms
                    FROM obligations WHERE recipient_entity_id=? ORDER BY created_at_ms DESC""",(entity_id,)).fetchall()]
            pay=[dict(r) for r in db.execute("""SELECT obligation_id,event_id,recipient_entity_id,amount_units,currency,
                    basis,bps,status,settlement_ref,external_verified,created_at_ms,settled_at_ms
                    FROM obligations WHERE payer_entity_id=? ORDER BY created_at_ms DESC""",(entity_id,)).fetchall()]
        summary={}
        for side,rows in (("receivable",rec),("payable",pay)):
            for x in rows:
                cur=x["currency"]; status=x["status"]
                summary.setdefault(cur,{}).setdefault(status,{"receivable":0,"payable":0})
                summary[cur][status][side]+=int(x["amount_units"])
        return {"receivable":rec,"payable":pay,"summary":summary}

    @staticmethod
    def _totals(positions:list[dict])->dict:
        totals={}
        for p in positions:
            cur=p["settlement_currency"]
            b=totals.setdefault(cur,{"observed_market_value":0,"priced_positions":0,"unpriced_positions":0,
                                     "unrealized_change":0,"unrealized_complete_positions":0})
            if p["market_value_amount_units"] is None: b["unpriced_positions"]+=1
            else: b["observed_market_value"]+=int(p["market_value_amount_units"]); b["priced_positions"]+=1
            if p["unrealized_change_amount_units"] is not None:
                b["unrealized_change"]+=int(p["unrealized_change_amount_units"]); b["unrealized_complete_positions"]+=1
        return totals

    def snapshot(self,wallet_id:str)->dict:
        w=self.wallet(wallet_id); entity=w["owner_entity_id"]; positions=self._positions(entity)
        with self._db(self.path) as db:
            watch=[r["instrument_id"] for r in db.execute(
                "SELECT instrument_id FROM watchlist WHERE wallet_id=? ORDER BY created_at_ms",(wallet_id,)).fetchall()]
        watch_quotes=[]
        if self.exchange_path.exists():
            with self._db(self.exchange_path) as db:
                for iid in watch:
                    inst=db.execute("SELECT instrument_id,instrument_class,settlement_currency,status FROM instruments WHERE instrument_id=?",(iid,)).fetchone()
                    if inst: watch_quotes.append({**dict(inst),"market":self._market(db,iid)})
        return {"schema":"entity-economic-wallet-snapshot-v1","profile":WALLET_PROFILE,"version":WALLET_VERSION,
                "created_at_ms":now_ms(),"wallet":w,"positions":positions,
                "portfolio_by_currency":self._totals(positions),"orders":self._orders(entity),
                "entitlements":self._entitlements(entity),"obligations":self._obligations(entity),
                "watchlist":watch_quotes,
                "fiat_custody":{"model":"EXTERNAL_BANK_OR_PAYMENT_SERVICE","wallet_cash_balance":None,
                               "wallet_does_not_custody_fiat":True,"payment_credentials_stored":False},
                "market_value_policy":{"last_settled_trade_only":True,"bid_ask_are_quotes_not_value":True,
                                       "offers_are_not_realized_value":True,"unpriced_positions_remain_unpriced":True,
                                       "indicative_only":True,"not_accounting_fair_value":True},
                "stock_style":{"enabled":True,"features":["POSITIONS","QUANTITY","COST_BASIS","LAST","BID","ASK",
                               "INDICATIVE_MARKET_VALUE","REALIZED_CHANGE","UNREALIZED_CHANGE","ORDERS","ACTIVITY"],
                               "rights_are_not_declared_corporate_shares":True,
                               "legal_classification_not_inferred":True},
                "wallet_record_is_not_signing_authority":True,
                "canonical_authority_remains_entity_eep_signatures":True,
                "protocol_tax_bps":0,"cryptocurrency_required":False}

    def treasury_snapshot(self,wallet_id:str)->dict:
        w=self.wallet(wallet_id)
        if w["wallet_type"]!="TREASURY": raise ValueError("treasury wallet required")
        with self._db(self.economic_path) as db:
            t=db.execute("SELECT * FROM treasuries WHERE treasury_id=? AND status='ACTIVE'",(w["treasury_id"],)).fetchone()
            if not t: raise KeyError("active treasury not found")
            policies=[dict(r) for r in db.execute("""SELECT policy_id,instrument_id,version,total_units,reserve_units,
                       primary_treasury_bps,secondary_royalty_bps,derivative_participation_bps,currency,status,effective_at_ms
                       FROM participation_policies WHERE treasury_id=? ORDER BY instrument_id,version""",(w["treasury_id"],)).fetchall()]
            reserves=[dict(r) for r in db.execute("""SELECT allocation_id,policy_id,instrument_id,units,created_at_ms
                       FROM reserve_allocations WHERE policy_id IN
                       (SELECT policy_id FROM participation_policies WHERE treasury_id=?)
                       ORDER BY instrument_id""",(w["treasury_id"],)).fetchall()]
            events=[dict(r) for r in db.execute("""SELECT event_id,event_type,instrument_id,subject_ref,gross_amount_units,
                       currency,created_at_ms FROM economic_events WHERE treasury_id=?
                       ORDER BY created_at_ms DESC LIMIT 200""",(w["treasury_id"],)).fetchall()]
        base=self.snapshot(wallet_id); base["schema"]="entity-btg-treasury-wallet-snapshot-v1"
        base["treasury"]={k:t[k] for k in ("treasury_id","owner_entity_id","treasury_entity_id","name",
                          "jurisdiction","policy_sha256","status","created_at_ms")}
        base["participation_policies"]=policies; base["reserve_allocations"]=reserves; base["economic_events"]=events
        base["treasury_controls"]={"separate_entity_required":True,"protocol_tax_bps":0,"token_balance":None,
                                   "fiat_remains_external":True,"reserve_rights_are_wallet_positions":True}
        return base

def _money(v:Any,currency:str|None)->str:
    if v is None: return "—"
    return f"{int(v):,} {currency or ''}".strip()

def render_stock_style_html(snapshot:dict,title:str|None=None)->str:
    w=snapshot["wallet"]; positions=snapshot["positions"]; totals=snapshot["portfolio_by_currency"]
    title=title or w["name"]
    cards="".join(f"<div class='card'><div class='muted'>{html.escape(cur)} observed value</div><div class='big'>{vals['observed_market_value']:,}</div><div class='small'>{vals['priced_positions']} priced · {vals['unpriced_positions']} unpriced</div></div>" for cur,vals in sorted(totals.items()))
    if not cards: cards="<div class='card'><div class='muted'>Portfolio</div><div class='big'>No priced positions</div><div class='small'>Rights appear here when issued or acquired.</div></div>"
    rows=[]
    for p in positions:
        m=p["market"]; b=p["cost_basis"]; cur=p["settlement_currency"]
        basis=_money(b["average_cost_per_unit"],cur) if b["average_cost_per_unit"] is not None else "—"
        rows.append("<tr>"+ "".join([
            f"<td><b>{html.escape(p['instrument_id'])}</b><br><span class='muted'>{html.escape(p['instrument_class'])}</span></td>",
            f"<td>{p['units']:,}</td>",f"<td>{_money(m['last'],cur)}</td>",f"<td>{_money(m['bid'],cur)}</td>",
            f"<td>{_money(m['ask'],cur)}</td>",f"<td>{_money(p['market_value_amount_units'],cur)}</td>",
            f"<td>{basis}<br><span class='muted'>{'complete' if b['basis_complete'] else 'partial/unknown'}</span></td>",
            f"<td>{_money(p['unrealized_change_amount_units'],cur)}</td>"])+"</tr>")
    orders="".join(f"<tr><td>{html.escape(o['instrument_id'])}</td><td>{o['side']}</td><td>{o['remaining']:,}</td><td>{o['limit_price']:,}</td><td>{o['status']}</td></tr>" for o in snapshot["orders"])
    if not orders: orders="<tr><td colspan='5' class='muted'>No orders</td></tr>"
    rec=len(snapshot["obligations"]["receivable"]); pay=len(snapshot["obligations"]["payable"])
    return f"""<!doctype html><html><head><meta charset='utf-8'><title>{html.escape(title)}</title>
<style>body{{font-family:Segoe UI,Arial;background:#0f1115;color:#eef2f7;margin:0}}header{{padding:24px 32px;border-bottom:1px solid #2a3038}}main{{padding:24px 32px}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}}.card{{background:#171b22;border:1px solid #2a3038;border-radius:12px;padding:18px}}.big{{font-size:28px;font-weight:700;margin-top:8px}}.muted{{color:#9aa4b2}}.small{{font-size:12px;color:#9aa4b2;margin-top:8px}}table{{width:100%;border-collapse:collapse;background:#171b22;border:1px solid #2a3038}}th,td{{padding:12px;border-bottom:1px solid #2a3038;text-align:left}}th{{color:#9aa4b2;font-size:12px;text-transform:uppercase}}h2{{margin-top:30px}}.pill{{display:inline-block;padding:4px 8px;border:1px solid #3b4654;border-radius:999px;margin-right:8px;color:#cbd5e1}}</style></head>
<body><header><h1>{html.escape(title)}</h1><div class='muted'>{html.escape(w['wallet_type'])} · {html.escape(w['owner_entity_id'])}</div></header><main>
<div><span class='pill'>ENTITY v3.4.3 app layer</span><span class='pill'>Fiat external</span><span class='pill'>Protocol tax 0</span><span class='pill'>Crypto not required</span></div>
<h2>Portfolio</h2><div class='grid'>{cards}<div class='card'><div class='muted'>Receivables</div><div class='big'>{rec}</div><div class='small'>ENTITY economic obligations</div></div><div class='card'><div class='muted'>Payables</div><div class='big'>{pay}</div><div class='small'>ENTITY economic obligations</div></div></div>
<h2>Positions</h2><table><thead><tr><th>Instrument</th><th>Units</th><th>Last</th><th>Bid</th><th>Ask</th><th>Indicative value</th><th>Cost basis</th><th>Unrealized</th></tr></thead><tbody>{''.join(rows) if rows else "<tr><td colspan='8' class='muted'>No rights positions yet.</td></tr>"}</tbody></table>
<h2>Orders / Offers</h2><table><thead><tr><th>Instrument</th><th>Side</th><th>Remaining</th><th>Limit</th><th>Status</th></tr></thead><tbody>{orders}</tbody></table>
<p class='small'>Observed market value uses last settled ENTITY trade only. Bids/asks remain quotes. Offers are not realized value. The wallet does not custody fiat and does not infer legal, securities, tax, or accounting classification.</p>
</main></body></html>"""
