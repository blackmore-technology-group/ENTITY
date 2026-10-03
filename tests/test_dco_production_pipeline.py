from __future__ import annotations
from pathlib import Path
import hashlib,importlib.util,sys,tempfile

ROOT=Path(__file__).resolve().parents[1]
PIPE=ROOT/"src"/"43_DCO_Factory"/"dco_production_pipeline.py"
BRIDGE=ROOT/"src"/"44_Shared_Bridges"/"robotics_bridge_registry.py"

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(spec)
    sys.modules[name]=m; spec.loader.exec_module(m); return m
def h(s): return hashlib.sha256(str(s).encode()).hexdigest()

def test_production_pipeline_enforces_passports_before_economics():
    m=load("dco_pipeline_test",PIPE)
    with tempfile.TemporaryDirectory() as td:
        p=m.DCOProductionPipeline(td)
        try:
            p.record_stage("DCO-1","ECONOMIC_INSTRUMENTS_ISSUED",h("bad"))
            assert False
        except ValueError: pass
        sequence=[
          "ASSET_BUILT","ASSET_QUALIFIED","PROVENANCE_SEALED","DCO_REGISTERED",
          "RIGHTS_PASSPORT_ISSUED","GLOBAL_PASSPORT_ISSUED","PROFILE_BTDU_BOUND",
          "ECONOMIC_INSTRUMENTS_ISSUED"]
        for i,s in enumerate(sequence): p.record_stage("DCO-1",s,h(i),{"i":i})
        status=p.status("DCO-1")
        assert status["ready_for_economic_issuance"] is True
        assert status["economic_instruments_issued"] is True
        assert status["bridge_bound"] is False

def test_public_safe_manifest_rejects_live_operational_keys():
    m=load("dco_pipeline_public_test",PIPE)
    base={"dco_id":"DCO-1","name":"Asset","asset_class":"DATASET","content_sha256":h("asset"),
          "controller":"BTG","originator":"BTG","version":"1.0","public_rights_summary":{"train":True},
          "rights_passport_sha256":h("rp"),"global_passport_sha256":h("gp"),"qualification_sha256":h("q"),
          "benchmark_summary":{},"public_provenance_refs":["urn:test"],"economic_state":{"state":"POTENTIAL","amount_units":0,"currency":"CAD"}}
    out=m.DCOProductionPipeline.build_public_safe_manifest(base)
    assert out["live_operational_state_included"] is False
    bad=dict(base,wallet_id="secret")
    try:
        m.DCOProductionPipeline.build_public_safe_manifest(bad); assert False
    except ValueError: pass

def test_one_robotics_bridge_supports_thirty_dcos():
    m=load("shared_robotics_bridge_test",BRIDGE)
    with tempfile.TemporaryDirectory() as td:
        r=m.SharedBridgeRegistry(td)
        for i in range(1,31):
            r.bind(f"DCO-{i:06d}",h(f"gp-{i}"),enabled_interfaces=[],exposure_mode="NOT_EXPOSED")
        bindings=r.bindings()
        assert len(bindings)==30
        assert r.get_bridge(m.ROBOTICS_BRIDGE_ID)["bridge_id"]==m.ROBOTICS_BRIDGE_ID
        assert len({x["dco_id"] for x in bindings})==30
        try:
            r.route_envelope("DCO-000001","ROS-2","READ","asset:test"); assert False
        except PermissionError: pass
