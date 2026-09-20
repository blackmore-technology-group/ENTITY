import importlib.util, json, pathlib, unittest, os, tempfile
REPO=pathlib.Path(__file__).resolve().parents[1]
BASE=REPO/"src"/"11_ADAM"/"full_runtime"
class AdamV2IntegrationContractTests(unittest.TestCase):
 def test_pin_and_protocol_boundary(self):
  pin=json.loads((BASE/"ADAM_REFERENCE_PIN.json").read_text(encoding="utf-8")); self.assertEqual(pin["authoritative_inner_sha256"],"3cc6541f2d00dd0580989cc7fe6e8abd56974d1069f61c710e230568e00b8da3"); self.assertTrue(pin["authoritative_inner_sidecar_matches"])
  dev=json.loads((REPO/"DEVELOPMENT_RELEASE_MANIFEST.json").read_text(encoding="utf-8")); self.assertEqual(dev["protocol"]["1.0"],"FROZEN_FOR_EXTERNAL_CONFORMANCE_UNCHANGED"); self.assertEqual(dev["protocol"]["2.0"],"DEVELOPMENT")
 def test_adapter_imports_without_adam_package(self):
  spec=importlib.util.spec_from_file_location("entity_adam_public",BASE/"canonical_full_adam_runtime.py"); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); self.assertTrue(hasattr(mod,"EntityFullAdamRuntime"))
 def test_missing_package_fails_closed(self):
  old=os.environ.pop("ENTITY_ADAM_V1_ROOT",None)
  try:
   spec=importlib.util.spec_from_file_location("entity_adam_public2",BASE/"canonical_full_adam_runtime.py"); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
   with tempfile.TemporaryDirectory(prefix="entity-adam-public-") as td:
    with self.assertRaises(FileNotFoundError): mod.EntityFullAdamRuntime(td,authorization_verifier=lambda r:True)
  finally:
   if old is not None: os.environ["ENTITY_ADAM_V1_ROOT"]=old
if __name__=="__main__": unittest.main()
