from __future__ import annotations
from pathlib import Path
import base64, hashlib, json, sys
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

def canon(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
def unb64(value):
    s=str(value); return base64.urlsafe_b64decode(s+"="*((4-len(s)%4)%4))
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def verify_entity_manifest(manifest):
    if manifest.get("schema")!="sovereign-entity-manifest-v2": return False
    data=dict(manifest); sig=dict(data.pop("signature",{})); key_id=str(sig.get("key_id") or "")
    method=next((x for x in data.get("verification_methods",[]) if x.get("key_id")==key_id),None)
    if not method or method.get("suite")!=sig.get("suite") or method.get("status")!="active": return False
    try:
        Ed25519PublicKey.from_public_bytes(unb64(method["public_key"])).verify(unb64(sig["signature"]),canon(data))
        return True
    except Exception: return False

def verify_signature(manifest,payload,record):
    if not verify_entity_manifest(manifest): return False
    if record.get("entity_id")!=manifest.get("entity_id"): return False
    payload_hash=hashlib.sha256(canon(payload)).hexdigest()
    if record.get("payload_sha256")!=payload_hash: return False
    method=next((x for x in manifest.get("verification_methods",[]) if x.get("key_id")==record.get("key_id")),None)
    if not method or method.get("suite")!=record.get("suite"): return False
    signed={"signature_schema":record.get("signature_schema"),"entity_id":record.get("entity_id"),
            "key_id":record.get("key_id"),"suite":record.get("suite"),
            "signed_at_ms":record.get("signed_at_ms"),"payload_sha256":payload_hash}
    try:
        Ed25519PublicKey.from_public_bytes(unb64(method["public_key"])).verify(unb64(record["signature"]),canon(signed))
        return True
    except Exception: return False

def verify_distribution(root):
    root=Path(root).resolve(); mp=root/"SIGNED_RELEASE_MANIFEST.json"; tp=root/"ENTITY_RELEASE_SIGNER_PUBLIC.json"
    if not mp.is_file() or not tp.is_file(): return {"valid":False,"reason":"required_manifest_missing"}
    release=json.loads(mp.read_text(encoding="utf-8")); trust=json.loads(tp.read_text(encoding="utf-8"))
    signature=dict(release.get("signature") or {}); payload={k:v for k,v in release.items() if k!="signature"}
    checks={"trust_manifest_valid":verify_entity_manifest(trust),
            "release_signature_valid":verify_signature(trust,payload,signature),
            "signer_matches":release.get("release_signer_entity_id")==trust.get("entity_id")}
    failures=[]
    for item in release.get("artifacts") or []:
        rel=str(item.get("path") or ""); p=(root/rel).resolve()
        try: p.relative_to(root)
        except ValueError: failures.append({"path":rel,"reason":"path_escape"}); continue
        if not p.is_file(): failures.append({"path":rel,"reason":"missing"}); continue
        if sha(p)!=item.get("sha256"): failures.append({"path":rel,"reason":"sha256_mismatch"})
    checks["artifact_hashes_valid"]=not failures
    return {"valid":all(checks.values()),"checks":checks,"artifact_failures":failures,
            "release_id":release.get("release_id"),"release_status":release.get("status"),
            "signer_entity_id":trust.get("entity_id")}

def main():
    target=Path(sys.argv[1] if len(sys.argv)>1 else ".")
    result=verify_distribution(target); print(json.dumps(result,indent=2,sort_keys=True)); return 0 if result["valid"] else 2
if __name__=="__main__": raise SystemExit(main())
