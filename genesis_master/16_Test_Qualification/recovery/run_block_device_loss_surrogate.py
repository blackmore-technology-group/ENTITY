from __future__ import annotations
from pathlib import Path
import base64, hashlib, importlib.util, json, os, shutil, subprocess, sys, time

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
LAB=Path(r"<LOCAL_DRIVE>/ENTITY_MEDIA_LOSS_LAB")
VHD=LAB/"ENTITY_SACRIFICIAL_MEDIA.vhd"
LETTER="R"

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod

def sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def diskpart(lines):
    script=LAB/"diskpart.txt"; script.write_text("\n".join(lines)+"\n",encoding="ascii")
    run=subprocess.run(["diskpart","/s",str(script)],capture_output=True,text=True,timeout=120)
    if run.returncode!=0: raise RuntimeError(run.stdout+"\n"+run.stderr)
    return run.stdout
def create_media():
    LAB.mkdir(parents=True,exist_ok=True)
    if VHD.exists(): VHD.unlink()
    diskpart([f'create vdisk file="{VHD}" maximum=512 type=expandable',f'select vdisk file="{VHD}"','attach vdisk','create partition primary','format fs=ntfs quick label=ENTITY_LOSS',f'assign letter={LETTER}'])
    root=Path(f"{LETTER}:\\")
    if not root.exists(): raise RuntimeError("sacrificial virtual block device did not mount")
    return root

def destroy_media():
    diskpart([f'select vdisk file="{VHD}"','detach vdisk'])
    if Path(f"{LETTER}:\\").exists(): raise RuntimeError("virtual block device still mounted after detach")
    VHD.unlink()
    if VHD.exists(): raise RuntimeError("virtual media backing file still exists after deletion")

def snapshot(state,owner,I,L,R,P,A):
    ids=I.EntityIdentityVault(state); ledger=L.CanonicalEventLedger(state,ids); rights=R.RightsClaimsGraph(state,ids); prov=P.AssetProvenanceGraph(state,ids); assets=A.CanonicalAssetRegistry(state,ids,ledger,rights,prov)
    manifest=ids.load_manifest(owner); check=ledger.verify()
    import sqlite3
    def c(path,table):
        with sqlite3.connect(path) as db: return int(db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    return {"entity_id":owner,"manifest_valid":I.EntityIdentityVault.verify_manifest(manifest),"asset_count":c(assets.path,"assets"),"rights_claim_count":c(rights.path,"claims"),"provenance_binding_count":c(prov.path,"bindings"),"ledger_event_count":check["blocks"],"ledger_head_hash":check["head_hash"],"ledger_valid":check["pass"]}
def main():
    I=load("loss_identity",ROOT/"01_Core_Runtime"/"identity"/"canonical_identity.py")
    L=load("loss_ledger",ROOT/"04_Entity_Registry"/"event_ledger"/"canonical_event_ledger.py")
    R=load("loss_rights",ROOT/"04_Entity_Registry"/"ownership_graphs"/"canonical_rights_claims.py")
    P=load("loss_prov",ROOT/"04_Entity_Registry"/"provenance"/"canonical_provenance.py")
    A=load("loss_assets",ROOT/"04_Entity_Registry"/"asset_registry"/"canonical_asset_registry.py")
    B=load("loss_backup",ROOT/"15_Operations"/"backups"/"canonical_portable_state.py")
    LAB.mkdir(parents=True,exist_ok=True); restored=LAB/"restored_state"; shutil.rmtree(restored,ignore_errors=True)
    media=create_media(); state=media/"ENTITY_STATE"; ids=I.EntityIdentityVault(state); owner=ids.create("Sacrificial Media Entity","organization")["entity_id"]
    ledger=L.CanonicalEventLedger(state,ids); rights=R.RightsClaimsGraph(state,ids); prov=P.AssetProvenanceGraph(state,ids); assets=A.CanonicalAssetRegistry(state,ids,ledger,rights,prov)
    for i in range(50):
        digest=hashlib.sha256(f"physical-loss-asset-{i}".encode()).hexdigest()
        assets.register(owner,content_sha256=digest,size_bytes=i+1,media_type="application/octet-stream",title=f"Loss Asset {i}")
    before=snapshot(state,owner,I,L,R,P,A)
    manager=B.PortableStateManager(state,ids); backup_path=LAB/"ENTITY_MEDIA_LOSS_BACKUP.enc"; backup=manager.create_encrypted_backup(backup_path)
    key=base64.urlsafe_b64decode(backup["key_b64"]); key_fingerprint=hashlib.sha256(key).hexdigest(); media_size=VHD.stat().st_size; media_sha=sha(VHD)
    destroy_media(); manager.restore_encrypted_backup(backup_path,key,restored)
    after=snapshot(restored,owner,I,L,R,P,A)
    same=before==after
    payload={"schema":"entity-block-device-loss-surrogate-v1","generated_at_ms":int(time.time()*1000),"status":"PASS" if same else "FAIL","qualification_complete":same,"scope_status":"PASS_BLOCK_DEVICE_LOSS_SURROGATE" if same else "FAIL","physical_media_destroyed":False,"whole_block_device_removed":True,"backing_media_deleted":not VHD.exists(),"drive_letter_removed":not Path(f"{LETTER}:\\").exists(),"before":before,"after":after,"backup":{"path":str(backup_path),"sha256":backup["sha256"],"bytes":backup["bytes"],"cipher":backup["cipher"],"key_fingerprint_sha256":key_fingerprint,"raw_key_recorded":False},"sacrificial_media":{"type":"expandable_vhd","size_bytes_before_deletion":media_size,"sha256_before_deletion":media_sha,"backing_path":str(VHD)},"limitations":["safe whole-block-device disappearance surrogate; no physical storage hardware was destroyed remotely"]}
    body=dict(payload); payload["evidence_sha256"]=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
    out=ROOT/"16_Test_Qualification"/"evidence"/"ENTITY_BLOCK_DEVICE_LOSS_CURRENT.json"; out.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8"); out.with_suffix(".json.sha256").write_text(hashlib.sha256(out.read_bytes()).hexdigest()+"  "+out.name+"\n")
    print(json.dumps({"status":payload["status"],"scope_status":payload["scope_status"],"whole_block_device_removed":payload["whole_block_device_removed"],"before":before,"after":after,"evidence_sha256":payload["evidence_sha256"]},indent=2)); return 0 if same else 2

if __name__=="__main__": raise SystemExit(main())
