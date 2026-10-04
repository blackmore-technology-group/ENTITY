from __future__ import annotations
from pathlib import Path
import hashlib, importlib.util, json, sqlite3, sys, tempfile

ROOT=Path(__file__).resolve().parents[1]

def load(name,rel):
    p=ROOT/rel; spec=importlib.util.spec_from_file_location(name,p)
    m=importlib.util.module_from_spec(spec); sys.modules[name]=m; spec.loader.exec_module(m); return m

class FakeIdentity:
    def load_manifest(self,eid): return {"entity_id":eid,"display_name":"Test Controller"}

class FakeFabric:
    def __init__(self):
        self.obj={"object_id":"obj3-test","controller_entity_id":"BTG","object_type":"SOFTWARE",
                  "title":"Robot Asset","content_sha256":"a"*64,
                  "descriptor":{"digital_commodity":True,"commodity_class":"ROBOTICS_ASSET","measurement_unit":"ASSET"}}
    def get_object(self,oid): return dict(self.obj)

class FakeOrigin:
    default_release_ref="entity-release:v3.4.3"
    def passport_binding(self,ref):
        return {"release_ref":ref,"release_tag":"v3.4.3",
                "origin_lineage_id":"entity-origin:shawn-btg-entity@1.0",
                "root_originator_entity_id":"SHAWN","steward_entity_id":"BTG",
                "protocol_entity_id":"ENTITY","asset_provenance_is_separate_from_protocol_origin":True,
                "protocol_origin_does_not_transfer_authority":True,
                "protocol_origin_does_not_transfer_user_asset_ownership":True,
                "economic_participation_requires_explicit_terms":True,"automatic_protocol_royalty_bps":0}

class FakePassports:
    def __init__(self,origin): self.origin=origin
    def get(self,pid):
        return {"passport_id":pid,"rights_passport_id":"rp-test",
                "profile_stack":{"profile_refs":["entity-profile:global@1.0","entity-profile:robotics@1.0"]},
                "protocol_origin":self.origin.passport_binding("entity-release:v3.4.3"),
                "btdu_binding":{"schema":"entity-btdu-passport-binding-v1","content_sha256":"a"*64}}
    def verify(self,gp): return {"valid":True}

class FakePackages:
    def list_packages(self): return ["robotics"]

class FakeSDK:
    def __init__(self): self.last=None
    def ingest_package_file(self,path,controller,package,config,asset_kind,**kwargs):
        self.last={"path":str(path),"controller":controller,"package":package,"config":config,
                   "asset_kind":asset_kind,"kwargs":kwargs}
        return {"object_id":"obj3-test","global_passport_id":"gp-test"}

class FakeUniverse:
    def __init__(self): self.content_sha256=None
    def ingest_file(self,path,receipt,**kwargs):
        self.content_sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest()
        return {"object_ref":"btdu:test","content_sha256":self.content_sha256}
    def passport_binding(self,ref):
        return {"schema":"entity-btdu-passport-binding-v1","universe_root":"u","object_ref":ref,
                "content_sha256":self.content_sha256,"sovereign_entity_id":"BTG",
                "protocol_origin_is_not_asset_provenance":True,"topology_does_not_create_ownership":True,
                "topology_does_not_create_economic_entitlement":True,"automatic_protocol_royalty_bps":0}
    def close(self): pass

class FakeCLI:
    def __init__(self):
        self.identity=FakeIdentity(); self.fabric=FakeFabric(); self.origin=FakeOrigin()
        self.passports=FakePassports(self.origin); self.packages=FakePackages(); self.sdk=FakeSDK()
    def runtime(self,state,require_current_release=False):
        assert require_current_release is True
        return self.identity,self.fabric,None,self.origin,self.passports,self.packages,self.sdk,{"verified":True}
    def _btdu_for_controller(self,state,identity,controller): return FakeUniverse()
    def _btdu_receipt(self,identity,controller,path,logical): return {"body":{"scope":"BTDU_WRITE"},"signature":{}}

def test_wallet_ingest_uses_canonical_robotics_pipeline_without_market_issue():
    m=load("wallet_asset_ingest_test","src/42_ENTITY_Wallet/asset_ingest.py")
    with tempfile.TemporaryDirectory() as td:
        src=Path(td)/"robot.py"; src.write_text("print('robot')",encoding="utf-8")
        cli=FakeCLI(); ing=m.WalletAssetIngestor(Path(td)/"state",cli)
        r=ing.ingest_file("BTG",src,title="Robot Asset",package="robotics",asset_kind="software",
                          jurisdiction="CA-BC",commodity_class="ROBOTICS_ASSET",
                          measurement_unit="ASSET",authority_basis="CONTROLLER_ENTITY:BTG")
        assert r["global_passport_verified"] is True
        assert r["market_instruments_created"] is False
        assert r["listing_created"] is False
        assert r["price_created"] is False
        assert r["protocol_origin"]["origin_lineage_id"]=="entity-origin:shawn-btg-entity@1.0"
        assert "entity-profile:robotics@1.0" in r["profile_refs"]
        assert cli.sdk.last["kwargs"]["digital_commodity"] is True
        assert cli.sdk.last["kwargs"]["btdu_binding"]["object_ref"]=="btdu:test"

