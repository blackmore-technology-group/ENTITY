from __future__ import annotations
from pathlib import Path
import base64, hashlib, json, os, re, secrets, shutil, sqlite3, tempfile, time, zipfile
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _now(): return int(time.time()*1000)
def _sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()


class PortableStateManager:
    """Interoperable JSON export plus encrypted full-state backup/restore."""
    def __init__(self,state_dir: str|Path,identity):
        self.state=Path(state_dir).resolve(); self.identity=identity
        self.root=self.state/"portability"; self.root.mkdir(parents=True,exist_ok=True)

    _DURABLE_ID_RE=re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,24}[0-9]*-[A-Za-z0-9_-]{8,}$")
    _REDACT_COLUMNS={"key_path","cipher_path","local_locator","password","secret","token","private_key"}

    @classmethod
    def _collect_ids(cls,value) -> set[str]:
        found=set()
        if isinstance(value,dict):
            for v in value.values(): found |= cls._collect_ids(v)
        elif isinstance(value,list):
            for v in value: found |= cls._collect_ids(v)
        elif isinstance(value,str) and cls._DURABLE_ID_RE.fullmatch(value):
            found.add(value)
        return found

    @classmethod
    def _redact_row(cls,row: dict) -> dict:
        out={}
        for k,v in row.items():
            lk=str(k).lower()
            if lk in cls._REDACT_COLUMNS or any(x in lk for x in ("password","secret","private_key")):
                out[k]="REDACTED_FROM_PORTABLE_EXPORT"
            else: out[k]=v
        return out

    @classmethod
    def _sqlite_export(cls,path: Path,entity_id: str) -> dict:
        out={"database":path.name,"scope":"ENTITY_ONLY","tables":{}}
        db=sqlite3.connect(path); db.row_factory=sqlite3.Row
        try:
            tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
            all_rows={t:[dict(r) for r in db.execute(f'SELECT * FROM "{t}"').fetchall()] for t in tables}
            selected={t:[] for t in tables}; tokens={entity_id}; changed=True; passes=0
            while changed and passes<8:
                changed=False; passes+=1
                for table,rows in all_rows.items():
                    already={json.dumps(r,sort_keys=True,default=str) for r in selected[table]}
                    for row in rows:
                        encoded=json.dumps(row,sort_keys=True,default=str)
                        if encoded in already: continue
                        if any(token in encoded for token in tokens):
                            selected[table].append(row); already.add(encoded); changed=True
                            for key,value in row.items():
                                if str(key).lower().endswith("_id") and isinstance(value,str): tokens.add(value)
                                try: tokens |= cls._collect_ids(json.loads(value)) if isinstance(value,str) and value[:1] in "[{" else set()
                                except Exception: pass
            for table,rows in selected.items():
                if rows: out["tables"][table]=[cls._redact_row(r) for r in rows]
        finally: db.close()
        out["selected_object_identifiers"]=len(tokens)
        return out
    def export_entity(self,entity_id: str,destination: str|Path) -> dict:
        dest=Path(destination).resolve(); dest.mkdir(parents=True,exist_ok=True)
        manifest=self.identity.load_manifest(entity_id)
        (dest/"identity_manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True),encoding="utf-8")
        exported=[]
        for db_path in sorted(self.state.rglob("*.sqlite")):
            if "portability" in {p.lower() for p in db_path.parts}: continue
            data=self._sqlite_export(db_path,entity_id)
            rel="__".join(db_path.relative_to(self.state).parts)+".json"
            out=dest/rel; out.write_text(json.dumps(data,indent=2,sort_keys=True,default=str),encoding="utf-8")
            exported.append(out)
        files=[dest/"identity_manifest.json",*exported]
        evidence={"schema":"entity-portable-export-v1","entity_id":entity_id,"created_at_ms":_now(),"scope":"ENTITY_ONLY","formats":["JSON"],"files":[{"name":p.name,"sha256":_sha(p),"bytes":p.stat().st_size} for p in files],"private_keys_included":False,"raw_vault_content_included":False,"local_paths_redacted":True,"global_interleaved_ledger_chain_included":False,"independent_subset_proof_target":"MERKLE_WITNESS_PHASE"}
        evidence["signature"]=self.identity.sign(entity_id,{k:v for k,v in evidence.items() if k!="signature"})
        (dest/"EXPORT_MANIFEST.json").write_text(json.dumps(evidence,indent=2,sort_keys=True),encoding="utf-8")
        return evidence

    def create_encrypted_backup(self,destination: str|Path,key: bytes|None=None) -> dict:
        backup_key=key or AESGCM.generate_key(bit_length=256)
        if len(backup_key)!=32: raise ValueError("backup key must be 32 bytes")
        dest=Path(destination).resolve(); dest.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory() as td:
            plain=Path(td)/"entity_state.zip"
            with zipfile.ZipFile(plain,"w",compression=zipfile.ZIP_DEFLATED) as z:
                for path in self.state.rglob("*"):
                    if path.is_file() and "portability" not in {p.lower() for p in path.parts}:
                        z.write(path,path.relative_to(self.state))
            raw=plain.read_bytes()
        nonce=secrets.token_bytes(12); aad=b"ENTITY_BACKUP_V1"
        dest.write_bytes(nonce+AESGCM(backup_key).encrypt(nonce,raw,aad))
        return {"schema":"entity-encrypted-backup-v1","path":str(dest),"sha256":_sha(dest),"bytes":dest.stat().st_size,"key_b64":base64.urlsafe_b64encode(backup_key).decode("ascii"),"encrypted":True,"cipher":"AES-256-GCM"}

    def restore_encrypted_backup(self,backup: str|Path,key: bytes,target_state: str|Path) -> dict:
        src=Path(backup).resolve(); target=Path(target_state).resolve(); target.mkdir(parents=True,exist_ok=True)
        blob=src.read_bytes(); nonce,ciphertext=blob[:12],blob[12:]
        raw=AESGCM(key).decrypt(nonce,ciphertext,b"ENTITY_BACKUP_V1")
        with tempfile.TemporaryDirectory() as td:
            zpath=Path(td)/"restore.zip"; zpath.write_bytes(raw)
            with zipfile.ZipFile(zpath,"r") as z: z.extractall(target)
        return {"restored":True,"target_state":str(target),"backup_sha256":_sha(src)}

    def status(self) -> dict:
        return {"ready":True,"portable_json":True,"encrypted_backup":True,"restore_supported":True,"database_independence":True}
