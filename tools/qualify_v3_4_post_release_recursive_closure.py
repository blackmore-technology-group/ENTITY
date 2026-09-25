from __future__ import annotations
import base64, hashlib, importlib.util, json, os, pathlib, shutil, sqlite3, sys

ROOT=pathlib.Path(__file__).resolve().parents[1]
INPUT=pathlib.Path(os.environ.get("ENTITY_V34_CLOSURE_INPUT",str(ROOT.parent/"ENTITY_V3_4_POST_RELEASE_INPUTS_20260924")))
STATE=pathlib.Path(os.environ.get("ENTITY_V34_CLOSURE_STATE",str(ROOT.parent/"_ENTITY_V3_4_POST_RELEASE_CLOSURE_STATE")))
ART=pathlib.Path(os.environ.get("ENTITY_V34_CLOSURE_ARTIFACTS",str(ROOT.parent/"ENTITY_V3_4_POST_RELEASE_CLOSURE_EVIDENCE")))
CAPTURE=INPUT/"POST_RELEASE_CAPTURE_MANIFEST_2026-09-24.json"
PUB_JSON=ROOT/"docs/qualification/ENTITY_V3_4_0_POST_RELEASE_RECURSIVE_CLOSURE_2026-09-24.json"
PUB_MD=ROOT/"docs/qualification/ENTITY_V3_4_0_POST_RELEASE_RECURSIVE_CLOSURE_2026-09-24.md"
CATALOG=ROOT/"docs/qualification/ENTITY_V3_4_0_POST_RELEASE_RECURSIVE_CLOSURE_CATALOG_2026-09-24.json"
PROFILES=["entity-profile:global@1.0","entity-profile:ai@1.0"]

def load(name,rel):
    spec=importlib.util.spec_from_file_location(name,ROOT/rel)
    mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod

def sha_bytes(data:bytes)->str: return hashlib.sha256(data).hexdigest()
def sha_file(path:pathlib.Path)->str: return sha_bytes(path.read_bytes())
def canon(value)->bytes: return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()

def tree_root(root:pathlib.Path,*,exclude_portability=True)->dict:
    rows=[]
    for p in sorted(root.rglob("*")):
        if not p.is_file(): continue
        rel=p.relative_to(root).as_posix()
        if exclude_portability and "portability" in {x.lower() for x in p.relative_to(root).parts}: continue
        rows.append((rel,sha_file(p),p.stat().st_size))
    material="\n".join(f"{rel}|{sha}|{size}" for rel,sha,size in rows).encode()
    return {"files":len(rows),"bytes":sum(x[2] for x in rows),"sha256":sha_bytes(material)}

def vault_root(root:pathlib.Path)->dict:
    vault=root/"content_vault"/"sha256"; rows=[]
    if vault.exists():
        for p in sorted(vault.rglob("*")):
            if p.is_file(): rows.append((p.relative_to(vault).as_posix(),sha_file(p),p.stat().st_size))
    material="\n".join(f"{rel}|{sha}|{size}" for rel,sha,size in rows).encode()
    return {"files":len(rows),"bytes":sum(x[2] for x in rows),"sha256":sha_bytes(material)}

def checkpoint(root:pathlib.Path):
    for p in root.rglob("*.sqlite"):
        try:
            with sqlite3.connect(p) as db: db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except sqlite3.Error: pass

def sqlite_semantic_root(root:pathlib.Path)->dict:
    parts=[]; table_count=0; row_count=0
    for path in sorted(root.rglob("*.sqlite")):
        if "portability" in {x.lower() for x in path.relative_to(root).parts}: continue
        db=sqlite3.connect(path); db.row_factory=sqlite3.Row
        try:
            tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
            for table in tables:
                q='SELECT * FROM "'+str(table).replace('"','""')+'"'
                rows=[dict(r) for r in db.execute(q).fetchall()]
                encoded=sorted(json.dumps(r,sort_keys=True,separators=(",",":"),default=str) for r in rows)
                h=sha_bytes("\n".join(encoded).encode())
                parts.append(f"{path.relative_to(root).as_posix()}|{table}|{len(rows)}|{h}")
                table_count+=1; row_count+=len(rows)
        finally: db.close()
    return {"databases":len(list(root.rglob('*.sqlite'))),"tables":table_count,"rows":row_count,
            "sha256":sha_bytes("\n".join(parts).encode())}

