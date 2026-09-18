from __future__ import annotations
from datetime import datetime, timezone
import base64, json

VC_CONTEXT="https://www.w3.org/ns/credentials/v2"
ODRL_CONTEXT="http://www.w3.org/ns/odrl.jsonld"
ENTITY_PROFILE="https://blackmoretechnology.group/ns/entity/odrl/v1"
ENTITY_VOCAB="https://blackmoretechnology.group/ns/entity/v1#"
DID_PREFIX="did:entity:"


def _iso(ms:int|None)->str|None:
    if ms is None: return None
    return datetime.fromtimestamp(int(ms)/1000,tz=timezone.utc).isoformat().replace("+00:00","Z")

def _ms(value:str|None)->int|None:
    if not value: return None
    return int(datetime.fromisoformat(str(value).replace("Z","+00:00")).timestamp()*1000)

def did(entity_id:str)->str: return DID_PREFIX+str(entity_id)
def entity_from_did(value:str)->str:
    if not str(value).startswith(DID_PREFIX): raise ValueError("unsupported DID method")
    return str(value)[len(DID_PREFIX):]

class EntityStandardsInterop:
    """Standards data-model adapter. It does not claim W3C Data Integrity cryptosuite conformance."""
    def __init__(self,identity): self.identity=identity

    def export_did_document(self,entity_id:str)->dict:
        manifest=self.identity.load_manifest(entity_id); controller=did(entity_id); methods=[]; auth=[]; assertion=[]
        for item in manifest.get("verification_methods") or []:
            kid=f"{controller}#{item['key_id']}"; purposes=set(item.get("purpose") or [])
            methods.append({"id":kid,"type":"Ed25519VerificationKey2020","controller":controller,"publicKeyMultibase":"u"+item["public_key"],"entity:keyStatus":item.get("status")})
            if "authentication" in purposes: auth.append(kid)
            if purposes.intersection({"assertion","contract"}): assertion.append(kid)
        return {"@context":["https://www.w3.org/ns/did/v1",{"entity":ENTITY_VOCAB}],"id":controller,"verificationMethod":methods,"authentication":auth,"assertionMethod":assertion,"entity:manifestRevision":manifest.get("manifest_revision")}

    @staticmethod
    def import_did_document(document:dict)->dict:
        doc=dict(document or {}); entity_id=entity_from_did(str(doc.get("id") or "")); methods=list(doc.get("verificationMethod") or [])
        if not methods: raise ValueError("DID document requires verificationMethod")
        for item in methods:
            if str(item.get("controller"))!=doc["id"] or not str(item.get("id","")).startswith(doc["id"]+"#"): raise ValueError("DID verification relationship mismatch")
        return {"entity_id":entity_id,"verification_methods":methods,"authentication":list(doc.get("authentication") or []),"assertion_method":list(doc.get("assertionMethod") or [])}

    def export_vc20(self,credential:dict)->dict:
        cred=dict(credential or {}); issuer=did(cred["issuer_entity_id"]); subject=did(cred["subject_entity_id"])
        vc={"@context":[VC_CONTEXT,{"entity":ENTITY_VOCAB}],"id":"urn:entity:credential:"+str(cred["credential_id"]),"type":["VerifiableCredential","EntityCredential"],"issuer":issuer,"validFrom":_iso(cred["created_at_ms"]),"credentialSubject":{"id":subject,**dict(cred.get("claims") or {})},"entity:credentialType":cred["credential_type"],"entity:trustLevel":cred["trust_level"]}
        if cred.get("expires_at_ms") is not None: vc["validUntil"]=_iso(cred["expires_at_ms"])
        if cred.get("signature") is not None: vc["entity:signatureRecord"]=dict(cred["signature"])
        return vc

    @staticmethod
    def import_vc20(vc:dict)->dict:
        value=dict(vc or {}); contexts=value.get("@context") or []
        if VC_CONTEXT not in (contexts if isinstance(contexts,list) else [contexts]): raise ValueError("VC 2.0 context required")
        types=value.get("type") or []
        if "VerifiableCredential" not in (types if isinstance(types,list) else [types]): raise ValueError("VerifiableCredential type required")
        issuer=value.get("issuer"); issuer=issuer.get("id") if isinstance(issuer,dict) else issuer
        subject=dict(value.get("credentialSubject") or {}); sid=subject.pop("id",None)
        if not issuer or not sid: raise ValueError("issuer and credentialSubject.id required")
        return {"external_id":value.get("id"),"issuer":str(issuer),"subject":str(sid),"claims":subject,"valid_from_ms":_ms(value.get("validFrom")),"valid_until_ms":_ms(value.get("validUntil")),"verification_state":"UNVERIFIED_EXTERNAL_STATE"}

    def verify_entity_vc20(self,vc:dict,issuer_manifest:dict)->dict:
        mapped=self.import_vc20(vc); signature=vc.get("entity:signatureRecord")
        if not signature: return {"data_model_valid":True,"entity_signature_valid":False,"reason":"no_entity_signature_extension"}
        cred_id=str(vc.get("id") or "").removeprefix("urn:entity:credential:"); subject=entity_from_did(mapped["subject"]); issuer=entity_from_did(mapped["issuer"])
        body={"schema":"entity-credential-v1","credential_id":cred_id,"issuer_entity_id":issuer,"subject_entity_id":subject,"credential_type":vc.get("entity:credentialType"),"claims":mapped["claims"],"trust_level":vc.get("entity:trustLevel"),"status":"ACTIVE","expires_at_ms":mapped["valid_until_ms"],"created_at_ms":mapped["valid_from_ms"]}
        return {"data_model_valid":True,"entity_signature_valid":bool(self.identity.verify_signature(issuer_manifest,body,signature)),"proof_scope":"ENTITY_EXTENSION_NOT_W3C_DATA_INTEGRITY"}

    @staticmethod
    def export_odrl_policy(policy:dict,*,asset_ref:str,assignee:str|None=None)->dict:
        rules=dict(policy.get("rules") or {}); out={"@context":ODRL_CONTEXT,"@type":"Agreement" if assignee else "Set","uid":"urn:entity:policy:%s:v%s"%(policy["policy_id"],policy["version"]),"profile":ENTITY_PROFILE}
        permission=[]; prohibition=[]
        for action,item in sorted(rules.items()):
            rule={"target":str(asset_ref),"assigner":did(policy["controller_entity_id"]),"action":ENTITY_VOCAB+"action/"+str(action).lower()}
            if assignee: rule["assignee"]=str(assignee)
            if item.get("constraints"): rule["constraint"]=[{"leftOperand":ENTITY_VOCAB+str(k),"operator":"eq","rightOperand":v} for k,v in sorted(item["constraints"].items())]
            if item.get("duties"): rule["duty"]=[{"action":ENTITY_VOCAB+"duty/"+str(x)} for x in item["duties"]]
            decision=str(item.get("decision") or "PROHIBIT").upper()
            (permission if decision in {"PERMIT","LICENSE_REQUIRED","OWNER_ONLY"} else prohibition).append(rule)
        if permission: out["permission"]=permission
        if prohibition: out["prohibition"]=prohibition
        if not permission and not prohibition: raise ValueError("ODRL policy must contain a rule")
        out["entity:sourcePolicy"]={"policy_id":policy["policy_id"],"version":int(policy["version"]),"rules":rules}
        return out

    @staticmethod
    def import_odrl_policy(document:dict)->dict:
        doc=dict(document or {}); context=doc.get("@context")
        if context!=ODRL_CONTEXT and ODRL_CONTEXT not in (context if isinstance(context,list) else []): raise ValueError("ODRL context required")
        if doc.get("@type") not in {"Set","Offer","Agreement","Policy"}: raise ValueError("unsupported ODRL policy type")
        rules=[]
        for kind,key in (("PERMIT","permission"),("PROHIBIT","prohibition")):
            for rule in doc.get(key) or []:
                if not rule.get("target") or not rule.get("action"): raise ValueError("ODRL rule target/action required")
                rules.append({"decision":kind,"target":rule["target"],"action":rule["action"],"assigner":rule.get("assigner"),"assignee":rule.get("assignee")})
        if not rules: raise ValueError("ODRL policy requires permission or prohibition")
        return {"uid":doc.get("uid"),"type":doc.get("@type"),"profile":doc.get("profile"),"rules":rules,"verification_state":"SEMANTICALLY_PARSED_NOT_LEGAL_DETERMINATION"}
