from __future__ import annotations
from pathlib import Path
import argparse, base64, hashlib, importlib.util, json, sqlite3, sys, time
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod

I=load("scale_identity",ROOT/"01_Core_Runtime"/"identity"/"canonical_identity.py")
L=load("scale_ledger",ROOT/"04_Entity_Registry"/"event_ledger"/"canonical_event_ledger.py")
R=load("scale_rights",ROOT/"04_Entity_Registry"/"ownership_graphs"/"canonical_rights_claims.py")
P=load("scale_provenance",ROOT/"04_Entity_Registry"/"provenance"/"canonical_provenance.py")
A=load("scale_assets",ROOT/"04_Entity_Registry"/"asset_registry"/"canonical_asset_registry.py")
B=load("scale_bulk",ROOT/"15_Operations"/"scale"/"canonical_bulk_ingest.py")

def sha_file(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()
def count(path,sql,args=()):
    with sqlite3.connect(path) as db: return int(db.execute(sql,args).fetchone()[0])

def verify_chain(ledger, identity, owner, sample_every=10000):
    manifest=identity.load_manifest(owner); prior=L.ZERO_HASH; n=0; sampled=0; failures=[]
    with sqlite3.connect(ledger.path) as db:
        db.row_factory=sqlite3.Row
        cur=db.execute("SELECT * FROM events ORDER BY sequence")
        for row in cur:
            n+=1
            body={"schema":row["schema_version"],"event_id":row["event_id"],"event_type":row["event_type"],"actor_entity_id":row["actor_entity_id"],"subject_ids":json.loads(row["subject_ids_json"]),"object_ids":json.loads(row["object_ids_json"]),"payload_hash":row["payload_hash"],"evidence_origin":row["evidence_origin"],"confidence":row["confidence"],"timestamp_ms":row["timestamp_ms"],"prior_hash":row["prior_hash"]}
            sig=json.loads(row["signature_json"])
            if row["prior_hash"]!=prior or L._sha({"body":body,"signature":sig})!=row["event_hash"]:
                failures.append({"sequence":row["sequence"],"reason":"hash_chain"}); break
            if n==1 or n % sample_every==0:
                if not I.EntityIdentityVault.verify_signature(manifest,body,sig): failures.append({"sequence":row["sequence"],"reason":"signature"}); break
                sampled+=1
            prior=row["event_hash"]
        head=db.execute("SELECT v FROM meta WHERE k='head_hash'").fetchone()[0]
    if head!=prior: failures.append({"reason":"head_mismatch"})
    return {"events_scanned":n,"sampled_signatures_verified":sampled,"full_hash_chain_verified":not failures,"failures":failures,"head_hash":head}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--state",required=True); ap.add_argument("--assets",type=int,default=1_000_000); ap.add_argument("--events",type=int,default=3_000_000); ap.add_argument("--batch-size",type=int,default=5000); ap.add_argument("--run-id",default="ENTITY-PROD-SCALE-v1")
    args=ap.parse_args(); state=Path(args.state); state.mkdir(parents=True,exist_ok=True)
    meta_path=state/"SCALE_RUN_META.json"; identity=I.EntityIdentityVault(state)
    if meta_path.exists(): meta=json.loads(meta_path.read_text()); owner=meta["owner_entity_id"]
    else:
        owner=identity.create("ENTITY Production Scale Qualification","organization")["entity_id"]
        meta={"owner_entity_id":owner,"run_id":args.run_id,"created_at_ms":int(time.time()*1000)}; meta_path.write_text(json.dumps(meta,indent=2,sort_keys=True)+"\n")
    ledger=L.CanonicalEventLedger(state,identity); rights=R.RightsClaimsGraph(state,identity); prov=P.AssetProvenanceGraph(state,identity); assets=A.CanonicalAssetRegistry(state,identity,ledger,rights,prov)
    bulk=B.CanonicalBulkAssetIngestor(state,identity,assets,ledger,rights,prov)
    extra=max(0,args.events-args.assets); started=time.time()
    asset_result=bulk.ingest_generated_assets(owner,count=args.assets,run_id=args.run_id,batch_size=args.batch_size,target_extra_events=extra)
    run=bulk._run(args.run_id,owner,args.assets,extra); event_result=bulk.append_generated_events(owner,count=extra,run_id=args.run_id,start_index=args.assets,base_ms=int(run["base_ms"]),batch_size=max(args.batch_size,10000)) if extra else {"events_completed":0,"seconds":0,"per_second":None}
    counts={"assets":count(assets.path,"SELECT COUNT(*) FROM assets"),"rights_claims":count(rights.path,"SELECT COUNT(*) FROM claims"),"rights_events":count(rights.path,"SELECT COUNT(*) FROM claim_events"),"provenance_bindings":count(prov.path,"SELECT COUNT(*) FROM bindings"),"ledger_events":count(ledger.path,"SELECT COUNT(*) FROM events")}
    chain=verify_chain(ledger,identity,owner,sample_every=10000)
    with sqlite3.connect(assets.path) as db:
        db.execute("ATTACH DATABASE ? AS rights",(str(rights.path),)); db.execute("ATTACH DATABASE ? AS prov",(str(prov.path),))
        semantic_mismatches=int(db.execute("SELECT COUNT(*) FROM assets a LEFT JOIN rights.claims c ON c.asset_id=a.asset_id AND c.right_type='DATA_CONTROLLER' LEFT JOIN prov.bindings p ON p.asset_id=a.asset_id WHERE c.claim_id IS NULL OR p.asset_id IS NULL OR p.content_sha256<>a.content_sha256").fetchone()[0])
    expected={"assets":args.assets,"rights_claims":args.assets,"rights_events":args.assets,"provenance_bindings":args.assets,"ledger_events":args.events}
    failures=[]
    for k,v in expected.items():
        if counts.get(k)!=v: failures.append(f"count_mismatch:{k}:{counts.get(k)}!={v}")
    if semantic_mismatches: failures.append(f"asset_rights_provenance_mismatch:{semantic_mismatches}")
    if chain["failures"]: failures.extend(["ledger_"+str(x) for x in chain["failures"]])
    db_files={"assets":assets.path,"rights":rights.path,"provenance":prov.path,"ledger":ledger.path,"bulk_receipts":bulk.receipts}
    files={k:{"path":str(p),"bytes":p.stat().st_size,"sha256":sha_file(p)} for k,p in db_files.items()}
    payload={"schema":"entity-production-scale-qualification-v1","generated_at_ms":int(time.time()*1000),"status":"PASS" if not failures else "FAIL","qualification_complete":not failures,"scope_status":"PASS_SCALE_VOLUME_SINGLE_WORKSTATION" if not failures else "FAIL","targets":{"assets":args.assets,"canonical_ledger_events":args.events},"counts":counts,"semantic_mismatches":semantic_mismatches,"asset_ingest":asset_result,"extra_event_ingest":event_result,"ledger_verification":chain,"elapsed_seconds":round(time.time()-started,3),"failures":failures,"state_root":str(state),"database_evidence":files,"limitations":["volume/throughput qualification executed on one workstation; distributed multi-machine storm is a separate qualification gate"]}
    body=dict(payload); payload["evidence_sha256"]=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
    out=ROOT/"16_Test_Qualification"/"evidence"/"ENTITY_PRODUCTION_SCALE_CURRENT.json"; out.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    out.with_suffix(".json.sha256").write_text(hashlib.sha256(out.read_bytes()).hexdigest()+"  "+out.name+"\n")
    print(json.dumps({"status":payload["status"],"scope_status":payload["scope_status"],"counts":counts,"semantic_mismatches":semantic_mismatches,"ledger_verification":chain,"elapsed_seconds":payload["elapsed_seconds"],"evidence_sha256":payload["evidence_sha256"]},indent=2)); return 0 if not failures else 2

if __name__=="__main__": raise SystemExit(main())
