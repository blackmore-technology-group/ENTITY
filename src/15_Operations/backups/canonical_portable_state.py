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
    _ENTITY_ID_RE=re.compile(r"^(?:ent1|ent2)-[a-z2-7]{52}$")
    _REDACT_COLUMNS={"key_path","cipher_path","local_locator","password","secret","token","private_key"}
    _NON_TRAVERSAL_ID_PREFIXES=("sig-","rec-")

    @classmethod
    def _contains_token(cls,value,tokens:set[str])->bool:
        if isinstance(value,dict):
            return any(cls._contains_token(v,tokens) for v in value.values())
        if isinstance(value,list):
            return any(cls._contains_token(v,tokens) for v in value)
        if isinstance(value,str):
            s=value.strip()
            if s in tokens:
                return True
            if s[:1] in "[{":
                try: return cls._contains_token(json.loads(s),tokens)
                except Exception: return False
        return False

    @classmethod
    def _reference_field(cls,key)->bool:
        k=str(key or "").lower()
        if k.endswith("_json"):
            k=k[:-5]
        return k.endswith(("_id","_ids","_ref","_refs")) or k in {"subject_ids","object_ids","parent_asset_ids"}

    @classmethod
    def _collect_ids(cls,value,key_hint=None)->set[str]:
        found=set()
        if isinstance(value,dict):
            for k,v in value.items(): found |= cls._collect_ids(v,k)
        elif isinstance(value,list):
            for v in value: found |= cls._collect_ids(v,key_hint)
        elif isinstance(value,str):
            s=value.strip()
            if s[:1] in "[{":
                try: found |= cls._collect_ids(json.loads(s),key_hint)
                except Exception: pass
            elif cls._reference_field(key_hint) and cls._DURABLE_ID_RE.fullmatch(s):
                if not cls._ENTITY_ID_RE.fullmatch(s) and not s.startswith(cls._NON_TRAVERSAL_ID_PREFIXES):
                    found.add(s)
        return found

    @classmethod
    def _redact_row(cls,row:dict)->dict:
        out={}
        for k,v in row.items():
            lk=str(k).lower()
            if lk in cls._REDACT_COLUMNS or any(x in lk for x in ("password","secret","private_key")):
                out[k]="REDACTED_FROM_PORTABLE_EXPORT"
            else: out[k]=v
        return out

    @classmethod
    def _sqlite_scan(cls,path:Path,tokens:set[str])->tuple[dict,set[str]]:
        out={"database":path.name,"scope":"ENTITY_ONLY","tables":{}}
        discovered=set()
        db=sqlite3.connect(path); db.row_factory=sqlite3.Row
        try:
            tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
            for table in tables:
                quoted=str(table).replace('"','""')
                cur=db.execute(f'SELECT * FROM "{quoted}"')
                selected=[]
                while True:
                    batch=cur.fetchmany(5000)
                    if not batch: break
                    for raw in batch:
                        row=dict(raw)
                        if cls._contains_token(row,tokens):
                            selected.append(cls._redact_row(row))
                            discovered |= cls._collect_ids(row)
                if selected: out["tables"][table]=selected
        finally: db.close()
        return out,discovered

    def resolve_entity_ref(self,entity_ref:str)->str:
        ref=str(entity_ref or "").strip()
        if not ref: raise ValueError("Entity ID or alias is required")
        try:
            manifest=self.identity.load_manifest(ref)
            return str(manifest["entity_id"])
        except (ValueError,FileNotFoundError,RuntimeError,KeyError):
            pass
        needle=ref.casefold(); matches=[]
        for manifest in self.identity.list_local():
            candidates=[str(manifest.get("display_name") or "")]
            candidates.extend(str(x) for x in (manifest.get("aliases") or []))
            if any(needle==candidate.strip().casefold() for candidate in candidates if candidate.strip()):
                matches.append(str(manifest["entity_id"]))
        matches=sorted(set(matches))
        if not matches: raise KeyError(f"unknown Entity ID or alias: {ref}")
        if len(matches)>1: raise ValueError(f"ambiguous Entity alias/display name: {ref}")
        return matches[0]

    def export_entity(self,entity_id:str,destination:str|Path)->dict:
        entity_id=self.resolve_entity_ref(entity_id)
        dest=Path(destination).resolve(); dest.mkdir(parents=True,exist_ok=True)
        manifest=self.identity.load_manifest(entity_id)
        (dest/"identity_manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True),encoding="utf-8")
        db_paths=[p for p in sorted(self.state.rglob("*.sqlite")) if "portability" not in {part.lower() for part in p.parts}]
        selected_by_db={}; seen_by_db={}; tokens={entity_id}; closure_passes=0
        for pass_index in range(6):
            snapshot=set(tokens); discovered=set()
            for db_path in db_paths:
                rel="__".join(db_path.relative_to(self.state).parts)+".json"
                scan,new_ids=self._sqlite_scan(db_path,snapshot); discovered |= new_ids
                bucket=selected_by_db.setdefault(rel,{}); seen=seen_by_db.setdefault(rel,{})
                for table,rows in scan["tables"].items():
                    target=bucket.setdefault(table,[]); table_seen=seen.setdefault(table,set())
                    for row in rows:
                        encoded=json.dumps(row,sort_keys=True,default=str,separators=(",",":"))
                        if encoded not in table_seen:
                            target.append(row); table_seen.add(encoded)
            tokens |= discovered; closure_passes=pass_index+1
            if tokens==snapshot: break
        exported=[]
        for db_path in db_paths:
            rel="__".join(db_path.relative_to(self.state).parts)+".json"
            tables=selected_by_db.get(rel,{})
            identifiers={entity_id} | self._collect_ids(tables)
            data={"database":db_path.name,"scope":"ENTITY_ONLY","scope_policy":"TARGET_ENTITY_AND_NON_ENTITY_OBJECT_CLOSURE","foreign_entity_traversal":False,"selected_object_identifiers":len(identifiers),"tables":tables}
            out=dest/rel
            out.write_text(json.dumps(data,indent=2,sort_keys=True,default=str),encoding="utf-8")
            exported.append(out)
        files=[dest/"identity_manifest.json",*exported]
        evidence={"schema":"entity-portable-export-v1","entity_id":entity_id,"created_at_ms":_now(),"scope":"ENTITY_ONLY","scope_policy":"TARGET_ENTITY_AND_NON_ENTITY_OBJECT_CLOSURE","foreign_entity_traversal":False,"cross_database_object_closure":True,"closure_passes":closure_passes,"formats":["JSON"],"files":[{"name":p.name,"sha256":_sha(p),"bytes":p.stat().st_size} for p in files],"private_keys_included":False,"raw_vault_content_included":False,"local_paths_redacted":True,"global_interleaved_ledger_chain_included":False,"independent_subset_proof_target":"MERKLE_WITNESS_PHASE"}
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