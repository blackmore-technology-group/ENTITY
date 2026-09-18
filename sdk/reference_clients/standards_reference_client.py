from __future__ import annotations
from datetime import datetime
import base64, hashlib, json
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

VC_CONTEXT="https://www.w3.org/ns/credentials/v2"
ODRL_CONTEXT="http://www.w3.org/ns/odrl.jsonld"
DID_PREFIX="did:entity:"

def canon(v): return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
def unb64(v): return base64.urlsafe_b64decode(str(v)+"="*(-len(str(v))%4))

def validate_did_document(doc:dict)->dict:
    value=dict(doc or {}); did=str(value.get("id") or "")
    failures=[]
    if not did.startswith(DID_PREFIX): failures.append("unsupported_did_method")
    methods={str(x.get("id")):x for x in value.get("verificationMethod") or []}
    if not methods: failures.append("verification_method_missing")
    for mid,item in methods.items():
        if str(item.get("controller"))!=did: failures.append(f"{mid}:controller_mismatch")
        if not str(item.get("publicKeyMultibase") or "").startswith("u"): failures.append(f"{mid}:public_key_encoding")
    for rel in ("authentication","assertionMethod"):
        for ref in value.get(rel) or []:
            if str(ref) not in methods: failures.append(f"{rel}:unresolved_reference")
    return {"valid":not failures,"failures":failures,"did":did,"verification_methods":len(methods)}

def validate_vc20(vc:dict)->dict:
    value=dict(vc or {}); failures=[]; contexts=value.get("@context") or []
    contexts=contexts if isinstance(contexts,list) else [contexts]; types=value.get("type") or []; types=types if isinstance(types,list) else [types]
    if VC_CONTEXT not in contexts: failures.append("vc20_context_missing")
    if "VerifiableCredential" not in types: failures.append("verifiable_credential_type_missing")
    issuer=value.get("issuer"); issuer=issuer.get("id") if isinstance(issuer,dict) else issuer
    if not issuer: failures.append("issuer_missing")
    subject=value.get("credentialSubject")
    if not isinstance(subject,dict) or not subject: failures.append("credential_subject_missing")
    for field in ("validFrom","validUntil"):
        if value.get(field):
            try: datetime.fromisoformat(str(value[field]).replace("Z","+00:00"))
            except Exception: failures.append(field+":invalid_datetime")
    return {"valid":not failures,"failures":failures,"issuer":issuer,"subject":subject}

def verify_entity_vc_extension(vc:dict,did_document:dict)->dict:
    model=validate_vc20(vc)
    if not model["valid"]: return {"valid":False,"failures":model["failures"]}
    sig=dict(vc.get("entity:signatureRecord") or {})
    if sig.get("signature_schema")!="entity-signature-record-v2": return {"valid":False,"failures":["entity_signature_extension_missing"]}
    credential_id=str(vc.get("id") or "").removeprefix("urn:entity:credential:")
    subject=dict(vc.get("credentialSubject") or {}); subject_id=str(subject.pop("id"))
    issuer=str(model["issuer"]); issuer_entity=issuer.removeprefix(DID_PREFIX); subject_entity=subject_id.removeprefix(DID_PREFIX)
    def ms(value): return None if not value else int(datetime.fromisoformat(str(value).replace("Z","+00:00")).timestamp()*1000)
    body={"schema":"entity-credential-v1","credential_id":credential_id,"issuer_entity_id":issuer_entity,"subject_entity_id":subject_entity,"credential_type":vc.get("entity:credentialType"),"claims":subject,"trust_level":vc.get("entity:trustLevel"),"status":"ACTIVE","expires_at_ms":ms(vc.get("validUntil")),"created_at_ms":ms(vc.get("validFrom"))}
    if hashlib.sha256(canon(body)).hexdigest()!=sig.get("payload_sha256"): return {"valid":False,"failures":["payload_hash_mismatch"]}
    key_ref=issuer+"#"+str(sig.get("key_id")); methods={str(x.get("id")):x for x in did_document.get("verificationMethod") or []}; method=methods.get(key_ref)
    if not method: return {"valid":False,"failures":["verification_method_not_found"]}
    record={k:sig[k] for k in ("signature_schema","entity_id","key_id","suite","signed_at_ms","payload_sha256")}
    try:
        Ed25519PublicKey.from_public_bytes(unb64(str(method["publicKeyMultibase"])[1:])).verify(unb64(sig["signature"]),canon(record))
        return {"valid":True,"failures":[],"proof_scope":"ENTITY_EXTENSION_NOT_W3C_DATA_INTEGRITY"}
    except Exception: return {"valid":False,"failures":["signature_invalid"]}

def validate_odrl22(doc:dict)->dict:
    value=dict(doc or {}); failures=[]; context=value.get("@context"); contexts=context if isinstance(context,list) else [context]
    if ODRL_CONTEXT not in contexts: failures.append("odrl_context_missing")
    if value.get("@type") not in {"Set","Offer","Agreement","Policy"}: failures.append("odrl_policy_type_invalid")
    if not value.get("uid"): failures.append("odrl_uid_missing")
    count=0
    for key in ("permission","prohibition","obligation"):
        for rule in value.get(key) or []:
            count+=1
            if key!="obligation" and not rule.get("target"): failures.append(f"{key}:target_missing")
            if not rule.get("action"): failures.append(f"{key}:action_missing")
    if count==0: failures.append("odrl_rule_missing")
    if value.get("@type")=="Agreement":
        for rule in (value.get("permission") or [])+(value.get("prohibition") or []):
            if not rule.get("assigner") or not rule.get("assignee"): failures.append("agreement_party_missing")
    return {"valid":not failures,"failures":failures,"rule_count":count,"profile":value.get("profile")}
