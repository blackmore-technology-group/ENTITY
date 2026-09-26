from pathlib import Path
import hashlib, importlib.util, json, os, sqlite3, sys, time

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
WORK=Path(r"<LOCAL_DRIVE>/ENTITY_QUALIFICATION_SCALE\million_asset_v2")
OUT=ROOT/"16_Test_Qualification"/"evidence"/"ENTITY_MILLION_ASSET_SCALE_CURRENT.json"
TARGET_ASSETS=1_000_000
BATCH_SIZE=10_000
EXPECTED_EVENTS=TARGET_ASSETS*3


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); assert spec and spec.loader
    mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod

I=load("million_identity",ROOT/"01_Core_Runtime"/"identity"/"canonical_identity.py")
B=load("million_bulk",ROOT/"04_Entity_Registry"/"bulk_ingest"/"canonical_bulk_ingest.py")


def file_sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()


def records(start: int, count: int):
    for i in range(start,start+count):
        yield {
            "content_sha256":hashlib.sha256(f"million-asset-{i}".encode()).hexdigest(),
            "size_bytes":1+(i%1_000_000),
            "media_type":"application/octet-stream",
            "title":f"million-asset-{i}",
            "classification":"PRIVATE",
            "metadata":{"ordinal":i,"scale_tier":"million_asset_v1"},
        }


def seal(payload: dict) -> dict:
    body=dict(payload); body.pop("evidence_sha256",None)
    payload["evidence_sha256"]=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
    return payload


def main():
    WORK.mkdir(parents=True,exist_ok=True)
    identity_state=WORK/"identity_state"; run_manifest=WORK/"RUN_MANIFEST.json"
    ids=I.EntityIdentityVault(identity_state)
    if run_manifest.is_file():
        run=json.loads(run_manifest.read_text(encoding="utf-8")); owner=run["owner_entity_id"]
    else:
        owner=ids.create("Million Asset Scale Owner","organization")["entity_id"]
        run={"schema":"entity-million-asset-run-v1","owner_entity_id":owner,"target_assets":TARGET_ASSETS,"expected_events":EXPECTED_EVENTS,"created_at_ms":int(time.time()*1000)}
        run_manifest.write_text(json.dumps(run,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    store=B.CanonicalBulkIngestStore(WORK/"store",ids,owner)
    initial=store.status(); completed_assets=int(initial["assets"])
    if completed_assets % BATCH_SIZE:
        raise RuntimeError(f"partial batch state is not resumable safely: assets={completed_assets}")
    started=time.perf_counter(); batch_times=[]
    for batch_index,start in enumerate(range(completed_assets,TARGET_ASSETS,BATCH_SIZE),start=completed_assets//BATCH_SIZE):
        count=min(BATCH_SIZE,TARGET_ASSETS-start); batch_id=f"million-{batch_index:06d}"
        t=time.perf_counter(); result=store.ingest_assets(records(start,count),batch_id=batch_id); elapsed=time.perf_counter()-t
        batch_times.append(elapsed)
        progress={"batch":batch_id,"assets_complete":start+count,"events_complete":int((start+count)*3),"batch_seconds":round(elapsed,3),"batch_hash":result["batch_hash"]}
        print(json.dumps(progress),flush=True)
        (WORK/"PROGRESS.json").write_text(json.dumps(progress,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    ingestion_seconds=time.perf_counter()-started
    status=store.status()
    if status["assets"]!=TARGET_ASSETS or status["events"]!=EXPECTED_EVENTS:
        raise RuntimeError(f"scale counts wrong: {status}")

    index_started=time.perf_counter()
    index_result=store.finalize_indexes()
    index_seconds=time.perf_counter()-index_started
    verify_started=time.perf_counter()
    verification=store.verify_all_batches(verify_rows=True)
    verify_seconds=time.perf_counter()-verify_started
    if verification.get("pass") is not True:
        raise RuntimeError(f"full bulk verification failed: {verification}")
    with sqlite3.connect(store.path,timeout=120) as db:
        db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    db_size=store.path.stat().st_size
    db_sha=file_sha256(store.path)
    total_seconds=ingestion_seconds+verify_seconds
    payload=seal({
        "schema":"entity-million-asset-scale-qualification-v1",
        "generated_at_ms":int(time.time()*1000),
        "status":"PASS",
        "qualification_complete":True,
        "scope":"single-workstation production bulk-ingest durability/verification tier",
        "limitations":["does not satisfy the separate distributed multi-machine storm requirement"],
        "targets":{"assets":TARGET_ASSETS,"events":EXPECTED_EVENTS,"batch_size":BATCH_SIZE},
        "observed":{"assets":status["assets"],"events":status["events"],"batches":status["batches"],"ingestion_seconds":round(ingestion_seconds,3),"index_build_seconds":round(index_seconds,3),"verification_seconds":round(verify_seconds,3),"total_seconds":round(total_seconds+index_seconds,3),"asset_ingest_per_second":round(TARGET_ASSETS/ingestion_seconds,2) if ingestion_seconds else None,"event_ingest_per_second":round(EXPECTED_EVENTS/ingestion_seconds,2) if ingestion_seconds else None},
        "index_build":index_result,"verification":verification,
        "database":{"path":str(store.path),"size_bytes":db_size,"sha256":db_sha},
        "semantics":{"signed_batch_attestations":True,"per_asset_hard_hash":True,"continuous_event_hash_chain":True,"registration_not_ownership":True,"batch_attestation_not_legal_truth":True},
        "source_sha256":{"bulk_ingest":file_sha256(ROOT/"04_Entity_Registry"/"bulk_ingest"/"canonical_bulk_ingest.py"),"runner":file_sha256(Path(__file__))},
    })
    OUT.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    OUT.with_suffix(".json.sha256").write_text(file_sha256(OUT)+"  "+OUT.name+"\n",encoding="utf-8")
    print(json.dumps({"status":"PASS","assets":TARGET_ASSETS,"events":EXPECTED_EVENTS,"batches":status["batches"],"evidence_sha256":payload["evidence_sha256"],"database_size_bytes":db_size,"output":str(OUT)},indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
