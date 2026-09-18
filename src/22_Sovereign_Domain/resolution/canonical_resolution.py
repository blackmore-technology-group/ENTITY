from __future__ import annotations
from pathlib import Path
import hashlib, json, time

def _canon(v): return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()
def _sha(v): return hashlib.sha256(v if isinstance(v,(bytes,bytearray)) else _canon(v)).hexdigest()
def _now(): return int(time.time()*1000)

class EntityNativeResolver:
    """DNS-independent verifier/resolver. Resolution sources are transport hints, never sovereign authority."""
    def __init__(self,identity):
        self.identity=identity
        self.sources={}
        self.highest_domain_version={}
        self.highest_service_version={}

    def add_snapshot(self,source_id:str,snapshot:dict)->dict:
        snap=json.loads(json.dumps(snapshot))
        proof=self.verify_snapshot(snap)
        if not proof["valid"]:
            raise PermissionError("invalid sovereign-domain snapshot: "+",".join(proof["failures"]))
        key=snap["domain"]["domain_id"]
        self.sources[(str(source_id),key)]=snap
        return {"accepted":True,"source_id":str(source_id),"domain_id":key,
                "resolver_is_authority":False,"snapshot_sha256":_sha(snap)}

    def _verify_claim(self,claim:dict)->bool:
        if not claim: return True
        body={k:claim[k] for k in ("schema","claim_id","domain_id","entity_root","normalized_name","namespace",
                                   "status","conflict_state","evidence","created_at_ms",
                                   "first_seen_is_not_ownership","dns_possession_is_not_authority")}
        return bool(self.identity.verify_signature(self.identity.load_manifest(claim["entity_root"]),body,claim["signature"]))

    def _verify_node(self,node:dict)->bool:
        body={k:node[k] for k in ("schema","domain_id","entity_root","node_id","public_key_b64","permitted_services",
                                  "network_scopes","publication_scopes","data_scopes","not_before_ms","expires_at_ms",
                                  "delegation","status","auth_version","created_at_ms")}
        return bool(self.identity.verify_signature(self.identity.load_manifest(node["entity_root"]),body,node["signature"]))

    def _verify_revocation(self,revocation:dict|None)->bool:
        if not revocation: return True
        body={k:revocation[k] for k in ("schema","revocation_id","domain_id","node_id","entity_root","reason","effective_at_ms","created_at_ms")}
        return bool(self.identity.verify_signature(self.identity.load_manifest(revocation["entity_root"]),body,revocation["signature"]))

    def _verify_service(self,service:dict)->bool:
        body={k:service[k] for k in ("schema","entity_root","domain_id","domain_name","service_id","service_type",
                                     "node_id","endpoint","protocol_version","capabilities","access_class",
                                     "required_credentials","policy_refs","data_classifications","economic_terms_ref",
                                     "availability","manifest_version","expires_at_ms","status","created_at_ms",
                                     "source_data_custody_transferred","provider_authority_inferred")}
        return bool(self.identity.verify_signature(self.identity.load_manifest(service["entity_root"]),body,service["signature"]))

    def verify_snapshot(self,snapshot:dict)->dict:
        failures=[]; snap=dict(snapshot or {})
        domain=dict(snap.get("domain") or {}); did=str(domain.get("domain_id") or ""); root=str(domain.get("entity_root") or "")
        if not did or not root: failures.append("domain_identity_missing")
        else:
            try: self.identity.load_manifest(root)
            except Exception: failures.append("entity_root_unknown")
        claim=snap.get("name_claim")
        if claim:
            if claim.get("domain_id")!=did or claim.get("entity_root")!=root: failures.append("name_claim_binding_mismatch")
            elif not self._verify_claim(claim): failures.append("name_claim_signature_invalid")
        nodes={}
        now=_now()
        for node in snap.get("nodes") or []:
            nid=str(node.get("node_id") or "")
            if node.get("domain_id")!=did or node.get("entity_root")!=root: failures.append(f"node:{nid}:binding_mismatch"); continue
            if not self._verify_node(node): failures.append(f"node:{nid}:signature_invalid"); continue
            if node.get("revocation") and not self._verify_revocation(node.get("revocation")):
                failures.append(f"node:{nid}:revocation_signature_invalid"); continue
            nodes[nid]=node
        for service in snap.get("services") or []:
            sid=str(service.get("service_id") or ""); nid=str(service.get("node_id") or "")
            if service.get("domain_id")!=did or service.get("entity_root")!=root: failures.append(f"service:{sid}:binding_mismatch"); continue
            if not self._verify_service(service): failures.append(f"service:{sid}:signature_invalid"); continue
            node=nodes.get(nid)
            if node is None: failures.append(f"service:{sid}:node_missing"); continue
            if service.get("status")=="ACTIVE":
                if node.get("effective_status",node.get("status"))!="ACTIVE": failures.append(f"service:{sid}:revoked_node")
                if int(node.get("not_before_ms") or 0)>now: failures.append(f"service:{sid}:node_not_yet_valid")
                exp=node.get("expires_at_ms")
                if exp is not None and int(exp)<=now: failures.append(f"service:{sid}:node_expired")
                sexp=service.get("expires_at_ms")
                if sexp is not None and int(sexp)<=now: failures.append(f"service:{sid}:manifest_expired")
                if str(service.get("service_type")) not in set(node.get("permitted_services") or []) and "*" not in set(node.get("permitted_services") or []):
                    failures.append(f"service:{sid}:outside_node_scope")
        return {"valid":not failures,"failures":failures,"domain_id":did,"entity_root":root,
                "snapshot_sha256":_sha(snap),"resolver_authority_claimed":False}

    def resolve(self,identifier:str,*,service_type:str|None=None,service_id:str|None=None)->dict:
        ident=str(identifier).strip().lower()
        candidates=[]
        for (_,did),snap in self.sources.items():
            domain=snap["domain"]; claim=snap.get("name_claim")
            matches=(did.lower()==ident or domain["entity_root"].lower()==ident or
                     (claim and (claim.get("normalized_name") or "").lower()==ident))
            if matches: candidates.append(snap)
        unique={s["domain"]["domain_id"]:s for s in candidates}
        if not unique: raise KeyError("Entity domain not found")
        if len(unique)>1:
            raise RuntimeError("Entity name conflict requires cryptographic/disambiguated identifier")
        snap=next(iter(unique.values())); proof=self.verify_snapshot(snap)
        if not proof["valid"]: raise PermissionError("resolution snapshot verification failed")
        domain=snap["domain"]; did=domain["domain_id"]; dv=int(domain.get("version") or 0)
        prior=self.highest_domain_version.get(did,0)
        if dv<prior: raise PermissionError("domain rollback/stale state detected")
        self.highest_domain_version[did]=max(prior,dv)
        services=[s for s in snap.get("services") or [] if s.get("status")=="ACTIVE"]
        if service_type: services=[s for s in services if str(s.get("service_type")).upper()==str(service_type).upper()]
        if service_id: services=[s for s in services if s.get("service_id")==service_id]
        valid=[]
        nodes={n["node_id"]:n for n in snap.get("nodes") or []}
        for s in services:
            sid=s["service_id"]; version=int(s.get("manifest_version") or 0); high=self.highest_service_version.get(sid,0)
            if version<high: continue
            node=nodes.get(s["node_id"])
            if not node or node.get("effective_status",node.get("status"))!="ACTIVE": continue
            self.highest_service_version[sid]=max(high,version)
            valid.append({"service":s,"node":node})
        if not valid: raise KeyError("no current authorized service endpoint")
        claim=snap.get("name_claim")
        if claim and claim.get("conflict_state")=="CONFLICT" and ident==(claim.get("normalized_name") or "").lower():
            raise RuntimeError("name conflict requires entity/domain identifier")
        root=domain["entity_root"]
        result={"schema":"entity-resolution-proof-v1","requested_identifier":identifier,"domain_id":did,"entity_root":root,
                "domain_name":claim.get("normalized_name") if claim else None,"domain_version":dv,
                "snapshot_sha256":proof["snapshot_sha256"],"services":valid,
                "dns_used_as_authority":False,"resolver_is_authority":False,"verified":True,"resolved_at_ms":_now()}
        result["resolution_proof_sha256"]=_sha(result)
        return result

    @staticmethod
    def reject_malicious_response(expected:dict,response:dict)->dict:
        problems=[]
        if response.get("entity_root")!=expected.get("entity_root"): problems.append("entity_root_substitution")
        if response.get("domain_id")!=expected.get("domain_id"): problems.append("domain_substitution")
        expected_services={x["service"]["service_id"]:x for x in expected.get("services") or []}
        for item in response.get("services") or []:
            sid=(item.get("service") or {}).get("service_id")
            if sid not in expected_services: problems.append("unauthorized_service_injection")
            elif item!=expected_services[sid]: problems.append("service_or_node_substitution")
        return {"accepted":not problems,"problems":problems}

    def status(self)->dict:
        return {"ready":True,"schema":"entity-native-resolver-v1","dns_required":False,
                "single_btg_resolver_required":False,"anti_rollback":True,"resolver_is_authority":False}
