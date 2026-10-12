"""BTG DataChip application manifest pilot: synthetic shared BC trail dataset."""
import copy
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat

BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE))
from sdk.datachip.application import sign_bundle,verify_bundle,SCHEMA
from sdk.datachip.formula_chip import pack_formula_bytes
from sdk.datachip.processor import DataChipError


class ApplicationBundles(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix="btg-app-pilot-")
        self.addCleanup(temp.cleanup)
        self.dir=Path(temp.name)
        self.signer=Ed25519PrivateKey.generate()
        self.keys={"btg-release-demo":self.signer.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)}
        self.paths={}
        # Synthetic! Not a real BC trail network, legal-zone or navigation product.
        self.trail=pack_formula_bytes(
            b"SYNTHETIC,BC-DEMO,TRAIL,0.0,0.0,NOT_FOR_NAVIGATION\n"*500,
            self.dir/"shared-trail.edcf")
        self.trail_path=self.dir/"shared-trail.edcf"
        self.trail_sha=hashlib.sha256(self.trail_path.read_bytes()).hexdigest()
        self.paths[self.trail["chip_id"]]=self.trail_path
        self.nav=pack_formula_bytes(b"DEMO-ROUTE-CONTRACT\n"*100,self.dir/"nav.edcf")
        self.nav_path=self.dir/"nav.edcf"
        self.paths[self.nav["chip_id"]]=self.nav_path
        self.nav_sha=hashlib.sha256(self.nav_path.read_bytes()).hexdigest()

    def module(self,name,doc,sha,kind,requires=(),data_right="public"):
        return dict(name=name,kind=kind,chip_id=doc["chip_id"],
                    sha256=sha,requires=list(requires),data_right=data_right)

    def bundle(self,app,modules,platforms=None):
        return dict(schema=SCHEMA,app_id=app,release_id="pilot-0.1",
                    signer_id="btg-release-demo",host_abi=1,
                    platforms=platforms or ["ios","windows","android","linux"],
                    modules=modules)

    def verify(self,body,app,platform="ios",paths=None):
        return verify_bundle(sign_bundle(self.signer,body),
                             trusted_bundle_keys=self.keys,expected_app=app,
                             expected_platform=platform,
                             available_chips=self.paths if paths is None else paths)

    def test_one_geographic_chip_serves_huntar_and_hikear(self):
        geo=self.module("trails",self.trail,self.trail_sha,"geographic")
        hunt=self.bundle("HuntAR",[geo])
        hike=self.bundle("HikeAR",[geo])
        for app,body in (("HuntAR",hunt),("HikeAR",hike)):
            result=self.verify(body,app)
            self.assertEqual(result["modules"]["trails"]["chip_id"],self.trail["chip_id"])
            self.assertEqual(result["module_order"],["trails"])
            self.assertTrue(result["publisher_signature_valid"])
            self.assertFalse(result["os_permissions_granted"])
            self.assertFalse(result["native_code_updated"])
        self.assertEqual(len(self.paths),2)  # same geo file; no duplication

    def test_dependency_order_and_rights_locked(self):
        geo=self.module("trails",self.trail,self.trail_sha,"geographic")
        nav=self.module("navigation",self.nav,self.nav_sha,
                        "navigation",requires=["trails"],data_right="grant-required")
        result=self.verify(self.bundle("HuntAR",[nav,geo]),"HuntAR")
        self.assertEqual(result["module_order"],["trails","navigation"])
        self.assertEqual(result["available_public_modules"],["trails"])
        self.assertEqual(result["rights_locked_modules"],["navigation"])
        self.assertTrue(result["requires_separate_rights"])

    def test_tampered_bundle_signature_rejected(self):
        geo=self.module("trails",self.trail,self.trail_sha,"geographic")
        signed=sign_bundle(self.signer,self.bundle("HuntAR",[geo]))
        signed["body"]["release_id"]="pilot-unsafe"
        with self.assertRaises(PermissionError):
            verify_bundle(signed,trusted_bundle_keys=self.keys,
                          expected_app="HuntAR",expected_platform="ios",
                          available_chips=self.paths)

    def test_untrusted_public_key_rejected(self):
        signed=sign_bundle(self.signer,self.bundle("HuntAR",[
            self.module("trails",self.trail,self.trail_sha,"geographic")]))
        with self.assertRaises(PermissionError):
            verify_bundle(signed,trusted_bundle_keys={},
                          expected_app="HuntAR",expected_platform="ios",
                          available_chips=self.paths)

    def test_wrong_host_rejected(self):
        with self.assertRaises(PermissionError):
            self.verify(self.bundle("HuntAR",[
                self.module("trails",self.trail,self.trail_sha,"geographic")]),"HikeAR")
        with self.assertRaises(PermissionError):
            self.verify(self.bundle("HuntAR",[
                self.module("trails",self.trail,self.trail_sha,"geographic")]),"HuntAR","macos")

    def test_tampered_chip_file_rejected(self):
        geo=self.module("trails",self.trail,self.trail_sha,"geographic")
        broken=self.dir/"bad.edcf"
        broken.write_bytes(self.trail_path.read_bytes()+b"ALTERED")
        with self.assertRaises(DataChipError):
            self.verify(self.bundle("HuntAR",[geo]),"HuntAR",
                        paths={self.trail["chip_id"]:broken})

    def test_missing_chip_rejected(self):
        geo=self.module("trails",self.trail,self.trail_sha,"geographic")
        with self.assertRaises(DataChipError):
            self.verify(self.bundle("HuntAR",[geo]),"HuntAR",paths={})

    def test_cycle_and_missing_dependency_rejected(self):
        geo=self.module("trails",self.trail,self.trail_sha,"geographic",requires=["navigation"])
        nav=self.module("navigation",self.nav,self.nav_sha,"navigation",requires=["trails"])
        with self.assertRaises(DataChipError):
            sign_bundle(self.signer,self.bundle("HuntAR",[geo,nav]))
        geo["requires"]=["unknown"]
        with self.assertRaises(DataChipError):
            sign_bundle(self.signer,self.bundle("HuntAR",[geo]))

    def test_bad_host_abi_and_wrong_kind_rejected(self):
        geo=self.module("trails",self.trail,self.trail_sha,"geographic")
        body=self.bundle("HuntAR",[geo])
        body["host_abi"]=2
        with self.assertRaises(DataChipError):
            sign_bundle(self.signer,body)
        body["host_abi"]=1
        geo["kind"]="native_executable"
        with self.assertRaises(DataChipError):
            sign_bundle(self.signer,body)

if __name__=="__main__":
    unittest.main()
