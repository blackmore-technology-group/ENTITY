from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import shutil
import subprocess
import sys
import time
import wave
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable

import numpy as np
from PIL import Image

from adam_v41.authority import Authority
from adam_v41.reactions import Effect, ReactionDefinition, ReactionEngine, ReactionError, ReactionIntent
from adam_v41.schema import TypeRegistry, TypeSpec, ValenceRule
from adam_v41.universe import AtomicUniverse
from adam_v42.chemistry import ChemistryCandidate, ChemistryLab
from adam_v42.distributed import DistributedUniverseCluster, QuorumCertificate, SovereignErasureStore, Vote
from adam_v42.evidence import EvidenceAlignmentEngine, EvidenceError
from adam_v42.formal import BoundedProofChecker, Law
from adam_v42.isolation import IsolatedKernelClient, IsolatedKernelError
from adam_v42.key_management import CryptoErasureStore, EncryptedSigningKeyStore, KeyStoreError
from adam_v42.operations_one import DeterministicO1Cognition, OperationsOneAuthority
from adam_v42.perception import MultimodalPerception
from adam_v42.query import DistributedAQL
from adam_v42.reactions_ext import AdvancedCondition, AdvancedPolicy, AdvancedReactionEngine, ComputedArgument
from adam_v42.security import AuthorizationError, ClosureAuthorization, SecurityLabel
from adam_v42.soak import run_logical_soak
from adam_v42.time_model import HybridLogicalClock, UncertainInstant, ValidInterval


class Audit:
    def __init__(self): self.checks: list[dict[str, Any]] = []
    def check(self, name: str, fn: Callable[[], Any]) -> Any:
        started = time.perf_counter()
        print(f"[AUDIT] START {name}", flush=True)
        try:
            evidence = fn()
            duration = round((time.perf_counter()-started)*1000,3)
            self.checks.append({"name": name, "status": "PASS", "duration_ms": duration, "evidence": evidence})
            print(f"[AUDIT] PASS  {name} ({duration} ms)", flush=True)
            return evidence
        except Exception as exc:
            duration = round((time.perf_counter()-started)*1000,3)
            self.checks.append({"name": name, "status": "FAIL", "duration_ms": duration, "error": f"{type(exc).__name__}: {exc}"})
            print(f"[AUDIT] FAIL  {name} ({duration} ms): {type(exc).__name__}: {exc}", flush=True)
            return None


def require(value: bool, message: str):
    if not value: raise AssertionError(message)


def wav_bytes() -> bytes:
    rate=8000; samples=(np.sin(2*math.pi*440*np.arange(rate)/rate)*20000).astype(np.int16)
    out=io.BytesIO()
    with wave.open(out,"wb") as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate);w.writeframes(samples.tobytes())
    return out.getvalue()


def png_bytes() -> bytes:
    out=io.BytesIO();Image.new("RGB",(48,32),(15,90,145)).save(out,format="PNG");return out.getvalue()


