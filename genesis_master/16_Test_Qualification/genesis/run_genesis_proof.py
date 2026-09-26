from pathlib import Path
import hashlib, json, re, subprocess, sys, time
ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
EV=ROOT/"16_Test_Qualification"/"evidence"
OUT=EV/"ENTITY_GENESIS_PROOF_CURRENT.json"

def load(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def sealed(path):
    data=load(path); expected=str(data.get("evidence_sha256") or "")
    body=dict(data); body.pop("evidence_sha256",None)
    actual=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
    return bool(expected and expected==actual)

TESTS=[
    ROOT/"16_Test_Qualification"/"genesis"/"test_genesis_composition.py",
    ROOT/"16_Test_Qualification"/"closure"/"test_engineering_requirements_closure.py",
    ROOT/"16_Test_Qualification"/"integration"/"test_full_entity_golden_e2e.py",
    ROOT/"16_Test_Qualification"/"integration"/"test_independently_reproducible_transaction.py",
    ROOT/"16_Test_Qualification"/"corporate_capital"/"test_section170_corporate_capital_golden.py",
    ROOT/"16_Test_Qualification"/"sovereign_domain"/"test_sovereign_domain.py",
    ROOT/"16_Test_Qualification"/"recovery"/"test_full_destructive_sovereignty.py",
    ROOT/"16_Test_Qualification"/"unit"/"test_independent_verifier.py",
    ROOT/"16_Test_Qualification"/"unit"/"test_independent_verifier_licence_usage.py",
]
cmd=[sys.executable,"-m","pytest","-q"]+[str(x) for x in TESTS]
run=subprocess.run(cmd,cwd=str(ROOT),capture_output=True,text=True)
out_text=(run.stdout or "")+("\n"+(run.stderr or "") if run.stderr else "")
match=re.search(r"(\d+) passed",out_text); passed=int(match.group(1)) if match else 0
failed=0 if run.returncode==0 else 1
skipped=sum(int(x) for x in re.findall(r"(\d+) skipped",out_text))

rtm=load(ROOT/"16_Test_Qualification"/"traceability"/"MASTER_RTM.json")
deps={
    "engineering_closure":EV/"ENTITY_ENGINEERING_REQUIREMENTS_CLOSURE_CURRENT.json",
    "million_scale":EV/"ENTITY_MILLION_ASSET_SCALE_CURRENT.json",
    "million_live":EV/"ENTITY_MILLION_SCALE_REVALIDATION_CURRENT.json",
    "block_device_loss":EV/"ENTITY_BLOCK_DEVICE_LOSS_CURRENT.json",
    "domain_internal":EV/"ENTITY_DOMAIN_INTERNAL_QUALIFICATION_CURRENT.json",
    "independent_transaction":EV/"ENTITY_INDEPENDENT_TRANSACTION_CURRENT.json",
    "corporate_capital":EV/"ENTITY_CORPORATE_CAPITAL_EVIDENCE_CURRENT.json",
}
checks={"pytest_exit_zero":run.returncode==0,"pytest_no_skips":skipped==0,
        "rtm_1997_closed":rtm.get("full_internal_requirements_closed") is True and rtm.get("active_internal_unclosed_count")==0 and rtm.get("state_counts",{}).get("QUALIFIED")==1997,
        "master_source_mirrored":rtm.get("master_source_mirrored") is True}
for name,path in deps.items(): checks[name+"_seal"]=sealed(path)
million=load(deps["million_scale"]); live=load(deps["million_live"]); loss=load(deps["block_device_loss"]); domain=load(deps["domain_internal"])
db=Path(live.get("database_path") or "")
checks.update({
    "million_scale_1m_3m":million.get("status")=="PASS" and million.get("observed",{}).get("assets")==1_000_000 and million.get("observed",{}).get("events")==3_000_000 and million.get("verification",{}).get("row_level_verified") is True,
    "million_live_state_present":db.is_file() and db.stat().st_size==million.get("database",{}).get("size_bytes"),
    "block_device_loss_pass":loss.get("status")=="PASS" and loss.get("whole_block_device_removed") is True and loss.get("backing_media_deleted") is True,
    "provider_independence_pass":domain.get("internal_gates",{}).get("PROVIDER_INDEPENDENCE_GATE",{}).get("pass") is True,
})
status="PASS" if all(checks.values()) else "FAIL"
record={
    "schema":"entity-genesis-proof-v1","generated_at_ms":int(time.time()*1000),"status":status,
    "qualification_complete":status=="PASS","campaign":"RTM_CLOSED_GENESIS_SOVEREIGN_CONTINUITY",
    "pytest":{"exit_code":run.returncode,"passed":passed,"failed":failed,"skipped":skipped,"output":out_text[-12000:]},
    "checks":checks,"rtm":{"requirement_count":rtm.get("requirement_count"),"qualified":rtm.get("state_counts",{}).get("QUALIFIED"),"rtm_sha256":rtm.get("rtm_sha256"),"master_source_mirrored":rtm.get("master_source_mirrored")},
    "scale":{"assets":million.get("observed",{}).get("assets"),"events":million.get("observed",{}).get("events"),"database_path":str(db),"database_size_bytes":db.stat().st_size if db.is_file() else None},
    "source_sha256":{str(p.relative_to(ROOT)):sha(p) for p in TESTS},
    "dependency_file_sha256":{name:sha(path) for name,path in deps.items()},
    "external_validation_pending":["two independent physical user-controlled devices","independently authored non-BTG implementation/interoperability"],
    "claim":"Genesis proves the complete internally executable sovereign/economic continuity chain with closed RTM, fresh end-to-end/adversarial verification, destructive recovery prerequisites and live million-scale state. External-party/device milestones remain separately unclaimed."
}
body=json.dumps(record,sort_keys=True,separators=(",",":"),default=str).encode(); record["evidence_sha256"]=hashlib.sha256(body).hexdigest()
OUT.write_text(json.dumps(record,indent=2,sort_keys=True)+"\n",encoding="utf-8")
OUT.with_suffix(".json.sha256").write_text(sha(OUT)+"  "+OUT.name+"\n",encoding="utf-8")
print(json.dumps({"status":status,"pytest_passed":passed,"checks":checks,"evidence_sha256":record["evidence_sha256"],"output":str(OUT)},indent=2))
raise SystemExit(0 if status=="PASS" else 2)