def db_counts(root:pathlib.Path)->dict:
    queries={"objects":("entity_v3/universal_fabric.sqlite","objects"),"rights":("entity_v3/universal_fabric.sqlite","rights"),
             "values":("entity_v3/universal_fabric.sqlite","value_records"),"provenance_edges":("entity_v3/universal_fabric.sqlite","provenance_edges"),
             "evidence_objects":("entity_v3_3_evidence.sqlite","evidence"),"rights_passports":("entity_v3_2_rights_passports.sqlite","passports"),
             "global_passports":("entity_v3_4_global_passports.sqlite","global_passports")}
    out={}
    for key,(rel,table) in queries.items():
        with sqlite3.connect(root/rel) as db: out[key]=int(db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    return out

def evidence_get(registry,evidence_id:str)->dict:
    with sqlite3.connect(registry.path) as db:
        db.row_factory=sqlite3.Row
        row=db.execute("SELECT body_json,body_sha256,signature_json FROM evidence WHERE evidence_id=?",(evidence_id,)).fetchone()
    if not row: raise KeyError(evidence_id)
    return dict(json.loads(row["body_json"]),body_sha256=row["body_sha256"],signature=json.loads(row["signature_json"]))

def validate_capture(capture:dict):
    if capture.get("constituents")!=1040: raise RuntimeError("capture constituent count drift")
    if capture.get("constituent_root_sha256")!="4feb51a4bd0d958b7beb3eddbe9fd78678b7c31c2a4fe3d6cf7d9f4d87aa6e06": raise RuntimeError("capture root drift")
    if capture.get("release",{}).get("commit")!="2db5bff64507b8d67642122a5ff2fc73dfef9152": raise RuntimeError("release commit drift")
    for row in capture["records"]:
        p=pathlib.Path(row["source_path"])
        if not p.is_file() or sha_file(p)!=row["sha256"] or p.stat().st_size!=row["bytes"]: raise RuntimeError("capture file drift: "+row["logical_path"])
    release=json.loads((INPUT/"github_evidence/ENTITY_release_v3.4.0.json").read_text(encoding="utf-8-sig"))
    tag=json.loads((INPUT/"github_evidence/ENTITY_tag_v3.4.0.json").read_text(encoding="utf-8-sig"))
    pr=json.loads((INPUT/"github_evidence/ENTITY_PR_41.json").read_text(encoding="utf-8-sig"))
    if release.get("tag_name")!="v3.4.0" or release.get("target_commitish")!=capture["release"]["commit"]: raise RuntimeError("release object mismatch")
    if tag.get("object",{}).get("sha")!=capture["release"]["commit"]: raise RuntimeError("tag object mismatch")
    if not pr.get("merged") or pr.get("merge_commit_sha")!=capture["release"]["commit"]: raise RuntimeError("PR merge mismatch")
    for p in (INPUT/"github_evidence").glob("*_run_*.json"):
        run=json.loads(p.read_text(encoding="utf-8-sig"))
        if run.get("status")!="completed" or run.get("conclusion")!="success": raise RuntimeError("non-success captured workflow: "+p.name)
    pub=json.loads((INPUT/"evidence_files/GITHUB_PUBLICATION_VERIFICATION_2026-09-24.json").read_text(encoding="utf-8-sig"))
    if pub.get("status")!="PASS" or any(x.get("workflow_conclusion")!="success" for x in pub.get("repositories",[])): raise RuntimeError("domain publication evidence invalid")

identity_mod=load("closure_identity","src/01_Core_Runtime/identity/canonical_identity.py")
fabric_mod=load("closure_fabric","src/30_Universal_Transaction_Fabric/canonical_universal_fabric.py")
rights_mod=load("closure_rights","src/36_Adoption_Layer/rights_passport.py")
load("reality_profile","src/37_Verifiable_Reality/reality_profile.py")
evidence_mod=load("closure_evidence","src/37_Verifiable_Reality/evidence_objects.py")
profile_mod=load("closure_profiles","src/38_Global_Passports/profile_registry.py")
industry_mod=load("closure_industry","src/38_Global_Passports/industry_profiles.py")
global_mod=load("closure_global","src/38_Global_Passports/global_passport.py")
ingest_mod=load("closure_ingest","src/38_Global_Passports/continuous_ingestion.py")
portable_mod=load("closure_portable","src/15_Operations/backups/canonical_portable_state.py")

def build_runtime(state:pathlib.Path,create=False):
    identity=identity_mod.EntityIdentityVault(state); fabric=fabric_mod.UniversalTransactionFabric(state,identity)
    evidence=evidence_mod.EvidenceRegistry(state,identity); rights=rights_mod.RightsPassportRegistry(state,identity,fabric)
    profiles=profile_mod.GlobalProfileRegistry(state,identity)
    if create:
        controller=identity.create("ENTITY v3.4 Post-Release Recursive Closure","organization")["entity_id"]
        industry_mod.install_builtin_profiles(profiles,controller)
    else: controller=None
    passports=global_mod.GlobalPassportRegistry(state,identity,fabric,rights,profiles)
    ingestion=ingest_mod.ContinuousProvenanceEngine(state,identity,fabric,evidence,rights,passports)
    portable=portable_mod.PortableStateManager(state,identity)
    return {"identity":identity,"fabric":fabric,"evidence":evidence,"rights":rights,"profiles":profiles,
            "passports":passports,"ingestion":ingestion,"portable":portable,"controller":controller}

def main():
    capture=json.loads(CAPTURE.read_text(encoding="utf-8")); validate_capture(capture)
    for p in (STATE,ART):
        if p.exists(): shutil.rmtree(p)
    STATE.mkdir(parents=True); ART.mkdir(parents=True)
    rt=build_runtime(STATE,create=True); controller=rt["controller"]
    cached=rt["identity"].open_signing_session(controller); original_sign=rt["identity"].sign
    rt["identity"].sign=lambda entity_id,payload: cached(payload) if entity_id==controller else original_sign(entity_id,payload)
    anchor=rt["ingestion"].ingest_file(CAPTURE,controller,PROFILES,
        logical_path="closure/POST_RELEASE_CAPTURE_MANIFEST_2026-09-24.json",version="3.4.0-post-release-closure")
    if not rt["passports"].verify(anchor["global_passport"])["valid"]: raise RuntimeError("anchor passport invalid")
    records=[]
    for i,row in enumerate(capture["records"],1):
        item=rt["ingestion"].ingest_file(row["source_path"],controller,PROFILES,
            logical_path=row["logical_path"],version="3.4.0-post-release-closure")
        if item["object"]["content_sha256"]!=row["sha256"]: raise RuntimeError("ingest hash mismatch: "+row["logical_path"])
        if not rt["passports"].verify(item["global_passport"])["valid"]: raise RuntimeError("global passport invalid: "+row["logical_path"])
        edge=rt["fabric"].add_provenance(controller,anchor["object"]["object_id"],item["object"]["object_id"],
            "POST_RELEASE_CLOSURE_CONSTITUENT",contribution_bps=0,evidence={"evidence_id":item["evidence"]["evidence_id"],"content_sha256":row["sha256"]})
        records.append({"logical_path":row["logical_path"],"category":row["category"],"bytes":row["bytes"],
            "content_sha256":row["sha256"],"object_id":item["object"]["object_id"],"evidence_id":item["evidence"]["evidence_id"],
            "right_id":item["right"]["right_id"],"rights_passport_id":item["rights_passport"]["passport_id"],
            "global_passport_id":item["global_passport"]["passport_id"],"global_passport_sha256":item["global_passport"]["body_sha256"],
            "value_id":item["value"]["value_id"],"provenance_edge_id":edge["edge_id"]})
        if i%100==0 or i==len(capture["records"]): print(json.dumps({"ingested":i,"total":len(capture["records"])}),flush=True)
    material="\n".join(f"{r['content_sha256']}  {r['logical_path']}" for r in records).encode()
    ingested_root=sha_bytes(material)
    if ingested_root!=capture["constituent_root_sha256"]: raise RuntimeError("ENTITY-ingested constituent root differs from frozen capture")
    counts_before=db_counts(STATE)
    expected=len(records)+1
    for key in ("objects","rights","values","evidence_objects","rights_passports","global_passports"):
        if counts_before[key]!=expected: raise RuntimeError(f"count mismatch {key}: {counts_before[key]} != {expected}")
    if counts_before["provenance_edges"]!=len(records): raise RuntimeError("provenance edge count mismatch")
    export_dir=ART/"sovereign_export"
    export=rt["portable"].export_entity(controller,export_dir)
    export_root=tree_root(export_dir,exclude_portability=False)
    checkpoint(STATE)
    state_before=tree_root(STATE)
    semantic_before=sqlite_semantic_root(STATE)
    vault_before=vault_root(STATE)
    backup_path=ART/"ENTITY_V3_4_POST_RELEASE_CLOSURE_STATE.aes256gcm"
    backup=rt["portable"].create_encrypted_backup(backup_path)
    recovery_material=base64.urlsafe_b64decode(backup["key_b64"])
    backup_public={"sha256":backup["sha256"],"bytes":backup["bytes"],"encrypted":backup["encrypted"],"cipher":backup["cipher"]}
    shutil.rmtree(STATE)
    if STATE.exists(): raise RuntimeError("destructive state deletion failed")
    rt["portable"].restore_encrypted_backup(backup_path,recovery_material,STATE)
    checkpoint(STATE)
    state_after=tree_root(STATE)
    semantic_after=sqlite_semantic_root(STATE)
    vault_after=vault_root(STATE)
    if state_before!=state_after: raise RuntimeError("exact state tree changed across destructive recovery")
    if semantic_before!=semantic_after: raise RuntimeError("semantic database root changed across destructive recovery")
    if vault_before!=vault_after: raise RuntimeError("content vault root changed across destructive recovery")
    restored=build_runtime(STATE,create=False)
    manifest=restored["identity"].load_manifest(controller)
    if not restored["identity"].verify_manifest(manifest): raise RuntimeError("controller identity failed after recovery")
    verification_rows=[{"logical_path":"closure/POST_RELEASE_CAPTURE_MANIFEST_2026-09-24.json","category":"closure_anchor",
        "bytes":CAPTURE.stat().st_size,"content_sha256":anchor["object"]["content_sha256"],"object_id":anchor["object"]["object_id"],
        "evidence_id":anchor["evidence"]["evidence_id"],"rights_passport_id":anchor["rights_passport"]["passport_id"],
        "global_passport_id":anchor["global_passport"]["passport_id"],"global_passport_sha256":anchor["global_passport"]["body_sha256"]}]+records
    failures=[]
    for i,row in enumerate(verification_rows,1):
        try:
            obj=restored["fabric"].get_object(row["object_id"])
            if obj.get("content_sha256")!=row["content_sha256"]: raise RuntimeError("object content hash")
            if obj.get("descriptor",{}).get("logical_path")!=row["logical_path"]: raise RuntimeError("logical path")
            ev=evidence_get(restored["evidence"],row["evidence_id"])
            if not restored["evidence"].verify_evidence(ev)["valid"]: raise RuntimeError("evidence")
            rp=restored["rights"].get(row["rights_passport_id"])
            if not restored["rights"].verify(rp)["valid"]: raise RuntimeError("rights passport")
            gp=restored["passports"].get(row["global_passport_id"])
            if gp.get("body_sha256")!=row["global_passport_sha256"] or not restored["passports"].verify(gp)["valid"]: raise RuntimeError("global passport")
            vp=STATE/"content_vault"/"sha256"/row["content_sha256"][:2]/row["content_sha256"]
            if not vp.is_file() or sha_file(vp)!=row["content_sha256"]: raise RuntimeError("vault content")
        except Exception as exc: failures.append({"logical_path":row["logical_path"],"reason":str(exc)})
        if i%200==0 or i==len(verification_rows): print(json.dumps({"reverified":i,"total":len(verification_rows),"failures":len(failures)}),flush=True)
    if failures: raise RuntimeError("post-recovery verification failures: "+json.dumps(failures[:5]))
    counts_after=db_counts(STATE)
    if counts_after!=counts_before: raise RuntimeError("record counts changed across recovery")
    catalog={"schema":"entity-v3-4-post-release-recursive-closure-catalog-v1","date":"2026-09-24",
        "target_release":"v3.4.0","target_release_commit":capture["release"]["commit"],"controller_entity_id":controller,
        "capture_constituent_root_sha256":capture["constituent_root_sha256"],"records":verification_rows,
        "claim_boundary":"BTG-controlled provenance evidence; not independent third-party validation, objective external truth, legal/regulatory approval, market adoption, or accounting fair value."}
    CATALOG.parent.mkdir(parents=True,exist_ok=True)
    CATALOG.write_text(json.dumps(catalog,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    category_counts={}
    for row in capture["records"]: category_counts[row["category"]]=category_counts.get(row["category"],0)+1
    report={"schema":"entity-v3-4-post-release-recursive-closure-v1","version":"3.4.0","date":"2026-09-24","status":"PASS",
        "campaign":"ENTITY v3.4.0 complete post-publication recursive closure","controller_entity_id":controller,
        "target":{"repository":"blackmore-technology-group/ENTITY","tag":"v3.4.0","commit":capture["release"]["commit"],"pull_request":41,"release_id":396162815,
                  "captured_repository_heads":capture["repo_heads"]},
        "coverage":{"constituents":capture["constituents"],"constituent_bytes":capture["constituent_bytes"],"closure_anchor_objects":1,
                    "total_ingested_objects":len(verification_rows),"category_counts":category_counts,"git_tracked_files":984,
                    "github_api_evidence_records":45,"release_evidence_artifacts":11},
        "roots":{"git_blob_inventory_sha256":capture["git_blob_root_sha256"],"frozen_constituent_root_sha256":capture["constituent_root_sha256"],
                 "entity_ingested_constituent_root_sha256":ingested_root,"capture_manifest_sha256":sha_file(CAPTURE),
                 "state_tree_before_destruction":state_before,"state_tree_after_recovery":state_after,
                 "sqlite_semantic_before_destruction":semantic_before,"sqlite_semantic_after_recovery":semantic_after,
                 "content_vault_before_destruction":vault_before,"content_vault_after_recovery":vault_after,
                 "sovereign_export_tree":export_root,"sovereign_export_manifest_sha256":sha_file(export_dir/"EXPORT_MANIFEST.json")},
        "entity_native_records":counts_after,"destructive_recovery":{"performed":True,"identical_state_tree":state_before==state_after,
                 "identical_sqlite_semantics":semantic_before==semantic_after,"identical_content_vault":vault_before==vault_after,
                 "all_objects_evidence_rights_passports_global_passports_and_vault_bytes_reverified":True,"encrypted_backup":backup_public},
        "release_evidence":{"final_public_conformance_run":36074202905,"final_codeql_run":36074203138,"publisher_run":36074265814,
                 "cleanroom_v3_4_result_sha256":"ac7504cce70576008cff069607619660a4b9bf0cad43b3f3de81078f1e80d9ba"},
        "closure_definition":{"immutable_target_is_v3_4_0_release_and_captured_external_repository_heads":True,
                 "later_publication_of_this_closure_report_is_not_part_of_the_frozen_target":True,
                 "reason":"Requiring a closure record to ingest the event that publishes that same record would create non-terminating self-reference."},
        "claim_boundary":{"btg_controlled_evidence_is_not_independent_third_party_validation":True,"objective_external_truth_claimed":False,
                 "legal_or_regulatory_compliance_claimed":False,"independent_security_review_claimed":False,"market_adoption_or_liquidity_claimed":False,
                 "accounting_fair_value_claimed":False,"custody_is_authority":False,"economic_value_invented":False}}
    PUB_JSON.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    md=f"""# ENTITY v3.4.0 Post-Release Recursive Closure — 2026-09-24

**Status: PASS**

This campaign closes the post-publication recursive provenance gap for the immutable ENTITY `v3.4.0` release at `{capture['release']['commit']}`.

## Frozen target

- ENTITY `v3.4.0` exact Git tree plus its final release/PR/CI/publisher evidence.
- Six BTG-controlled v3.4 clean-room repositories at captured `main` commits.
- `ENTITY-GITHUB-APP` at its captured qualified `main` commit plus installation/webhook evidence.
- Six published v3.4 domain repositories and their sealed archive evidence.
- Exact Git blob bytes were used; Windows checkout line-ending transformations were not trusted.

## Coverage

- Git-tracked source/repository files: **984**
- GitHub API evidence records: **45**
- Additional release evidence artifacts: **11**
- Frozen constituents: **{capture['constituents']}**
- Frozen constituent bytes: **{capture['constituent_bytes']:,}**
- ENTITY-native ingested objects including closure anchor: **{len(verification_rows)}**

## Canonical roots

- Git blob inventory: `{capture['git_blob_root_sha256']}`
- Frozen constituent root: `{capture['constituent_root_sha256']}`
- ENTITY-ingested constituent root: `{ingested_root}`
"""
    md+=f"""
## ENTITY-native governed state

- ENTITY objects: **{counts_after['objects']}**
- signed Evidence Objects: **{counts_after['evidence_objects']}**
- rights records: **{counts_after['rights']}**
- Rights Passports: **{counts_after['rights_passports']}**
- Global Passports: **{counts_after['global_passports']}**
- explicit zero-value records: **{counts_after['values']}**
- zero-weight provenance edges from closure anchor: **{counts_after['provenance_edges']}**

Each constituent is recoverable from the content-addressed ENTITY vault and is bound to an ENTITY object, signed evidence, rights record, Rights Passport, Global Passport and zero-value economic baseline. The zero-weight provenance edges describe membership in the closure corpus; they do not invent contribution percentages or ownership.

## Destructive recovery proof

The generated closure state was encrypted using AES-256-GCM, deleted, restored, and re-opened. The exact state tree, canonical SQLite semantic root and content-vault root were identical before destruction and after recovery.

- state tree: `{state_before['sha256']}`
- SQLite semantic root: `{semantic_before['sha256']}`
- content vault root: `{vault_before['sha256']}`
- sovereign export tree: `{export_root['sha256']}`

All **{len(verification_rows)}** registered objects were rechecked after recovery; their vault bytes, Evidence Objects, Rights Passports and Global Passports all verified.
"""
    md+="""
## Closure boundary

The frozen closure target is the immutable `v3.4.0` release plus the external BTG-controlled repositories/evidence captured for this campaign. This report and its later publication commit are intentionally outside that frozen target: requiring a record to ingest the event that publishes that same record would create non-terminating self-reference rather than a meaningful finite closure.

## Claim boundary

This is a BTG-controlled recursive qualification. It proves content integrity, attributable provenance, governed rights/passport registration, release-evidence capture and destructive recovery for the named frozen corpus. It does **not** establish objective external truth, unrelated third-party interoperability, independent security review, legal or regulatory compliance, market adoption/liquidity, legal ownership, or accounting fair value. Provider custody remains non-authoritative, and no monetary value or historical contribution percentage was invented.
"""
    PUB_MD.write_text(md,encoding="utf-8")
    print(json.dumps({"status":"PASS","constituents":capture["constituents"],"ingested_objects":len(verification_rows),
        "constituent_root_sha256":capture["constituent_root_sha256"],"state_root_sha256":state_after["sha256"],
        "semantic_root_sha256":semantic_after["sha256"],"vault_root_sha256":vault_after["sha256"],
        "sovereign_export_root_sha256":export_root["sha256"],"public_json":str(PUB_JSON),"public_md":str(PUB_MD),"catalog":str(CATALOG)},indent=2))

if __name__=="__main__": main()
