from __future__ import annotations
from pathlib import Path
import importlib.util,json,sqlite3,sys,tempfile

ROOT=Path(__file__).resolve().parents[1]
SHAWN="ent2-shawn"; BTG="ent2-btg"; ENTITY="ent2-entity"

def load():
    p=ROOT/"src"/"42_ENTITY_Wallet"/"lineage_resolver.py"
    spec=importlib.util.spec_from_file_location("wallet_lineage_test",p)
    m=importlib.util.module_from_spec(spec); sys.modules[spec.name]=m; spec.loader.exec_module(m); return m

def write_manifest(state,eid,name):
    p=state/"identity"/"manifests"; p.mkdir(parents=True,exist_ok=True)
    (p/f"{eid}.json").write_text(json.dumps({"entity_id":eid,"display_name":name}),encoding="utf-8")

def test_robotics_lineage_resolves_shawn_btg_entity_robotics_without_transferring_ownership():
    m=load()
    with tempfile.TemporaryDirectory() as td:
        state=Path(td)
        write_manifest(state,SHAWN,"Shawn Blackmore")
        write_manifest(state,BTG,"Blackmore Technology Group Limited")
        write_manifest(state,ENTITY,"ENTITY")

        db=sqlite3.connect(state/"entity_protocol_origin.sqlite")
        db.execute("CREATE TABLE origin_chains(lineage_id TEXT PRIMARY KEY,body_sha256 TEXT,body_json TEXT,signatures_json TEXT)")
        origin={"lineage_id":"entity-origin:shawn-btg-entity@1.0","root_originator_entity_id":SHAWN,
                "steward_entity_id":BTG,"protocol_entity_id":ENTITY}
        db.execute("INSERT INTO origin_chains VALUES(?,?,?,?)",(origin["lineage_id"],"o"*64,json.dumps(origin),"{}"))
        db.commit(); db.close()

        db=sqlite3.connect(state/"entity_v3_4_global_profiles.sqlite")
        db.execute("""CREATE TABLE profile_variants(profile_ref TEXT,body_sha256 TEXT,profile_id TEXT,version TEXT,
                    kind TEXT,body_json TEXT,issuer_entity_id TEXT,signature_json TEXT,created_at_ms INTEGER,
                    active_canonical INTEGER)""")
        for i,(ref,kind) in enumerate([
            ("entity-profile:global@1.0","GLOBAL"),("entity-profile:robotics@1.0","INDUSTRY")]):
            body={"profile_ref":ref,"profile_id":ref.split("@")[0],"kind":kind}
            db.execute("INSERT INTO profile_variants VALUES(?,?,?,?,?,?,?,?,?,?)",
                       (ref,str(i)*64,body["profile_id"],"1.0",kind,json.dumps(body),ENTITY,"{}",i,1))
        db.commit(); db.close()

        db=sqlite3.connect(state/"entity_v3_4_global_passports.sqlite")
        db.execute("""CREATE TABLE global_passports(passport_id TEXT,object_id TEXT,controller_entity_id TEXT,
                    version TEXT,body_sha256 TEXT,body_json TEXT,signature_json TEXT,created_at_ms INTEGER)""")
        gp={"passport_id":"gp1","object_id":"obj-child","controller_entity_id":BTG,"version":"1.1",
            "profile_stack":{"profile_refs":["entity-profile:global@1.0","entity-profile:robotics@1.0"]},
            "protocol_origin":{"origin_lineage_id":"entity-origin:shawn-btg-entity@1.0",
                               "root_originator_entity_id":SHAWN,"steward_entity_id":BTG,
                               "protocol_entity_id":ENTITY},
            "btdu_binding":{"schema":"entity-btdu-passport-binding-v1","object_ref":"btdu:child"}}
        db.execute("INSERT INTO global_passports VALUES(?,?,?,?,?,?,?,?)",
                   ("gp1","obj-child",BTG,"1.1","g"*64,json.dumps(gp),"{}",10))
        db.commit(); db.close()

        fp=state/"entity_v3"/"universal_fabric.sqlite"; fp.parent.mkdir(parents=True)
        db=sqlite3.connect(fp)
        db.execute("""CREATE TABLE objects(object_id TEXT,controller_entity_id TEXT,object_type TEXT,title TEXT,
                    content_sha256 TEXT,descriptor_json TEXT,status TEXT,created_at_ms INTEGER,signature_json TEXT)""")
        db.execute("""CREATE TABLE provenance_edges(edge_id TEXT,parent_object_id TEXT,child_object_id TEXT,
                    relation TEXT,contribution_bps INTEGER,evidence_json TEXT,actor_entity_id TEXT,
                    created_at_ms INTEGER,signature_json TEXT)""")
        db.execute("INSERT INTO objects VALUES(?,?,?,?,?,?,?,?,?)",
                   ("obj-parent",BTG,"DATASET","BIRFR-1","a"*64,"{}","ACTIVE",1,"{}"))
        db.execute("INSERT INTO objects VALUES(?,?,?,?,?,?,?,?,?)",
                   ("obj-child",BTG,"SOFTWARE","Failure Detector","b"*64,
                    json.dumps({"digital_commodity":True}),"ACTIVE",2,"{}"))
        db.execute("INSERT INTO provenance_edges VALUES(?,?,?,?,?,?,?,?,?)",
                   ("edge1","obj-parent","obj-child","TRAINED_AND_DERIVED_FROM",0,"{}",BTG,3,"{}"))
        db.commit(); db.close()

        resolver=m.WalletLineageResolver(state)
        result=resolver.resolve({"object_id":"obj-child","controller_entity_id":BTG})
        assert result["protocol_lineage"]["display_path"]=="Shawn Blackmore → Blackmore Technology Group Limited → ENTITY → Robotics"
        assert result["protocol_lineage"]["passport_protocol_origin_embedded"] is True
        assert result["asset_lineage"]["controller_entity_id"]==BTG
        assert result["asset_lineage"]["parents"][0]["title"]=="BIRFR-1"
        assert result["asset_lineage"]["protocol_origin_does_not_transfer_asset_ownership"] is True
        assert result["capability_bindings"]["BTDU"]["bound"] is True
        assert result["capability_bindings"]["ADAM"]["sovereign_authority"] is False
        assert result["capability_bindings"]["NIKI"]["sovereign_authority"] is False

