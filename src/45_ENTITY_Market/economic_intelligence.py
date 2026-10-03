from __future__ import annotations
from pathlib import Path
from collections import defaultdict
import json, sqlite3, time

DAY_MS=24*60*60*1000
MONTH_MS=30*DAY_MS

class EntityEconomicIntelligence:
    """Observed, settlement-aware market analytics for ENTITY instruments.

    Metrics are keyed by canonical instrument_id. Market identifiers/tickers are
    human aliases only. Observations describe trading in bounded rights and must
    never be represented as intrinsic or accounting value of the underlying DCO.
    """

    def __init__(self,state_dir:str|Path,market_registry,fabric,global_passports=None):
        self.state=Path(state_dir); self.market_registry=market_registry
        self.fabric=fabric; self.global_passports=global_passports
        self.exchange_path=self.state/"entity_v3_exchange.sqlite"
        self.eopp_path=self.state/"entity_v3_economic_participation.sqlite"
        self.passport_path=self.state/"entity_v3_4_global_passports.sqlite"

    @staticmethod
    def _db(path:Path):
        db=sqlite3.connect(path); db.row_factory=sqlite3.Row; return db

    def _passport(self,passport_id:str)->dict|None:
        if self.global_passports is not None:
            try: return self.global_passports.get(passport_id)
            except Exception: pass
        if not self.passport_path.exists(): return None
        db=self._db(self.passport_path)
        try:
            row=db.execute("SELECT body_json FROM global_passports WHERE passport_id=?",(passport_id,)).fetchone()
            return json.loads(row["body_json"]) if row else None
        finally: db.close()

    @staticmethod
    def _primary_domain(passport:dict|None)->str:
        refs=list(((passport or {}).get("profile_stack") or {}).get("profile_refs") or [])
        for ref in refs:
            if "entity-profile:global@" in ref: continue
            return str(ref).split("@",1)[0].split(":")[-1].upper().replace("-","_")
        return "UNCLASSIFIED"

    def _classification(self,instrument:dict)->dict:
        obj=self.fabric.get_object(instrument["underlying_dco_id"])
        descriptor=dict(obj.get("descriptor") or {})
        meta=dict(descriptor.get("metadata") or {})
        passport=self._passport(instrument["global_passport_id"])
        return {
            "underlying_dco_id":instrument["underlying_dco_id"],
            "asset_title":obj.get("title"),
            "object_type":obj.get("object_type"),
            "asset_class":descriptor.get("commodity_class") or obj.get("object_type") or "UNCLASSIFIED",
            "asset_subtype":meta.get("asset_subtype") or meta.get("category") or descriptor.get("commodity_class") or "UNCLASSIFIED",
            "primary_domain":self._primary_domain(passport),
            "issuer_entity_id":instrument["issuer_entity_id"],
            "rights_class":instrument["rights_class"],
        }

    def _royalties(self,instrument_id:str)->dict:
        out={"settled_amounts_by_currency":{},"externally_verified_amounts_by_currency":{},
             "settled_obligation_count":0,"externally_verified_obligation_count":0}
        if not self.eopp_path.exists(): return out
        db=self._db(self.eopp_path)
        try:
            rows=db.execute("""SELECT o.amount_units,o.currency,o.status,o.external_verified,o.basis
                               FROM obligations o
                               JOIN economic_events e ON e.event_id=o.event_id
                               WHERE e.instrument_id=? AND o.status='SETTLED'
                                 AND o.basis IN ('SECONDARY_ROYALTY','DERIVATIVE_PARTICIPATION',
                                                 'PRIMARY_TREASURY_ALLOCATION')""",(instrument_id,)).fetchall()
        except sqlite3.OperationalError:
            rows=[]
        finally: db.close()
        settled=defaultdict(int); verified=defaultdict(int)
        for r in rows:
            cur=str(r["currency"]); amount=int(r["amount_units"]); settled[cur]+=amount
            out["settled_obligation_count"]+=1
            if int(r["external_verified"]):
                verified[cur]+=amount; out["externally_verified_obligation_count"]+=1
        out["settled_amounts_by_currency"]=dict(sorted(settled.items()))
        out["externally_verified_amounts_by_currency"]=dict(sorted(verified.items()))
        return out

    def instrument_metrics(self,instrument_id:str,*,as_of_ms:int|None=None)->dict:
        instrument=self.market_registry.instrument(instrument_id)
        now=int(as_of_ms if as_of_ms is not None else time.time()*1000)
        start24=now-DAY_MS; start30=now-MONTH_MS
        db=self._db(self.exchange_path)
        try:
            trades=db.execute("""SELECT t.*,c.external_verified,c.status clearing_status
                                 FROM trades t LEFT JOIN clearing c ON c.trade_id=t.trade_id
                                 WHERE t.instrument_id=? AND t.status='SETTLED'
                                 ORDER BY t.created_at_ms,t.trade_id""",(instrument_id,)).fetchall()
            balances=db.execute("SELECT holder,units FROM balances WHERE instrument_id=? AND units>0",(instrument_id,)).fetchall()
            orders=db.execute("""SELECT participant,side,remaining,status FROM orders
                                 WHERE instrument_id=? AND status IN ('OPEN','PARTIAL')""",(instrument_id,)).fetchall()
            issuer_balance_row=db.execute("SELECT units FROM balances WHERE instrument_id=? AND holder=?",
                                          (instrument_id,instrument["issuer_entity_id"])).fetchone()
        finally: db.close()

        def summarize(rows):
            units=sum(int(r["quantity"]) for r in rows)
            notional=sum(int(r["quantity"])*int(r["price"]) for r in rows)
            verified=[r for r in rows if int(r["external_verified"] or 0)==1]
            self_rows=[r for r in rows if r["buyer"]==r["seller"]]
            buyers={r["buyer"] for r in rows}; sellers={r["seller"] for r in rows}
            prices=[int(r["price"]) for r in rows]
            pairs=defaultdict(lambda:{"forward":0,"reverse":0,"notional":0})
            unordered=defaultdict(lambda:{"dirs":set(),"notional":0})
            for r in rows:
                b,s=str(r["buyer"]),str(r["seller"]); n=int(r["quantity"])*int(r["price"])
                key=tuple(sorted((b,s))); unordered[key]["dirs"].add((b,s)); unordered[key]["notional"]+=n
            reciprocal_notional=sum(v["notional"] for v in unordered.values() if len(v["dirs"])>1)
            pair_max=max((v["notional"] for v in unordered.values()),default=0)
            return {
                "trade_count":len(rows),"volume_units":units,"notional_amount_units":notional,
                "unique_buyers":len(buyers),"unique_sellers":len(sellers),
                "high_price":max(prices) if prices else None,"low_price":min(prices) if prices else None,
                "externally_verified_trade_count":len(verified),
                "externally_verified_volume_units":sum(int(r["quantity"]) for r in verified),
                "externally_verified_notional_amount_units":sum(int(r["quantity"])*int(r["price"]) for r in verified),
                "self_trade_count":len(self_rows),
                "self_trade_notional_amount_units":sum(int(r["quantity"])*int(r["price"]) for r in self_rows),
                "reciprocal_counterparty_notional_amount_units":reciprocal_notional,
                "largest_counterparty_pair_notional_amount_units":pair_max,
                "largest_counterparty_pair_share":(pair_max/notional) if notional else None,
            }

        rows24=[r for r in trades if int(r["created_at_ms"])>=start24]
        rows30=[r for r in trades if int(r["created_at_ms"])>=start30]
        last=trades[-1] if trades else None
        last_verified=next((r for r in reversed(trades) if int(r["external_verified"] or 0)==1),None)
        issuer_balance=int(issuer_balance_row["units"]) if issuer_balance_row else 0
        issuer_reserved=sum(int(r["remaining"]) for r in orders if r["side"]=="SELL" and r["participant"]==instrument["issuer_entity_id"])
        open_sell_units=sum(int(r["remaining"]) for r in orders if r["side"]=="SELL")
        total_supply=int(instrument["supply"])
        active_holder_count=len(balances)
        nonissuer_holder_count=sum(1 for r in balances if r["holder"]!=instrument["issuer_entity_id"])
        m30=summarize(rows30)
        flags=[]
        if m30["self_trade_count"]: flags.append("SELF_TRADE_ACTIVITY_PRESENT")
        if m30["reciprocal_counterparty_notional_amount_units"]: flags.append("RECIPROCAL_COUNTERPARTY_FLOW_PRESENT")
        if m30["largest_counterparty_pair_share"] is not None and m30["largest_counterparty_pair_share"]>=0.50:
            flags.append("COUNTERPARTY_CONCENTRATION_HIGH")
        if m30["trade_count"] and m30["externally_verified_trade_count"]==0:
            flags.append("NO_EXTERNALLY_VERIFIED_SETTLEMENTS_IN_WINDOW")
        classification=self._classification(instrument)
        return {
            "schema":"entity-economic-intelligence-instrument-v1",
            "instrument_id":instrument_id,
            "market_identifier":instrument["market_identifier"],
            "display_symbol":instrument["display_symbol"],
            "instrument_name":instrument["instrument_name"],
            "issuer_entity_id":instrument["issuer_entity_id"],
            **classification,
            "settlement_currency":self._settlement_currency(instrument_id),
            "last_settled_price":None if last is None else int(last["price"]),
            "last_settled_trade_at_ms":None if last is None else int(last["created_at_ms"]),
            "last_externally_verified_price":None if last_verified is None else int(last_verified["price"]),
            "last_externally_verified_trade_at_ms":None if last_verified is None else int(last_verified["created_at_ms"]),
            "window_24h":summarize(rows24),"window_30d":m30,
            "lifetime":summarize(trades),
            "total_supply_units":total_supply,
            "issuer_inventory_units":issuer_balance,
            "issuer_unreserved_inventory_units":max(0,issuer_balance-issuer_reserved),
            "open_sell_offer_units":open_sell_units,
            "circulating_units":max(0,total_supply-issuer_balance),
            "active_holder_count":active_holder_count,
            "nonissuer_holder_count":nonissuer_holder_count,
            "royalties_and_participation":self._royalties(instrument_id),
            "market_integrity":{
                "flags":flags,
                "related_wallet_detection_performed":False,
                "related_wallet_detection_requires_authorized_relationship_evidence":True,
                "raw_volume_is_not_proof_of_value":True,
                "orders_and_quotes_are_not_counted_as_realized_demand":True,
                "settled_trades_only_for_price_volume_metrics":True,
            },
            "valuation_boundary":{
                "observed_prices_value_instrument_rights_not_underlying_dco":True,
                "instrument_price_times_supply_is_not_underlying_asset_value":True,
                "market_observation_is_not_accounting_fair_value":True,
                "intrinsic_value_not_claimed":True,
            },
            "as_of_ms":now,
        }

    def _settlement_currency(self,instrument_id:str)->str|None:
        db=self._db(self.exchange_path)
        try:
            row=db.execute("SELECT settlement_currency FROM instruments WHERE instrument_id=?",(instrument_id,)).fetchone()
            return row["settlement_currency"] if row else None
        finally: db.close()

    def dco_rights_demand(self,dco_id:str,*,as_of_ms:int|None=None)->dict:
        db=self.market_registry._db()
        try:
            rows=db.execute("""SELECT instrument_id FROM instrument_packages
                               WHERE underlying_dco_id=? AND status='ACTIVE'
                               ORDER BY rights_class,market_identifier""",(str(dco_id),)).fetchall()
        finally: db.close()
        metrics=[self.instrument_metrics(r["instrument_id"],as_of_ms=as_of_ms) for r in rows]
        by_rights=defaultdict(lambda:{"instruments":0,"volume_units_30d":0,"notional_30d_by_currency":defaultdict(int),
                                     "unique_buyers":set(),"settled_trades":0})
        for m in metrics:
            r=by_rights[m["rights_class"]]; r["instruments"]+=1
            r["volume_units_30d"]+=m["window_30d"]["volume_units"]; r["settled_trades"]+=m["window_30d"]["trade_count"]
            cur=m["settlement_currency"] or "UNSPECIFIED"
            r["notional_30d_by_currency"][cur]+=m["window_30d"]["notional_amount_units"]
        clean={k:{**v,"notional_30d_by_currency":dict(v["notional_30d_by_currency"])}
               for k,v in sorted(by_rights.items())}
        return {"schema":"entity-dco-rights-demand-v1","underlying_dco_id":str(dco_id),
                "instruments":metrics,"rights_class_rollup":clean,
                "observed_demand_is_for_instrument_rights_not_intrinsic_asset_value":True}

    def economy_rollup(self,*,group_by:str="asset_class",as_of_ms:int|None=None)->dict:
        allowed={"asset_class","asset_subtype","primary_domain","rights_class","issuer_entity_id","underlying_dco_id"}
        if group_by not in allowed: raise ValueError("unsupported rollup dimension")
        db=self.market_registry._db()
        try:
            ids=[r["instrument_id"] for r in db.execute(
                "SELECT instrument_id FROM instrument_packages WHERE status='ACTIVE' ORDER BY instrument_id").fetchall()]
        finally: db.close()
        groups=defaultdict(lambda:{"instrument_count":0,"settled_trades_30d":0,"volume_units_30d":0,
                                   "notional_30d_by_currency":defaultdict(int),"unique_buyer_sum":0})
        for iid in ids:
            m=self.instrument_metrics(iid,as_of_ms=as_of_ms); key=str(m.get(group_by) or "UNCLASSIFIED")
            g=groups[key]; g["instrument_count"]+=1; g["settled_trades_30d"]+=m["window_30d"]["trade_count"]
            g["volume_units_30d"]+=m["window_30d"]["volume_units"]; g["unique_buyer_sum"]+=m["window_30d"]["unique_buyers"]
            g["notional_30d_by_currency"][m["settlement_currency"] or "UNSPECIFIED"]+=m["window_30d"]["notional_amount_units"]
        rows=[]
        for key,g in groups.items():
            rows.append({"group":key,"instrument_count":g["instrument_count"],
                         "settled_trades_30d":g["settled_trades_30d"],"volume_units_30d":g["volume_units_30d"],
                         "notional_30d_by_currency":dict(sorted(g["notional_30d_by_currency"].items())),
                         "sum_instrument_unique_buyers_30d":g["unique_buyer_sum"]})
        rows.sort(key=lambda x:(-sum(x["notional_30d_by_currency"].values()),x["group"]))
        return {"schema":"entity-economy-rollup-v1","group_by":group_by,"rows":rows,
                "cross_currency_notional_is_not_summed_into_one_value":True,
                "rollup_is_observed_market_activity_not_underlying_asset_valuation":True,
                "as_of_ms":int(as_of_ms if as_of_ms is not None else time.time()*1000)}
