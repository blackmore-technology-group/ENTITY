from __future__ import annotations
from pathlib import Path
import importlib.util,sys,tempfile,sqlite3,time

ROOT=Path(__file__).resolve().parents[1]
def load(name,rel):
    p=ROOT/rel; spec=importlib.util.spec_from_file_location(name,p)
    m=importlib.util.module_from_spec(spec); sys.modules[name]=m; spec.loader.exec_module(m); return m

class FakePassports:
    def __init__(self,kind): self.kind=kind; self.records={}
    def bind(self,pid,object_id,controller,rp=None,actions=None,profiles=None):
        if self.kind=="rights":
            self.records[pid]={"passport_id":pid,"object_id":object_id,"controller_entity_id":controller,
                "rights":[{"effect":"ALLOW","actions":list(actions or ["READ","TRAIN","COMMERCIALIZE"])}]}
        else:
            self.records[pid]={"passport_id":pid,"object_id":object_id,"controller_entity_id":controller,
                "rights_passport_id":rp,"profile_stack":{"profile_refs":list(profiles or ["entity-profile:global@1.0","entity-profile:ai@1.0"])}}
    def get(self,pid): return dict(self.records[pid])
    def verify(self,p): return {"valid":True}

def test_settlement_aware_instrument_metrics_and_rollups():
    ident=load("intel_identity","src/01_Core_Runtime/identity/canonical_identity.py")
    fabmod=load("intel_fabric","src/30_Universal_Transaction_Fabric/canonical_universal_fabric.py")
    exmod=load("intel_exchange","src/31_Profiles/exchange_protocol.py")
    marketmod=load("intel_market","src/45_ENTITY_Market/canonical_market_registry.py")
    intelmod=load("intel_engine","src/45_ENTITY_Market/economic_intelligence.py")
    with tempfile.TemporaryDirectory() as td:
        state=Path(td); vault=ident.EntityIdentityVault(state)
        issuer=vault.create("Acme Corp","organization")["entity_id"]
        b1=vault.create("Buyer One","person")["entity_id"]; b2=vault.create("Buyer Two","person")["entity_id"]
        venue_owner=vault.create("Market Operator","organization")["entity_id"]
        fabric=fabmod.UniversalTransactionFabric(state,vault); ex=exmod.ExchangeProtocol(state,vault,fabric)
        rights=FakePassports("rights"); gps=FakePassports("global")
        reg=marketmod.EntityEconomicMarketRegistry(state,vault,fabric,ex,rights,gps)
        venue=ex.create_venue(venue_owner,"Test Market","CA",["ORDER_BOOK"],"a"*64)
        asset=fabric.register_digital_commodity(issuer,"Weather Data 2026","b"*64,
            commodity_class="WEATHER_DATA",measurement_unit="ASSET",object_type="DATASET",
            metadata={"asset_subtype":"WEATHER"})
        rights.bind("rp",asset["object_id"],issuer,actions=["READ","TRAIN","COMMERCIALIZE"])
        gps.bind("gp",asset["object_id"],issuer,"rp",profiles=["entity-profile:global@1.0","entity-profile:ai@1.0"])
        ins=reg.create_instrument(issuer,asset["object_id"],instrument_name="Weather Data AI Training Rights",
            display_symbol="WX26-TRN",instrument_class="SPOT_LICENSE",rights_class="TRAINING",
            rights={"actions":["TRAIN"]},supply=100,rights_passport_id="rp",global_passport_id="gp",
            settlement_currency="CAD",jurisdiction="CA",namespace="ACME",transferable=True,
            buyer_receives=["AI training right"],buyer_does_not_receive=["dataset ownership"])
        reg.create_listing(issuer,ins["instrument_id"],venue["venue_id"],market_id="ENTITY-PRIMARY",
            quote_unit="CAD",minimum_quantity=1,pricing_method="ORDER_BOOK")
        now=2_000_000_000_000
        db=sqlite3.connect(state/"entity_v3_exchange.sqlite")
        db.execute("UPDATE balances SET units=70 WHERE instrument_id=? AND holder=?",(ins["instrument_id"],issuer))
        db.execute("INSERT OR REPLACE INTO balances(instrument_id,holder,units) VALUES(?,?,?)",(ins["instrument_id"],b1,20))
        db.execute("INSERT OR REPLACE INTO balances(instrument_id,holder,units) VALUES(?,?,?)",(ins["instrument_id"],b2,10))
        trades=[
            ("t1",b1,issuer,10,18,now-2*60*60*1000,1),
            ("t2",b2,issuer,8,21,now-10*DAY if False else now-10*24*60*60*1000,0),
            ("t3",b1,b1,2,20,now-5*24*60*60*1000,1),
        ]
        for tid,buyer,seller,qty,price,ts,verified in trades:
            db.execute("""INSERT INTO trades(trade_id,venue_id,instrument_id,buy_order_id,sell_order_id,buyer,seller,
                        quantity,price,execution_model,status,created_at_ms) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                       (tid,venue["venue_id"],ins["instrument_id"],None,None,buyer,seller,qty,price,"ORDER_BOOK","SETTLED",ts))
            db.execute("INSERT INTO clearing(trade_id,payer,payee,amount_units,currency,status,payment_ref,external_verified) VALUES(?,?,?,?,?,?,?,?)",
                       (tid,buyer,seller,qty*price,"CAD","SETTLED","pay-"+tid,verified))
        db.commit(); db.close()

        ep=sqlite3.connect(state/"entity_v3_economic_participation.sqlite")
        ep.execute("CREATE TABLE economic_events(event_id TEXT PRIMARY KEY,instrument_id TEXT)")
        ep.execute("""CREATE TABLE obligations(event_id TEXT,amount_units INTEGER,currency TEXT,status TEXT,
                    external_verified INTEGER,basis TEXT)""")
        ep.execute("INSERT INTO economic_events VALUES(?,?)",("e1",ins["instrument_id"]))
        ep.execute("INSERT INTO obligations VALUES(?,?,?,?,?,?)",("e1",38,"CAD","SETTLED",1,"SECONDARY_ORIGINATOR_ROYALTY"))
        ep.commit(); ep.close()

        eng=intelmod.EntityEconomicIntelligence(state,reg,fabric,gps)
        m=eng.instrument_metrics(ins["instrument_id"],as_of_ms=now)
        assert m["market_identifier"]=="ACME:WX26-TRN"
        assert m["last_settled_price"]==18
        assert m["window_24h"]["volume_units"]==10
        assert m["window_30d"]["volume_units"]==20
        assert m["window_30d"]["unique_buyers"]==2
        assert m["window_30d"]["self_trade_count"]==1
        assert "SELF_TRADE_ACTIVITY_PRESENT" in m["market_integrity"]["flags"]
        assert m["active_holder_count"]==3
        assert m["issuer_inventory_units"]==70
        assert m["royalties_and_participation"]["externally_verified_amounts_by_currency"]["CAD"]==38
        assert m["valuation_boundary"]["observed_prices_value_instrument_rights_not_underlying_dco"] is True
        assert m["asset_class"]=="WEATHER_DATA"
        assert m["primary_domain"]=="AI"

        d=eng.dco_rights_demand(asset["object_id"],as_of_ms=now)
        assert d["rights_class_rollup"]["TRAINING"]["volume_units_30d"]==20
        roll=eng.economy_rollup(group_by="asset_class",as_of_ms=now)
        assert roll["rows"][0]["group"]=="WEATHER_DATA"
        assert roll["rows"][0]["volume_units_30d"]==20
