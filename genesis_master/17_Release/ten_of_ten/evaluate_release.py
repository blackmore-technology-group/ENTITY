from __future__ import annotations
from pathlib import Path
import hashlib, json, time

ROOT = Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
EVIDENCE = ROOT / "16_Test_Qualification" / "evidence"
OUT = ROOT / "17_Release" / "manifests" / "ENTITY_10_10_RELEASE_GATE_CURRENT.json"


def load(path: Path) -> dict | None:
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception: return None


def sealed_pass(path: Path) -> tuple[bool, str]:
    data = load(path)
    if not data: return False, "missing_or_unreadable"
    if data.get("status") != "PASS": return False, f"status={data.get('status')}"
    expected = str(data.get("evidence_sha256") or "")
    if not expected: return False, "missing_evidence_sha256"
    body = dict(data); body.pop("evidence_sha256", None)
    actual = hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
    if actual != expected: return False, "seal_hash_mismatch"
    limitations = list(data.get("limitations") or [])
    if limitations: return False, f"limitations={len(limitations)}"
    if data.get("qualification_complete") is False:
        return False, "qualification_complete=false"
    return True, "PASS"


def gate(name: str, passed: bool, reason: str, evidence: str | None = None, *, external_only: bool=False) -> dict:
    return {"gate":name,"pass":bool(passed),"reason":reason,"evidence":evidence,"external_only":bool(external_only)}


