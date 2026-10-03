from __future__ import annotations
from pathlib import Path
import importlib.util,sys,tempfile,hashlib

ROOT=Path(__file__).resolve().parents[1]
def load(name,rel):
    p=ROOT/rel; spec=importlib.util.spec_from_file_location(name,p)
    m=importlib.util.module_from_spec(spec); sys.modules[name]=m; spec.loader.exec_module(m); return m

def test_venue_retirement_is_signed_fail_closed_and_preserves_history():
    ident=load("venue_retire_ident","src/01_Core_Runtime/identity/canonical_identity.py")
    fabmod=load("venue_retire_fabric","src/30_Universal_Transaction_Fabric/canonical_universal_fabric.py")
    exmod=load("venue_retire_exchange","src/31_Profiles/exchange_protocol.py")
    with tempfile.TemporaryDirectory() as td:
        state=Path(td); vault=ident.EntityIdentityVault(state)
        operator=vault.create("Reference Venue Operator","organization")["entity_id"]
        issuer=vault.create("Issuer","organization")["entity_id"]
        fabric=fabmod.UniversalTransactionFabric(state,vault); ex=exmod.ExchangeProtocol(state,vault,fabric)
        venue=ex.create_venue(operator,"Reference Market","CA",["ORDER_BOOK"],hashlib.sha256(b"policy").hexdigest())
        asset=fabric.register_digital_commodity(issuer,"Asset","1"*64,commodity_class="DATA",measurement_unit="ASSET")
        inst=ex.define_instrument(issuer,asset["object_id"],"SPOT_LICENSE",{"actions":["READ"]},10,"CAD")
        disc=ex.publish_disclosure(venue["venue_id"],inst["instrument_id"],issuer,"LISTING_INFORMATION","2"*64)
        ex.list_instrument(venue["venue_id"],inst["instrument_id"],issuer,disclosure_sha256=disc["content_sha256"])
        try:
            ex.retire_venue(operator,venue["venue_id"],"must fail while listing is active")
            assert False,"active listing must block venue retirement"
        except ValueError:
            pass
        ex.withdraw_instrument(issuer,inst["instrument_id"],"unused prelaunch instrument")
        retirement=ex.retire_venue(operator,venue["venue_id"],"unused test venue")
        status=ex.venue_status(venue["venue_id"])
        assert status["status"]=="RETIRED"
        assert status["retirement"]["retirement_id"]==retirement["retirement_id"]
        assert status["retirement"]["venue_is_not_protocol_authority"] is True
        assert ex.instrument_status(inst["instrument_id"])["status"]=="WITHDRAWN"
        with ex._db() as db:
            assert db.execute("select count(*) from venues where venue_id=?",(venue["venue_id"],)).fetchone()[0]==1
            assert db.execute("select count(*) from listings where instrument_id=?",(inst["instrument_id"],)).fetchone()[0]==1

def test_venue_retirement_refuses_open_orders():
    ident=load("venue_retire_ident2","src/01_Core_Runtime/identity/canonical_identity.py")
    fabmod=load("venue_retire_fabric2","src/30_Universal_Transaction_Fabric/canonical_universal_fabric.py")
    exmod=load("venue_retire_exchange2","src/31_Profiles/exchange_protocol.py")
    with tempfile.TemporaryDirectory() as td:
        state=Path(td); vault=ident.EntityIdentityVault(state)
        operator=vault.create("Operator","organization")["entity_id"]
        issuer=vault.create("Issuer","organization")["entity_id"]
        buyer=vault.create("Buyer","person")["entity_id"]
        fabric=fabmod.UniversalTransactionFabric(state,vault); ex=exmod.ExchangeProtocol(state,vault,fabric)
        venue=ex.create_venue(operator,"Market","CA",["ORDER_BOOK"],"a"*64)
        asset=fabric.register_digital_commodity(issuer,"Asset","b"*64,commodity_class="DATA",measurement_unit="ASSET")
        inst=ex.define_instrument(issuer,asset["object_id"],"SPOT_LICENSE",{"actions":["READ"]},10,"CAD")
        disc=ex.publish_disclosure(venue["venue_id"],inst["instrument_id"],issuer,"LISTING_INFORMATION","c"*64)
        ex.list_instrument(venue["venue_id"],inst["instrument_id"],issuer,disclosure_sha256=disc["content_sha256"])
        ex.submit_order(venue["venue_id"],inst["instrument_id"],buyer,"BUY",1,5,nonce="open-buy")
        try:
            ex.retire_venue(operator,venue["venue_id"],"must fail")
            assert False,"open order must block retirement"
        except ValueError:
            pass
