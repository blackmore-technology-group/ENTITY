from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib, importlib.util, json, sys
import pytest

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
EV=ROOT/"16_Test_Qualification"/"evidence"

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    assert spec and spec.loader
    mod=importlib.util.module_from_spec(spec)
    sys.modules[name]=mod
    spec.loader.exec_module(mod)
    return mod

def canonical_seal_ok(path):
    data=json.loads(Path(path).read_text(encoding="utf-8"))
    expected=str(data.get("evidence_sha256") or "")
    body=dict(data); body.pop("evidence_sha256",None)
    actual=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
    return bool(expected) and expected==actual

I=load("chaos_identity",ROOT/"01_Core_Runtime"/"identity"/"canonical_identity.py")
E=load("chaos_economics",ROOT/"01_Core_Runtime"/"service_runtime"/"canonical_economics.py")
P=load("chaos_policy",ROOT/"01_Core_Runtime"/"policy_engine"/"canonical_policy.py")
C=load("chaos_caps",ROOT/"01_Core_Runtime"/"permissions"/"canonical_permissions.py")
S=load("chaos_states",ROOT/"15_Operations"/"runtime_states"/"service_state_machine.py")

def _ids(tmp_path):
    state=tmp_path/"state"
    ids=I.EntityIdentityVault(state)
    a=ids.create("Chaos A","organization")["entity_id"]
    b=ids.create("Chaos B","organization")["entity_id"]
    c=ids.create("Chaos C","organization")["entity_id"]
    return state,ids,a,b,c

def test_concurrent_settlement_nonce_storm_exactly_one_commit(tmp_path):
    state,ids,payer,payee,_=_ids(tmp_path)
    econ=E.SettlementEngine(state,ids)
    def attempt(i):
        try:
            return (True,econ.create(payer,payee,amount_units=100,currency="CAD",obligation_ref="chaos",transaction_nonce="same-nonce"))
        except Exception as exc:
            return (False,type(exc).__name__)
    with ThreadPoolExecutor(max_workers=32) as pool:
        results=list(pool.map(attempt,range(64)))
    assert sum(1 for ok,_ in results if ok)==1
    assert sum(1 for ok,_ in results if not ok)==63
    assert econ.status()["settlements"]==1

def test_concurrent_confirmation_cannot_double_post(tmp_path):
    state,ids,payer,payee,_=_ids(tmp_path)
    econ=E.SettlementEngine(state,ids)
    s=econ.create(payer,payee,amount_units=777,currency="CAD",obligation_ref="confirm-race",transaction_nonce="confirm-race")
    econ.authorize(payer,s["settlement_id"])
    def confirm(_):
        try:
            return (True,econ.confirm(payer,s["settlement_id"]))
        except Exception as exc:
            return (False,type(exc).__name__)
    with ThreadPoolExecutor(max_workers=24) as pool:
        results=list(pool.map(confirm,range(32)))
    assert sum(1 for ok,_ in results if ok)==1
    assert econ.get(s["settlement_id"])["state"]=="CONFIRMED"
    assert econ.balance(payer,"CAD")["net"]==-777
    assert econ.balance(payee,"CAD")["net"]==777

def test_threshold_duplicate_outsider_and_revocation_fail_closed(tmp_path):
    state,ids,owner,a,b=_ids(tmp_path)
    outsider=ids.create("Outsider","person")["entity_id"]
    store=C.ThresholdAuthorityStore(state,ids)
    pol=store.create_policy(owner,"SHARE_ISSUANCE",[a,b],2)
    store.approve(pol["policy_id"],"req-1",a,object_ref="class-A")
    assert store.authorize(pol["policy_id"],"req-1","SHARE_ISSUANCE",object_ref="class-A")["allowed"] is False
    with pytest.raises(ValueError): store.approve(pol["policy_id"],"req-1",a,object_ref="class-A")
    with pytest.raises(PermissionError): store.approve(pol["policy_id"],"req-1",outsider,object_ref="class-A")
    store.approve(pol["policy_id"],"req-1",b,object_ref="class-A")
    assert store.authorize(pol["policy_id"],"req-1","SHARE_ISSUANCE",object_ref="class-A")["allowed"] is True
    store.revoke_policy(owner,pol["policy_id"])
    assert store.authorize(pol["policy_id"],"req-1","SHARE_ISSUANCE",object_ref="class-A")["allowed"] is False

def test_policy_and_capability_request_storm_stays_fail_closed(tmp_path):
    state,ids,owner,peer,_=_ids(tmp_path)
    policy=P.PolicyConsentEngine(state,ids)
    pol=policy.create_policy(owner,"Chaos policy",{"VIEW":"PERMIT","AI_TRAINING":"PROHIBIT","PROFILE_BUILDING":"PROHIBIT"})
    caps=C.AuthorityCapabilityStore(state,ids)
    cap=caps.grant(owner,"agent-chaos",operations=["VIEW"],asset_scope=["asset-ok"],counterparty_scope=[peer],financial_limit=100)
    for i in range(5000):
        assert policy.evaluate(pol["policy_id"],f"UNKNOWN_{i}")["allowed"] is False
        assert caps.authorize(cap["capability_id"],"agent-chaos","EXPORT",asset_id="asset-ok",counterparty_id=peer,amount=1)["allowed"] is False
        assert caps.authorize(cap["capability_id"],"agent-chaos","VIEW",asset_id=f"asset-{i}",counterparty_id=peer,amount=1)["allowed"] is False
    assert policy.evaluate(pol["policy_id"],"AI_TRAINING")["allowed"] is False
    assert policy.evaluate(pol["policy_id"],"PROFILE_BUILDING")["allowed"] is False

