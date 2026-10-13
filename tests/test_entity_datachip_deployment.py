"""Atomic verified DataChip staging, restart and fail-closed update checks."""
from __future__ import annotations
from pathlib import Path
import hashlib
import json
import sys
import tempfile
import unittest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from sdk.datachip.application import SCHEMA,sign_bundle
from sdk.datachip.deployment import DataChipDeploymentManager
from sdk.datachip.formula_chip import pack_formula_bytes
from sdk.datachip.processor import DataChipError

def pub(k):
    return k.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)

class DeploymentQualificationTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(prefix="entity-deployment-")
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.private=Ed25519PrivateKey.generate()
        self.keys={"btg-release-signing":pub(self.private)}
        self.mgr=DataChipDeploymentManager(self.root/"install",
            app_id="HuntAR",platform="windows",trusted_bundle_keys=self.keys)
        self.chip=self.root/"trail.edcf"
        self.doc=pack_formula_bytes(b"SYNTHETIC-TRAIL,NOT-FOR-NAVIGATION|"*200,self.chip)
        self.digest=hashlib.sha256(self.chip.read_bytes()).hexdigest()
        self.mapping={self.doc["chip_id"]:self.chip}
    def manifest(self,number,*,locked=True):
        body={"schema":SCHEMA,"app_id":"HuntAR",
              "release_id":f"release-{number:08d}",
              "signer_id":"btg-release-signing","host_abi":1,
              "platforms":["windows"],"modules":[{
                 "name":"trails","kind":"geographic",
                 "chip_id":self.doc["chip_id"],"sha256":self.digest,
                 "requires":[],"data_right":"grant-required" if locked else "public",
              }]}
        return sign_bundle(self.private,body)
    def stage(self,num,**kw):
        return self.mgr.stage_and_activate(self.manifest(num),
             local_chips=self.mapping,**kw)
    def test_first_signed_deployment_and_restart(self):
        outcome=self.stage(1)
        self.assertEqual(outcome["status"],"activated")
        self.assertEqual(outcome["rights_locked_modules"],["trails"])
        self.assertFalse(outcome["native_code_modified"])
        restarted=DataChipDeploymentManager(self.root/"install",
            app_id="HuntAR",platform="windows",trusted_bundle_keys=self.keys)
        result=restarted.active()
        self.assertEqual(result["sequence"],1)
        self.assertEqual(result["verified_manifest"]["rights_locked_modules"],["trails"])
    def test_upgrade_downgrade_and_sequence_collision(self):
        self.stage(1)
        self.stage(2)
        self.assertEqual(self.mgr.active()["sequence"],2)
        with self.assertRaises(PermissionError):
            self.stage(1)
        self.assertEqual(self.stage(2)["status"],"already-active")
        with self.assertRaises(PermissionError):
            self.mgr.stage_and_activate(self.manifest(2,locked=False),
                local_chips=self.mapping)
    def test_staging_fault_preserves_last_known_good(self):
        self.stage(1)
        def crash():
            raise RuntimeError("simulated power loss before commit")
        with self.assertRaises(RuntimeError):
            self.stage(2,before_commit=crash)
        self.assertEqual(self.mgr.active()["sequence"],1)
        leftover=list(self.mgr.releases.glob(".datac-stage-*"))
        self.assertEqual(leftover,[])
    def test_tampered_chip_source_never_activates(self):
        self.stage(1)
        changed=self.root/"changed.edcf"
        changed.write_bytes(self.chip.read_bytes()+b"TAMPERING")
        with self.assertRaises(DataChipError):
            self.mgr.stage_and_activate(self.manifest(2),
                 local_chips={self.doc["chip_id"]:changed})
        self.assertEqual(self.mgr.active()["sequence"],1)
    def test_untrusted_publisher_never_activates(self):
        different=Ed25519PrivateKey.generate()
        bad=sign_bundle(different,self.manifest(1)["body"])
        with self.assertRaises(PermissionError):
            self.mgr.stage_and_activate(bad,local_chips=self.mapping)
        self.assertIsNone(self.mgr.active())
    def test_wrong_app_or_platform_denied(self):
        wrong=DataChipDeploymentManager(self.root/"other",
            app_id="SearchAR",platform="windows",trusted_bundle_keys=self.keys)
        with self.assertRaises(PermissionError):
            wrong.stage_and_activate(self.manifest(1),local_chips=self.mapping)
        wrong=DataChipDeploymentManager(self.root/"other2",
            app_id="HuntAR",platform="ios",trusted_bundle_keys=self.keys)
        with self.assertRaises(PermissionError):
            wrong.stage_and_activate(self.manifest(1),local_chips=self.mapping)
    def test_corrupt_active_chip_detected_on_restart(self):
        self.stage(1)
        path=next(iter(self.mgr.active()["chip_paths"].values()))
        with path.open("ab") as f:
            f.write(b"ALTERED")
        with self.assertRaises(DataChipError):
            self.mgr.active()
        with self.assertRaises(DataChipError):
            self.stage(2)
    def test_corrupt_active_pointer_fails_closed(self):
        self.stage(1)
        self.mgr.pointer.write_text('{"broken":true}')
        with self.assertRaises(DataChipError):
            self.mgr.active()
        with self.assertRaises(DataChipError):
            self.stage(2)
    def test_unsequenced_release_rejected(self):
        signed=self.manifest(1)
        signed["body"]["release_id"]="2026.10.12"
        with self.assertRaises(DataChipError):
            self.mgr.stage_and_activate(signed,local_chips=self.mapping)
        self.assertIsNone(self.mgr.active())
    def test_missing_source_fails(self):
        with self.assertRaises(DataChipError):
            self.mgr.stage_and_activate(self.manifest(1),local_chips={})
        self.assertIsNone(self.mgr.active())

if __name__=="__main__":
    unittest.main()