def test_legacy_passport_without_embedded_origin_is_flagged_for_supersession():
    m=load()
    with tempfile.TemporaryDirectory() as td:
        state=Path(td)
        for eid,name in ((SHAWN,"Shawn Blackmore"),(BTG,"Blackmore Technology Group Limited"),(ENTITY,"ENTITY")):
            write_manifest(state,eid,name)
        db=sqlite3.connect(state/"entity_protocol_origin.sqlite")
        db.execute("CREATE TABLE origin_chains(lineage_id TEXT PRIMARY KEY,body_sha256 TEXT,body_json TEXT,signatures_json TEXT)")
        body={"lineage_id":"entity-origin:shawn-btg-entity@1.0","root_originator_entity_id":SHAWN,
              "steward_entity_id":BTG,"protocol_entity_id":ENTITY}
        db.execute("INSERT INTO origin_chains VALUES(?,?,?,?)",(body["lineage_id"],"o"*64,json.dumps(body),"{}")); db.commit(); db.close()
        db=sqlite3.connect(state/"entity_v3_4_global_passports.sqlite")
        db.execute("""CREATE TABLE global_passports(passport_id TEXT,object_id TEXT,controller_entity_id TEXT,
                    version TEXT,body_sha256 TEXT,body_json TEXT,signature_json TEXT,created_at_ms INTEGER)""")
        gp={"passport_id":"legacy","object_id":"obj","controller_entity_id":BTG,"version":"1.0",
            "profile_stack":{"profile_refs":[]},"protocol_origin":None}
        db.execute("INSERT INTO global_passports VALUES(?,?,?,?,?,?,?,?)",("legacy","obj",BTG,"1.0","x"*64,json.dumps(gp),"{}",1)); db.commit(); db.close()
        fp=state/"entity_v3"/"universal_fabric.sqlite"; fp.parent.mkdir(parents=True)
        db=sqlite3.connect(fp); db.execute("""CREATE TABLE provenance_edges(edge_id TEXT,parent_object_id TEXT,child_object_id TEXT,
                    relation TEXT,contribution_bps INTEGER,evidence_json TEXT,actor_entity_id TEXT,created_at_ms INTEGER,signature_json TEXT)"""); db.commit(); db.close()
        result=m.WalletLineageResolver(state).resolve({"object_id":"obj","controller_entity_id":BTG})
        assert result["protocol_lineage"]["resolved_from_canonical_origin_registry"] is True
        assert result["protocol_lineage"]["needs_passport_lineage_supersession"] is True
