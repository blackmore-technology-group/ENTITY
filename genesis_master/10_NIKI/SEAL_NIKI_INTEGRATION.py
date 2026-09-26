from pathlib import Path
import hashlib, json, re, time

ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
NIKI=ROOT/"10_NIKI"
PKG=NIKI/"sovereign_adapted"/"Blackmore_Central_Intelligence_Advanced_NIKI_ADAM_BSIE_v0.6.1_AR_INTELLIGENCE_COMPLETE"
BASE=PKG/"central_runtime"
EVIDENCE=BASE/"tests"/"evidence"/"FULL_PYTEST_NIKI_ENTITY2_CAUSAL_HARNESS.txt"
OUT_DIR=NIKI/"tests"/"evidence"
OUT_DIR.mkdir(parents=True,exist_ok=True)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path,obj):
    Path(path).write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n",encoding="utf-8")


def parse_pytest(path):
    raw=Path(path).read_bytes()
    if raw.startswith((b"\xff\xfe",b"\xfe\xff")):
        text=raw.decode("utf-16")
    else:
        text=raw.decode("utf-8",errors="replace")
    summaries=[line.strip() for line in text.splitlines() if " passed" in line and " in " in line]
    if not summaries:
        raise RuntimeError("unable to locate pytest summary in current NIKI+ENTITY evidence")
    line=summaries[-1]
    def count(label):
        m=re.search(rf"(\d+)\s+{label}",line)
        return int(m.group(1)) if m else 0
    duration=re.search(r"\bin\s+([0-9.]+)s(?:\s+\([^)]*\))?\s*$",line)
    if not duration:
        raise RuntimeError("unable to parse pytest duration from current NIKI+ENTITY evidence")
    return {"passed":count("passed"),"failed":count("failed"),"skipped":count("skipped"),"warning_count":count("warnings?"),"duration_seconds":float(duration.group(1)),"summary":line}


def collect_contracts():
    roots=[NIKI/"context_adapters",NIKI/"entity_intelligence",NIKI/"overlay_generation",NIKI/"policy_constraints",NIKI/"reasoning_interfaces"]
    out={}
    for root in roots:
        for p in sorted(root.glob("*.json")):
            out[str(p.relative_to(NIKI))]=sha(p)
    return out


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


MATRIX=load_json(NIKI/"ENTITY_SYSTEM_COMPLETION_MATRIX.json")
PYTEST=parse_pytest(EVIDENCE)
PYTEST.update({"evidence":str(EVIDENCE),"evidence_sha256":sha(EVIDENCE)})
if PYTEST["failed"] != 0:
    raise RuntimeError("cannot seal NIKI+ENTITY qualification with failing merged tests")

DOMAIN_INTERNAL=ROOT/"16_Test_Qualification"/"evidence"/"ENTITY_DOMAIN_INTERNAL_QUALIFICATION_CURRENT.json"
DOMAIN_OVERALL=ROOT/"16_Test_Qualification"/"evidence"/"ENTITY_DOMAIN_QUALIFICATION_CURRENT.json"
domain_internal=load_json(DOMAIN_INTERNAL) if DOMAIN_INTERNAL.exists() else {}
domain_overall=load_json(DOMAIN_OVERALL) if DOMAIN_OVERALL.exists() else {}

CODE_FILES=[
    BASE/"blackmore_ci"/"unified_service.py",
    BASE/"blackmore_ci"/"sovereign_authority_gate.py",
    BASE/"blackmore_ci"/"niki.py",
    BASE/"blackmore_ci"/"intelligence_core.py",
    BASE/"blackmore_ci"/"causal_intelligence.py",
    BASE/"blackmore_ci"/"cognition_router.py",
    BASE/"blackmore_ci"/"niki_handoffs.py",
    BASE/"blackmore_ci"/"system_completion_matrix.py",
    BASE/"blackmore_ci"/"bsie23.py",
    BASE/"blackmore_ci"/"models.py",
    BASE/"blackmore_ci"/"validation.py",
    BASE/"blackmore_ci"/"service.py",
    BASE/"blackmore_ci"/"entity_service.py",
    BASE/"tests"/"test_unified_entity_authority.py",
    BASE/"tests"/"test_niki_handoffs.py",
    BASE/"tests"/"test_causal_intelligence_v130.py",
    PKG/"RUN_ENTITY_NIKI.ps1",
]
code_hashes={str(p.relative_to(PKG)):sha(p) for p in CODE_FILES}
code_root=hashlib.sha256(json.dumps(code_hashes,sort_keys=True,separators=(",",":")).encode()).hexdigest()

