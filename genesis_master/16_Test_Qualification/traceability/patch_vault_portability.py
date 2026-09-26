from pathlib import Path
p=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network\08_Data_Vaults\canonical_encrypted_vault.py")
s=p.read_text(encoding="utf-8")
s=s.replace('            db.execute("INSERT INTO objects VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(object_id,controller_entity_id,digest,len(raw),str(media_type)[:256],classification,"ACTIVE",str(cipher_path),str(key_path),json.dumps(dict(metadata or {}),sort_keys=True),now,now))','            db.execute("INSERT INTO objects VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(object_id,controller_entity_id,digest,len(raw),str(media_type)[:256],classification,"ACTIVE",str(cipher_path.relative_to(self.root)),str(key_path.relative_to(self.root)),json.dumps(dict(metadata or {}),sort_keys=True),now,now))')
anchor='    def read_bytes(self,controller_entity_id: str,object_id: str) -> bytes:\n'
helper='    def _storage_path(self,stored: str,kind: str) -> Path:\n        raw=Path(str(stored))\n        if not raw.is_absolute(): return self.root/raw\n        if raw.exists(): return raw\n        base=self.keys if kind=="key" else self.objects\n        return base/raw.name\n\n'
s=s.replace(anchor,helper+anchor)
s=s.replace('        key_path=Path(row["key_path"]); cipher_path=Path(row["cipher_path"])','        key_path=self._storage_path(row["key_path"],"key"); cipher_path=self._storage_path(row["cipher_path"],"cipher")')
s=s.replace('            kp=Path(row["key_path"])','            kp=self._storage_path(row["key_path"],"key")')
s=s.replace('            cp=Path(row["cipher_path"])','            cp=self._storage_path(row["cipher_path"],"cipher")')
p.write_text(s,encoding="utf-8")
print("patched",p)
