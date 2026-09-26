from pathlib import Path
import hashlib, json
ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
EV=ROOT/"16_Test_Qualification"/"evidence"
new_ev=json.loads((EV/"ENTITY_EVENT_LEDGER_ASSET_REGISTRY_CURRENT.json").read_text(encoding="utf-8"))
new_ev_sha=str(new_ev["evidence_sha256"])
for rel,impl in [
    ("04_Entity_Registry/event_ledger/ENTITY_RUNTIME_BINDING.json","04_Entity_Registry/event_ledger/canonical_event_ledger.py"),
    ("04_Entity_Registry/asset_registry/ENTITY_RUNTIME_BINDING.json","04_Entity_Registry/asset_registry/canonical_asset_registry.py")]:
    p=ROOT/rel; data=json.loads(p.read_text(encoding="utf-8"))
    data["implementation_version"]="2.0.1-v2.2-compat"
    data["implementation_sha256"]=hashlib.sha256((ROOT/impl).read_bytes()).hexdigest()
    for q in data.get("qualification_evidence",[]):
        if "ENTITY_EVENT_LEDGER_ASSET_REGISTRY_CURRENT.json" in str(q.get("path")): q["sha256"]=new_ev_sha
    p.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print("bindings refreshed",new_ev_sha)
release_files=[
"ENTITY_PRIVACY_ADVERSARIAL_CURRENT.json","ENTITY_SECURITY_ADVERSARIAL_CURRENT.json","ENTITY_AI_GOVERNANCE_CURRENT.json",
"ENTITY_RIGHTS_PROVENANCE_CURRENT.json","ENTITY_ECONOMIC_QUALIFICATION_CURRENT.json","ENTITY_CORPORATE_CAPITAL_EVIDENCE_CURRENT.json",
"ENTITY_STANDARDS_INTEROP_CURRENT.json","ENTITY_DESTRUCTIVE_RECOVERY_CURRENT.json","ENTITY_FULL_E2E_QUALIFICATION_CURRENT.json"]
for name in release_files:
    p=EV/name; d=json.loads(p.read_text(encoding="utf-8")); expected=str(d.get("evidence_sha256") or "")
    body=dict(d); body.pop("evidence_sha256",None)
    actual=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
    print(name,"PASS" if expected==actual else "SEAL_MISMATCH",expected,actual)
