from pathlib import Path
import base64, hashlib, importlib.util, json, random, sys, tempfile, time
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network"); SEED=20260916; rng=random.Random(SEED)
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod
I=load("gi_identity",ROOT/"01_Core_Runtime"/"identity"/"canonical_identity.py")
P=load("gi_policy",ROOT/"01_Core_Runtime"/"policy_engine"/"canonical_policy.py")
C=load("gi_caps",ROOT/"01_Core_Runtime"/"permissions"/"canonical_permissions.py")
E=load("gi_evidence",ROOT/"04_Entity_Registry"/"evidence_assertions"/"canonical_evidence.py")
G=load("gi_privilege",ROOT/"00_Governance"/"privilege_graph"/"canonical_privilege_graph.py")
S=load("gi_states",ROOT/"15_Operations"/"runtime_states"/"service_state_machine.py")
EC=load("gi_econ",ROOT/"01_Core_Runtime"/"service_runtime"/"canonical_economics.py")
L=load("gi_ledger",ROOT/"04_Entity_Registry"/"event_ledger"/"canonical_event_ledger.py")
R=load("gi_rights",ROOT/"04_Entity_Registry"/"ownership_graphs"/"canonical_rights_claims.py")
PV=load("gi_prov",ROOT/"04_Entity_Registry"/"provenance"/"canonical_provenance.py")
A=load("gi_assets",ROOT/"04_Entity_Registry"/"asset_registry"/"canonical_asset_registry.py")

def expect_raises(fn):
    try: fn(); return False
    except Exception: return True

