from __future__ import annotations
from pathlib import Path
import importlib.util,sys,tempfile

ROOT=Path(__file__).resolve().parents[1]

def load(name,rel):
    p=ROOT/rel; spec=importlib.util.spec_from_file_location(name,p)
    m=importlib.util.module_from_spec(spec); sys.modules[name]=m; spec.loader.exec_module(m); return m

class FakePassports:
    def __init__(self,kind): self.kind=kind; self.records={}
    def bind(self,pid,object_id,controller,rp=None,actions=None):
        if self.kind=="rights":
            self.records[pid]={"passport_id":pid,"object_id":object_id,"controller_entity_id":controller,
                               "rights":[{"effect":"ALLOW","actions":list(actions or ["READ","COPY","DERIVE","TRAIN","EVALUATE","COMMERCIALIZE"])}]}
        else:
            self.records[pid]={"passport_id":pid,"object_id":object_id,"controller_entity_id":controller,
                               "rights_passport_id":rp}
    def get(self,pid): return dict(self.records[pid])
    def verify(self,p): return {"valid":True}

def test_multi_issuer_symbols_canonical_ids_listing_sheet_and_portable_package():
    ident=load("market_test_identity","src/01_Core_Runtime/identity/canonical_identity.py")
    fabmod=load("market_test_fabric","src/30_Universal_Transaction_Fabric/canonical_universal_fabric.py")
    exmod=load("market_test_exchange","src/31_Profiles/exchange_protocol.py")
    marketmod=load("market_test_registry","src/45_ENTITY_Market/canonical_market_registry.py")
    with tempfile.TemporaryDirectory() as td:
        state=Path(td)
        vault=ident.EntityIdentityVault(state)
        acme=vault.create("Acme Corp","organization")["entity_id"]
        jane=vault.create("Jane Smith","person")["entity_id"]
        venue_owner=vault.create("Independent Market","organization")["entity_id"]
        fabric=fabmod.UniversalTransactionFabric(state,vault)
        ex=exmod.ExchangeProtocol(state,vault,fabric)
        venue=ex.create_venue(venue_owner,"ENTITY Test Market","CA",["ORDER_BOOK"],"a"*64)
        rights=FakePassports("rights"); gps=FakePassports("global")
        reg=marketmod.EntityEconomicMarketRegistry(state,vault,fabric,ex,rights,gps)

        a=fabric.register_digital_commodity(acme,"Vision Model 07","1"*64,
            commodity_class="AI_MODEL",measurement_unit="ASSET",object_type="MODEL")
        j=fabric.register_digital_commodity(jane,"Photography Collection 2026","2"*64,
            commodity_class="CREATIVE_COLLECTION",measurement_unit="ASSET",object_type="DOCUMENT")
        rights.bind("rp-acme",a["object_id"],acme); gps.bind("gp-acme",a["object_id"],acme,"rp-acme")
        rights.bind("rp-jane",j["object_id"],jane); gps.bind("gp-jane",j["object_id"],jane,"rp-jane")

        ia=reg.create_instrument(acme,a["object_id"],instrument_name="Vision Model 07 Commercial Training Rights",
            display_symbol="SHARED-TRN",instrument_class="SPOT_LICENSE",rights_class="TRAINING",
            rights={"actions":["TRAIN","EVALUATE"]},supply=100,rights_passport_id="rp-acme",
            global_passport_id="gp-acme",settlement_currency="CAD",jurisdiction="CA",
            namespace="ACME",transferable=True,buyer_receives=["commercial training right"],
            buyer_does_not_receive=["ownership of the model","copyright ownership"])
        ij=reg.create_instrument(jane,j["object_id"],instrument_name="Photography Collection Commercial Rights",
            display_symbol="SHARED-TRN",instrument_class="SPOT_LICENSE",rights_class="COMMERCIAL",
            rights={"actions":["COMMERCIALIZE"]},supply=25,rights_passport_id="rp-jane",
            global_passport_id="gp-jane",settlement_currency="CAD",jurisdiction="CA",
            namespace="JSMITH",transferable=True,buyer_receives=["defined commercial-use right"],
            buyer_does_not_receive=["copyright ownership"])

        assert ia["market_identifier"]=="ACME:SHARED-TRN"
        assert ij["market_identifier"]=="JSMITH:SHARED-TRN"
        assert ia["instrument_id"]!=ij["instrument_id"]
        assert ia["instrument_id"].startswith("entity.instrument:v1:")
        assert reg.resolve_symbol("ACME","SHARED-TRN")["instrument_id"]==ia["instrument_id"]
        assert reg.resolve_symbol("JSMITH","SHARED-TRN")["instrument_id"]==ij["instrument_id"]

        listing=reg.create_listing(acme,ia["instrument_id"],venue["venue_id"],
            market_id="ENTITY-PRIMARY",quote_unit="CAD",trade_mode="ORDER_BOOK",
            settlement_method="PAYMENT_VERSUS_RIGHT",minimum_quantity=1,pricing_method="ORDER_BOOK")
        assert listing["listing_id"].startswith("entity.listing:v1:")
        assert listing["information"]["sheet_does_not_replace_rights_passport"] is True
        assert "ownership of the model" in listing["information"]["buyer_does_not_receive"]
        assert listing["machine_manifest"]["instrument_id"]==ia["instrument_id"]
        assert ex.instrument_status(ia["instrument_id"])["status"]=="ACTIVE"

        pkg=reg.export_portable_package(listing["listing_id"],state/"portable")
        required={"LISTING_INFORMATION.pdf","LISTING_INFORMATION.md","entity-instrument.json",
                  "instrument.json","listing.json","rights-passport.json","global-passport.json",
                  "provenance.json","verification.json","SHA256SUMS","ENTITY_INSTRUMENT.md"}
        assert required.issubset(set(pkg["files"]))
        assert (state/"portable"/"LISTING_INFORMATION.pdf").read_bytes().startswith(b"%PDF-1.4")
        assert "ACME:SHARED-TRN" in (state/"portable"/"ENTITY_INSTRUMENT.md").read_text(encoding="utf-8")
        status=reg.status()
        assert status["multi_issuer"] is True
        assert status["entity_owns_protocol_not_assets"] is True
        assert status["listing_information_required"] is True