def main() -> int:
    matrix_path = ROOT / "10_NIKI" / "ENTITY_SYSTEM_COMPLETION_MATRIX.json"
    matrix = load(matrix_path) or {}
    gates=[]
    all_ready = bool(matrix) and matrix.get("canonical_ready_count") == matrix.get("authority_count")
    gates.append(gate("architecture", all_ready, f"canonical_ready={matrix.get('canonical_ready_count',0)}/{matrix.get('authority_count',0)}", str(matrix_path)))

    core_path = EVIDENCE / "ENTITY_CANONICAL_CORE_QUALIFICATION_CURRENT.json"
    core_ok, core_reason = sealed_pass(core_path)
    gates.append(gate("sovereignty", core_ok, core_reason, str(core_path)))

    evidence_files = {
        "privacy":"ENTITY_PRIVACY_ADVERSARIAL_CURRENT.json",
        "security":"ENTITY_SECURITY_ADVERSARIAL_CURRENT.json",
        "ai_governance":"ENTITY_AI_GOVERNANCE_CURRENT.json",
        "rights_provenance":"ENTITY_RIGHTS_PROVENANCE_CURRENT.json",
        "economics":"ENTITY_ECONOMIC_QUALIFICATION_CURRENT.json",
        "corporate_capital":"ENTITY_CORPORATE_CAPITAL_EVIDENCE_CURRENT.json",
        "interoperability":"ENTITY_STANDARDS_INTEROP_CURRENT.json",
        "resilience":"ENTITY_DESTRUCTIVE_RECOVERY_CURRENT.json",
        "independent_transaction":"ENTITY_INDEPENDENT_TRANSACTION_CURRENT.json",
        "sovereign_authority_doctrine":"ENTITY_SOVEREIGN_AUTHORITY_DOCTRINE_CURRENT.json",
        "qualification":"ENTITY_FULL_E2E_QUALIFICATION_CURRENT.json",
        "asset_ledger":"ENTITY_ASSET_LEDGER_CURRENT.json",
        "contracts_usage":"ENTITY_CONTRACTS_USAGE_CURRENT.json",
        "credentials_migration":"ENTITY_CREDENTIALS_MIGRATION_CURRENT.json",
        "event_ledger_asset_registry":"ENTITY_EVENT_LEDGER_ASSET_REGISTRY_CURRENT.json",
        "failure_state_machine":"ENTITY_FAILURE_STATE_MACHINE_CURRENT.json",
        "generated_invariants":"ENTITY_GENERATED_INVARIANTS_CURRENT.json",
        "independent_verifier":"ENTITY_INDEPENDENT_VERIFIER_CURRENT.json",
        "phase1_storage_portability":"ENTITY_PHASE1_STORAGE_PORTABILITY_CURRENT.json",
        "privilege_graph":"ENTITY_PRIVILEGE_GRAPH_CURRENT.json",
        "release_attestation":"ENTITY_RELEASE_ATTESTATION_CURRENT.json",
        "release_closure_authorities":"ENTITY_RELEASE_CLOSURE_AUTHORITIES_CURRENT.json",
        "v2_assurance_core":"ENTITY_V2_ASSURANCE_CORE_CURRENT.json",
        "engineering_requirements_closure":"ENTITY_ENGINEERING_REQUIREMENTS_CLOSURE_CURRENT.json",
        "genesis_proof":"ENTITY_GENESIS_PROOF_CURRENT.json",
        "btg_application_sdk":"ENTITY_BTG_APPLICATION_SDK_CURRENT.json",
        "open_entity_sdk":"ENTITY_OPEN_SDK_CURRENT.json",
    }
    for name, filename in evidence_files.items():
        path=EVIDENCE/filename; ok,reason=sealed_pass(path)
        gates.append(gate(name,ok,reason,str(path)))

    niki_path=ROOT/"10_NIKI"/"tests"/"evidence"/"NIKI_ENTITY_INTEGRATION_QUALIFICATION_CURRENT.json"
    niki_ok,niki_reason=sealed_pass(niki_path)
    gates.append(gate("niki_entity_integration",niki_ok,niki_reason,str(niki_path)))

    regression_path=EVIDENCE/"ENTITY_REPOSITORY_REGRESSION_CURRENT.json"
    regression_ok,regression_reason=sealed_pass(regression_path)
    gates.append(gate("repository_regression",regression_ok,regression_reason,str(regression_path)))

    chaos_path=EVIDENCE/"ENTITY_ULTIMATE_CHAOS_QUALIFICATION_CURRENT.json"
    chaos_ok,chaos_reason=sealed_pass(chaos_path)
    gates.append(gate("ultimate_chaos_internal",chaos_ok,chaos_reason,str(chaos_path)))

    domain_internal_path=EVIDENCE/"ENTITY_DOMAIN_INTERNAL_QUALIFICATION_CURRENT.json"
    domain_internal_ok,domain_internal_reason=sealed_pass(domain_internal_path)
    gates.append(gate("sovereign_domain_internal",domain_internal_ok,domain_internal_reason,str(domain_internal_path)))

    domain_overall_path=EVIDENCE/"ENTITY_DOMAIN_QUALIFICATION_CURRENT.json"
    domain_overall_ok,domain_overall_reason=sealed_pass(domain_overall_path)
    gates.append(gate("sovereign_domain_external",domain_overall_ok,domain_overall_reason,str(domain_overall_path),external_only=True))

    rtm_path=ROOT/"16_Test_Qualification"/"traceability"/"MASTER_RTM.json"
    rtm=load(rtm_path) or {}
    rtm_ok=rtm.get("full_internal_requirements_closed") is True and rtm.get("active_internal_unclosed_count")==0 and rtm.get("state_counts",{}).get("QUALIFIED")==rtm.get("requirement_count")==1997 and rtm.get("master_source_mirrored") is True
    gates.append(gate("master_rtm_closure",rtm_ok,"PASS" if rtm_ok else "rtm_not_fully_closed",str(rtm_path)))
    passed=sum(1 for x in gates if x["pass"]); total=len(gates)
    internal_gates=[x for x in gates if not x.get("external_only")]
    internal_chaos_ready=all(x["pass"] for x in internal_gates)
    payload={
        "schema":"entity-release-gate-v3",
        "generated_at_ms":int(time.time()*1000),
        "status":"PASS" if passed == total else "BLOCKED",
        "ten_of_ten":passed == total,
        "internal_chaos_preflight_ready":internal_chaos_ready,
        "internal_chaos_qualified":chaos_ok,
        "gates_passed":passed,"gates_total":total,"score_percent":round(100*passed/total,1),
        "internal_gates_passed":sum(1 for x in internal_gates if x["pass"]),"internal_gates_total":len(internal_gates),
        "gates":gates,
        "master_rtm":{"path":str(rtm_path),"requirement_count":rtm.get("requirement_count"),"rtm_sha256":rtm.get("rtm_sha256"),"master_source_mirrored":rtm.get("master_source_mirrored"),"full_internal_requirements_closed":rtm.get("full_internal_requirements_closed"),"active_internal_unclosed_count":rtm.get("active_internal_unclosed_count"),"qualified":rtm.get("state_counts",{}).get("QUALIFIED")},
        "qualification_notes":["The authoritative SERS-003 v2.2 and sovereign-domain specifications are mirrored in-repository and hash-verified.","Internal Ultimate CHAOS, RTM closure and Genesis Proof are mandatory internal release gates.","Final sovereign-domain release remains externally blocked by the physical-device and independent non-BTG interoperability milestones."],
        "claim":"Internal CHAOS qualification and full release are separate claims. Full release may be claimed only when every gate, including external sovereign-domain validation, passes.",
    }
    raw=json.dumps(payload,sort_keys=True,separators=(",",":"),default=str).encode()
    payload["gate_evidence_sha256"]=hashlib.sha256(raw).hexdigest()
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"status":payload["status"],"score_percent":payload["score_percent"],"passed":passed,"total":total,"internal_chaos_preflight_ready":internal_chaos_ready,"internal_passed":payload["internal_gates_passed"],"internal_total":payload["internal_gates_total"],"output":str(OUT)},indent=2))
    return 0 if payload["ten_of_ten"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
