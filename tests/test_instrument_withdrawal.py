from __future__ import annotations
from pathlib import Path
import importlib.util,sys,tempfile,sqlite3

ROOT=Path(__file__).resolve().parents[1]
def load(name,rel):
    p=ROOT/rel; spec=importlib.util.spec_from_file_location(name,p)
    m=importlib.util.module_from_spec(spec); sys.modules[name]=m; spec.loader.exec_module(m); return m

def test_signed_instrument_withdrawal_preserves_history_and_deactivates_listing():
    ident=load("withdraw_identity","src/01_Core_Runtime/identity/canonical_identity.py")
    fabmod=load("withdraw_fabric","src/30_Universal_Transaction_Fabric/canonical_universal_fabric.py")
    exmod=load("withdraw_exchange","src/31_Profiles/exchange_protocol.py")
    migmod=load("withdraw_migration","src/45_ENTITY_Market/prelaunch_withdrawal.py")
    with tempfile.TemporaryDirectory() as td:
        state=Path(td); vault=ident.EntityIdentityVault(state)
        issuer=vault.create("Issuer","organization")["entity_id"]
        venue_owner=vault.create("Venue","organization")["entity_id"]
        fabric=fabmod.UniversalTransactionFabric(state,vault)
        ex=exmod.ExchangeProtocol(state,vault,fabric)
        obj=fabric.register_digital_commodity(issuer,"Asset","a"*64,
            commodity_class="ROBOTICS_ASSET",measurement_unit="ASSET",object_type="SOFTWARE")
        venue=ex.create_venue(venue_owner,"Market","CA",["ORDER_BOOK"],"b"*64)
        inst=ex.define_instrument(issuer,obj["object_id"],"SPOT_LICENSE",{"actions":["EXECUTE"]},100,"CAD")
        disc=ex.publish_disclosure(venue["venue_id"],inst["instrument_id"],issuer,"LISTING_INFORMATION","c"*64)
        listing=ex.list_instrument(venue["venue_id"],inst["instrument_id"],issuer,
                                   disclosure_sha256=disc["content_sha256"])

        migration=migmod.PrelaunchEconomicWithdrawal(state,vault)
        audit=migration.audit([obj["object_id"]])
        assert audit["safe_to_withdraw"] is True
        result=migration.apply([obj["object_id"]],[],"SUPERSEDED_PRELAUNCH_MODEL")
        assert result["status"]=="WITHDRAWN_UNUSED_PRELAUNCH_ECONOMICS"
        assert result["eep_wire_protocol_changed"] is False
        assert result["historical_records_deleted"] is False
        assert result["issuer_signatures"]
        assert Path(result["receipt_path"]).is_file()

        db=sqlite3.connect(state/"entity_v3_exchange.sqlite"); db.row_factory=sqlite3.Row
        try:
            assert db.execute("SELECT COUNT(*) n FROM instruments WHERE instrument_id=?",(inst["instrument_id"],)).fetchone()["n"]==1
            assert db.execute("SELECT status FROM instruments WHERE instrument_id=?",(inst["instrument_id"],)).fetchone()["status"]=="WITHDRAWN"
            assert db.execute("SELECT status FROM listings WHERE listing_id=?",(listing["listing_id"],)).fetchone()["status"]=="WITHDRAWN"
        finally: db.close()
        try:
            ex.submit_order(venue["venue_id"],inst["instrument_id"],issuer,"SELL",1,1,nonce="after-withdraw")
            assert False,"withdrawn instrument must not accept orders"
        except KeyError:
            pass

def test_dco_factory_withdrawal_stops_counting_qualified_issuance_without_deleting_history():
    mod=load("withdraw_factory","src/43_DCO_Factory/canonical_dco_factory.py")
    with tempfile.TemporaryDirectory() as td:
        f=mod.DCOFactory(td)
        plan={"plan_sha256":"a"*64,"physical_instrument_count":20,"total_right_units":1000}
        run=f.record_issuance("DCO-TEST",plan,status="QUALIFIED")
        before=f.portfolio_summary()
        assert before["qualified_physical_instruments"]==20
        w=f.withdraw_issuance(run["issuance_id"],"SUPERSEDED_ASSET_FIRST_ALIGNMENT",evidence_sha256="b"*64)
        assert w["history_preserved"] is True
        after=f.portfolio_summary()
        assert after["qualified_physical_instruments"]==0
        assert after["qualified_right_units"]==0
        assert after["withdrawn_issuance_runs"]==1
        db=sqlite3.connect(Path(td)/"dco_factory"/"entity_dco_factory.sqlite")
        try:
            assert db.execute("SELECT COUNT(*) FROM issuance_runs").fetchone()[0]==1
            assert db.execute("SELECT COUNT(*) FROM issuance_withdrawals").fetchone()[0]==1
        finally: db.close()