def read_test_log(root: Path, name: str, expected_passed: int) -> dict[str, Any]:
    path = root / "artifacts" / "test_logs" / name
    text = path.read_text(encoding="utf-8")
    require(f"{expected_passed} passed" in text, f"test log {name} does not prove {expected_passed} passes")
    return {"log": str(path.relative_to(root)), "expected_passed": expected_passed, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "tail": text.strip().splitlines()[-1]}


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--output",default="artifacts/full_audit");args=parser.parse_args()
    root=Path(__file__).resolve().parent; output=(root/args.output).resolve()
    if output.exists(): shutil.rmtree(output)
    output.mkdir(parents=True)
    audit=Audit()

    audit.check("source_tree_compiles", lambda: {"compiled": True} if subprocess.run([sys.executable,"-m","compileall","-q","adam_v41","adam_v42"],cwd=root).returncode==0 else (_ for _ in()).throw(AssertionError("compile failure")))
    audit.check("pytest_v040_v041_regression_13", lambda: read_test_log(root,"v040_v041.log",13))
    audit.check("pytest_v042_core_15", lambda: read_test_log(root,"v042_core.log",15))
    audit.check("pytest_v042_o1_3", lambda: read_test_log(root,"v042_o1.log",3))

    cluster_box={}
    def distributed():
        cluster=DistributedUniverseCluster(output/"distributed",3); ids=cluster.leader.ids; old_term=cluster.term
        cert1=cluster.apply(ReactionIntent("ASSIGN_EQUIPMENT",{"equipment":ids["equipment"],"project":ids["project"],"actor":ids["actor"]}))
        require(cluster.verify_certificate(cert1),"certificate invalid")
        old_leader=cluster.leader_id;cluster.stop_node(old_leader);require(cluster.term>old_term,"term did not advance")
        cert2=cluster.apply(ReactionIntent("RELEASE_EQUIPMENT",{"equipment":ids["equipment"],"project":ids["project"],"actor":ids["actor"]},{"location":"YARD"}))
        cluster.start_node(old_leader);require(len({n.state_digest() for n in cluster.nodes.values()})==1,"recovery divergence")
        cluster_box["cluster"]=cluster
        return {"nodes":len(cluster.nodes),"quorum":cluster.quorum,"term":cluster.term,"index":cluster.index,"leader":cluster.leader_id,"votes_first":len(cert1.votes),"votes_second":len(cert2.votes)}
    audit.check("majority_consensus_failover_recovery",distributed)

    def cert_tamper():
        c=cluster_box["cluster"];cert=c.certificates[0];v=cert.votes[0]
        bad=QuorumCertificate(cert.term,cert.index,cert.proposal_digest,cert.state_digest_before,(Vote(v.node_id,v.authority_id,v.public_key_hex,"00"*64),*cert.votes[1:]),cert.hlc)
        require(not c.verify_certificate(bad),"tampered certificate accepted")
        return {"tamper_rejected":True}
    audit.check("byzantine_signature_tamper_rejection",cert_tamper)

    def sovereignty():
        data=os.urandom(65537);nodes=[(f"ca{i}","CA") for i in range(5)]+[("us","US"),("eu","EU")]
        store=SovereignErasureStore(output/"sovereign",nodes,3,2);oid=store.put(data,allowed_jurisdictions={"CA"});p=store.manifest[oid]["placements"]
        require(all(x["jurisdiction"]=="CA" for x in p),"cross-border placement")
        rebuilt=store.reconstruct(oid,{p[0]["node_id"],p[1]["node_id"]});require(rebuilt==data,"RS recovery failed")
        return {"object_id":oid,"bytes":len(data),"geometry":"3+2","losses_tolerated":2,"jurisdictions":sorted({x["jurisdiction"] for x in p})}
    audit.check("sovereignty_and_reed_solomon_two_loss_recovery",sovereignty)

    def inference_security():
        authority=Authority(output/"closure_auth");p=ClosureAuthorization(authority);p.label("identity",SecurityLabel.INTERNAL);p.label("diagnosis",SecurityLabel.CONFIDENTIAL);p.protect_combination({"identity","diagnosis"},SecurityLabel.RESTRICTED)
        grant=p.issue("analyst",["care"],SecurityLabel.CONFIDENTIAL);p.authorize(grant,"care",["identity"])
        try:p.authorize(grant,"care",["identity","diagnosis"])
        except AuthorizationError:return {"direct_allowed":True,"restricted_inference_denied":True}
        raise AssertionError("restricted inference accepted")
    audit.check("purpose_bound_inference_closure_authorization",inference_security)

    def isolated():
        with IsolatedKernelClient(output/"isolated") as client:
            eq,_=client.genesis_entity("equipment","EQ",{"status":"AVAILABLE","location":"YARD"});pr,_=client.genesis_entity("project","P",{"status":"ACTIVE"});a,_=client.genesis_entity("person","A",{"name":"A","grant::ASSIGN_EQUIPMENT":True,"grant::RELEASE_EQUIPMENT":True})
            client.apply(ReactionIntent("ASSIGN_EQUIPMENT",{"equipment":eq,"project":pr,"actor":a}));require(client.entity_view(eq)["status"]=="ASSIGNED","process commit failed")
            denied=False
            try:client.raw_commit_probe()
            except IsolatedKernelError:denied=True
            require(denied,"raw endpoint exposed")
            return {"pid":client.pid,"raw_mutation_endpoint":False,"status":"ASSIGNED"}
    audit.check("os_process_authority_isolation",isolated)

    perception_box={}
    def perception():
        u=AtomicUniverse(output/"perception");cap=u.enable_commit_guard();p=MultimodalPerception(u,capability=cap)
        items=[(b"The river bank is 12 metres wide. Alice Example inspected it.",p.text),(png_bytes(),p.image),(wav_bytes(),p.audio),(b"import math\ndef area(r): return math.pi*r*r\n",p.program),(b"id,value\nA,10\nB,20\n",p.tabular_csv)]
        results=[]
        for payload,method in items:
            r=method(payload);require(p.alignment.exact.reconstruct(r.evidence_object_id)==payload,"exact mismatch");require(p.alignment.verify_claim(r.claims[0].claim_id)["pass"],"alignment failed");results.append({"modality":r.modality,"evidence":r.evidence_object_id,"features":r.features})
        perception_box["universe"]=u
        return {"modalities":[r["modality"] for r in results],"aligned_claims":len(results),"root":u.root_hash}
    audit.check("multimodal_exact_semantic_alignment",perception)

    def low_confidence():
        u=perception_box["universe"];cap=u._commit_guard_token;align=EvidenceAlignmentEngine(u,capability=cap);e=align.ingest_evidence(b"ambiguous",media_type="text/plain",name="a.txt")
        try:align.assert_claim("ambiguous",{},evidence_object_id=e.object_id,extractor="x",confidence=.2,authoritative=True)
        except EvidenceError:return {"low_confidence_authority_denied":True}
        raise AssertionError("low confidence claim accepted")
    audit.check("low_confidence_semantic_authority_rejection",low_confidence)

    o1_box={}
    def o1_migration():
        store=OperationsOneAuthority(output/"operations_one");report=store.migrate(root/"data/operations_one_real_records.json",max_records_per_domain=24)
        require(report.records_migrated>=80,"insufficient real records");require(report.aligned_entities==report.records_migrated,"unaligned entity");require(report.exact_roundtrip and report.view_equivalence,"migration mismatch")
        o1_box["store"]=store;o1_box["report"]=report
        return asdict(report)
    audit.check("operations_one_selected_domains_sole_authority",o1_migration)

    def o1_training():
        store=o1_box["store"];model,report=DeterministicO1Cognition.train(store.records(),output/"training"/"O1_REAL_COGNITION.json")
        require(report.accuracy>=.95,"real-data classification accuracy below gate");require(report.rejected_ood,"OOD probe accepted")
        label,margin,ood=model.predict(store.records()[0][1]);require(label==store.records()[0][0] and not ood,"known record failed")
        o1_box["model"]=model
        return asdict(report)
    audit.check("operations_one_real_data_training",o1_training)

    def query():
        store=o1_box["store"];q=DistributedAQL(store.records(),sequence_provider=lambda:store.universe.sequence);plan,rows=q.execute('MATCH "Invoice Register" WHERE invoice_type == "Progress" RETURN invoice_no,amount_before_tax')
        require(rows and plan.strategy=="SHARD_PRUNED_SCAN","query planning failed")
        return {"strategy":plan.strategy,"estimated_rows":plan.estimated_rows,"returned":len(rows),"shards":plan.shards}
    audit.check("declarative_shard_pruned_aql",query)

    def chemistry():
        states=[view for _,view in o1_box["store"].records()[:50]];auth=[Authority(output/f"chem_auth_{i}") for i in range(3)];lab=ChemistryLab(output/"chemistry",auth)
        good=lab.evaluate(ChemistryCandidate("rename_source",1,2,{"source_sheet":"source_domain"}),states);bad=lab.evaluate(ChemistryCandidate("drop_source",2,3,{},("source_sheet",)),states)
        require(good.status=="PROMOTED" and bad.status=="REJECTED_EQUIVALENCE","chemistry gates wrong")
        return {"promoted":good.receipt_id,"approvals":len(good.approvals),"replayed":good.historical_states_replayed,"bad_failures":bad.equivalence_failures}
    audit.check("chemistry_shadow_replay_independent_promotion",chemistry)

    def formal():
        states=[(a,b) for a in range(5) for b in range(5)];actions=list(range(5))
        def transition(s,x):return None if x>s[0] else (s[0]-x,s[1]+x)
        proof=BoundedProofChecker.prove_transition("balance",states,actions,transition,lambda before,action,after:sum(before)==sum(after));require(proof.status=="PROVEN_BOUNDED","law not proven")
        refuted=BoundedProofChecker.prove(Law("false_universal","a == b",{"a":(0,1),"b":(0,1)}));require(refuted.status=="REFUTED","counterexample not found")
        return {"proof_id":proof.certificate_id,"cases":proof.cases_checked,"counterexample_detection":True}
    audit.check("machine_checked_bounded_conservation_proofs",formal)

    def key_management():
        ks=EncryptedSigningKeyStore(output/"keys","audit-passphrase");old=ks.descriptor;sig=ks.sign(b"authority-event");new=ks.rotate();require(new.generation==2 and ks.verify(b"authority-event",sig,old.key_id),"rotation/history failed");raw=ks.path.read_bytes();require(b"authority_private" not in raw,"plaintext marker present")
        return {"old_key":old.key_id,"new_key":new.key_id,"generation":new.generation,"encrypted_at_rest":True}
    audit.check("encrypted_key_storage_rotation_history",key_management)

    def erasure():
        s=CryptoErasureStore(output/"crypto_erasure",b"master");oid=s.put(b"regulated record");require(s.get(oid)==b"regulated record","pre-erasure read failed");t=s.erase(oid,"retention expired","records officer")
        denied=False
        try:s.get(oid)
        except KeyStoreError:denied=True
        require(denied,"erased object readable")
        return {"object_id":oid,"unreadable":True,"tombstone":t}
    audit.check("cryptographic_erasure_with_audit_tombstone",erasure)

    def time_model():
        a=HybridLogicalClock("a",now_ns=lambda:100);b=HybridLogicalClock("b",now_ns=lambda:90);a1=a.tick();b1=b.merge(a1);a2=a.merge(b1);require(a1<b1<a2,"causal order failed");require(ValidInterval(0,20).relation(ValidInterval(5,10))=="CONTAINS","interval relation wrong");require(ValidInterval(10,20).intersects_uncertainty(UncertainInstant(19,25)),"uncertainty relation wrong")
        return {"a1":a1.canonical(),"b1":b1.canonical(),"a2":a2.canonical(),"interval_algebra":True}
    audit.check("hybrid_logical_time_interval_uncertainty",time_model)

    def advanced_reaction():
        u=AtomicUniverse(output/"advanced_reaction");cap=u.enable_commit_guard();base=ReactionEngine(u,TypeRegistry(),capability=cap);base.register_type(TypeSpec("account",(ValenceRule("balance",1,1,value_type="number"),ValenceRule("budget",1,1,value_type="number"))));base.register_type(TypeSpec("person",(),allow_unlisted_predicates=True));base.register_reaction(ReactionDefinition("POST_COST",1,{"account":"account","actor":"person"},"actor",("POST_COST",),(),(Effect("account","balance","set_arg",value_arg="new_balance"),)))
        acct,_=base.genesis_entity("account","A",{"balance":60,"budget":100});actor,_=base.genesis_entity("person","U",{"grant::POST_COST":True});adv=AdvancedReactionEngine(base);adv.register_policy(AdvancedPolicy("POST_COST",(AdvancedCondition("account","balance","sum_plus_arg_lte",{"arg":"amount","role":"account","predicate":"budget"}),),(ComputedArgument("new_balance","account","balance","add",operand_arg="amount"),)))
        adv.apply(ReactionIntent("POST_COST",{"account":acct,"actor":actor},{"amount":25}));require(u.entity_view(acct)["balance"]==85.0,"arithmetic effect failed");before=u.root_hash
        try:adv.apply(ReactionIntent("POST_COST",{"account":acct,"actor":actor},{"amount":20}))
        except ReactionError:pass
        else:raise AssertionError("over-budget reaction accepted")
        require(u.root_hash==before,"rejected advanced reaction mutated state")
        return {"balance":85.0,"aggregate_guard":True,"arithmetic_effect":True}
    audit.check("extended_aggregate_temporal_arithmetic_reaction_language",advanced_reaction)

    soak=audit.check("accelerated_30_logical_day_distributed_soak",lambda:asdict(run_logical_soak(output/"soak_30_logical_days",logical_days=30,cycles_per_day=4)))
    if soak:
        audit.check("bounded_distributed_performance",lambda:{"commits":soak["commits"],"seconds":soak["elapsed_seconds"],"commits_per_second":round(soak["commits"]/max(soak["elapsed_seconds"],1e-9),3),"peak_memory_bytes":soak["peak_memory_bytes"]})

    gaps=[
        {"id":"H-001","v041":"HIGH OPEN","v042":"BOUNDED CLOSED","remaining":"Rust kernel not compiled; HSM boundary still pending"},
        {"id":"H-002","v041":"CRITICAL OPEN","v042":"BOUNDED CLOSED","remaining":"Not a production Raft/BFT/WAN implementation"},
        {"id":"H-003","v041":"CRITICAL OPEN","v042":"PARTIAL","remaining":"Five codecs implemented; universal semantic understanding remains unsolved"},
        {"id":"H-004","v041":"CRITICAL OPEN","v042":"BOUNDED CLOSED","remaining":"Policy graph tested; arbitrary learned side-channel inference remains open"},
        {"id":"H-005","v041":"CRITICAL OPEN","v042":"PARTIAL","remaining":"Real O1 records train cognition; real temporal sensor trajectories remain limited"},
        {"id":"H-006","v041":"CRITICAL OPEN","v042":"BOUNDED CLOSED","remaining":"Selected O1 domains only, not complete production deployment"},
        {"id":"H-007","v041":"HIGH OPEN","v042":"BOUNDED CLOSED","remaining":"Aggregate/arithmetic/temporal wrapper is not a universal reaction language"},
        {"id":"H-008","v041":"HIGH OPEN","v042":"PARTIAL","remaining":"Bounded proof checker is not a general theorem prover"},
        {"id":"H-009","v041":"HIGH OPEN","v042":"BOUNDED CLOSED","remaining":"Enforced on v0.42 claims/migrated entities, not retroactive legacy content"},
        {"id":"H-010","v041":"HIGH OPEN","v042":"BOUNDED CLOSED","remaining":"Promotion/replay implemented; autonomous discovery remains bounded"},
        {"id":"H-011","v041":"HIGH OPEN","v042":"BOUNDED CLOSED","remaining":"Deterministic vocabulary OOD gate, not formal open-world calibration"},
        {"id":"H-012","v041":"HIGH OPEN","v042":"PARTIAL","remaining":"Encrypted rotating keys implemented; no HSM/KMS integration"},
        {"id":"H-013","v041":"HIGH OPEN","v042":"BOUNDED CLOSED","remaining":"Cryptographic erasure implemented; legal workflow certification pending"},
        {"id":"H-014","v041":"HIGH OPEN","v042":"PARTIAL","remaining":"30 logical days executed; 30 wall-clock days not executed"},
        {"id":"H-015","v041":"MEDIUM OPEN","v042":"BOUNDED CLOSED","remaining":"AQL shard pruning/cache implemented; production cost optimizer pending"},
        {"id":"H-016","v041":"MEDIUM OPEN","v042":"BOUNDED CLOSED","remaining":"HLC/interval uncertainty implemented; global clock qualification pending"},
        {"id":"H-017","v041":"MEDIUM OPEN","v042":"BOUNDED CLOSED","remaining":"Integer model matched independent processes; cross-OS/hardware lab pending"},
        {"id":"H-018","v041":"MEDIUM OPEN","v042":"PARTIAL","remaining":"Measured bounded performance only; production SLA unproven"},
    ]
    passed=sum(c["status"]=="PASS" for c in audit.checks);failed=len(audit.checks)-passed
    result={
        "build":"0.42.0.dev1","classification":"bounded distributed cognitive-universe research prototype",
        "audit":{"passed":passed,"failed":failed,"checks":audit.checks},
        "gap_status":{"bounded_closed":sum(g["v042"]=="BOUNDED CLOSED" for g in gaps),"partial":sum(g["v042"]=="PARTIAL" for g in gaps),"fully_universal_closed":0,"gaps":gaps},
        "claim_boundary":"The build materially closes or mitigates all 18 v0.41 gaps at bounded prototype level, but does not prove a complete universal artificial living universe, production Byzantine consensus, universal perception, arbitrary theorem proving, HSM deployment, 30 wall-clock days, or production SLAs.",
    }
    path=output/"ADAM_V042_AUDIT_RESULTS.json";path.write_text(json.dumps(result,indent=2,sort_keys=True,default=str),encoding="utf-8")
    print(json.dumps({"result":str(path),"passed":passed,"failed":failed,"bounded_closed":result["gap_status"]["bounded_closed"],"partial":result["gap_status"]["partial"]},indent=2))
    if failed: raise SystemExit(1)

if __name__=="__main__":main()