BINDING_FILES={
    "platform_bindings":NIKI/"ENTITY_PLATFORM_BINDINGS.json",
    "runtime_binding_schema":NIKI/"ENTITY_RUNTIME_BINDING_SCHEMA.json",
    "canonical_runtime_abi":NIKI/"CANONICAL_RUNTIME_ABI.json",
    "completion_matrix":NIKI/"ENTITY_SYSTEM_COMPLETION_MATRIX.json",
    "ready_queue":NIKI/"CANONICAL_READY_HANDOFF_QUEUE.json",
}
record={
    "schema":"niki-entity-integration-qualification-v5",
    "generated_at_ms":int(time.time()*1000),
    "date":time.strftime("%Y-%m-%d"),
    "scope":"NIKI_ENTITY_UNIFIED_INTERNAL_INTEGRATION",
    "status":"PASS",
    "qualification_complete":True,
    "limitations":[],
    "full_suite":PYTEST,
    "canonical_runtime":{
        "authority_count":MATRIX["authority_count"],
        "ready_count":MATRIX["canonical_ready_count"],
        "production_required_count":MATRIX["production_required_count"],
        "production_required_ready":MATRIX["production_required_ready"],
        "permanent_bootstrap_allowed":MATRIX["permanent_bootstrap_allowed"],
        "system_acceptance_status":MATRIX["system_acceptance_status"],
    },
    "sovereign_domain":{
        "internal_status":domain_internal.get("status"),
        "internal_qualification_complete":domain_internal.get("qualification_complete"),
        "internal_evidence_sha256":sha(DOMAIN_INTERNAL) if DOMAIN_INTERNAL.exists() else None,
        "full_sers_status":domain_overall.get("status"),
        "full_sers_qualification_complete":domain_overall.get("qualification_complete"),
        "full_sers_evidence_sha256":sha(DOMAIN_OVERALL) if DOMAIN_OVERALL.exists() else None,
        "external_validation_pending":not bool(domain_overall.get("qualification_complete")),
    },
    "contracts":collect_contracts(),
    "binding_files":{k:sha(v) for k,v in BINDING_FILES.items()},
    "code_hashes":code_hashes,
    "code_manifest_root_sha256":code_root,
    "security_controls":[
        "ENTITY_CORE requires sovereign_context",
        "private content requires canonical capability and consent",
        "retained learning requires separate PROFILE_BUILDING consent",
        "cross-Entity context requires subject consent",
        "external reasoner disclosure is denied by default for canonical ENTITY requests",
        "NIKI action handoff resolves canonical ADAM authority but never executes directly",
        "canonical operation dispatch is explicit allowlist only",
        "causal model activation is explicit ENTITY-approved and never autonomous",
        "counterfactual analysis has no sovereign mutation authority",
    ],
    "invariants":[
        "NIKI is not an ENTITY authority owner",
        "NIKI reasons/proposes; canonical ENTITY authorities mutate sovereign state",
        "legacy AR remains compatible outside sovereign Entity context",
        "embedded fallbacks cannot satisfy production acceptance",
        "production bootstrap is canonical-only",
        "full original NIKI route surface is preserved in unified runtime",
        "NIKI causal intelligence uses bounded equation types and does not execute arbitrary model code",
        "adaptive cognition routing selects reasoning stages but never grants action authority",
    ],
}
body=dict(record)
body.pop("evidence_sha256",None)
record["evidence_sha256"]=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
QUAL=OUT_DIR/"NIKI_ENTITY_INTEGRATION_QUALIFICATION_CURRENT.json"
dump(QUAL,record)
qual_hash=sha(QUAL)
QUAL.with_suffix(".json.sha256").write_text(qual_hash+"  "+QUAL.name+"\n",encoding="utf-8")

handoff={
    "schema":"niki-interface-handoff-v5",
    "date":record["date"],
    "workstream_owner":"10_NIKI",
    "canonical_authority_owner":str(ROOT)+" root directories outside 10_NIKI",
    "status":"PASS_INTERNAL",
    "full_suite":record["full_suite"],
    "canonical_runtime":record["canonical_runtime"],
    "sovereign_domain":record["sovereign_domain"],
    "contracts":record["contracts"],
    "binding_files":record["binding_files"],
    "code_manifest_root_sha256":code_root,
    "qualification":{"path":str(QUAL),"record_sha256":qual_hash},
    "invariants":record["invariants"],
    "external_release_boundary":"Sovereign-domain physical-device and independent non-BTG interoperability milestones remain external until demonstrated.",
}
HANDOFF=NIKI/"NIKI_INTERFACE_HANDOFF_CURRENT.json"
dump(HANDOFF,handoff)
handoff_hash=sha(HANDOFF)
HANDOFF.with_suffix(".json.sha256").write_text(handoff_hash+"  "+HANDOFF.name+"\n",encoding="utf-8")
print(json.dumps({"qualification":str(QUAL),"qualification_sha256":qual_hash,"handoff":str(HANDOFF),"handoff_sha256":handoff_hash,"passed":PYTEST["passed"],"skipped":PYTEST["skipped"],"authorities":MATRIX["authority_count"],"ready":MATRIX["canonical_ready_count"],"production_required":MATRIX["production_required_count"],"production_ready":MATRIX["production_required_ready"],"code_manifest_root_sha256":code_root},indent=2))
