from pathlib import Path
p=Path(r'<LOCAL_DRIVE>/Sovereign_Entity_Network\22_Sovereign_Domain\resolution\canonical_resolution.py')
t=p.read_text(encoding='utf-8')
needle='''    def _verify_node(self,node:dict)->bool:
        body={k:node[k] for k in ("schema","domain_id","entity_root","node_id","public_key_b64","permitted_services",
                                  "network_scopes","publication_scopes","data_scopes","not_before_ms","expires_at_ms",
                                  "delegation","status","auth_version","created_at_ms")}
        return bool(self.identity.verify_signature(self.identity.load_manifest(node["entity_root"]),body,node["signature"]))
'''
replacement=needle+'''\n    def _verify_revocation(self,revocation:dict|None)->bool:\n        if not revocation: return True\n        body={k:revocation[k] for k in ("schema","revocation_id","domain_id","node_id","entity_root","reason","effective_at_ms","created_at_ms")}\n        return bool(self.identity.verify_signature(self.identity.load_manifest(revocation["entity_root"]),body,revocation["signature"]))\n'''
assert needle in t
t=t.replace(needle,replacement)
t=t.replace('''            if not self._verify_node(node): failures.append(f"node:{nid}:signature_invalid"); continue
            nodes[nid]=node''','''            if not self._verify_node(node): failures.append(f"node:{nid}:signature_invalid"); continue
            if node.get("revocation") and not self._verify_revocation(node.get("revocation")):
                failures.append(f"node:{nid}:revocation_signature_invalid"); continue
            nodes[nid]=node''')
t=t.replace('node.get("status")!="ACTIVE"','node.get("effective_status",node.get("status"))!="ACTIVE"')
p.write_text(t,encoding='utf-8')
print('patched resolver')
