from pathlib import Path
p=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network\01_Core_Runtime\identity\canonical_identity.py")
s=p.read_text(encoding='utf-8')
s=s.replace('def __init__(self, state_dir: str | Path):\n        self.root = Path(state_dir) / "identity"','def __init__(self, state_dir: str | Path, key_protector=None):\n        self.root = Path(state_dir) / "identity"')
s=s.replace('        self._lock = RLock()','        self.key_protector = key_protector\n        self._lock = RLock()',1)
old='''    def _write_private(self, path: Path, raw: bytes) -> None:\n        path.write_bytes(raw)\n        try: os.chmod(path, 0o600)\n        except OSError: pass\n'''
new='''    def _write_private(self, path: Path, raw: bytes) -> None:\n        path.write_bytes(raw)\n        try: os.chmod(path, 0o600)\n        except OSError: pass\n\n    def _read_private_key_bytes(self, entity_id: str, key_id: str) -> bytes:\n        raw_path=self._entity_key_dir(entity_id)/f"{key_id}.key"\n        if raw_path.is_file(): return raw_path.read_bytes()\n        wrapped_path=self._entity_key_dir(entity_id)/f"{key_id}.key.tpm"\n        if wrapped_path.is_file():\n            if self.key_protector is None: raise RuntimeError("hardware-protected private key requires configured key protector")\n            return self.key_protector.unwrap(wrapped_path.read_bytes())\n        raise FileNotFoundError(str(raw_path))\n'''
if old not in s: raise SystemExit('write private block not found')
s=s.replace(old,new)
p.write_text(s,encoding='utf-8')
print('phase1 patched')
s=p.read_text(encoding='utf-8')
s=s.replace('raw = (self.keys / f"{entity_id}.ed25519.key").read_bytes()','raw = (self.keys / f"{entity_id}.ed25519.key").read_bytes()')
s=s.replace('raw = (self._entity_key_dir(entity_id) / f"{key_id}.key").read_bytes()','raw = self._read_private_key_bytes(entity_id,key_id)')
s=s.replace('old_raw=(self._entity_key_dir(entity_id)/f"{old_id}.key").read_bytes()','old_raw=self._read_private_key_bytes(entity_id,old_id)')
s=s.replace('recovery_path=self._entity_key_dir(entity_id)/f"{recovery_id}.key"\n        if not recovery_path.exists(): raise RuntimeError("recovery private key unavailable")\n        recovery_key=Ed25519PrivateKey.from_private_bytes(recovery_path.read_bytes())','recovery_key=Ed25519PrivateKey.from_private_bytes(self._read_private_key_bytes(entity_id,recovery_id))')
insert='''\n    def hardware_protect_key(self, entity_id: str, key_id: str, protector=None) -> dict:\n        protector=protector or self.key_protector\n        if protector is None: raise RuntimeError("hardware key protector required")\n        kd=self._entity_key_dir(entity_id); raw_path=kd/f"{key_id}.key"; wrapped_path=kd/f"{key_id}.key.tpm"\n        if wrapped_path.is_file() and not raw_path.is_file(): return {"entity_id":entity_id,"key_id":key_id,"hardware_protected":True,"wrapped_path":str(wrapped_path)}\n        if not raw_path.is_file(): raise FileNotFoundError(str(raw_path))\n        raw=raw_path.read_bytes(); wrapped=protector.wrap(raw)\n        if protector.unwrap(wrapped)!=raw: raise RuntimeError("TPM key protection round-trip failed")\n        self._write_private(wrapped_path,wrapped); raw_path.unlink()\n        return {"entity_id":entity_id,"key_id":key_id,"hardware_protected":True,"wrapped_path":str(wrapped_path),"raw_private_key_removed":True}\n\n    def hardware_protect_recovery(self, entity_id: str, protector=None) -> list[dict]:\n        manifest=self.load_manifest(entity_id); authorities=list((manifest.get("recovery_policy") or {}).get("authorities") or [])\n        if not authorities: raise RuntimeError("no recovery authority configured")\n        return [self.hardware_protect_key(entity_id,str(k),protector) for k in authorities]\n'''
marker='    def pairwise_id(self, entity_id: str, relationship: str) -> str:\n'
if marker not in s: raise SystemExit('pairwise marker missing')
s=s.replace(marker,insert+'\n'+marker)
p.write_text(s,encoding='utf-8')
print('phase2 patched')
