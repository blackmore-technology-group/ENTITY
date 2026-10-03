from __future__ import annotations
from pathlib import Path
import importlib.util,json,sqlite3,sys,tempfile

ROOT=Path(__file__).resolve().parents[1]
def load(name,rel):
    p=ROOT/rel; spec=importlib.util.spec_from_file_location(name,p)
    m=importlib.util.module_from_spec(spec); sys.modules[name]=m; spec.loader.exec_module(m); return m

def test_unused_prelaunch_issuance_with_reserve_is_withdrawn_without_history_deletion():
    ident=load("prelaunch_ident","src/01_Core_Runtime/identity/canonical_identity.py")
    fabmod=load("prelaunch_fabric","src/30_Universal_Transaction_Fabric/canonical_universal_fabric.py")
    exmod=load("prelaunch_exchange","src/31_Profiles/exchange_protocol.py")
    eoppmod=load("prelaunch_eopp","src/33_Economic_Participation/economic_participation.py")
    factorymod=load("prelaunch_factory","src/43_DCO_Factory/canonical_dco_factory.py")
    migmod=load("prelaunch_migration","src/45_ENTITY_Market/prelaunch_withdrawal.py")
    with tempfile.TemporaryDirectory() as td:
        state=Path(td); vault=ident.EntityIdentityVault(state)
        issuer=vault.create("Issuer","organization")["entity_id"]
        treasury_entity=vault.create("Issuer Treasury","organization")["entity_id"]
        venue_owner=vault.create("Market","organization")["entity_id"]
        fabric=fabmod.UniversalTransactionFabric(state,vault); ex=exmod.ExchangeProtocol(state,vault,fabric)
        eopp=eoppmod.EconomicParticipationProfile(state,vault); factory=factorymod.DCOFactory(state)
        asset=fabric.register_digital_commodity(issuer,"Robot Asset","a"*64,commodity_class="ROBOTICS_ASSET",measurement_unit="ASSET",object_type="ROBOTICS_ASSET")
        inst=ex.define_instrument(issuer,asset["object_id"],"SPOT_LICENSE",{"actions":["COMMERCIALIZE"]},100,"CAD",transferable=True)
        venue=ex.create_venue(venue_owner,"Prelaunch","CA",["ORDER_BOOK"],"b"*64)
        disc=ex.publish_disclosure(venue["venue_id"],inst["instrument_id"],issuer,"LISTING_INFORMATION","c"*64)
        ex.list_instrument(venue["venue_id"],inst["instrument_id"],issuer,min_lot=1,tick_size=1,disclosure_sha256=disc["content_sha256"])
        treasury=eopp.create_treasury(issuer,treasury_entity,"Treasury","CA","d"*64)
        pol=eopp.define_participation(issuer,treasury["treasury_id"],inst["instrument_id"],100,25,"CAD")
        eopp.allocate_eep_reserve(ex,pol["policy_id"])

        template={"template_id":"ROBOTICS-TEST","profile":"STANDARD","products":[
            {"archetype":"EVALUATION","eep_class":"SPOT_LICENSE","scarcity_class":"CONTROLLED_CAPACITY","initial_supply":1},
            {"archetype":"COMMERCIAL","eep_class":"SPOT_LICENSE","scarcity_class":"FIXED_CAP","initial_supply":100},
            {"archetype":"TRAINING","eep_class":"SPOT_LICENSE","scarcity_class":"CONTROLLED_CAPACITY","initial_supply":10},
        ]}
        factory.register_template(template)
        plan=factory.plan("ROBOTICS-TEST",dco_code="DCO-TEST",family="ROBOTICS")
        factory.create_master(dco_id="DCO-TEST",template_id="ROBOTICS-TEST",family="ROBOTICS",
            source_sha256="a"*64,plan=plan,lifecycle="ACTIVE_PRELAUNCH")
        issuance=factory.record_issuance("DCO-TEST",plan)

        migration=migmod.PrelaunchEconomicWithdrawal(state,vault)
        audit=migration.audit([asset["object_id"]],["DCO-TEST"])
        assert audit["safe_to_withdraw"] is True
        assert audit["instrument_count"]==1
        assert audit["economic_event_count"]==0
        assert audit["external_or_unexplained_balances"]==[]

        result=migration.apply([asset["object_id"]],["DCO-TEST"],"Superseded unused prelaunch rights experiment")
        assert result["historical_records_deleted"] is False
        assert result["eep_wire_protocol_changed"] is False
        assert Path(result["receipt_path"]).is_file()

        db=sqlite3.connect(state/"entity_v3_exchange.sqlite"); db.row_factory=sqlite3.Row
        assert db.execute("select status from instruments where instrument_id=?",(inst["instrument_id"],)).fetchone()["status"]=="WITHDRAWN"
        assert db.execute("select status from listings where instrument_id=?",(inst["instrument_id"],)).fetchone()["status"]=="WITHDRAWN"
        assert db.execute("select units from balances where instrument_id=? and holder=?",(inst["instrument_id"],issuer)).fetchone()["units"]==100
        assert db.execute("select units from balances where instrument_id=? and holder=?",(inst["instrument_id"],treasury_entity)).fetchone()["units"]==0
        assert db.execute("select count(*) from instruments where instrument_id=?",(inst["instrument_id"],)).fetchone()[0]==1
        db.close()

        ep=sqlite3.connect(state/"entity_v3_economic_participation.sqlite"); ep.row_factory=sqlite3.Row
        assert ep.execute("select status from participation_policies where policy_id=?",(pol["policy_id"],)).fetchone()["status"]=="WITHDRAWN"
        assert ep.execute("select count(*) from participation_policy_withdrawals where policy_id=?",(pol["policy_id"],)).fetchone()[0]==1
        assert ep.execute("select count(*) from reserve_allocations where instrument_id=?",(inst["instrument_id"],)).fetchone()[0]==1
        ep.close()

        fd=sqlite3.connect(state/"dco_factory"/"entity_dco_factory.sqlite"); fd.row_factory=sqlite3.Row
        assert fd.execute("select lifecycle from dco_masters where dco_id='DCO-TEST'").fetchone()["lifecycle"]=="ACTIVE"
        assert fd.execute("select count(*) from issuance_withdrawals where issuance_id=?",(issuance["issuance_id"],)).fetchone()[0]==1
        fd.close()

