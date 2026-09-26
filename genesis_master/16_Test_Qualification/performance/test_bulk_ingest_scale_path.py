from pathlib import Path
import hashlib, importlib.util, json, sqlite3, sys
import pytest

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); assert spec and spec.loader
    mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod

I=load("bulk_identity",ROOT/"01_Core_Runtime"/"identity"/"canonical_identity.py")
B=load("bulk_store",ROOT/"04_Entity_Registry"/"bulk_ingest"/"canonical_bulk_ingest.py")

def rows(start,count):
    return [{"content_sha256":hashlib.sha256(f"asset-{i}".encode()).hexdigest(),"size_bytes":i+1,"media_type":"application/octet-stream","title":f"asset-{i}","metadata":{"ordinal":i}} for i in range(start,start+count)]

def test_signed_bulk_batches_and_full_row_verification(tmp_path):
    ids=I.EntityIdentityVault(tmp_path/"identity-state")
    owner=ids.create("Bulk Owner","organization")["entity_id"]
    store=B.CanonicalBulkIngestStore(tmp_path/"bulk",ids,owner)
    a=store.ingest_assets(rows(0,250),batch_id="batch-0001")
    b=store.ingest_assets(rows(250,250),batch_id="batch-0002")
    assert a["asset_count"]==250 and a["event_count"]==750
    assert b["prior_batch_hash"]==a["batch_hash"]
    assert store.verify_batch("batch-0001",verify_rows=True)["pass"] is True
    assert store.verify_batch("batch-0002",verify_rows=True)["pass"] is True
    assert store.verify_all_batches(verify_rows=True)["pass"] is True
    status=store.status(); assert status["assets"]==500 and status["events"]==1500

def test_duplicate_batch_and_tamper_fail_closed(tmp_path):
    ids=I.EntityIdentityVault(tmp_path/"identity-state")
    owner=ids.create("Bulk Owner","organization")["entity_id"]
    store=B.CanonicalBulkIngestStore(tmp_path/"bulk",ids,owner)
    store.ingest_assets(rows(0,100),batch_id="batch-0001")
    with pytest.raises(ValueError,match="already exists"):
        store.ingest_assets(rows(100,1),batch_id="batch-0001")
    with sqlite3.connect(store.path) as db:
        db.execute("UPDATE assets SET record_sha256=? WHERE rowid=(SELECT MIN(rowid) FROM assets)",("f"*64,))
        db.commit()
    result=store.verify_batch("batch-0001",verify_rows=True)
    assert result["pass"] is False
    assert result["asset_rows_ok"] is False
