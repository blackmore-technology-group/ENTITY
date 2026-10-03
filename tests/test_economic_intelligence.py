from __future__ import annotations
from pathlib import Path
import importlib.util,sys,tempfile,time,sqlite3

ROOT=Path(__file__).resolve().parents[1]

def load(name,rel):
    p=ROOT/rel; spec=importlib.util.spec_from_file_location(name,p)
    m=importlib.util.module_from_spec(spec); sys.modules[name]=m; spec.loader.exec_module(m); return m

class FakePassports:
    def __init__(self,kind): self.kind=kind; self.records={}
    def bind(self,pid,object_id,controller,rp=None,actions=None):
        if self.kind=="rights":
            self.records[pid]={"passport_id":pid,"object_id":object_id,"controller_entity_id":controller,
                               "rights":[{"effect":"ALLOW","actions":list(actions or ["READ","TRAIN","COMMERCIALIZE"])}]}
        else:
            self.records[pid]={"passport_id":pid,"object_id":object_id,"controller_entity_id":controller,
                               "rights_passport_id":rp,
                               "profile_stack":{"profile_refs":["entity-profile:global@1.0","entity-profile:robotics@1.0"]}}
    def get(self,pid): return dict(self.records[pid])
    def verify(self,p): return {"valid":True}

def test_economic_intelligence_uses_settled_trades_and_flags_suspicious_flow():
    ident=load("intel_identity","src/01_Core_Runtime/identity/canonical_identity.py")
    fabmod=load("intel_fabric","src/30_Universal_Transaction_Fabric/canonical_universal_fabric.py")
    exmod=load("intel_exchange","src/31_Profiles/exchange_protocol.py")
    marketmod=load("intel_market","src/45_ENTITY_Market/canonical_market_registry.py")
    intelmod=load("intel_engine","src/45_ENTITY_Market/economic_intelligence.py")
    with tempfile.TemporaryDirectory() as td:
        state=Path(td); vault=ident.EntityIdentityVault(state)
        issuer=vault.create("Acme Corp","organization")["entity_id"]
        a=vault.create("Buyer A","person")["entity_id"]; b=vault.create("Buyer B","person")["entity_id"]
        fabric=fabmod.UniversalTransactionFabric(state,vault); ex=exmod.ExchangeProtocol(state,vault,fabric)
        rights=FakePassports("rights"); gps=FakePassports("global")
        reg=marketmod.EntityEconomicMarketRegistry(state,vault,fabric,ex,rights,gps)
        obj=fabric.register_digital_commodity(issuer,"Robot Navigation Dataset","1"*64,
            commodity_class="ROBOT_NAVIGATION",measurement_unit="ASSET",object_type="DATASET",
            metadata={"asset_subtype":"NAVIGATION"})
        rights.bind("rp",obj["object_id"],issuer,actions=["TRAIN"])
        gps.bind("gp",obj["object_id"],issuer,"rp")
        inst=reg.create_instrument(issuer,obj["object_id"],instrument_name="Robot Navigation Training Rights",
            display_symbol="NAV26-TRN",instrument_class="SPOT_LICENSE",rights_class="TRAINING",
            rights={"actions":["TRAIN"]},supply=1000,rights_passport_id="rp",global_passport_id="gp",
            settlement_currency="CAD",jurisdiction="CA",namespace="ACME",transferable=True,
            buyer_receives=["AI training right"],buyer_does_not_receive=["dataset ownership"])
        iid=inst["instrument_id"]; now=int(time.time()*1000)

        db=sqlite3.connect(state/"entity_v3_exchange.sqlite")
        # settled clean trade
        db.execute("INSERT INTO trades VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                   ("t1","venue",iid,None,None,a,issuer,100,18,"ORDER_BOOK","SETTLED",now-1000))
        db.execute("INSERT INTO clearing VALUES(?,?,?,?,?,?,?,?)",
                   ("t1",a,issuer,1800,"CAD","SETTLED","pay1",1))
        # settled self-trade: counted as market activity but integrity-flagged
        db.execute("INSERT INTO trades VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                   ("t2","venue",iid,None,None,b,b,10,99,"ORDER_BOOK","SETTLED",now-900))
        db.execute("INSERT INTO clearing VALUES(?,?,?,?,?,?,?,?)",
                   ("t2",b,b,990,"CAD","SETTLED","pay2",1))
        # reciprocal flow between A and B
        db.execute("INSERT INTO trades VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                   ("t3","venue",iid,None,None,a,b,5,20,"ORDER_BOOK","SETTLED",now-800))
        db.execute("INSERT INTO clearing VALUES(?,?,?,?,?,?,?,?)",
                   ("t3",a,b,100,"CAD","SETTLED","pay3",1))
        db.execute("INSERT INTO trades VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                   ("t4","venue",iid,None,None,b,a,5,20,"ORDER_BOOK","SETTLED",now-700))
        db.execute("INSERT INTO clearing VALUES(?,?,?,?,?,?,?,?)",
                   ("t4",b,a,100,"CAD","SETTLED","pay4",1))
        # unsettled trade must not affect observed price/volume
        db.execute("INSERT INTO trades VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                   ("t5","venue",iid,None,None,a,issuer,999,777,"ORDER_BOOK","EXECUTED_UNSETTLED",now-600))
        db.execute("INSERT INTO clearing VALUES(?,?,?,?,?,?,?,?)",
                   ("t5",a,issuer,776223,"CAD","PENDING",None,0))
        db.execute("UPDATE balances SET units=700 WHERE instrument_id=? AND holder=?",(iid,issuer))
        db.execute("INSERT OR REPLACE INTO balances VALUES(?,?,?)",(iid,a,200))
        db.execute("INSERT OR REPLACE INTO balances VALUES(?,?,?)",(iid,b,100))
        db.commit(); db.close()

        intel=intelmod.EntityEconomicIntelligence(state,reg,fabric,gps)
        m=intel.instrument_metrics(iid,as_of_ms=now)
        assert m["last_settled_price"]==20
        assert m["window_30d"]["trade_count"]==4
        assert m["window_30d"]["volume_units"]==120
        assert m["window_30d"]["self_trade_count"]==1
        assert "SELF_TRADE_ACTIVITY_PRESENT" in m["market_integrity"]["flags"]
        assert "RECIPROCAL_COUNTERPARTY_FLOW_PRESENT" in m["market_integrity"]["flags"]
        assert m["valuation_boundary"]["observed_prices_value_instrument_rights_not_underlying_dco"] is True
        assert m["asset_class"]=="ROBOT_NAVIGATION"
        assert m["primary_domain"]=="ROBOTICS"
        assert m["active_holder_count"]==3

        d=intel.dco_rights_demand(obj["object_id"],as_of_ms=now)
        assert d["rights_class_rollup"]["TRAINING"]["volume_units_30d"]==120
        roll=intel.economy_rollup(group_by="asset_class",as_of_ms=now)
        assert roll["rows"][0]["group"]=="ROBOT_NAVIGATION"
        assert roll["rows"][0]["volume_units_30d"]==120
        assert roll["rollup_is_observed_market_activity_not_underlying_asset_valuation"] is True
