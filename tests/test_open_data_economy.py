from __future__ import annotations
from pathlib import Path
import hashlib,importlib.util,json,sqlite3,sys,tempfile

ROOT=Path(__file__).resolve().parents[1]
MOD=ROOT/"src"/"45_Open_Data_Economy"/"open_data_economy.py"

def load():
    spec=importlib.util.spec_from_file_location("open_data_economy_test",MOD)
    m=importlib.util.module_from_spec(spec); sys.modules[spec.name]=m; spec.loader.exec_module(m); return m
def h(v): return hashlib.sha256(str(v).encode()).hexdigest()

def test_economic_constitution_preserves_original_doctrine():
    m=load()
    s=m.OpenEconomyConstitution.status()
    assert s["rights_not_copies_are_economic_object"] is True
    assert s["protocol_tax_bps"]==0
    assert s["cryptocurrency_required"] is False
    assert s["gas_required"] is False
    assert s["automatic_btg_royalty_bps"]==0
    assert s["issuer_neutral"] is True
    assert s["provider_neutral"] is True
    assert m.OpenEconomyConstitution.validate_runtime_claims(s)["valid"] is True
    assert m.OpenEconomyConstitution.validate_runtime_claims({"protocol_tax_bps":1})["valid"] is False

def test_create_my_dco_is_issuer_neutral_and_separates_retained_offered_rights():
    m=load()
    with tempfile.TemporaryDirectory() as td:
        svc=m.CreateMyDCOService(td)
        a=svc.create_draft(
            issuer_entity_id="person-alice",name="Alice Farm Observations",asset_class="DATASET",
            content_sha256=h("alice-data"),provenance_root=h("alice-prov"),authority_evidence_sha256=h("alice-authority"),
            privacy_profile="SELECTIVE_DISCLOSURE",
            retained_rights=[{"action":"CONTROL"},{"action":"REDISTRIBUTE"}],
            offered_rights=[{"action":"TRAIN","quantity":100,"duration_ms":31536000000,
                             "commercial_use_allowed":True,"raw_transfer_allowed":False},
                            {"action":"QUERY","quantity":1000,"duration_ms":31536000000}],
        )
        b=svc.create_draft(
            issuer_entity_id="company-beta",name="Beta Sensor Data",asset_class="DATASET",
            content_sha256=h("beta-data"),provenance_root=h("beta-prov"),authority_evidence_sha256=h("beta-authority"),
            privacy_profile="CONFIDENTIAL_PROVENANCE",
            retained_rights=[{"action":"CONTROL"}],
            offered_rights=[{"action":"RESEARCH","quantity":50}],
        )
        assert a["issuer_entity_id"]=="person-alice"
        assert b["issuer_entity_id"]=="company-beta"
        assert a["protocol_tax_bps"]==0 and b["automatic_btg_royalty_bps"]==0
        assert a["registration_is_not_ownership"] is True
        assert a["offered_rights"][0]["raw_transfer_allowed"] is False
        assert svc.user_experience_schema()["internal_terms_hidden_from_normal_user"]==["EEP","EOPP","BTDU"]

