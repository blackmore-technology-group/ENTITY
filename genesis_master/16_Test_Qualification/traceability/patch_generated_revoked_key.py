from pathlib import Path
p=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network\16_Test_Qualification\model_based\run_generated_invariants.py")
s=p.read_text(encoding="utf-8")
s=s.replace('import hashlib, importlib.util, json, random, sys, tempfile, time','import base64, hashlib, importlib.util, json, random, sys, tempfile, time\nfrom cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey')
old='        counts["historical_signatures_after_recovery"]=100\n'
new='''        counts["historical_signatures_after_recovery"]=100\n        old_key_id=signed[0][1]["key_id"]; method=next(x for x in manifest["verification_methods"] if x["key_id"]==old_key_id); old_raw=(state/"identity"/"keys"/owner/f"{old_key_id}.key").read_bytes(); old_key=Ed25519PrivateKey.from_private_bytes(old_raw)\n        for i in range(100):\n            payload={"post_revocation":i}; digest=hashlib.sha256(I.canonical_json(payload)).hexdigest(); rec={"signature_schema":"entity-signature-record-v2","entity_id":owner,"key_id":old_key_id,"suite":method["suite"],"signed_at_ms":int(method["revoked_at_ms"])+1+i,"payload_sha256":digest}; rec["signature"]=base64.urlsafe_b64encode(old_key.sign(I.canonical_json(rec))).decode("ascii").rstrip("=")\n            if I.EntityIdentityVault.verify_signature(manifest,payload,rec): failures.append(f"revoked_key_late_authorization:{i}")\n        counts["revoked_key_post_revocation_rejected"]=100\n'''
s=s.replace(old,new)
p.write_text(s,encoding="utf-8"); print("patched",p)
