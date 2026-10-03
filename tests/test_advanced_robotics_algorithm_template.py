from __future__ import annotations
from pathlib import Path
import importlib.util,json,sys,tempfile
ROOT=Path(__file__).resolve().parents[1]
MOD=ROOT/"src"/"43_DCO_Factory"/"canonical_dco_factory.py"
TPL=ROOT/"templates"/"dco"/"BTG_ADVANCED_ROBOTICS_ALGORITHM_01.json"
def load():
 s=importlib.util.spec_from_file_location("advanced_robotics_template_test",MOD)
 m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m);return m
def test_advanced_robotics_algorithm_template():
 m=load()
 with tempfile.TemporaryDirectory() as td:
  f=m.DCOFactory(td);reg=f.register_template(json.loads(TPL.read_text(encoding="utf-8")))
  assert reg["archetype_count"]==7
  p=f.plan("BTG-ADVANCED-ROBOTICS-ALGORITHM-01",dco_code="DCO-000002",family="ROBOTICS_FAILURE_DETECTION_ALGORITHM")
  assert p["archetype_count"]==7
  assert p["physical_instrument_count"]==16
  assert p["total_right_units"]==11868
  assert p["treasury_reserve_units"]==2030
