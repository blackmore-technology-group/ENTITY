from pathlib import Path

p=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network\04_Entity_Registry\asset_registry\canonical_asset_registry.py")
s=p.read_text(encoding="utf-8")
old='''    def __init__(self,state_dir:str|Path,identity,ledger=None,rights_graph=None,provenance=None):\n        self.root=Path(state_dir)/"asset_registry"; self.root.mkdir(parents=True,exist_ok=True)\n        self.path=self.root/"assets.sqlite"; self.identity=identity; self.ledger=ledger\n        self.rights_graph=rights_graph; self.provenance=provenance; self._lock=RLock(); self._init_db()'''
new='''    def __init__(self,state_dir:str|Path,identity,ledger=None,rights_graph=None,provenance=None):\n        # Preserve the pre-v2 positional ABI: (state, identity, rights_graph, provenance, ledger).\n        if ledger is not None and not hasattr(ledger,"append") and rights_graph is not None and hasattr(rights_graph,"register_binding") and provenance is not None and hasattr(provenance,"append"):\n            ledger,rights_graph,provenance=provenance,ledger,rights_graph\n        self.root=Path(state_dir)/"asset_registry"; self.root.mkdir(parents=True,exist_ok=True)\n        self.path=self.root/"assets.sqlite"; self.identity=identity; self.ledger=ledger\n        self.rights_graph=rights_graph; self.provenance=provenance; self._lock=RLock(); self._init_db()'''
if old not in s: raise SystemExit("constructor anchor missing")
s=s.replace(old,new,1)
old='''        return {"asset_id":asset_id,"controller_entity_id":controller_entity_id,"content_sha256":digest,"status":"ACTIVE","ownership_claimed_not_proven":True,"rights_control_claim":control_claim,"provenance":prov,"event":event}'''
new='''        return {"asset_id":asset_id,"controller_entity_id":controller_entity_id,"content_sha256":digest,"status":"ACTIVE","state":"ACTIVE","ownership_claimed_not_proven":True,"ownership_not_inferred":True,"rights_control_claim":control_claim,"provenance":prov,"event":event}'''
if old not in s: raise SystemExit("register return anchor missing")
s=s.replace(old,new,1)
old='''            out=dict(row); out["metadata"]=json.loads(out.pop("metadata_json")); out["owner_semantics"]="controller record only; not legal ownership proof"'''
new='''            out=dict(row); out["metadata"]=json.loads(out.pop("metadata_json")); out["owner_semantics"]="controller record only; not legal ownership proof"; out["state"]=out["status"]'''
if old not in s: raise SystemExit("get anchor missing")
s=s.replace(old,new,1)
marker='''    def deactivate(self,controller_entity_id:str,asset_id:str,reason:str="owner_action")->dict:\n'''
method='''    def set_state(self,controller_entity_id:str,asset_id:str,state:str,reason:str="owner_action")->dict:\n        row=self.get(asset_id)\n        if not row: raise KeyError("asset not found")\n        if row["controller_entity_id"]!=controller_entity_id: raise PermissionError("asset controller mismatch")\n        target=str(state or "").strip().upper()\n        if not target or len(target)>64: raise ValueError("asset state required")\n        with self._connect() as db: db.execute("UPDATE assets SET status=?,updated_at_ms=? WHERE asset_id=?",(target,_now(),asset_id))\n        event=self.ledger.append(controller_entity_id,"asset.state_changed",subject_ids=[controller_entity_id],object_ids=[asset_id],payload={"asset_id":asset_id,"from_state":row["status"],"to_state":target,"reason":str(reason)[:256],"historical_provenance_preserved":True}) if self.ledger else None\n        return {"asset_id":asset_id,"status":target,"state":target,"historical_provenance_preserved":True,"event":event}\n\n'''
if marker not in s: raise SystemExit("deactivate anchor missing")
s=s.replace(marker,method+marker,1)
p.write_text(s,encoding="utf-8")
print("patched asset registry compatibility")
