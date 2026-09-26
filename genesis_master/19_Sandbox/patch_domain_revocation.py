from pathlib import Path
p=Path(r'<LOCAL_DRIVE>/Sovereign_Entity_Network\22_Sovereign_Domain\core\canonical_domain.py')
t=p.read_text(encoding='utf-8')
needle='''            db.execute("""CREATE TABLE IF NOT EXISTS migrations(
                migration_id TEXT PRIMARY KEY,domain_id TEXT NOT NULL,from_node TEXT,to_node TEXT,
                from_provider TEXT,to_provider TEXT,semantic_hash_before TEXT NOT NULL,
                semantic_hash_after TEXT NOT NULL,signature_json TEXT NOT NULL,
                created_at_ms INTEGER NOT NULL)""")'''
insert=needle+'''\n            db.execute("""CREATE TABLE IF NOT EXISTS revocations(
                revocation_id TEXT PRIMARY KEY,domain_id TEXT NOT NULL,node_id TEXT NOT NULL,
                entity_id TEXT NOT NULL,reason TEXT NOT NULL,effective_at_ms INTEGER NOT NULL,
                signature_json TEXT NOT NULL,created_at_ms INTEGER NOT NULL)""")'''
if 'CREATE TABLE IF NOT EXISTS revocations' not in t:
    assert needle in t
    t=t.replace(needle,insert)
start=t.index('    def revoke_node(')
end=t.index('    def publish_service(',start)
new='''    def revoke_node(self,entity_id:str,node_id:str,reason:str="owner_action")->dict:
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

'''
t=t[:start]+new+t[end:]
start=t.index('    def get_node(')
end=t.index('    def get_service(',start)
new='''    def get_node(self,node_id:str)->dict:
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

'''
t=t[:start]+new+t[end:]
t=t.replace('if node["status"]!="ACTIVE": raise PermissionError("node not active")',
            'if node.get("effective_status")!="ACTIVE": raise PermissionError("node not active")')
p.write_text(t,encoding='utf-8')
print('patched',p)
