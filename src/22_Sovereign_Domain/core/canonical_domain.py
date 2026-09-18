from __future__ import annotations
from pathlib import Path
from contextlib import contextmanager
import json, sqlite3, secrets, time

ACCESS_CLASSES={"PUBLIC","RELATIONSHIP_ONLY","CREDENTIAL_REQUIRED","LICENSE_REQUIRED","PAID","PRIVATE","LOCAL_ONLY","DISABLED"}
SERVICE_TYPES={"PRESENCE","PUBLIC_PROFILE","CONTENT","FILES","APPLICATION","API","MESSAGING","SEARCH","SOFTWARE","DATASET","DATA_OFFER","MARKETPLACE","LICENSING","PAYMENT","VERIFICATION","CREDENTIALS","AI_SERVICE","COMPUTE_TO_DATA","STREAM","NOTIFICATION","DISCOVERY","ECONOMIC_SERVICE"}

def _now(): return int(time.time()*1000)
def _id(prefix): return f"{prefix}-"+secrets.token_hex(20)

class EntityDomainAuthority:
    """Sovereign Entity-domain registry. Nodes, endpoints and providers never become the Entity root."""
    def __init__(self,state_dir:str|Path,identity):
        self.root=Path(state_dir)/"sovereign_domain"
        self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/"domain.sqlite"
        self.identity=identity
        self._init_db()

    @contextmanager
    def _connect(self):
        db=sqlite3.connect(self.path,timeout=30)
        db.row_factory=sqlite3.Row
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def _init_db(self):
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=FULL")
            db.execute("""CREATE TABLE IF NOT EXISTS domains(
                domain_id TEXT PRIMARY KEY,entity_id TEXT NOT NULL,namespace TEXT NOT NULL,
                current_name TEXT,version INTEGER NOT NULL,status TEXT NOT NULL,
                created_at_ms INTEGER NOT NULL,updated_at_ms INTEGER NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS name_claims(
                claim_id TEXT PRIMARY KEY,domain_id TEXT NOT NULL,entity_id TEXT NOT NULL,
                normalized_name TEXT NOT NULL,namespace TEXT NOT NULL,status TEXT NOT NULL,
                conflict_state TEXT NOT NULL,evidence_json TEXT NOT NULL,signature_json TEXT NOT NULL,
                created_at_ms INTEGER NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS nodes(
                node_id TEXT PRIMARY KEY,domain_id TEXT NOT NULL,entity_id TEXT NOT NULL,
                public_key_b64 TEXT NOT NULL,permitted_services_json TEXT NOT NULL,
                network_scopes_json TEXT NOT NULL,publication_scopes_json TEXT NOT NULL,
                data_scopes_json TEXT NOT NULL,not_before_ms INTEGER NOT NULL,expires_at_ms INTEGER,
                delegation_json TEXT NOT NULL,status TEXT NOT NULL,auth_version INTEGER NOT NULL,
                signature_json TEXT NOT NULL,created_at_ms INTEGER NOT NULL,updated_at_ms INTEGER NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS services(
                service_id TEXT PRIMARY KEY,domain_id TEXT NOT NULL,node_id TEXT NOT NULL,
                service_type TEXT NOT NULL,endpoint_json TEXT NOT NULL,protocol_version TEXT NOT NULL,
                capabilities_json TEXT NOT NULL,access_class TEXT NOT NULL,
                required_credentials_json TEXT NOT NULL,policy_refs_json TEXT NOT NULL,
                data_classifications_json TEXT NOT NULL,economic_terms_ref TEXT,
                availability_json TEXT NOT NULL,manifest_version INTEGER NOT NULL,
                expires_at_ms INTEGER,status TEXT NOT NULL,signature_json TEXT NOT NULL,
                created_at_ms INTEGER NOT NULL,updated_at_ms INTEGER NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS migrations(
                migration_id TEXT PRIMARY KEY,domain_id TEXT NOT NULL,from_node TEXT,to_node TEXT,
                from_provider TEXT,to_provider TEXT,semantic_hash_before TEXT NOT NULL,
                semantic_hash_after TEXT NOT NULL,signature_json TEXT NOT NULL,
                created_at_ms INTEGER NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS revocations(
                revocation_id TEXT PRIMARY KEY,domain_id TEXT NOT NULL,node_id TEXT NOT NULL,
                entity_id TEXT NOT NULL,reason TEXT NOT NULL,effective_at_ms INTEGER NOT NULL,
                signature_json TEXT NOT NULL,created_at_ms INTEGER NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS audit(
                audit_id TEXT PRIMARY KEY,domain_id TEXT,event_type TEXT NOT NULL,
                actor_entity_id TEXT NOT NULL,payload_json TEXT NOT NULL,
                created_at_ms INTEGER NOT NULL)""")

    @staticmethod
    def normalize_name(value:str)->str:
        name=".".join(part.strip().lower() for part in str(value or "").strip().split(".") if part.strip())
        if not name or len(name)>253: raise ValueError("invalid Entity name")
        if any(not all(c.isalnum() or c in "-_" for c in part) for part in name.split(".")):
            raise ValueError("Entity name contains unsupported characters")
        return name

    def _audit(self,db,domain_id,event_type,actor,payload):
        db.execute("INSERT INTO audit VALUES(?,?,?,?,?,?)",
                   (_id("daud1"),domain_id,str(event_type),actor,json.dumps(dict(payload or {}),sort_keys=True),_now()))

    def create_domain(self,entity_id:str,*,namespace:str="entity",requested_name:str|None=None)->dict:
        self.identity.load_manifest(entity_id)
        did=_id("domain1"); now=_now(); ns=str(namespace or "entity").lower()
        with self._connect() as db:
            db.execute("INSERT INTO domains VALUES(?,?,?,?,?,?,?,?)",(did,entity_id,ns,None,1,"ACTIVE",now,now))
            self._audit(db,did,"DOMAIN_CREATED",entity_id,{"namespace":ns})
        out={"schema":"entity-domain-v1","domain_id":did,"entity_root":entity_id,"namespace":ns,
             "version":1,"status":"ACTIVE","created_at_ms":now,
             "dns_required":False,"registrar_required":False,"btg_host_required":False}
        if requested_name:
            out["name_claim"]=self.claim_name(entity_id,did,requested_name)
        return out

    def claim_name(self,entity_id:str,domain_id:str,name:str,*,evidence:dict|None=None)->dict:
        row=self.get_domain(domain_id)
        if row["entity_root"]!=entity_id: raise PermissionError("domain controller mismatch")
        normalized=self.normalize_name(name); now=_now(); cid=_id("name1")
        with self._connect() as db:
            clashes=db.execute("SELECT domain_id FROM name_claims WHERE namespace=? AND normalized_name=? AND status='ACTIVE' AND domain_id<>?",
                               (row["namespace"],normalized,domain_id)).fetchall()
        conflict="CONFLICT" if clashes else "CLEAR"
        body={"schema":"entity-name-claim-v1","claim_id":cid,"domain_id":domain_id,"entity_root":entity_id,
              "normalized_name":normalized,"namespace":row["namespace"],"status":"ACTIVE",
              "conflict_state":conflict,"evidence":dict(evidence or {}),"created_at_ms":now,
              "first_seen_is_not_ownership":True,"dns_possession_is_not_authority":True}
        sig=self.identity.sign(entity_id,body)
        with self._connect() as db:
            db.execute("INSERT INTO name_claims VALUES(?,?,?,?,?,?,?,?,?,?)",
                       (cid,domain_id,entity_id,normalized,row["namespace"],"ACTIVE",conflict,
                        json.dumps(body["evidence"],sort_keys=True),json.dumps(sig,sort_keys=True),now))
            db.execute("UPDATE domains SET current_name=?,version=version+1,updated_at_ms=? WHERE domain_id=?",
                       (normalized,now,domain_id))
            self._audit(db,domain_id,"NAME_CLAIMED",entity_id,{"claim_id":cid,"name":normalized,"conflict":conflict})
        return {**body,"signature":sig}

    def authorize_node(self,entity_id:str,domain_id:str,public_key_b64:str,*,permitted_services:list[str],
                       network_scopes:list[str]|None=None,publication_scopes:list[str]|None=None,
                       data_scopes:list[str]|None=None,not_before_ms:int|None=None,expires_at_ms:int|None=None,
                       delegation:dict|None=None,node_id:str|None=None)->dict:
        domain=self.get_domain(domain_id)
        if domain["entity_root"]!=entity_id: raise PermissionError("domain controller mismatch")
        nid=str(node_id or _id("node1")); now=_now(); start=int(not_before_ms or now)
        services=sorted({str(x).upper() for x in permitted_services})
        if not services: raise ValueError("permitted_services required")
        body={"schema":"entity-node-authorization-v1","domain_id":domain_id,"entity_root":entity_id,"node_id":nid,
              "public_key_b64":str(public_key_b64),"permitted_services":services,
              "network_scopes":sorted({str(x) for x in network_scopes or ["*"]}),
              "publication_scopes":sorted({str(x) for x in publication_scopes or services}),
              "data_scopes":sorted({str(x) for x in data_scopes or []}),
              "not_before_ms":start,"expires_at_ms":int(expires_at_ms) if expires_at_ms is not None else None,
              "delegation":dict(delegation or {}),"status":"ACTIVE","auth_version":1,"created_at_ms":now}
        sig=self.identity.sign(entity_id,body)
        with self._connect() as db:
            db.execute("INSERT INTO nodes VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                       (nid,domain_id,entity_id,body["public_key_b64"],json.dumps(services),json.dumps(body["network_scopes"]),
                        json.dumps(body["publication_scopes"]),json.dumps(body["data_scopes"]),start,body["expires_at_ms"],
                        json.dumps(body["delegation"],sort_keys=True),"ACTIVE",1,json.dumps(sig,sort_keys=True),now,now))
            self._audit(db,domain_id,"NODE_AUTHORIZED",entity_id,{"node_id":nid,"services":services})
        return {**body,"signature":sig}

    def revoke_node(self,entity_id:str,node_id:str,reason:str="owner_action")->dict:
        node=self.get_node(node_id)
        if node["entity_root"]!=entity_id: raise PermissionError("node controller mismatch")
        if node.get("effective_status")=="REVOKED": raise ValueError("node already revoked")
        now=_now(); rid=_id("rev1")
        body={"schema":"entity-node-revocation-v1","revocation_id":rid,"domain_id":node["domain_id"],
              "node_id":node_id,"entity_root":entity_id,"reason":str(reason)[:1024],
              "effective_at_ms":now,"created_at_ms":now}
        sig=self.identity.sign(entity_id,body)
        with self._connect() as db:
            db.execute("INSERT INTO revocations VALUES(?,?,?,?,?,?,?,?)",
                       (rid,node["domain_id"],node_id,entity_id,body["reason"],now,json.dumps(sig,sort_keys=True),now))
            self._audit(db,node["domain_id"],"NODE_REVOKED",entity_id,
                        {"node_id":node_id,"revocation_id":rid,"reason":body["reason"]})
        return {**body,"signature":sig,"status":"REVOKED","entity_root_unchanged":True,
                "historical_evidence_preserved":True}

    def publish_service(self,entity_id:str,domain_id:str,node_id:str,service_type:str,endpoint:dict, *,
                        protocol_version:str="1",capabilities:list[str]|None=None,access_class:str="PUBLIC",
                        required_credentials:list[str]|None=None,policy_refs:list[str]|None=None,
                        data_classifications:list[str]|None=None,economic_terms_ref:str|None=None,
                        availability:dict|None=None,expires_at_ms:int|None=None,service_id:str|None=None)->dict:
        domain=self.get_domain(domain_id); node=self.get_node(node_id)
        if domain["entity_root"]!=entity_id or node["entity_root"]!=entity_id or node["domain_id"]!=domain_id:
            raise PermissionError("domain/node controller mismatch")
        if node.get("effective_status")!="ACTIVE": raise PermissionError("node not active")
        now=_now()
        if node.get("not_before_ms",0)>now or (node.get("expires_at_ms") is not None and int(node["expires_at_ms"])<=now):
            raise PermissionError("node authorization outside validity window")
        st=str(service_type).upper()
        if st not in SERVICE_TYPES: raise ValueError("unsupported service type")
        if st not in set(node["permitted_services"]) and "*" not in set(node["permitted_services"]):
            raise PermissionError("service outside node authorization")
        ac=str(access_class).upper()
        if ac not in ACCESS_CLASSES: raise ValueError("unsupported access class")
        sid=str(service_id or _id("svc1"))
        prior=None
        with self._connect() as db:
            prior=db.execute("SELECT manifest_version FROM services WHERE service_id=?",(sid,)).fetchone()
        version=int(prior["manifest_version"])+1 if prior else 1
        body={"schema":"entity-service-manifest-v1","entity_root":entity_id,"domain_id":domain_id,
              "domain_name":domain.get("current_name"),"service_id":sid,"service_type":st,"node_id":node_id,
              "endpoint":dict(endpoint),"protocol_version":str(protocol_version),
              "capabilities":sorted({str(x) for x in capabilities or []}),"access_class":ac,
              "required_credentials":sorted({str(x) for x in required_credentials or []}),
              "policy_refs":sorted({str(x) for x in policy_refs or []}),
              "data_classifications":sorted({str(x).upper() for x in data_classifications or []}),
              "economic_terms_ref":economic_terms_ref,"availability":dict(availability or {}),
              "manifest_version":version,"expires_at_ms":int(expires_at_ms) if expires_at_ms is not None else None,
              "status":"ACTIVE","created_at_ms":now,
              "source_data_custody_transferred":False,"provider_authority_inferred":False}
        sig=self.identity.sign(entity_id,body)
        with self._connect() as db:
            if prior:
                db.execute("""UPDATE services SET node_id=?,service_type=?,endpoint_json=?,protocol_version=?,
                    capabilities_json=?,access_class=?,required_credentials_json=?,policy_refs_json=?,
                    data_classifications_json=?,economic_terms_ref=?,availability_json=?,manifest_version=?,
                    expires_at_ms=?,status='ACTIVE',signature_json=?,created_at_ms=?,updated_at_ms=? WHERE service_id=?""",
                    (node_id,st,json.dumps(body["endpoint"],sort_keys=True),body["protocol_version"],
                     json.dumps(body["capabilities"]),ac,json.dumps(body["required_credentials"]),
                     json.dumps(body["policy_refs"]),json.dumps(body["data_classifications"]),economic_terms_ref,
                     json.dumps(body["availability"],sort_keys=True),version,body["expires_at_ms"],
                     json.dumps(sig,sort_keys=True),now,now,sid))
            else:
                db.execute("INSERT INTO services VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                           (sid,domain_id,node_id,st,json.dumps(body["endpoint"],sort_keys=True),body["protocol_version"],
                            json.dumps(body["capabilities"]),ac,json.dumps(body["required_credentials"]),
                            json.dumps(body["policy_refs"]),json.dumps(body["data_classifications"]),economic_terms_ref,
                            json.dumps(body["availability"],sort_keys=True),version,body["expires_at_ms"],"ACTIVE",
                            json.dumps(sig,sort_keys=True),now,now))
            self._audit(db,domain_id,"SERVICE_PUBLISHED",entity_id,{"service_id":sid,"node_id":node_id,"version":version})
        return {**body,"signature":sig}

    def get_domain(self,domain_id:str)->dict:
        with self._connect() as db:
            row=db.execute("SELECT * FROM domains WHERE domain_id=?",(domain_id,)).fetchone()
        if not row: raise KeyError("domain not found")
        out=dict(row)
        return {"schema":"entity-domain-v1","domain_id":out["domain_id"],"entity_root":out["entity_id"],
                "namespace":out["namespace"],"current_name":out["current_name"],"version":int(out["version"]),
                "status":out["status"],"created_at_ms":out["created_at_ms"],"updated_at_ms":out["updated_at_ms"]}

    def get_node(self,node_id:str)->dict:
        with self._connect() as db:
            row=db.execute("SELECT * FROM nodes WHERE node_id=?",(node_id,)).fetchone()
            rev=db.execute("SELECT * FROM revocations WHERE node_id=? ORDER BY effective_at_ms DESC LIMIT 1",(node_id,)).fetchone()
        if not row: raise KeyError("node not found")
        out=dict(row)
        result={"schema":"entity-node-authorization-v1","node_id":out["node_id"],"domain_id":out["domain_id"],
                "entity_root":out["entity_id"],"public_key_b64":out["public_key_b64"],
                "permitted_services":json.loads(out["permitted_services_json"]),
                "network_scopes":json.loads(out["network_scopes_json"]),
                "publication_scopes":json.loads(out["publication_scopes_json"]),
                "data_scopes":json.loads(out["data_scopes_json"]),"not_before_ms":out["not_before_ms"],
                "expires_at_ms":out["expires_at_ms"],"delegation":json.loads(out["delegation_json"]),
                "status":out["status"],"auth_version":int(out["auth_version"]),
                "created_at_ms":out["created_at_ms"],"signature":json.loads(out["signature_json"])}
        if rev:
            rb={"schema":"entity-node-revocation-v1","revocation_id":rev["revocation_id"],
                "domain_id":rev["domain_id"],"node_id":rev["node_id"],"entity_root":rev["entity_id"],
                "reason":rev["reason"],"effective_at_ms":rev["effective_at_ms"],"created_at_ms":rev["created_at_ms"]}
            result["revocation"]={**rb,"signature":json.loads(rev["signature_json"])}
            result["effective_status"]="REVOKED"
        else:
            result["revocation"]=None; result["effective_status"]=out["status"]
        return result

    def get_service(self,service_id:str)->dict:
        with self._connect() as db:
            row=db.execute("SELECT * FROM services WHERE service_id=?",(service_id,)).fetchone()
        if not row: raise KeyError("service not found")
        domain=self.get_domain(row["domain_id"])
        return {"schema":"entity-service-manifest-v1","entity_root":domain["entity_root"],"domain_id":row["domain_id"],
                "domain_name":domain.get("current_name"),"service_id":row["service_id"],"service_type":row["service_type"],
                "node_id":row["node_id"],"endpoint":json.loads(row["endpoint_json"]),
                "protocol_version":row["protocol_version"],"capabilities":json.loads(row["capabilities_json"]),
                "access_class":row["access_class"],"required_credentials":json.loads(row["required_credentials_json"]),
                "policy_refs":json.loads(row["policy_refs_json"]),"data_classifications":json.loads(row["data_classifications_json"]),
                "economic_terms_ref":row["economic_terms_ref"],"availability":json.loads(row["availability_json"]),
                "manifest_version":int(row["manifest_version"]),"expires_at_ms":row["expires_at_ms"],
                "status":row["status"],"created_at_ms":row["created_at_ms"],
                "source_data_custody_transferred":False,"provider_authority_inferred":False,
                "signature":json.loads(row["signature_json"])}

    def list_services(self,domain_id:str)->list[dict]:
        with self._connect() as db:
            rows=db.execute("SELECT service_id FROM services WHERE domain_id=? ORDER BY service_type,service_id",(domain_id,)).fetchall()
        return [self.get_service(r["service_id"]) for r in rows]

    def current_name_claim(self,domain_id:str)->dict|None:
        with self._connect() as db:
            row=db.execute("SELECT * FROM name_claims WHERE domain_id=? AND status='ACTIVE' ORDER BY created_at_ms DESC LIMIT 1",(domain_id,)).fetchone()
        if not row: return None
        body={"schema":"entity-name-claim-v1","claim_id":row["claim_id"],"domain_id":row["domain_id"],
              "entity_root":row["entity_id"],"normalized_name":row["normalized_name"],"namespace":row["namespace"],
              "status":row["status"],"conflict_state":row["conflict_state"],"evidence":json.loads(row["evidence_json"]),
              "created_at_ms":row["created_at_ms"],"first_seen_is_not_ownership":True,"dns_possession_is_not_authority":True}
        return {**body,"signature":json.loads(row["signature_json"])}

    def verify_node(self,node:dict)->bool:
        body={k:node[k] for k in ("schema","domain_id","entity_root","node_id","public_key_b64","permitted_services",
              "network_scopes","publication_scopes","data_scopes","not_before_ms","expires_at_ms","delegation","status","auth_version","created_at_ms")}
        return bool(self.identity.verify_signature(self.identity.load_manifest(node["entity_root"]),body,node["signature"]))

    def verify_service(self,service:dict)->bool:
        body={k:service[k] for k in ("schema","entity_root","domain_id","domain_name","service_id","service_type","node_id",
              "endpoint","protocol_version","capabilities","access_class","required_credentials","policy_refs",
              "data_classifications","economic_terms_ref","availability","manifest_version","expires_at_ms","status","created_at_ms",
              "source_data_custody_transferred","provider_authority_inferred")}
        return bool(self.identity.verify_signature(self.identity.load_manifest(service["entity_root"]),body,service["signature"]))

    def semantic_hash(self,domain_id:str)->str:
        """Hash sovereign meaning, deliberately excluding replaceable infrastructure bindings."""
        import hashlib
        snapshot=self.public_snapshot(domain_id)
        claim=snapshot.get("name_claim") or {}
        semantic={"domain_id":snapshot["domain"]["domain_id"],"entity_root":snapshot["domain"]["entity_root"],
                  "name":{"normalized_name":claim.get("normalized_name"),"namespace":claim.get("namespace"),
                          "conflict_state":claim.get("conflict_state")},
                  "services":[{k:s.get(k) for k in ("service_id","service_type","access_class","required_credentials",
                              "policy_refs","data_classifications","economic_terms_ref","status")}
                              for s in snapshot["services"]]}
        raw=json.dumps(semantic,sort_keys=True,separators=(",",":"),default=str).encode()
        return hashlib.sha256(raw).hexdigest()

    def record_migration(self,entity_id:str,domain_id:str,*,from_node:str|None,to_node:str|None,
                         from_provider:str|None,to_provider:str|None,semantic_hash_before:str,semantic_hash_after:str)->dict:
        domain=self.get_domain(domain_id)
        if domain["entity_root"]!=entity_id: raise PermissionError("domain controller mismatch")
        if semantic_hash_before!=semantic_hash_after:
            raise RuntimeError("provider/device migration changed sovereign domain semantics")
        mid=_id("dmig1"); now=_now()
        body={"schema":"entity-domain-migration-v1","migration_id":mid,"domain_id":domain_id,"entity_root":entity_id,
              "from_node":from_node,"to_node":to_node,"from_provider":from_provider,"to_provider":to_provider,
              "semantic_hash_before":semantic_hash_before,"semantic_hash_after":semantic_hash_after,
              "created_at_ms":now,"provider_replacement_is_not_entity_replacement":True}
        sig=self.identity.sign(entity_id,body)
        with self._connect() as db:
            db.execute("INSERT INTO migrations VALUES(?,?,?,?,?,?,?,?,?,?)",
                       (mid,domain_id,from_node,to_node,from_provider,to_provider,semantic_hash_before,semantic_hash_after,
                        json.dumps(sig,sort_keys=True),now))
            self._audit(db,domain_id,"DOMAIN_MIGRATED",entity_id,{"migration_id":mid,"from_provider":from_provider,"to_provider":to_provider})
        return {**body,"signature":sig}

    def public_snapshot(self,domain_id:str)->dict:
        domain=self.get_domain(domain_id)
        with self._connect() as db:
            node_ids=[r["node_id"] for r in db.execute("SELECT node_id FROM nodes WHERE domain_id=? ORDER BY node_id",(domain_id,))]
            migrations=[dict(r) for r in db.execute("SELECT * FROM migrations WHERE domain_id=? ORDER BY created_at_ms",(domain_id,))]
        migration_records=[]
        for m in migrations:
            sig=json.loads(m.pop("signature_json"))
            migration_records.append({"schema":"entity-domain-migration-v1","migration_id":m["migration_id"],
                "domain_id":m["domain_id"],"entity_root":domain["entity_root"],"from_node":m.get("from_node"),
                "to_node":m.get("to_node"),"from_provider":m.get("from_provider"),"to_provider":m.get("to_provider"),
                "semantic_hash_before":m["semantic_hash_before"],"semantic_hash_after":m["semantic_hash_after"],
                "created_at_ms":m["created_at_ms"],"provider_replacement_is_not_entity_replacement":True,"signature":sig})
        return {"schema":"entity-domain-public-snapshot-v1","domain":domain,"name_claim":self.current_name_claim(domain_id),
                "nodes":[self.get_node(x) for x in node_ids],"services":self.list_services(domain_id),
                "migrations":migration_records,"dns_authority_required":False,"btg_authority_required":False,
                "cloud_host_required":False}

    def status(self)->dict:
        with self._connect() as db:
            domains=int(db.execute("SELECT COUNT(*) FROM domains").fetchone()[0])
            nodes=int(db.execute("SELECT COUNT(*) FROM nodes").fetchone()[0])
            services=int(db.execute("SELECT COUNT(*) FROM services").fetchone()[0])
        return {"ready":True,"schema":"entity-sovereign-domain-authority-v1","domains":domains,"nodes":nodes,"services":services,
                "domain_is_dns":False,"domain_is_device":False,"provider_is_authority":False,"owner_controlled_hosting":True}
