from pathlib import Path
import hashlib, json
ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
platform=json.loads((ROOT/"10_NIKI"/"ENTITY_PLATFORM_BINDINGS.json").read_text())
rows=[]
for authority,item in sorted(platform["bindings"].items()):
    owner=ROOT/item["owner"]; marker=owner/"ENTITY_RUNTIME_BINDING.json"
    contract=ROOT/Path(item["owner"]).parts[0]/"ENTITY_REQUIREMENTS.md"
    expected=hashlib.sha256(contract.read_bytes()).hexdigest() if contract.is_file() else None
    row={"authority":authority,"owner":item["owner"],"binding":marker.is_file(),"expected_req":expected}
    if marker.is_file():
        try:
            raw=json.loads(marker.read_text()); multi=raw.get("authorities")
            payload=dict(raw)
            if isinstance(multi,dict) and authority in multi:
                payload.pop("authorities",None); payload.update(multi[authority])
            row["status"]=payload.get("status"); row["actual_req"]=payload.get("requirements_sha256") or raw.get("requirements_sha256")
            row["req_match"]=str(row["actual_req"]).lower()==str(expected).lower()
            evs=payload.get("qualification_evidence") or raw.get("qualification_evidence") or []
            ev_state=[]
            for ev in evs:
                p=ev.get("path") if isinstance(ev,dict) else None
                if not p: continue
                ep=(ROOT/p).resolve() if not Path(p).is_absolute() else Path(p)
                exists=ep.is_file(); actual=hashlib.sha256(ep.read_bytes()).hexdigest() if exists else None
                ev_state.append({"path":p,"exists":exists,"hash_match":exists and actual==ev.get("sha256")})
            row["evidence"]=ev_state
        except Exception as e: row["error"]=repr(e)
    rows.append(row)
print(json.dumps(rows,indent=2))
