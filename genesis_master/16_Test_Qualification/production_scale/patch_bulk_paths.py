from pathlib import Path
ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")

def insert_before(path, marker, block):
    p=ROOT/path; s=p.read_text(encoding="utf-8")
    first=block.splitlines()[0].strip()
    if first in s:
        print("already", path); return
    if marker not in s: raise RuntimeError(f"marker missing: {path}: {marker}")
    s=s.replace(marker, block+"\n"+marker, 1)
    p.write_text(s,encoding="utf-8")
    print("patched", path)

ledger='''    def append_batch(self,actor_entity_id:str,events:list[dict])->list[dict]:
        """Append many fully signed/hash-chained events in one durable transaction."""
        items=list(events or [])
        if not items: return []
        sign=self.identity.open_signing_session(actor_entity_id)
        out=[]; rows=[]
        with self._lock,self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            prior=db.execute("SELECT v FROM meta WHERE k='head_hash'").fetchone()[0]
            for item in items:
                payload=dict(item.get("payload") or {})
                supplied=item.get("payload_sha256")
                payload_hash=str(supplied).lower() if supplied is not None else _sha(payload)
                if len(payload_hash)!=64 or any(c not in "0123456789abcdef" for c in payload_hash): raise ValueError("payload_sha256 must be SHA-256 hex")
                if supplied is not None and item.get("payload") is not None and _sha(payload)!=payload_hash: raise ValueError("payload and payload_sha256 disagree")
                now=_now(); event_id="evt1-"+uuid.uuid4().hex
                body={"schema":"ENTITY-EVENT-v1","event_id":event_id,"event_type":str(item.get("event_type") or ""),"actor_entity_id":str(actor_entity_id),"subject_ids":list(item.get("subject_ids") or []),"object_ids":list(item.get("object_ids") or []),"payload_hash":payload_hash,"evidence_origin":str(item.get("evidence_origin") or "DIRECT_OBSERVATION"),"confidence":float(item.get("confidence",1.0)),"timestamp_ms":now,"prior_hash":prior}
                signature=sign(body); event_hash=_sha({"body":body,"signature":signature})
                rows.append((event_id,body["event_type"],str(actor_entity_id),json.dumps(body["subject_ids"]),json.dumps(body["object_ids"]),payload_hash,body["evidence_origin"],body["confidence"],now,prior,event_hash,json.dumps(signature,sort_keys=True),"ENTITY-EVENT-v1",payload_hash))
                out.append({"event_id":event_id,"event_hash":event_hash,"prior_hash":prior,"payload_hash":payload_hash,"payload_sha256":payload_hash,"signature":signature,"timestamp_ms":now,"raw_payload_stored":False})
                prior=event_hash
            db.executemany("INSERT INTO events(event_id,event_type,actor_entity_id,subject_ids_json,object_ids_json,payload_hash,evidence_origin,confidence,timestamp_ms,prior_hash,event_hash,signature_json,schema_version,payload_sha256) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",rows)
            db.execute("UPDATE meta SET v=? WHERE k='head_hash'",(prior,))
        return out
'''
insert_before(Path('04_Entity_Registry/event_ledger/canonical_event_ledger.py'),'    def rows(self):',ledger)
prov='''    def register_bindings_batch(self,controller_entity_id:str,bindings:list[dict])->list[dict]:
        """Register many individually signed provenance bindings in one transaction."""
        items=list(bindings or [])
        if not items: return []
        sign=self.identity.open_signing_session(controller_entity_id)
        rows=[]; out=[]
        for item in items:
            digest=_sha256_hex(item.get("content_sha256")); origin=str(item.get("evidence_origin") or "DIRECT_OBSERVATION").upper()
            if origin not in EVIDENCE_ORIGINS: raise ValueError("unsupported evidence_origin")
            c2pa=_sha256_hex(item.get("c2pa_manifest_sha256")) if item.get("c2pa_manifest_sha256") else None
            now=_now(); body={"schema":"entity-provenance-binding-v2","asset_id":str(item["asset_id"]),"controller_entity_id":controller_entity_id,"content_sha256":digest,"soft_binding_type":item.get("soft_binding_type"),"soft_binding_value":item.get("soft_binding_value"),"c2pa_manifest_sha256":c2pa,"c2pa_reference":item.get("c2pa_reference"),"provenance_status":"RECORDED","truth_status":"NOT_ASSESSED","evidence_origin":origin,"recorded_at_ms":now}
            sig=sign(body); rows.append((body["asset_id"],controller_entity_id,digest,body["soft_binding_type"],body["soft_binding_value"],c2pa,body["c2pa_reference"],"RECORDED","NOT_ASSESSED",origin,now,json.dumps(sig,sort_keys=True))); out.append(dict(body,signature=sig))
        with self._lock,self._connect() as db:
            db.execute("BEGIN IMMEDIATE"); db.executemany("INSERT OR REPLACE INTO bindings VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",rows)
        return out
'''
insert_before(Path('04_Entity_Registry/provenance/canonical_provenance.py'),'    def verify_hard_binding(self,asset_id: str,observed_sha256: str) -> dict:',prov)