def test_instrument_requires_controlled_dco():
    ident=load("market_test_identity2","src/01_Core_Runtime/identity/canonical_identity.py")
    fabmod=load("market_test_fabric2","src/30_Universal_Transaction_Fabric/canonical_universal_fabric.py")
    exmod=load("market_test_exchange2","src/31_Profiles/exchange_protocol.py")
    marketmod=load("market_test_registry2","src/45_ENTITY_Market/canonical_market_registry.py")
    with tempfile.TemporaryDirectory() as td:
        state=Path(td); vault=ident.EntityIdentityVault(state)
        owner=vault.create("Asset Owner","person")["entity_id"]; attacker=vault.create("Other Issuer","person")["entity_id"]
        fabric=fabmod.UniversalTransactionFabric(state,vault); ex=exmod.ExchangeProtocol(state,vault,fabric)
        rights=FakePassports("rights"); gps=FakePassports("global")
        reg=marketmod.EntityEconomicMarketRegistry(state,vault,fabric,ex,rights,gps)
        obj=fabric.register_digital_commodity(owner,"Asset","3"*64,commodity_class="DATA",measurement_unit="ASSET")
        rights.bind("rp",obj["object_id"],owner); gps.bind("gp",obj["object_id"],owner,"rp")
        try:
            reg.create_instrument(attacker,obj["object_id"],instrument_name="Impersonation",
                display_symbol="FAKE",instrument_class="SPOT_LICENSE",rights_class="COMMERCIAL",
                rights={"actions":["COMMERCIALIZE"]},supply=1,rights_passport_id="rp",
                global_passport_id="gp",settlement_currency="CAD",jurisdiction="CA")
            assert False,"non-controller issuance must fail"
        except PermissionError:
            pass
