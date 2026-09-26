from __future__ import annotations
from pathlib import Path
import hashlib, json, time

SUBSYSTEMS={"ENTITY","NIKI","ADAM","BSIE","BECP","CONNECTOR","UNTRUSTED_DATA"}
DECISIONS={"ALLOW","DENY","REVIEW_REQUIRED","NOT_AUTOMATICALLY_VERIFIED"}

class PrivilegeGraph:
    """Versioned default-deny cross-subsystem authority contract."""
    def __init__(self, policy_path: str|Path|None=None):
        self.path=Path(policy_path) if policy_path else Path(__file__).with_name("ENTITY_PRIVILEGE_GRAPH_v1.json")
        self.data=json.loads(self.path.read_text(encoding="utf-8"))
        if self.data.get("schema")!="entity-privilege-graph-v1": raise ValueError("unsupported privilege graph schema")
        self.rules=list(self.data.get("rules") or [])

    @staticmethod
    def _has_cap(context: dict, cap: str) -> bool:
        return cap in {str(x).upper() for x in (context.get("capabilities") or [])}

    def evaluate(self, source: str, target: str, operation: str, context: dict|None=None) -> dict:
        src=str(source).upper(); dst=str(target).upper(); op=str(operation).upper(); ctx=dict(context or {})
        if src not in SUBSYSTEMS or dst not in SUBSYSTEMS: return self._decision(src,dst,op,"DENY","unknown_subsystem")
        for rule in self.rules:
            if rule["source"]==src and rule["target"]==dst and rule["operation"]==op:
                required=str(rule.get("required_capability") or "").upper()
                decision=rule["decision"] if not required or self._has_cap(ctx,required) else "DENY"
                reason=rule.get("reason") if decision==rule["decision"] else f"missing_capability:{required}"
                return self._decision(src,dst,op,decision,reason)
        return self._decision(src,dst,op,"DENY","default_deny")
    def _decision(self,src,dst,op,decision,reason):
        if decision not in DECISIONS: raise ValueError("invalid privilege decision")
        return {"schema":"entity-privilege-decision-v1","source":src,"target":dst,"operation":op,
                "decision":decision,"reason":str(reason),"policy_version":self.data["version"],
                "policy_sha256":hashlib.sha256(self.path.read_bytes()).hexdigest(),"evaluated_at_ms":int(time.time()*1000)}

    def status(self) -> dict:
        return {"ready":True,"schema":self.data["schema"],"version":self.data["version"],
                "default_decision":"DENY","rule_count":len(self.rules),"authority_boundaries_enforced":True}

def privilege_graph_v1() -> dict:
    return PrivilegeGraph().data
