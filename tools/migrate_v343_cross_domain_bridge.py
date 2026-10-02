from __future__ import annotations
from pathlib import Path
import argparse, importlib.util, json, os, sqlite3, sys, time
REPO=Path(__file__).resolve().parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--state",required=True); ap.add_argument("--btdu-state",required=True)
    ap.add_argument("--owner",required=True); ap.add_argument("--adam-root",required=True)
    a=ap.parse_args()
    os.environ["ENTITY_ADAM_V1_ROOT"]=str(Path(a.adam_root).resolve())
    ident=load("v343_bridge_migration_identity",REPO/"src"/"01_Core_Runtime"/"identity"/"canonical_identity.py")
    btdu=load("v343_bridge_migration_btdu",REPO/"src"/"40_BTDU"/"canonical_btdu.py")
    vault=ident.EntityIdentityVault(Path(a.state)); vault.load_manifest(a.owner)
    body={"schema":"entity-btdu-authorization-v1","actor_entity_id":a.owner,"scope":"BTDU_WRITE",
          "purpose":"install governed cross-domain semantic bridge derived index",
          "nonce":"v343-cross-domain-bridge-20261002"}
    receipt={"body":body,"signature":vault.sign(a.owner,body)}
    if not vault.verify_signature(vault.load_manifest(a.owner),body,receipt["signature"]):
        raise SystemExit("owner authorization signature verification failed")
    dbp=Path(a.btdu_state)/"btdu_index.sqlite"
    db=sqlite3.connect(dbp,timeout=30); db.row_factory=sqlite3.Row
    try:
        db.execute("PRAGMA busy_timeout=30000"); db.execute("PRAGMA journal_mode=WAL"); db.execute("PRAGMA synchronous=NORMAL")
        with db: result=btdu.install_cross_domain_bridge_index(db,receipt)
        quick=db.execute("PRAGMA quick_check").fetchone()[0]
        explicit=int(db.execute("""select count(*) from language_relations where
          ((source_ref like 'math-%' and (target_ref like 'code-%' or target_ref like 'lemma:%')) or
           (target_ref like 'math-%' and (source_ref like 'code-%' or source_ref like 'lemma:%')) or
           (source_ref like 'lemma:%' and target_ref like 'code-%') or
           (target_ref like 'lemma:%' and source_ref like 'code-%'))""").fetchone()[0])
    finally: db.close()
    if quick!="ok" or result["concepts"]!=7 or explicit<=0: raise SystemExit("bridge migration qualification failed")
    print(json.dumps(dict(result,sqlite_quick_check=quick,explicit_cross_domain_relations=explicit),indent=2,sort_keys=True))
if __name__=="__main__": main()
