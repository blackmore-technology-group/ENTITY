from pathlib import Path
import json

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
platform=ROOT/"10_NIKI"/"ENTITY_PLATFORM_BINDINGS.json"
data=json.loads(platform.read_text(encoding="utf-8"))
updates={
 "information_projection":{"owner":"01_Core_Runtime\\information_projection","embedded":"blackmore_ci.niki_disclosure_guard"},
 "evidence_assertion":{"owner":"04_Entity_Registry\\evidence_assertions","embedded":"blackmore_ci.evidence_boundary"},
 "rights_ontology":{"owner":"04_Entity_Registry\\rights_ontology","embedded":"blackmore_ci.rights_claims"},
}
data.setdefault("bindings",{}).update(updates)
platform.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n",encoding="utf-8")

rights=ROOT/"04_Entity_Registry"/"ownership_graphs"/"ENTITY_RUNTIME_BINDING.json"
r=json.loads(rights.read_text(encoding="utf-8"))
for ev in r.get("qualification_evidence") or []:
    if isinstance(ev,dict): ev["sha256"]="2906030e973085b6e87862f00dfcffb3dbb6602c13e68cc8463ff192f14b1961"
rights.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print("registered",sorted(updates))
