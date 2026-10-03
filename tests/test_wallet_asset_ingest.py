from __future__ import annotations
from pathlib import Path
import hashlib, importlib.util, json, sqlite3, sys, tempfile

ROOT=Path(__file__).resolve().parents[1]

def load(name,rel):
    p=ROOT/rel; spec=importlib.util.spec_from_file_location(name,p)
    m=importlib.util.module_from_spec(spec); sys.modules[name]=m; spec.loader.exec_module(m); return m

class FakeFabric:
    def __init__(self): self.calls=[]
    def register_digital_commodity(self,controller,title,content_sha256,*,commodity_class,measurement_unit,metadata):
        self.calls.append((controller,title,content_sha256,commodity_class,measurement_unit,metadata))
        return {"object_id":"obj3-test","controller_entity_id":controller,"title":title,
                "content_sha256":content_sha256,"digital_commodity_object":True}

def test_ingest_registers_asset_without_market_instrument():
    m=load("wallet_asset_ingest_test","src/42_ENTITY_Wallet/asset_ingest.py")
    with tempfile.TemporaryDirectory() as td:
        src=Path(td)/"robotics.bin"; src.write_bytes(b"robotics-asset")
        f=FakeFabric(); ing=m.WalletAssetIngestor(Path(td)/"state",f)
        r=ing.ingest_file("ent2-test",src,title="Robot Asset",commodity_class="ROBOTICS_DATA",
                          measurement_unit="ASSET",authority_basis="CREATOR_CONTROLLED")
        assert r["market_instruments_created"] is False
        assert r["listing_created"] is False
        assert r["price_created"] is False
        assert r["content_sha256"]==hashlib.sha256(b"robotics-asset").hexdigest()
        assert Path(r["custody"]["path"]).is_file()
        assert f.calls[0][5]["market_instruments_created_automatically"] is False

def test_wallet_lists_digital_assets_separately_from_positions():
    m=load("wallet_assets_view_test","src/42_ENTITY_Wallet/canonical_wallet.py")
    with tempfile.TemporaryDirectory() as td:
        state=Path(td); dbp=state/"entity_v3"/"universal_fabric.sqlite"; dbp.parent.mkdir(parents=True)
        db=sqlite3.connect(dbp)
        db.execute("""CREATE TABLE objects(object_id TEXT PRIMARY KEY,controller_entity_id TEXT,object_type TEXT,
                    title TEXT,content_sha256 TEXT,descriptor_json TEXT,status TEXT,created_at_ms INTEGER,signature_json TEXT)""")
        descriptor=json.dumps({"digital_commodity":True,"commodity_class":"ROBOTICS","measurement_unit":"ASSET"})
        db.execute("INSERT INTO objects VALUES(?,?,?,?,?,?,?,?,?)",
                   ("obj3-r","OWNER","DATASET","Robotics Asset","a"*64,descriptor,"ACTIVE",1,"{}"))
        db.commit(); db.close()
        w=m.EntityEconomicWallet(state); wr=w.ensure_wallet("OWNER","Owner Wallet")
        snap=w.snapshot(wr["wallet_id"])
        assert len(snap["assets"])==1
        assert snap["assets"][0]["title"]=="Robotics Asset"
        assert snap["positions"]==[]
        assert snap["asset_model"]["ingest_does_not_issue_market_instruments"] is True
