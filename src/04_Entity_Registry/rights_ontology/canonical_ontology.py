from __future__ import annotations
from pathlib import Path
import json

ONTOLOGY_PATH=Path(__file__).with_name("ENTITY_RIGHTS_ONTOLOGY_v1.json")

class RightsOntology:
    def __init__(self,path: str|Path|None=None):
        self.path=Path(path) if path else ONTOLOGY_PATH
        self.data=json.loads(self.path.read_text(encoding="utf-8"))
        if self.data.get("schema")!="entity-rights-ontology-v1": raise ValueError("unsupported rights ontology schema")
        self.right_types=frozenset(self.data.get("stakeholder_right_types") or [])
        self.verification_states=frozenset(self.data.get("verification_states") or [])
        self.dispute_states=frozenset(self.data.get("dispute_states") or [])
        if self.verification_states & self.dispute_states: raise ValueError("verification and dispute state vocabularies must remain separate")

    def validate_right_type(self,value: str) -> str:
        key=str(value or "").upper()
        if key not in self.right_types: raise ValueError("unsupported ontology right type")
        return key

    def status(self) -> dict:
        return {"ready":True,"schema":self.data["schema"],"version":self.data["version"],
                "right_type_count":len(self.right_types),"state_separation":True,
                "registration_time_determinative":False}

def rights_ontology_v1() -> dict:
    return RightsOntology().data
