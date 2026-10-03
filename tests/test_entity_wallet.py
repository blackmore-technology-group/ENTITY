from __future__ import annotations
from pathlib import Path
import importlib.util, json, sqlite3, sys, tempfile, unittest

HERE=Path(__file__).resolve().parents[1]
MOD=HERE/"src"/"42_ENTITY_Wallet"/"canonical_wallet.py"
def load():
    spec=importlib.util.spec_from_file_location("wallet_test_mod",MOD)
    mod=importlib.util.module_from_spec(spec); sys.modules[spec.name]=mod; spec.loader.exec_module(mod); return mod

class WalletTests(unittest.TestCase):
    def setUp(self):
        self.td=tempfile.TemporaryDirectory(ignore_cleanup_errors=True); self.state=Path(self.td.name)
        ex=sqlite3.connect(self.state/"entity_v3_exchange.sqlite")
        ex.executescript("""
        CREATE TABLE balances(instrument_id TEXT,holder TEXT,units INTEGER,PRIMARY KEY(instrument_id,holder));
        CREATE TABLE instruments(instrument_id TEXT PRIMARY KEY,issuer TEXT,underlying_object_id TEXT,instrument_class TEXT,rights_json TEXT,total_units INTEGER,transferable INTEGER,duration_ms INTEGER,settlement_currency TEXT,delivery_mode TEXT,status TEXT,created_at_ms INTEGER,signature_json TEXT);
        CREATE TABLE trades(trade_id TEXT PRIMARY KEY,venue_id TEXT,instrument_id TEXT,buy_order_id TEXT,sell_order_id TEXT,buyer TEXT,seller TEXT,quantity INTEGER,price INTEGER,execution_model TEXT,status TEXT,created_at_ms INTEGER);
        CREATE TABLE orders(order_id TEXT PRIMARY KEY,venue_id TEXT,instrument_id TEXT,participant TEXT,side TEXT,quantity INTEGER,remaining INTEGER,limit_price INTEGER,tif TEXT,status TEXT,nonce TEXT,created_at_ms INTEGER,received_at_ms INTEGER,signature_json TEXT);
        CREATE TABLE usage(usage_id TEXT PRIMARY KEY,instrument_id TEXT,holder TEXT,action TEXT,units INTEGER,nonce TEXT,created_at_ms INTEGER,signature_json TEXT);
        CREATE TABLE entitlements(entitlement_id TEXT PRIMARY KEY,trade_id TEXT,instrument_id TEXT,holder TEXT,quantity INTEGER,rights_json TEXT,expires_at_ms INTEGER,created_at_ms INTEGER,signature_json TEXT);
        """)
        rights=json.dumps({"actions":["TRAIN"]})
        ex.execute("INSERT INTO instruments VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",("I1","ISS","DCO","SUBSCRIPTION",rights,100,1,1000,"CAD","ENTITLEMENT","ACTIVE",1,"{}"))
        ex.execute("INSERT INTO instruments VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",("I2","ISS","DCO2","COMPUTE_TO_DATA",json.dumps({"actions":["INFER"]}),1000,0,1000,"CAD","ENTITLEMENT","ACTIVE",1,"{}"))
        ex.execute("INSERT INTO balances VALUES('I1','BUYER',6)")
        ex.execute("INSERT INTO balances VALUES('I2','BUYER',2)")
        ex.execute("INSERT INTO trades VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",("T1","V","I1","B1","S1","BUYER","ISS",10,100,"ORDER_BOOK","SETTLED",10))
        ex.execute("INSERT INTO trades VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",("T2","V","I1","B2","S2","OTHER","BUYER",4,150,"ORDER_BOOK","SETTLED",20))
        ex.execute("INSERT INTO orders VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",("OB","V","I1","OTHER","BUY",1,1,140,"GTC","OPEN","n",30,30,"{}"))
        ex.execute("INSERT INTO orders VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",("OA","V","I1","OTHER","SELL",1,1,160,"GTC","OPEN","n2",30,30,"{}"))
        ex.execute("INSERT INTO entitlements VALUES(?,?,?,?,?,?,?,?,?)",("E1","T1","I1","BUYER",10,rights,999999,10,"{}"))
        ex.execute("INSERT INTO usage VALUES(?,?,?,?,?,?,?,?)",("U1","I1","BUYER","TRAIN",2,"u",40,"{}"))
        ex.commit(); ex.close()
        ep=sqlite3.connect(self.state/"entity_v3_economic_participation.sqlite")
        ep.executescript("""
        CREATE TABLE treasuries(treasury_id TEXT PRIMARY KEY,owner_entity_id TEXT,treasury_entity_id TEXT UNIQUE,name TEXT,jurisdiction TEXT,policy_sha256 TEXT,status TEXT,created_at_ms INTEGER,signature_json TEXT);
        CREATE TABLE participation_policies(policy_id TEXT PRIMARY KEY,instrument_id TEXT,version INTEGER,originator_entity_id TEXT,treasury_id TEXT,total_units INTEGER,reserve_units INTEGER,primary_treasury_bps INTEGER,secondary_royalty_bps INTEGER,derivative_participation_bps INTEGER,currency TEXT,terms_sha256 TEXT,effective_at_ms INTEGER,status TEXT,created_at_ms INTEGER,signature_json TEXT);
        CREATE TABLE reserve_allocations(allocation_id TEXT PRIMARY KEY,policy_id TEXT,instrument_id TEXT,originator_entity_id TEXT,treasury_entity_id TEXT,units INTEGER,created_at_ms INTEGER,originator_signature_json TEXT,treasury_signature_json TEXT);
        CREATE TABLE economic_events(event_id TEXT PRIMARY KEY,dedupe_key TEXT,event_type TEXT,policy_id TEXT,treasury_id TEXT,instrument_id TEXT,actor_entity_id TEXT,subject_ref TEXT,gross_amount_units INTEGER,currency TEXT,evidence_sha256 TEXT,details_json TEXT,created_at_ms INTEGER,signature_json TEXT);
        CREATE TABLE obligations(obligation_id TEXT PRIMARY KEY,event_id TEXT,payer_entity_id TEXT,recipient_entity_id TEXT,amount_units INTEGER,currency TEXT,basis TEXT,bps INTEGER,status TEXT,settlement_ref TEXT,verifier_entity_id TEXT,verification_evidence_sha256 TEXT,external_verified INTEGER,created_at_ms INTEGER,settled_at_ms INTEGER);
        """)
        ep.execute("INSERT INTO treasuries VALUES(?,?,?,?,?,?,?,?,?)",("TR","BTG","TREAS","BTG Treasury","CA","a"*64,"ACTIVE",1,"{}"))
        ep.execute("INSERT INTO obligations VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",("O1","EV","PAYER","BUYER",500,"CAD","ROYALTY",500,"ACCRUED",None,None,None,0,1,None))
        ep.commit(); ep.close()

    def tearDown(self): self.td.cleanup()

    def test_stock_style_participant_snapshot(self):
        m=load(); w=m.EntityEconomicWallet(self.state)
        rec=w.ensure_wallet("BUYER","Buyer Wallet")
        snap=w.snapshot(rec["wallet_id"])
        p={x["instrument_id"]:x for x in snap["positions"]}
        self.assertEqual(p["I1"]["units"],6)
        self.assertEqual(p["I1"]["market"]["last"],150)
        self.assertEqual(p["I1"]["market"]["bid"],140)
        self.assertEqual(p["I1"]["market"]["ask"],160)
        self.assertEqual(p["I1"]["market_value_amount_units"],900)
        self.assertEqual(p["I1"]["cost_basis"]["average_cost_per_unit"],100)
        self.assertEqual(p["I1"]["unrealized_change_amount_units"],300)
        self.assertIsNone(p["I2"]["market_value_amount_units"])
        self.assertEqual(p["I1"]["usage_units_recorded"],2)
        self.assertIsNone(snap["fiat_custody"]["wallet_cash_balance"])
        self.assertTrue(snap["fiat_custody"]["wallet_does_not_custody_fiat"])
        self.assertEqual(snap["obligations"]["receivable"][0]["amount_units"],500)
        self.assertTrue(snap["wallet_record_is_not_signing_authority"])
        self.assertTrue(snap["canonical_authority_remains_entity_eep_signatures"])

    def test_treasury_wallet(self):
        m=load(); w=m.EntityEconomicWallet(self.state)
        rec=w.ensure_wallet("TREAS","BTG Treasury Wallet",wallet_type="TREASURY",treasury_id="TR")
        snap=w.treasury_snapshot(rec["wallet_id"])
        self.assertEqual(snap["treasury"]["owner_entity_id"],"BTG")
        self.assertTrue(snap["treasury_controls"]["fiat_remains_external"])
        self.assertIsNone(snap["treasury_controls"]["token_balance"])
        self.assertEqual(snap["protocol_tax_bps"],0)

    def test_offer_does_not_create_market_value(self):
        m=load(); w=m.EntityEconomicWallet(self.state)
        rec=w.ensure_wallet("BUYER","Buyer Wallet")
        snap=w.snapshot(rec["wallet_id"])
        p={x["instrument_id"]:x for x in snap["positions"]}["I2"]
        self.assertIsNone(p["market"]["last"])
        self.assertIsNone(p["market_value_amount_units"])

if __name__=="__main__": unittest.main()
