from pathlib import Path
import importlib.util, json, sqlite3

ROOT=Path(__file__).resolve().parents[2]

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

I=load("portable_scope_identity",ROOT/"01_Core_Runtime"/"identity"/"canonical_identity.py")
B=load("portable_scope_backup",ROOT/"15_Operations"/"backups"/"canonical_portable_state.py")

def make_db(path,ddl,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(path) as db:
        db.execute(ddl)
        placeholders=",".join("?" for _ in rows[0])
        db.executemany(f"INSERT INTO {ddl.split()[2].split('(')[0]} VALUES({placeholders})",rows)

def test_alias_resolution_and_strict_foreign_entity_boundary(tmp_path):
    state=tmp_path/"state"; identity=I.EntityIdentityVault(state)
    owner=identity.create("Owner Person","person",aliases=["owner.person.entity"])["entity_id"]
    company=identity.create("Example Company","business",aliases=["company.entity"])["entity_id"]
    foreign=identity.create("Foreign Person","person",aliases=["foreign.person.entity"])["entity_id"]
    make_db(state/"a"/"assets.sqlite",
        "CREATE TABLE assets(asset_id TEXT PRIMARY KEY,controller_entity_id TEXT,note TEXT)",
        [("asset1-owner-record",owner,"owner asset"),("asset1-foreign-record",foreign,"foreign asset")])
    make_db(state/"b"/"usage.sqlite",
        "CREATE TABLE usage(usage_id TEXT PRIMARY KEY,asset_id TEXT,note TEXT)",
        [("usage1-owner-record","asset1-owner-record","owner usage"),("usage1-foreign-record","asset1-foreign-record","foreign usage")])
    make_db(state/"c"/"authority.sqlite",
        "CREATE TABLE relationships(relationship_id TEXT PRIMARY KEY,entity_id TEXT,party_ref TEXT,relationship_type TEXT)",
        [("srel1-owner-direct",company,owner,"GOVERNANCE_AUTHORITY"),("srel1-foreign-only",company,foreign,"OTHER")])
    make_db(state/"d"/"domain.sqlite",
        "CREATE TABLE domains(domain_id TEXT PRIMARY KEY,entity_id TEXT,current_name TEXT)",
        [("domain1-owner-record",owner,"owner.person.entity"),("domain1-company-record",company,"company.entity"),("domain1-foreign-record",foreign,"foreign.person.entity")])

    dest=tmp_path/"export"
    evidence=B.PortableStateManager(state,identity).export_entity("owner.person.entity",dest)
    assert evidence["entity_id"]==owner
    assert evidence["foreign_entity_traversal"] is False
    assert evidence["cross_database_object_closure"] is True

    usage=json.loads((dest/"b__usage.sqlite.json").read_text(encoding="utf-8"))["tables"]["usage"]
    assert [row["usage_id"] for row in usage]==["usage1-owner-record"]
    rels=json.loads((dest/"c__authority.sqlite.json").read_text(encoding="utf-8"))["tables"]["relationships"]
    assert [row["relationship_id"] for row in rels]==["srel1-owner-direct"]

    domains=json.loads((dest/"d__domain.sqlite.json").read_text(encoding="utf-8"))["tables"]["domains"]
    assert [row["current_name"] for row in domains]==["owner.person.entity"]

    all_exported="\n".join(p.read_text(encoding="utf-8") for p in dest.glob("*.json"))
    assert "foreign.person.entity" not in all_exported
    assert '"current_name": "company.entity"' not in all_exported
