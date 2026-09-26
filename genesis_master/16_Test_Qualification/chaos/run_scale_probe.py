from pathlib import Path
import hashlib, importlib.util, json, sys, tempfile, time
ROOT=Path(r"<LOCAL_DRIVE>/Sovereign_Entity_Network")
OUT=ROOT/"16_Test_Qualification"/"evidence"/"ENTITY_CHAOS_SCALE_PROBE_CURRENT.json"

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); assert spec and spec.loader
    mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod

def run_block(fn):
    t=time.perf_counter(); count=fn(); elapsed=time.perf_counter()-t
    return {"count":count,"seconds":round(elapsed,4),"per_second":round(count/elapsed,2) if elapsed else None}

I=load("scale_identity",ROOT/"01_Core_Runtime"/"identity"/"canonical_identity.py")
L=load("scale_ledger",ROOT/"04_Entity_Registry"/"event_ledger"/"canonical_event_ledger.py")
R=load("scale_rights",ROOT/"04_Entity_Registry"/"ownership_graphs"/"canonical_rights_claims.py")
PV=load("scale_prov",ROOT/"04_Entity_Registry"/"provenance"/"canonical_provenance.py")
A=load("scale_assets",ROOT/"04_Entity_Registry"/"asset_registry"/"canonical_asset_registry.py")
E=load("scale_econ",ROOT/"01_Core_Runtime"/"service_runtime"/"canonical_economics.py")
P=load("scale_policy",ROOT/"01_Core_Runtime"/"policy_engine"/"canonical_policy.py")
C=load("scale_caps",ROOT/"01_Core_Runtime"/"permissions"/"canonical_permissions.py")

def main():
    results={}; failures=[]
    with tempfile.TemporaryDirectory() as td:
        state=Path(td)/"state"; ids=I.EntityIdentityVault(state)
        created=[]
        def identities():
            for i in range(2000): created.append(ids.create(f"Scale Entity {i}","organization")["entity_id"])
            return len(created)
        results["entity_creation"]=run_block(identities)
        owner,peer=created[0],created[1]
        ledger=L.CanonicalEventLedger(state,ids); rights=R.RightsClaimsGraph(state,ids); prov=PV.AssetProvenanceGraph(state,ids)
        assets=A.CanonicalAssetRegistry(state,ids,ledger,rights,prov)
        def asset_load():
            for i in range(2000):
                assets.register(owner,content_sha256=hashlib.sha256(f"scale-asset-{i}".encode()).hexdigest(),size_bytes=i+1,media_type="application/octet-stream",title=f"scale-{i}")
            return 2000
        results["asset_registration"]=run_block(asset_load)
        econ=E.SettlementEngine(state,ids)
        def settlements():
            for i in range(1000):
                s=econ.create(owner,peer,amount_units=1+(i%100),currency="CAD",obligation_ref=f"scale-ob-{i}",transaction_nonce=f"scale-settle-{i}")
                econ.authorize(owner,s["settlement_id"]); econ.confirm(owner,s["settlement_id"])
            return 1000
        results["settlement_finalization"]=run_block(settlements)
        policy=P.PolicyConsentEngine(state,ids); pol=policy.create_policy(owner,"Scale",{"VIEW":"PERMIT"})
        caps=C.AuthorityCapabilityStore(state,ids); cap=caps.grant(owner,"scale-agent",operations=["VIEW"],asset_scope=["asset-ok"],counterparty_scope=[peer])
        def deny_storm():
            denied=0
            for i in range(50000):
                denied += int(not policy.evaluate(pol["policy_id"],f"UNKNOWN_{i}")["allowed"])
            for i in range(50000):
                denied += int(not caps.authorize(cap["capability_id"],"scale-agent","VIEW",asset_id=f"asset-{i}",counterparty_id=peer)["allowed"])
            if denied!=100000: failures.append(f"deny_storm:{denied}")
            return 100000
        results["fail_closed_authorization"]=run_block(deny_storm)
        if econ.status()["settlements"]!=1000: failures.append("settlement_count")
        if assets.status()["assets"]<2000: failures.append("asset_count")
    payload={"schema":"entity-chaos-scale-probe-v1","generated_at_ms":int(time.time()*1000),"status":"PASS" if not failures else "FAIL","qualification_complete":not failures,"limitations":["progressive workstation probe; does not claim million-asset/multi-million-event production scale"],"results":results,"failures":failures}
    body=dict(payload); payload["evidence_sha256"]=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()
    OUT.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(payload,indent=2)); return 0 if not failures else 2
if __name__=="__main__": raise SystemExit(main())
