from pathlib import Path

p=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network\04_Entity_Registry\event_ledger\canonical_event_ledger.py")
s=p.read_text(encoding="utf-8")
needle='''            db.execute("CREATE TABLE IF NOT EXISTS events(sequence INTEGER PRIMARY KEY AUTOINCREMENT,event_id TEXT UNIQUE NOT NULL,event_type TEXT NOT NULL,actor_entity_id TEXT NOT NULL,subject_ids_json TEXT NOT NULL,object_ids_json TEXT NOT NULL,payload_hash TEXT NOT NULL,evidence_origin TEXT NOT NULL,confidence REAL NOT NULL,timestamp_ms INTEGER NOT NULL,prior_hash TEXT NOT NULL,event_hash TEXT NOT NULL,signature_json TEXT NOT NULL,schema_version TEXT NOT NULL)")'''
replacement=needle+'''\n            cols={str(r[1]) for r in db.execute("PRAGMA table_info(events)").fetchall()}\n            if "payload_sha256" not in cols:\n                db.execute("ALTER TABLE events ADD COLUMN payload_sha256 TEXT")\n                db.execute("UPDATE events SET payload_sha256=payload_hash WHERE payload_sha256 IS NULL")'''
if needle not in s: raise SystemExit("events schema anchor missing")
s=s.replace(needle,replacement,1)
old='''    def append(self,actor_entity_id:str,event_type:str,*,subject_ids=None,object_ids=None,payload=None,evidence_origin="DIRECT_OBSERVATION",confidence=1.0)->dict:\n        body_payload=dict(payload or {}); payload_hash=_sha(body_payload); now=_now(); event_id="evt1-"+uuid.uuid4().hex'''
new='''    def append(self,actor_entity_id:str,event_type:str,*,subject_ids=None,object_ids=None,payload=None,payload_sha256=None,metadata=None,evidence_origin="DIRECT_OBSERVATION",confidence=1.0)->dict:\n        body_payload=dict(payload or {})\n        if payload_sha256 is not None:\n            payload_hash=str(payload_sha256).lower()\n            if len(payload_hash)!=64 or any(c not in "0123456789abcdef" for c in payload_hash): raise ValueError("payload_sha256 must be SHA-256 hex")\n            if payload is not None and _sha(body_payload)!=payload_hash: raise ValueError("payload and payload_sha256 disagree")\n        else:\n            payload_hash=_sha(body_payload)\n        now=_now(); event_id="evt1-"+uuid.uuid4().hex'''
if old not in s: raise SystemExit("append anchor missing")
s=s.replace(old,new,1)
old='''            db.execute("INSERT INTO events(event_id,event_type,actor_entity_id,subject_ids_json,object_ids_json,payload_hash,evidence_origin,confidence,timestamp_ms,prior_hash,event_hash,signature_json,schema_version) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",(event_id,str(event_type),str(actor_entity_id),json.dumps(body["subject_ids"]),json.dumps(body["object_ids"]),payload_hash,str(evidence_origin),float(confidence),now,prior,event_hash,json.dumps(signature,sort_keys=True),"ENTITY-EVENT-v1"))'''
new='''            db.execute("INSERT INTO events(event_id,event_type,actor_entity_id,subject_ids_json,object_ids_json,payload_hash,evidence_origin,confidence,timestamp_ms,prior_hash,event_hash,signature_json,schema_version,payload_sha256) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(event_id,str(event_type),str(actor_entity_id),json.dumps(body["subject_ids"]),json.dumps(body["object_ids"]),payload_hash,str(evidence_origin),float(confidence),now,prior,event_hash,json.dumps(signature,sort_keys=True),"ENTITY-EVENT-v1",payload_hash))'''
if old not in s: raise SystemExit("insert anchor missing")
s=s.replace(old,new,1)
old='''        return {"event_id":event_id,"event_hash":event_hash,"prior_hash":prior,"payload_hash":payload_hash,"signature":signature,"timestamp_ms":now}'''
new='''        return {"event_id":event_id,"event_hash":event_hash,"prior_hash":prior,"payload_hash":payload_hash,"payload_sha256":payload_hash,"signature":signature,"timestamp_ms":now,"raw_payload_stored":False}'''
if old not in s: raise SystemExit("return anchor missing")
s=s.replace(old,new,1)
old='''            sig=json.loads(row["signature_json"])\n            if row["prior_hash"]!=prior:'''
new='''            sig=json.loads(row["signature_json"])\n            if row.get("payload_sha256") not in {None,row["payload_hash"]}: return {"pass":False,"reason":"event_hash_failure","sequence":row["sequence"]}\n            if row["prior_hash"]!=prior:'''
if old not in s: raise SystemExit("verify anchor missing")
s=s.replace(old,new,1)
marker='''    def verify_checkpoint(self,checkpoint_id:str)->dict:\n'''
alias='''    def create_checkpoint(self,signer_entity_id:str,*,from_sequence:int=1,to_sequence:int|None=None)->dict:\n        out=self.checkpoint(signer_entity_id,from_sequence=from_sequence,to_sequence=to_sequence)\n        return {**out,"leaf_count":out["event_count"]}\n\n'''
if marker not in s: raise SystemExit("checkpoint anchor missing")
s=s.replace(marker,alias+marker,1)
p.write_text(s,encoding="utf-8")
print("patched event ledger compatibility")