def test_dco_preserves_real_asset_type():
    identity=load("wallet_asset_identity","src/01_Core_Runtime/identity/canonical_identity.py")
    fabric_mod=load("wallet_asset_fabric","src/30_Universal_Transaction_Fabric/canonical_universal_fabric.py")
    with tempfile.TemporaryDirectory() as td:
        vault=identity.EntityIdentityVault(td); owner=vault.create("Owner","organization")["entity_id"]
        fabric=fabric_mod.UniversalTransactionFabric(td,vault)
        obj=fabric.register_digital_commodity(owner,"Algorithm","b"*64,commodity_class="ROBOTICS_ALGORITHM",
                                              measurement_unit="ASSET",object_type="SOFTWARE")
        assert obj["object_type"]=="SOFTWARE"
        assert obj["descriptor"]["digital_commodity"] is True

def test_wallet_lists_digital_assets_separately_from_positions():
    m=load("wallet_assets_view_test","src/42_ENTITY_Wallet/canonical_wallet.py")
    with tempfile.TemporaryDirectory() as td:
        state=Path(td); dbp=state/"entity_v3"/"universal_fabric.sqlite"; dbp.parent.mkdir(parents=True)
        db=sqlite3.connect(dbp)
        db.execute("""CREATE TABLE objects(object_id TEXT PRIMARY KEY,controller_entity_id TEXT,object_type TEXT,
                    title TEXT,content_sha256 TEXT,descriptor_json TEXT,status TEXT,created_at_ms INTEGER,signature_json TEXT)""")
        db.execute("""CREATE TABLE provenance_edges(edge_id TEXT PRIMARY KEY,parent_object_id TEXT,child_object_id TEXT,
                    relation TEXT,contribution_bps INTEGER,evidence_json TEXT,actor_entity_id TEXT,created_at_ms INTEGER,signature_json TEXT)""")
        descriptor=json.dumps({"digital_commodity":True,"commodity_class":"ROBOTICS","measurement_unit":"ASSET"})
        db.execute("INSERT INTO objects VALUES(?,?,?,?,?,?,?,?,?)",
                   ("obj3-r","OWNER","SOFTWARE","Robotics Asset","a"*64,descriptor,"ACTIVE",1,"{}"))
        db.commit(); db.close()
        w=m.EntityEconomicWallet(state); wr=w.ensure_wallet("OWNER","Owner Wallet")
        snap=w.snapshot(wr["wallet_id"])
        assert len(snap["assets"])==1
        assert snap["assets"][0]["title"]=="Robotics Asset"
        assert snap["positions"]==[]
        assert snap["asset_model"]["ingest_does_not_issue_market_instruments"] is True
        assert snap["asset_model"]["protocol_lineage_and_asset_provenance_are_separate"] is True


def test_retired_dco_factory_master_is_not_current_wallet_asset():
    m=load("wallet_retired_asset_view_test","src/42_ENTITY_Wallet/canonical_wallet.py")
    with tempfile.TemporaryDirectory() as td:
        state=Path(td); dbp=state/"entity_v3"/"universal_fabric.sqlite"; dbp.parent.mkdir(parents=True)
        db=sqlite3.connect(dbp)
        db.execute("""CREATE TABLE objects(object_id TEXT PRIMARY KEY,controller_entity_id TEXT,object_type TEXT,
                    title TEXT,content_sha256 TEXT,descriptor_json TEXT,status TEXT,created_at_ms INTEGER,signature_json TEXT)""")
        db.execute("""CREATE TABLE provenance_edges(edge_id TEXT PRIMARY KEY,parent_object_id TEXT,child_object_id TEXT,
                    relation TEXT,contribution_bps INTEGER,evidence_json TEXT,actor_entity_id TEXT,created_at_ms INTEGER,signature_json TEXT)""")
        desc=json.dumps({"digital_commodity":True,"commodity_class":"ROBOTICS_PILOT","measurement_unit":"ASSET"})
        db.execute("INSERT INTO objects VALUES(?,?,?,?,?,?,?,?,?)",
                   ("obj-pilot","OWNER","DATASET","Historical Pilot","f"*64,desc,"ACTIVE",1,"{}"))
        db.commit(); db.close()
        fdbp=state/"dco_factory"/"entity_dco_factory.sqlite"; fdbp.parent.mkdir(parents=True)
        fdb=sqlite3.connect(fdbp)
        fdb.execute("""CREATE TABLE dco_masters(dco_id TEXT,template_id TEXT,family TEXT,source_sha256 TEXT,
                     provenance_root TEXT,semantic_fingerprint TEXT,version TEXT,lifecycle TEXT,
                     master_json TEXT,created_at_ms INTEGER)""")
        fdb.execute("INSERT INTO dco_masters VALUES(?,?,?,?,?,?,?,?,?,?)",
                    ("DCO-PILOT","T","ROBOTICS","f"*64,None,None,"1","RETIRED_EXPERIMENT","{}",1))
        fdb.commit(); fdb.close()
        w=m.EntityEconomicWallet(state); wr=w.ensure_wallet("OWNER","Owner Wallet")
        assert w.snapshot(wr["wallet_id"])["assets"]==[]
