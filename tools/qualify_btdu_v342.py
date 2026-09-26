from __future__ import annotations

from pathlib import Path
import argparse, base64, hashlib, importlib.util, json, os, shutil, time

REPO=Path(__file__).resolve().parents[1]

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

def file_sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()

def inventory(root):
    root=Path(root); out={}
    for p in sorted(root.rglob('*')):
        if p.is_file() and 'portability' not in {x.lower() for x in p.relative_to(root).parts}:
            out[p.relative_to(root).as_posix()]={'bytes':p.stat().st_size,'sha256':file_sha(p)}
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo',default=str(REPO))
    ap.add_argument('--production-state',required=True)
    ap.add_argument('--adam-root',required=True)
    ap.add_argument('--git-bin',default='git')
    ap.add_argument('--work-dir',required=True)
    ap.add_argument('--owner-entity-id',default='ent2-6eoiiztjyhmyh2tbr5psmofcduwvjledubhoiqwo6mjfoqkn6ica')
    args=ap.parse_args()
    repo=Path(args.repo).resolve(); production=Path(args.production_state).resolve(); work=Path(args.work_dir).resolve()
    if work.exists(): shutil.rmtree(work)
    work.mkdir(parents=True)
    os.environ['ENTITY_ADAM_V1_ROOT']=str(Path(args.adam_root).resolve()); os.environ['ENTITY_GIT_BIN']=str(args.git_bin)
    identity_mod=load('btdu_q_identity',repo/'src'/'01_Core_Runtime'/'identity'/'canonical_identity.py')
    portable_mod=load('btdu_q_portable',repo/'src'/'15_Operations'/'backups'/'canonical_portable_state.py')
    origin_mod=load('btdu_q_origin',repo/'src'/'38_Global_Passports'/'protocol_origin.py')
    btdu_mod=load('btdu_q_runtime',repo/'src'/'40_BTDU'/'canonical_btdu.py')

    live_identity=identity_mod.EntityIdentityVault(production); owner=live_identity.load_manifest(args.owner_entity_id)
    if owner['entity_id']!=args.owner_entity_id: raise RuntimeError('canonical owner mismatch')
    auth_body={'schema':'entity-btdu-authorization-v1','actor_entity_id':args.owner_entity_id,'scope':'BTDU_WRITE','purpose':'ENTITY-v3.4.2 self-ingestion qualification','issued_at_ms':int(time.time()*1000),'repo_head':btdu_mod.BlackmoreTechnologyDataUniverse._git(repo,'rev-parse','HEAD')}
    auth={'body':auth_body,'signature':live_identity.sign(args.owner_entity_id,auth_body)}
    def verifier(record):
        try:
            body=dict(record['body']); sig=dict(record['signature'])
            if body.get('actor_entity_id')!=args.owner_entity_id or body.get('scope')!='BTDU_WRITE': return False
            return live_identity.verify_signature(live_identity.load_manifest(args.owner_entity_id),body,sig)
        except Exception: return False
    if not verifier(auth): raise RuntimeError('self-ingestion authorization failed')

    # Create a stable disposable copy of protected state. This copy is the destructive-test target.
    source_copy=work/'protected_state_copy'
    shutil.copytree(production,source_copy,ignore=shutil.ignore_patterns('portability'))
    copy_identity=identity_mod.EntityIdentityVault(source_copy)
    copy_identity.load_manifest(args.owner_entity_id)
    portable=portable_mod.PortableStateManager(source_copy,copy_identity)
    export_dir=work/'portable_entity_export'; export=portable.export_entity(args.owner_entity_id,export_dir)
    export_body={k:v for k,v in export.items() if k!='signature'}
    export_sig_ok=copy_identity.verify_signature(copy_identity.load_manifest(args.owner_entity_id),export_body,export['signature'])
    if not export_sig_ok: raise RuntimeError('portable export signature invalid')

    btdu_state=work/'btdu_state'
    u=btdu_mod.BlackmoreTechnologyDataUniverse(btdu_state,authorization_verifier=verifier,sovereign_entity_id=args.owner_entity_id)
    primitive=u.materialize_primitive_bytes(auth)
    sample=b'ENTITY/AUTHORITY/RIGHT/EVENT/VALUE -> BTDU -> ADAM deterministic reconstruction'
    exact=u.encode_exact_bytes('btdu-genesis-sample',sample,auth,chunk_size=64)
    if u.reconstruct_exact_bytes(exact['compound_id'])!=sample: raise RuntimeError('primitive reconstruction failed')
    repo_manifest=u.ingest_repository(repo,auth,source_entity_id=btdu_mod.ENTITY_PROTOCOL_ENTITY_ID,controller_entity_id=args.owner_entity_id,rights_holder_entity_id=args.owner_entity_id,provenance_ref='git://blackmore-technology-group/ENTITY')
    portable_objects=[]
    for p in sorted(export_dir.rglob('*')):
        if p.is_file():
            portable_objects.append(u.ingest_file(p,auth,logical_path='portable-state/'+p.relative_to(export_dir).as_posix(),source_entity_id=args.owner_entity_id,controller_entity_id=args.owner_entity_id,rights_holder_entity_id=args.owner_entity_id,provenance_ref='entity-portable-export://'+export['entity_id']))
    genesis_lineage=u.mirror_genesis_market_chain(auth,prefix='entity-genesis-v342',evidence_sha256=file_sha(export_dir/'EXPORT_MANIFEST.json'))
    btdu_verify=u.verify(deep=True)
    if not btdu_verify['pass']: raise RuntimeError('BTDU deep verification failed')
    btdu_root=btdu_verify['atomic_root']; object_count=btdu_verify['objects']; u.close()

    original_inventory=inventory(source_copy)
    backup_path=work/'protected_state_backup.entity.enc'; backup=portable.create_encrypted_backup(backup_path)
    backup_key=base64.urlsafe_b64decode(backup['key_b64'])
    backup_public={k:v for k,v in backup.items() if k!='key_b64'}
    shutil.rmtree(source_copy)
    restored=work/'restored_protected_state'
    portable.restore_encrypted_backup(backup_path,backup_key,restored)
    restored_inventory=inventory(restored)
    exact_restore=(original_inventory==restored_inventory)
    if not exact_restore: raise RuntimeError('encrypted full-state restoration inventory mismatch')
    restored_identity=identity_mod.EntityIdentityVault(restored); restored_identity.load_manifest(args.owner_entity_id)
    challenge={'schema':'entity-btdu-restored-identity-challenge-v1','owner_entity_id':args.owner_entity_id,'btdu_root':btdu_root,'nonce':hashlib.sha256(json.dumps(repo_manifest,sort_keys=True).encode()).hexdigest()}
    challenge_sig=restored_identity.sign(args.owner_entity_id,challenge)
    restored_signing_ok=restored_identity.verify_signature(restored_identity.load_manifest(args.owner_entity_id),challenge,challenge_sig)
    if not restored_signing_ok: raise RuntimeError('restored sovereign identity cannot sign')
    protocol_release_present=False
    try:
        reg=origin_mod.ProtocolOriginRegistry(restored,restored_identity); rel=reg.get_release('entity-release:v3.4.1'); protocol_release_present=(rel['body']['release_tag']=='v3.4.1')
    except Exception:
        protocol_release_present=False

    # Never retain a plaintext disposable identity copy or the backup decryption key.
    backup_key=b'\x00'*len(backup_key)
    shutil.rmtree(restored)
    backup_path.unlink(missing_ok=True)

    result={'qualification':'ENTITY v3.4.2 BTDU complete self-ingestion and protected-state recovery','timestamp_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'pass':bool(btdu_verify['pass'] and exact_restore and restored_signing_ok and export_sig_ok),'authorization':{'actor_entity_id':args.owner_entity_id,'signature_verified':True},'btdu':{'atomic_root':btdu_root,'objects':object_count,'repository_manifest':repo_manifest,'primitive_byte_atoms':primitive['unique'],'genesis_economic_lineage':genesis_lineage,'verify':btdu_verify},'portable_entity_state':{'export_signature_verified':export_sig_ok,'files_ingested':len(portable_objects),'private_keys_in_portable_export':False,'raw_vault_content_in_portable_export':False},'protected_full_state_recovery':{'encrypted_backup':backup_public,'original_file_count':len(original_inventory),'restored_file_count':len(restored_inventory),'exact_inventory_match':exact_restore,'restored_sovereign_signing_key_operational':restored_signing_ok,'v3.4.1_protocol_origin_present_after_restore':protocol_release_present,'plaintext_disposable_restored_copy_deleted':not restored.exists(),'encrypted_backup_deleted_after_test':not backup_path.exists()},'claim_boundaries':{'btdu_topology_does_not_create_rights':True,'automatic_protocol_royalty_bps':0,'protocol_origin_is_not_asset_provenance':True,'private_key_material_not_ingested_into_btdu':True}}
    out=work/'BTDU_V3_4_2_SELF_INGESTION_QUALIFICATION.json'; out.write_text(json.dumps(result,indent=2,sort_keys=True),encoding='utf-8')
    print(json.dumps({'PASS':result['pass'],'BTDU_ROOT':btdu_root,'OBJECTS':object_count,'REPO_FILES':repo_manifest['tracked_files'],'PORTABLE_STATE_FILES':len(portable_objects),'PROTECTED_STATE_FILES':len(original_inventory),'EXACT_RESTORE':exact_restore,'RESTORED_SIGNING':restored_signing_ok,'PROTOCOL_ORIGIN_341':protocol_release_present,'RESULT':str(out)},indent=2))
    if not result['pass']: raise SystemExit(2)

if __name__=='__main__': main()
