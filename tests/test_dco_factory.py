from __future__ import annotations
from pathlib import Path
import hashlib, importlib.util, json, sys, tempfile

ROOT=Path(__file__).resolve().parents[1]
MOD=ROOT/"src"/"43_DCO_Factory"/"canonical_dco_factory.py"
TPL=ROOT/"templates"/"dco"/"BTG_STRATEGIC_AI_ROBOTICS_01.json"

def load():
    spec=importlib.util.spec_from_file_location("dco_factory_test_mod",MOD)
    mod=importlib.util.module_from_spec(spec); sys.modules[spec.name]=mod; spec.loader.exec_module(mod); return mod

def digest(i): return hashlib.sha256(f"asset-{i}".encode()).hexdigest()

def test_robotics_template_plans_12_archetypes_and_21_physical_instruments():
    m=load()
    with tempfile.TemporaryDirectory() as td:
        f=m.DCOFactory(td)
        reg=f.register_template(json.loads(TPL.read_text(encoding="utf-8")))
        assert reg["archetype_count"]==12
        p=f.plan("BTG-STRATEGIC-AI-ROBOTICS-01",dco_code="DCO-ROBOTICS-TEST",family="INDUSTRIAL_ROBOTICS")
        assert p["archetype_count"]==12
        assert p["physical_instrument_count"]==21
        assert p["total_right_units"]==28418
        assert p["treasury_reserve_units"]==2280
        assert p["protocol_change_required"] is False

def test_duplicate_version_and_derivative_classification():
    m=load()
    with tempfile.TemporaryDirectory() as td:
        f=m.DCOFactory(td); f.register_template(json.loads(TPL.read_text(encoding="utf-8")))
        p=f.plan("BTG-STRATEGIC-AI-ROBOTICS-01",dco_code="DCO-A",family="INDUSTRIAL_ROBOTICS")
        f.create_master(dco_id="DCO-A",template_id=p["template_id"],family="INDUSTRIAL_ROBOTICS",
                        source_sha256=digest(1),semantic_fingerprint="sem-a",plan=p)
        assert f.classify_candidate(source_sha256=digest(1))["decision"]=="DUPLICATE_REJECT"
        assert f.classify_candidate(source_sha256=digest(2),version_of="DCO-A")["decision"]=="NEW_VERSION"
        assert f.classify_candidate(source_sha256=digest(3),derivative_of="DCO-A")["decision"]=="DERIVATIVE_OF_EXISTING_DCO"

def test_10000_dco_registry_design_target():
    m=load()
    with tempfile.TemporaryDirectory() as td:
        f=m.DCOFactory(td); f.register_template(json.loads(TPL.read_text(encoding="utf-8")))
        records=[{"dco_id":f"DCO-{i:05d}","template_id":"BTG-STRATEGIC-AI-ROBOTICS-01",
                  "family":"QUALIFICATION","source_sha256":digest(i)} for i in range(10000)]
        assert f.bulk_register_masters(records)==10000
        s=f.portfolio_summary()
        assert s["total_dcos"]==10000
        assert s["active_dcos"]==10000
        assert s["target_design_capacity_dcos"]==10000
