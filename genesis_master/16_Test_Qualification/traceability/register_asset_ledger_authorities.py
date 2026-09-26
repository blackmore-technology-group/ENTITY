from pathlib import Path
import json

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
p=ROOT/"10_NIKI"/"ENTITY_PLATFORM_BINDINGS.json"
data=json.loads(p.read_text(encoding="utf-8")); b=data["bindings"]
b["data_universe"]["owner"]="04_Entity_Registry\\asset_registry"
b["asset_registry"]={"embedded":"blackmore_ci.data_universe","owner":"04_Entity_Registry\\asset_registry"}
b["event_ledger"]={"embedded":"blackmore_ci.data_universe","owner":"04_Entity_Registry\\event_ledger"}
p.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print(len(b),b["data_universe"],b["asset_registry"],b["event_ledger"],sep="\n")