def test_combined_revoked_consent_compromised_capability_and_malicious_state(tmp_path):
    state,ids,owner,peer,_=_ids(tmp_path)
    policy=P.PolicyConsentEngine(state,ids)
    pol=policy.create_policy(owner,"Combined",{"AI_INFERENCE":"PERMIT","AI_TRAINING":"PROHIBIT"})
    consent=policy.grant_consent(owner,pol["policy_id"],purpose="inference",asset_scope=["asset-1"],counterparty_entity_id=peer)
    caps=C.AuthorityCapabilityStore(state,ids)
    cap=caps.grant(owner,"agent-good",operations=["AI_INFERENCE"],asset_scope=["asset-1"],counterparty_scope=[peer])
    sm=S.ServiceStateMachine(state); sm.register("niki-entity")
    policy.revoke_consent(owner,consent["consent_id"])
    sm.transition("niki-entity","MALICIOUS_INPUT",trigger="combined-chaos",evidence={"prompt_injection":True})
    assert policy.authorize_consent(consent["consent_id"],counterparty_entity_id=peer,purpose="inference",asset_scope=["asset-1"],action="AI_INFERENCE")["allowed"] is False
    assert caps.authorize(cap["capability_id"],"agent-attacker","AI_INFERENCE",asset_id="asset-1",counterparty_id=peer)["allowed"] is False
    for op in S.HIGH_IMPACT:
        assert sm.authorize_operation("niki-entity",op)["allowed"] is False

def test_current_evidence_seals_detect_tamper_and_preserve_external_block():
    current=sorted(EV.glob("ENTITY_*_CURRENT.json"))
    assert current
    for path in current:
        assert canonical_seal_ok(path),path.name
    domain=json.loads((EV/"ENTITY_DOMAIN_QUALIFICATION_CURRENT.json").read_text(encoding="utf-8"))
    assert domain["status"]=="BLOCKED" and domain["qualification_complete"] is False
    assert len(domain.get("limitations") or [])==2
    sample=json.loads((EV/"ENTITY_FULL_E2E_QUALIFICATION_CURRENT.json").read_text(encoding="utf-8"))
    expected=sample["evidence_sha256"]
    sample["scope"]="TAMPERED_SCOPE"
    body=dict(sample); body.pop("evidence_sha256",None)
    tampered=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
    assert tampered!=expected

def test_release_gate_has_no_hidden_internal_blocker():
    gate=json.loads((ROOT/"17_Release"/"manifests"/"ENTITY_10_10_RELEASE_GATE_CURRENT.json").read_text(encoding="utf-8"))
    assert gate["internal_chaos_preflight_ready"] is True
    internal=[g for g in gate["gates"] if not g.get("external_only")]
    assert internal and all(g["pass"] for g in internal)
    external=[g for g in gate["gates"] if g.get("external_only")]
    assert len(external)==1 and external[0]["gate"]=="sovereign_domain_external"
    assert external[0]["pass"] is False

def test_failure_state_matrix_denies_every_high_impact_operation(tmp_path):
    sm=S.ServiceStateMachine(tmp_path/"state")
    for i,target in enumerate(["DEGRADED","OFFLINE","DEPENDENCY_UNAVAILABLE","MALICIOUS_INPUT","CONFLICTING_STATE","RECOVERY"]):
        sid=f"svc-{i}"; sm.register(sid)
        evidence={"attack":target} if target in {"MALICIOUS_INPUT","CONFLICTING_STATE"} else None
        sm.transition(sid,target,trigger="chaos",evidence=evidence)
        for op in S.HIGH_IMPACT:
            result=sm.authorize_operation(sid,op)
            assert result["allowed"] is False and result["reason"]=="high_impact_fail_closed"

def test_expired_consent_and_capability_cannot_authorize(tmp_path):
    state,ids,owner,peer,_=_ids(tmp_path)
    policy=P.PolicyConsentEngine(state,ids)
    pol=policy.create_policy(owner,"Expiry",{"AI_INFERENCE":"PERMIT"})
    consent=policy.grant_consent(owner,pol["policy_id"],purpose="inference",asset_scope=["asset-1"],counterparty_entity_id=peer,expires_at_ms=1)
    result=policy.authorize_consent(consent["consent_id"],counterparty_entity_id=peer,purpose="inference",asset_scope=["asset-1"],action="AI_INFERENCE")
    assert result["allowed"] is False and result["reason"]=="consent_expired"
    caps=C.AuthorityCapabilityStore(state,ids)
    cap=caps.grant(owner,"agent",operations=["VIEW"],asset_scope=["asset-1"],expires_at_ms=1)
    result=caps.authorize(cap["capability_id"],"agent","VIEW",asset_id="asset-1")
    assert result["allowed"] is False and result["reason"]=="capability_expired"

def test_restart_preserves_replay_protection_and_double_entry(tmp_path):
    state,ids,payer,payee,_=_ids(tmp_path)
    econ=E.SettlementEngine(state,ids)
    s=econ.create(payer,payee,amount_units=321,currency="CAD",obligation_ref="restart",transaction_nonce="restart-nonce")
    econ.authorize(payer,s["settlement_id"])
    econ=E.SettlementEngine(state,ids)
    with pytest.raises(ValueError,match="duplicate/replayed"):
        econ.create(payer,payee,amount_units=321,currency="CAD",obligation_ref="restart",transaction_nonce="restart-nonce")
    econ.confirm(payer,s["settlement_id"])
    econ=E.SettlementEngine(state,ids)
    with pytest.raises(ValueError): econ.confirm(payer,s["settlement_id"])
    assert econ.balance(payer,"CAD")["net"]==-321 and econ.balance(payee,"CAD")["net"]==321