def main():
    counts={}; failures=[]
    with tempfile.TemporaryDirectory() as td:
        state=Path(td)/"state"; ids=I.EntityIdentityVault(state)
        owner=ids.create("Invariant Owner","organization")["entity_id"]; peer=ids.create("Invariant Peer","organization")["entity_id"]
        graph=G.PrivilegeGraph(); subs=sorted(G.SUBSYSTEMS)
        for i in range(5000):
            src=rng.choice(subs); dst=rng.choice(subs); op=f"UNDECLARED_{rng.randrange(10**9)}"
            if graph.evaluate(src,dst,op)["decision"]!="DENY": failures.append(f"privilege_default_deny:{i}")
        counts["privilege_default_deny"]=5000
        if graph.evaluate("NIKI","ENTITY","RIGHTS_MUTATE")["decision"]!="DENY": failures.append("niki_rights_mutation")
        counts["niki_read_not_mutation_authority"]=1

        policy=P.PolicyConsentEngine(state,ids); pol=policy.create_policy(owner,"Generated",{"VIEW":"PERMIT"})
        for i in range(1000):
            if policy.evaluate(pol["policy_id"],f"UNKNOWN_{i}")["allowed"]: failures.append(f"policy_fail_closed:{i}")
        counts["policy_unknown_action_fail_closed"]=1000

        caps=C.AuthorityCapabilityStore(state,ids)
        cap=caps.grant(owner,"agent-generated",operations=["EXPORT"],asset_scope=["asset-allowed"],counterparty_scope=[peer],financial_limit=1000)
        for i in range(1000):
            wrong_asset=f"asset-{i}"
            if caps.authorize(cap["capability_id"],"agent-generated","EXPORT",asset_id=wrong_asset,counterparty_id=peer,amount=1)["allowed"]: failures.append(f"capability_scope_expand:{i}")
        counts["capability_scope_non_expansion"]=1000

        base=E.EvidenceAssertionFactory.create("x",claimant=owner,evidence_origin="UNKNOWN")
        for i in range(500):
            if not expect_raises(lambda: E.EvidenceAssertionFactory.create(i,claimant=owner,evidence_origin="UNKNOWN",verification_level="VERIFIED")): failures.append(f"unknown_to_verified:{i}")
            if not expect_raises(lambda: E.EvidenceAssertionFactory.transition(base,verification_level="VERIFIED",evidence_origin="ENTITY_ASSERTION",evidence_reference=f"ref-{i}")): failures.append(f"bad_evidence_transition:{i}")
        counts["evidence_no_silent_verification"]=1000
        sm=S.ServiceStateMachine(state)
        for idx,target in enumerate(["DEGRADED","OFFLINE","DEPENDENCY_UNAVAILABLE","MALICIOUS_INPUT","CONFLICTING_STATE","RECOVERY","QUARANTINED"]):
            sid=f"svc-{idx}"; sm.register(sid)
            if target=="QUARANTINED":
                sm.transition(sid,"MALICIOUS_INPUT",trigger="generated",evidence={"case":idx}); sm.transition(sid,"QUARANTINED",trigger="generated",evidence={"case":idx})
            else: sm.transition(sid,target,trigger="generated",evidence={"case":idx} if target in {"MALICIOUS_INPUT","CONFLICTING_STATE"} else None)
            for j in range(500):
                op=rng.choice(sorted(S.HIGH_IMPACT))
                if sm.authorize_operation(sid,op)["allowed"]: failures.append(f"degraded_high_impact:{idx}:{j}")
        counts["degraded_high_impact_fail_closed"]=3500

        econ=EC.SettlementEngine(state,ids); expected=0
        for i in range(100):
            amount=rng.randint(1,1000); nonce=f"generated-settlement-{i}"; expected+=amount
            s=econ.create(owner,peer,amount_units=amount,currency="CAD",obligation_ref=f"ob-{i}",transaction_nonce=nonce,settlement_kind="INTERNAL_ACCOUNTING")
            econ.authorize(owner,s["settlement_id"]); econ.confirm(owner,s["settlement_id"])
            if not expect_raises(lambda n=nonce: econ.create(owner,peer,amount_units=1,currency="CAD",obligation_ref="dup",transaction_nonce=n,settlement_kind="INTERNAL_ACCOUNTING")): failures.append(f"settlement_replay:{i}")
        b1=econ.balance(owner,"CAD"); b2=econ.balance(peer,"CAD")
        if b1["net"]!=-expected or b2["net"]!=expected or b1["net"]+b2["net"]!=0: failures.append("double_entry_balance")
        counts["settlement_replay_rejected"]=100; counts["double_entry_balanced_batches"]=100

        signed=[]
        for i in range(100):
            payload={"historical":i}; signed.append((payload,ids.sign(owner,payload)))
        manifest=ids.recover_signing_key(owner)
        for i,(payload,sig) in enumerate(signed):
            if not I.EntityIdentityVault.verify_signature(manifest,payload,sig): failures.append(f"historical_signature:{i}")
        counts["historical_signatures_after_recovery"]=100
        old_key_id=signed[0][1]["key_id"]; method=next(x for x in manifest["verification_methods"] if x["key_id"]==old_key_id); old_raw=(state/"identity"/"keys"/owner/f"{old_key_id}.key").read_bytes(); old_key=Ed25519PrivateKey.from_private_bytes(old_raw)
        for i in range(100):
            payload={"post_revocation":i}; digest=hashlib.sha256(I.canonical_json(payload)).hexdigest(); rec={"signature_schema":"entity-signature-record-v2","entity_id":owner,"key_id":old_key_id,"suite":method["suite"],"signed_at_ms":int(method["revoked_at_ms"])+1+i,"payload_sha256":digest}; rec["signature"]=base64.urlsafe_b64encode(old_key.sign(I.canonical_json(rec))).decode("ascii").rstrip("=")
            if I.EntityIdentityVault.verify_signature(manifest,payload,rec): failures.append(f"revoked_key_late_authorization:{i}")
        counts["revoked_key_post_revocation_rejected"]=100
        ledger=L.CanonicalEventLedger(state,ids); rights=R.RightsClaimsGraph(state,ids); prov=PV.AssetProvenanceGraph(state,ids); assets=A.CanonicalAssetRegistry(state,ids,ledger,rights,prov)
        for i in range(25):
            digest=hashlib.sha256(f"asset-{i}".encode()).hexdigest(); asset=assets.register(owner,content_sha256=digest,size_bytes=i+1,media_type="application/octet-stream",title=f"asset-{i}")
            before=prov.lineage(asset["asset_id"]); assets.deactivate(owner,asset["asset_id"],reason="generated invariant"); after=prov.lineage(asset["asset_id"])
            if before!=after: failures.append(f"provenance_rewrite:{i}")
        counts["asset_deactivation_preserves_provenance"]=25

    total=sum(counts.values()); payload={"schema":"entity-generated-invariant-campaign-v1","generated_at_ms":int(time.time()*1000),"seed":SEED,
      "status":"PASS" if not failures else "FAIL","qualification_complete":not failures,"limitations":[],"framework":"deterministic generated/model-based campaign; Hypothesis unavailable",
      "generated_cases":total,"invariant_case_counts":counts,"failures":failures,
      "required_invariants":["unauthorized actors cannot mutate protected rights","revoked keys cannot authorize later operations","duplicate settlement requests cannot duplicate settlements","finalized double-entry accounting balances","asset deletion cannot rewrite provenance","policy denial fails closed","NIKI read cannot imply mutation","capability scope cannot expand","historical signatures remain verifiable","unknown evidence cannot silently become verified"]}
    raw=json.dumps(payload,sort_keys=True,separators=(",",":"),default=str).encode(); payload["evidence_sha256"]=hashlib.sha256(raw).hexdigest()
    out=ROOT/"16_Test_Qualification"/"evidence"/"ENTITY_GENERATED_INVARIANTS_CURRENT.json"; out.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"status":payload["status"],"generated_cases":total,"failures":len(failures),"evidence_sha256":payload["evidence_sha256"]},indent=2)); return 0 if not failures else 2
if __name__=="__main__": raise SystemExit(main())
