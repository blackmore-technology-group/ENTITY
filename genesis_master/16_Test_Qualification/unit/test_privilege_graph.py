from pathlib import Path
import importlib.util, sys

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
P=ROOT/"00_Governance"/"privilege_graph"/"canonical_privilege_graph.py"
spec=importlib.util.spec_from_file_location("entity_privilege_graph_test",P); assert spec and spec.loader
mod=importlib.util.module_from_spec(spec); sys.modules[spec.name]=mod; spec.loader.exec_module(mod)


def test_required_negative_authority_cases():
    g=mod.PrivilegeGraph()
    assert g.evaluate("NIKI","ENTITY","MUTATE_RIGHTS")["decision"]=="DENY"
    assert g.evaluate("NIKI","ENTITY","MUTATE_SETTLEMENT")["decision"]=="DENY"
    assert g.evaluate("BECP","ENTITY","ESCALATE_AUTHORITY")["decision"]=="DENY"
    assert g.evaluate("UNTRUSTED_DATA","ADAM","GRANT_AUTHORITY")["decision"]=="DENY"
    assert g.evaluate("CONNECTOR","ENTITY","ACCESS_UNRELATED_VAULT_SCOPE")["decision"]=="DENY"
    assert g.evaluate("BSIE","ENTITY","ASSERT_OWNERSHIP_FROM_OBSERVATION")["decision"]=="NOT_AUTOMATICALLY_VERIFIED"


def test_adam_export_and_value_transfer_require_exact_capability():
    g=mod.PrivilegeGraph()
    assert g.evaluate("ADAM","ENTITY","EXPORT_PROTECTED_ASSET")["decision"]=="DENY"
    assert g.evaluate("ADAM","ENTITY","EXPORT_PROTECTED_ASSET",{"capabilities":["ASSET_EXPORT"]})["decision"]=="ALLOW"
    assert g.evaluate("ADAM","ENTITY","TRANSFER_VALUE",{"capabilities":["ASSET_EXPORT"]})["decision"]=="DENY"
    assert g.evaluate("ADAM","ENTITY","TRANSFER_VALUE",{"capabilities":["SETTLEMENT_EXECUTE"]})["decision"]=="ALLOW"

def test_default_deny_and_policy_hash_are_enforced():
    g=mod.PrivilegeGraph()
    out=g.evaluate("NIKI","ENTITY","UNDECLARED_OPERATION")
    assert out["decision"]=="DENY" and out["reason"]=="default_deny"
    assert len(out["policy_sha256"])==64


def test_reasoning_and_governed_execution_are_narrowly_allowed():
    g=mod.PrivilegeGraph()
    assert g.evaluate("NIKI","ENTITY","READ_GOVERNED_PROJECTION")["decision"]=="ALLOW"
    assert g.evaluate("NIKI","ADAM","PROPOSE_ACTION")["decision"]=="ALLOW"
    assert g.evaluate("ENTITY","ADAM","EXECUTE_GOVERNED_ACTION")["decision"]=="DENY"
    assert g.evaluate("ENTITY","ADAM","EXECUTE_GOVERNED_ACTION",{"capabilities":["GOVERNED_EXECUTION"]})["decision"]=="ALLOW"
