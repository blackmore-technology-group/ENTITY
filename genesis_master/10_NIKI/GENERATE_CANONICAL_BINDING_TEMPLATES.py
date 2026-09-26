from pathlib import Path
import hashlib, json, time

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network\10_NIKI")
matrix_path=ROOT/"ENTITY_SYSTEM_COMPLETION_MATRIX.json"
queue_path=ROOT/"CANONICAL_READY_HANDOFF_QUEUE.json"
queue=json.loads(queue_path.read_text(encoding="utf-8"))
templates=[]
for group in queue["owner_groups"]:
    owner=group["owner"]
    items=group["authorities"]
    req_hash=items[0]["requirements_sha256"]
    if len(items)==1:
        a=items[0]
        template={
            "schema":"entity-runtime-binding-v1","authority":a["authority"],
            "status":"DEVELOPMENT","abi_version":"1","python_file":"<IMPLEMENTATION.py>",
            "exports":a["required_exports"],"implementation_version":"<VERSION>",
            "requirements_sha256":req_hash,"qualification_evidence":[]}
    else:
        template={
            "schema":"entity-runtime-binding-v1","status":"DEVELOPMENT","abi_version":"1",
            "implementation_version":"<VERSION>","requirements_sha256":req_hash,
            "qualification_evidence":[],"authorities":{}}
        for a in items:
            template["authorities"][a["authority"]]={
                "status":"DEVELOPMENT","python_file":"<IMPLEMENTATION.py>",
                "exports":a["required_exports"]}
    templates.append({"owner":owner,"multi_authority":len(items)>1,"template":template})
bundle={
    "schema":"entity-canonical-binding-template-bundle-v1",
    "generated_at_ms":int(time.time()*1000),
    "source_matrix_sha256":hashlib.sha256(matrix_path.read_bytes()).hexdigest(),
    "templates":templates,
    "rule":"Do not change status to READY until implementation and qualification evidence satisfy the owner requirements contract."
}
out=ROOT/"CANONICAL_RUNTIME_BINDING_TEMPLATES.json"
out.write_text(json.dumps(bundle,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(json.dumps({"templates":len(templates),"sha256":hashlib.sha256(out.read_bytes()).hexdigest(),"path":str(out)}))
