from __future__ import annotations
from pathlib import Path
import importlib.util,json,sys,tempfile

ROOT=Path(__file__).resolve().parents[1]
MOD=ROOT/"src"/"43_DCO_Factory"/"canonical_dco_factory.py"
TPL=ROOT/"templates"/"dco"/"BTG_STRATEGIC_ROBOTICS_DATASET_01.json"

def load():
    spec=importlib.util.spec_from_file_location("birfr_factory_test",MOD)
    m=importlib.util.module_from_spec(spec); sys.modules[spec.name]=m; spec.loader.exec_module(m); return m

def test_birfr_dataset_template():
    m=load()
    with tempfile.TemporaryDirectory() as td:
        f=m.DCOFactory(td)
        reg=f.register_template(json.loads(TPL.read_text(encoding="utf-8")))
        assert reg["archetype_count"]==11
        p=f.plan("BTG-STRATEGIC-ROBOTICS-DATASET-01",dco_code="DCO-000001",family="ROBOTICS_FAILURE_RECOVERY_DATASET")
        assert p["archetype_count"]==11
        assert p["physical_instrument_count"]==20
        assert p["total_right_units"]==18418
        assert p["treasury_reserve_units"]==2280
        assert p["protocol_change_required"] is False