def test_market_discovery_is_rights_first_not_issuer_ranked():
    m=load()
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/"exchange.sqlite"
        db=sqlite3.connect(p)
        db.executescript("""
        CREATE TABLE venues(venue_id TEXT PRIMARY KEY,operator TEXT,name TEXT,jurisdiction TEXT,execution_models_json TEXT,policy_sha256 TEXT,status TEXT,created_at_ms INTEGER,signature_json TEXT);
        CREATE TABLE instruments(instrument_id TEXT PRIMARY KEY,issuer TEXT,underlying_object_id TEXT,instrument_class TEXT,rights_json TEXT,total_units INTEGER,transferable INTEGER,duration_ms INTEGER,settlement_currency TEXT,delivery_mode TEXT,status TEXT,created_at_ms INTEGER,signature_json TEXT);
        CREATE TABLE listings(listing_id TEXT PRIMARY KEY,venue_id TEXT,instrument_id TEXT,lister TEXT,min_lot INTEGER,tick_size INTEGER,disclosure_sha256 TEXT,status TEXT,created_at_ms INTEGER,signature_json TEXT);
        CREATE TABLE orders(order_id TEXT PRIMARY KEY,venue_id TEXT,instrument_id TEXT,participant TEXT,side TEXT,quantity INTEGER,remaining INTEGER,limit_price INTEGER,tif TEXT,nonce TEXT,status TEXT,created_at_ms INTEGER,signature_json TEXT);
        CREATE TABLE trades(trade_id TEXT PRIMARY KEY,venue_id TEXT,instrument_id TEXT,buyer TEXT,seller TEXT,quantity INTEGER,price INTEGER,execution_model TEXT,status TEXT,created_at_ms INTEGER);
        """)
        db.execute("INSERT INTO venues VALUES(?,?,?,?,?,?,?,?,?)",("v1","operator-x","Neutral Venue","CA-BC","[]",h("p"),"ACTIVE",1,"{}"))
        r1={"actions":["TRAIN","DERIVE"],"commercial_use_allowed":True,"raw_dataset_delivery":False,"jurisdiction":"CA-BC"}
        r2={"actions":["QUERY"],"commercial_use_allowed":False,"raw_dataset_delivery":True,"jurisdiction":"CA-BC"}
        for iid,issuer,rights in [("i1","issuer-a",r1),("i2","issuer-b",r2)]:
            db.execute("INSERT INTO instruments VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                       (iid,issuer,"o-"+iid,"SPOT_LICENSE",json.dumps(rights),100,1,1000,"CAD","ENTITLEMENT","ACTIVE",1,"{}"))
            db.execute("INSERT INTO listings VALUES(?,?,?,?,?,?,?,?,?,?)",
                       ("l-"+iid,"v1",iid,issuer,1,1,h(iid),"ACTIVE",1,"{}"))
        db.execute("INSERT INTO orders VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",("ord1","v1","i1","buyer","BUY",10,10,20,"GTC","n","OPEN",2,"{}"))
        db.execute("INSERT INTO orders VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",("ord2","v1","i1","seller","SELL",10,10,30,"GTC","n2","OPEN",3,"{}"))
        db.commit(); db.close()
        s=m.RightsMarketDiscovery(p).search({"actions":["TRAIN"],"commercial_use_required":True,
                                             "derivative_models_required":True,"raw_transfer_required":False,
                                             "region":"CA-BC"})
        assert s["result_count"]==1
        assert s["results"][0]["instrument_id"]=="i1"
        assert s["results"][0]["issuer_is_ranking_factor"] is False
        assert s["results"][0]["market"]["bid"]==20
        assert s["results"][0]["market"]["ask"]==30
        assert s["available_actions"]==["BUY","BID","REQUEST_QUOTE"]

def test_normal_participant_portfolio_not_treasury_first():
    m=load()
    snap={"schema":"entity-economic-wallet-snapshot-v1",
          "wallet":{"wallet_type":"PARTICIPANT","owner_entity_id":"alice","name":"My Data Economy"},
          "positions":[{"instrument_id":"i1","underlying_object_id":"o1","instrument_class":"SPOT_LICENSE",
                        "units":50,"transferable":True,"settlement_currency":"CAD",
                        "rights":{"display_name":"Training Right","actions":["TRAIN"],"symbol":"DATA-TRN"},
                        "market":{"last":20,"bid":18,"ask":22},"market_value_amount_units":1000,
                        "usage_units_recorded":4}],
          "orders":[{"side":"SELL","remaining":10,"status":"OPEN"}],
          "entitlements":[{"quantity":5}],
          "obligations":{"receivable":[],"payable":[],"summary":{}},
          "portfolio_by_currency":{"CAD":{"observed_market_value":1000}},
          "fiat_custody":{"wallet_does_not_custody_fiat":True},
          "market_value_policy":{"indicative_only":True}}
    out=m.ParticipantPortfolioView.simplify(snap)
    assert out["summary"]["rights_held"]==50
    assert out["summary"]["rights_currently_offered"]==10
    assert out["summary"]["rights_licensed_or_entitled"]==5
    assert out["protocol_tax_bps"]==0
    assert out["positions"][0]["not_accounting_fair_value"] is True

def test_data_pool_deterministic_allocation_and_no_protocol_cut():
    m=load()
    with tempfile.TemporaryDirectory() as td:
        p=m.DataPoolManager(td)
        pool=p.create_pool("farmer-coop","Agriculture Data Pool","aggregate farm observations",h("terms"))
        p.add_contribution(pool["pool_id"],"farmer-a","dco-a","c-a",45,h("pa"),{"actions":["TRAIN"]})
        p.add_contribution(pool["pool_id"],"farmer-b","dco-b","c-b",25,h("pb"),{"actions":["TRAIN"]})
        p.add_contribution(pool["pool_id"],"farmer-c","dco-c","c-c",30,h("pc"),{"actions":["TRAIN"]})
        plan=p.allocation_plan(pool["pool_id"],101,"CAD",h("payment"))
        assert plan["allocated_amount_units"]==101
        amounts={x["contributor_entity_id"]:x["amount_units"] for x in plan["allocations"]}
        assert amounts=={"farmer-a":45,"farmer-b":25,"farmer-c":31}
        assert plan["protocol_tax_bps"]==0
        assert plan["automatic_btg_royalty_bps"]==0
        assert plan["allocation_plan_is_not_settlement"] is True

def test_optional_services_are_competitive_not_protocol_privilege():
    m=load()
    with tempfile.TemporaryDirectory() as td:
        r=m.OptionalServiceProviderRegistry(td)
        r.register("btg","MARKET_DATA",h("btg-terms"))
        r.register("competitor","MARKET_DATA",h("competitor-terms"))
        rows=r.providers("MARKET_DATA")
        assert [x["provider_entity_id"] for x in rows]==["btg","competitor"]
        assert all(x["protocol_privilege"] is False and x["exclusive_provider"] is False for x in rows)