rights='''    def assert_claims_batch(self,claimant_entity_id:str,claims:list[dict])->list[dict]:
        """Assert many individually signed rights claims and signed claim events in one transaction."""
        self._require_local(claimant_entity_id); items=list(claims or [])
        if not items: return []
        sign=self.identity.open_signing_session(claimant_entity_id); claim_rows=[]; event_rows=[]; out=[]
        for item in items:
            rtype=str(item.get("right_type") or "DATA_CONTROLLER").upper(); origin=str(item.get("evidence_origin") or "ENTITY_ASSERTION").upper()
            if rtype not in RIGHT_TYPES: raise ValueError("unsupported right_type")
            if origin not in EVIDENCE_ORIGINS: raise ValueError("unsupported evidence_origin")
            now=_now(); claim_id=_id(); scope=dict(item.get("scope") or {}); evidence=dict(item.get("evidence") or {})
            body={"schema":"entity-rights-claim-v2","claim_id":claim_id,"asset_id":str(item["asset_id"]),"claimant_entity_id":claimant_entity_id,"right_type":rtype,"share":{"numerator":1,"denominator":1},"territory":str(item.get("territory") or "unspecified"),"jurisdiction":str(item.get("jurisdiction") or "unspecified"),"legal_basis":str(item.get("legal_basis") or "entity_asset_registration"),"scope":scope,"evidence":evidence,"evidence_origin":origin,"effective_at_ms":int(item.get("effective_at_ms") or now),"expires_at_ms":item.get("expires_at_ms"),"verification_level":"SELF_ASSERTED","lifecycle_status":"ACTIVE","supersedes_claim_id":None}
            sig=sign(body); claim_rows.append((claim_id,body["asset_id"],claimant_entity_id,rtype,1,1,body["territory"],body["jurisdiction"],body["legal_basis"],json.dumps(scope,sort_keys=True),json.dumps(evidence,sort_keys=True),origin,body["effective_at_ms"],body["expires_at_ms"],"SELF_ASSERTED","ACTIVE",None,json.dumps(sig,sort_keys=True),now,now))
            ep={"right_type":rtype,"verification_level":"SELF_ASSERTED","evidence_origin":origin}; eb={"claim_id":claim_id,"event_type":"claim.asserted","actor_entity_id":claimant_entity_id,"payload":ep,"timestamp_ms":now}; es=sign(eb); eid="evt1-"+uuid.uuid4().hex
            event_rows.append((eid,claim_id,"claim.asserted",claimant_entity_id,json.dumps(ep,sort_keys=True),json.dumps(es,sort_keys=True),now)); out.append(dict(body,signature=sig,event={"event_id":eid,"timestamp_ms":now,"signature":es}))
        with self._lock,self._connect() as db:
            db.execute("BEGIN IMMEDIATE"); db.executemany("INSERT INTO claims VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",claim_rows); db.executemany("INSERT INTO claim_events(event_id,claim_id,event_type,actor_entity_id,payload_json,signature_json,timestamp_ms) VALUES(?,?,?,?,?,?,?)",event_rows)
        return out
'''
insert_before(Path('04_Entity_Registry/ownership_graphs/canonical_rights_claims.py'),'    def verify_claim(self,verifier_entity_id: str,claim_id: str,level: str,evidence: dict) -> dict:',rights)
assets='''    def register_batch(self,controller_entity_id:str,assets:list[dict])->list[dict]:
        """Register many assets with full ledger/rights/provenance semantics using batch-capable canonical stores."""
        items=list(assets or [])
        if not items: return []
        self.identity.load_manifest(controller_entity_id)
        now=_now(); rows=[]; loc_rows=[]; base=[]
        for item in items:
            digest=str(item.get("content_sha256") or "").lower()
            if len(digest)!=64 or any(c not in "0123456789abcdef" for c in digest): raise ValueError("content_sha256 must be SHA-256 hex")
            asset_id=_id(); meta=dict(item.get("metadata") or {}); classification=str(item.get("classification") or "PRIVATE").upper()[:32]
            rows.append((asset_id,controller_entity_id,digest,max(0,int(item.get("size_bytes") or 0)),str(item.get("media_type") or "application/octet-stream")[:128],str(item.get("title") or asset_id)[:512],classification,"ACTIVE",json.dumps(meta,sort_keys=True),now,now))
            if item.get("local_locator"): loc_rows.append((asset_id,str(item["local_locator"])))
            base.append({"asset_id":asset_id,"controller_entity_id":controller_entity_id,"content_sha256":digest,"status":"ACTIVE","state":"ACTIVE","ownership_claimed_not_proven":True,"ownership_not_inferred":True})
        with self._lock,self._connect() as db:
            db.execute("BEGIN IMMEDIATE"); db.executemany("INSERT INTO assets VALUES(?,?,?,?,?,?,?,?,?,?,?)",rows)
            if loc_rows: db.executemany("INSERT INTO locators VALUES(?,?)",loc_rows)
        events=self.ledger.append_batch(controller_entity_id,[{"event_type":"asset.registered","subject_ids":[controller_entity_id],"object_ids":[x["asset_id"]],"payload":{"asset_id":x["asset_id"],"content_sha256":x["content_sha256"],"controller_entity_id":controller_entity_id,"registration_not_ownership":True},"evidence_origin":"DIRECT_OBSERVATION"} for x in base]) if self.ledger else [None]*len(base)
        claims=self.rights_graph.assert_claims_batch(controller_entity_id,[{"asset_id":x["asset_id"],"right_type":"DATA_CONTROLLER","legal_basis":"entity_asset_registration","scope":{"control_of_entity_record":True},"evidence":{"content_sha256":x["content_sha256"]}} for x in base]) if self.rights_graph else [None]*len(base)
        provs=self.provenance.register_bindings_batch(controller_entity_id,[{"asset_id":x["asset_id"],"content_sha256":x["content_sha256"],"evidence_origin":"DIRECT_OBSERVATION"} for x in base]) if self.provenance else [None]*len(base)
        return [dict(x,event=events[i],rights_control_claim=claims[i],provenance=provs[i]) for i,x in enumerate(base)]
'''
insert_before(Path('04_Entity_Registry/asset_registry/canonical_asset_registry.py'),'    def get(self,asset_id:str,*,include_private_locator=False)->dict|None:',assets)
