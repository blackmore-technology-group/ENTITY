from pathlib import Path
import importlib.util, sys, pytest
ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod
S=load("service_state_machine_test",ROOT/"15_Operations"/"runtime_states"/"service_state_machine.py")

def test_all_required_states_and_high_impact_fail_closed(tmp_path):
    m=S.ServiceStateMachine(tmp_path); m.register("svc")
    assert m.authorize_operation("svc","SETTLEMENT_EXECUTE")["allowed"] is True
    for state in ["DEGRADED","OFFLINE","DEPENDENCY_UNAVAILABLE","MALICIOUS_INPUT","CONFLICTING_STATE","RECOVERY","QUARANTINED"]:
        m=S.ServiceStateMachine(tmp_path/state); m.register("svc")
        evidence={"case":state} if state in {"MALICIOUS_INPUT","CONFLICTING_STATE","QUARANTINED"} else None
        if state=="QUARANTINED":
            m.transition("svc","MALICIOUS_INPUT",trigger="attack",evidence={"attack":"x"}); m.transition("svc","QUARANTINED",trigger="contain",evidence=evidence)
        else: m.transition("svc",state,trigger="qualification",evidence=evidence)
        for op in S.HIGH_IMPACT: assert m.authorize_operation("svc",op)["allowed"] is False

def test_security_states_require_evidence_and_invalid_transitions_fail_closed(tmp_path):
    m=S.ServiceStateMachine(tmp_path); m.register("svc")
    with pytest.raises(ValueError): m.transition("svc","MALICIOUS_INPUT",trigger="attack")
    with pytest.raises(PermissionError): m.transition("svc","QUARANTINED",trigger="skip",evidence={"x":1})
    assert m.authorize_operation("svc","UNDECLARED_MUTATION")["allowed"] is False

def test_recovery_path_exposes_required_operational_metadata(tmp_path):
    m=S.ServiceStateMachine(tmp_path); m.register("svc"); m.transition("svc","DEPENDENCY_UNAVAILABLE",trigger="provider-down")
    d=m.describe("svc"); assert d["fail_closed"] is True and d["user_visible_status"] and d["recovery_action"]
    assert m.authorize_operation("svc","MIGRATE")["allowed"] is True
    m.transition("svc","RECOVERY",trigger="owner-restore"); assert m.authorize_operation("svc","RIGHTS_MUTATE")["allowed"] is False
    m.transition("svc","NORMAL",trigger="verified-restore"); assert m.describe("svc")["fail_closed"] is False
    assert len(m.history("svc"))==3
