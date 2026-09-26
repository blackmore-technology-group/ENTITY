from pathlib import Path
import hashlib, importlib.util, sqlite3, sys
import pytest

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); assert spec and spec.loader
    mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod
I=load("seg_identity",ROOT/"01_Core_Runtime"/"identity"/"canonical_identity.py")
S=load("seg_store",ROOT/"04_Entity_Registry"/"bulk_ingest"/"canonical_segmented_bulk_ingest.py")

def rows(start,count):
    for i in range(start,start+count):
        yield {"content_sha256":hashlib.sha256(f"seg-{i}".encode()).hexdigest(),"size_bytes":i+1,"media_type":"application/octet-stream","title":f"seg-{i}","metadata":{"ordinal":i}}

def test_segment_chain_and_full_verification(tmp_path):
    ids=I.EntityIdentityVault(tmp_path/"identity")
    owner=ids.create("Segment Owner","organization")["entity_id"]
    store=S.CanonicalSegmentedBulkStore(tmp_path/"bulk",ids,owner)
    a=store.ingest_segment(rows(0,250),batch_id="seg-0001")
    b=store.ingest_segment(rows(250,250),batch_id="seg-0002")
    assert a["asset_count"]==250 and a["event_count"]==750
    assert b["prior_batch_hash"]==a["batch_hash"]
    result=store.verify_all(full_rows=True)
    assert result["pass"] is True and result["assets"]==500 and result["events"]==1500
    assert store.status()["orphan_segments"]==[]

def test_duplicate_and_segment_tamper_are_rejected(tmp_path):
    ids=I.EntityIdentityVault(tmp_path/"identity")
    owner=ids.create("Segment Owner","organization")["entity_id"]
    store=S.CanonicalSegmentedBulkStore(tmp_path/"bulk",ids,owner)
    out=store.ingest_segment(rows(0,100),batch_id="seg-0001")
    with pytest.raises(ValueError,match="already exists"):
        store.ingest_segment(rows(100,1),batch_id="seg-0001")
    path=Path(out["segment_path"])
    with sqlite3.connect(path) as db:
        db.execute("UPDATE assets SET record_sha256=? WHERE asset_ordinal=0",("f"*64,)); db.commit()
    result=store.verify_segment("seg-0001",full_rows=True)
    assert result["pass"] is False
    assert result["segment_file_ok"] is False or result["asset_merkle_ok"] is False