def test_withdrawal_refuses_real_market_activity():
    ident=load("prelaunch_ident2","src/01_Core_Runtime/identity/canonical_identity.py")
    fabmod=load("prelaunch_fabric2","src/30_Universal_Transaction_Fabric/canonical_universal_fabric.py")
    exmod=load("prelaunch_exchange2","src/31_Profiles/exchange_protocol.py")
    migmod=load("prelaunch_migration2","src/45_ENTITY_Market/prelaunch_withdrawal.py")
    with tempfile.TemporaryDirectory() as td:
        state=Path(td); vault=ident.EntityIdentityVault(state)
        issuer=vault.create("Issuer","organization")["entity_id"]; buyer=vault.create("Buyer","person")["entity_id"]
        venue_owner=vault.create("Market","organization")["entity_id"]
        fabric=fabmod.UniversalTransactionFabric(state,vault); ex=exmod.ExchangeProtocol(state,vault,fabric)
        asset=fabric.register_digital_commodity(issuer,"Asset","e"*64,commodity_class="DATA",measurement_unit="ASSET")
        inst=ex.define_instrument(issuer,asset["object_id"],"SPOT_LICENSE",{"actions":["READ"]},10,"CAD",transferable=True)
        venue=ex.create_venue(venue_owner,"Market","CA",["ORDER_BOOK"],"f"*64)
        disc=ex.publish_disclosure(venue["venue_id"],inst["instrument_id"],issuer,"LISTING_INFORMATION","1"*64)
        ex.list_instrument(venue["venue_id"],inst["instrument_id"],issuer,disclosure_sha256=disc["content_sha256"])
        ex.submit_order(venue["venue_id"],inst["instrument_id"],buyer,"BUY",1,10,nonce="buyer-order")
        migration=migmod.PrelaunchEconomicWithdrawal(state,vault)
        audit=migration.audit([asset["object_id"]])
        assert audit["safe_to_withdraw"] is False
        assert audit["activity_counts"]["orders"]==1
        try:
            migration.apply([asset["object_id"]],[],"must refuse")
            assert False,"migration must fail closed after market activity"
        except RuntimeError:
            pass
