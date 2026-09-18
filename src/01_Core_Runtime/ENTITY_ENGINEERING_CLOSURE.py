from pathlib import Path
import importlib.util,sys
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'01_Core_Runtime'/'engineering_controls'/'canonical_engineering_controls.py'
s=importlib.util.spec_from_file_location('entity_engineering_controls_shared',p); m=importlib.util.module_from_spec(s); sys.modules[s.name]=m; s.loader.exec_module(m)
CanonicalEngineeringControlPlane=m.CanonicalEngineeringControlPlane
