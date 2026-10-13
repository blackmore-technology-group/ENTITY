"""C ABI parity verification for native Swift/Windows/NDK integration."""
from __future__ import annotations
import ctypes
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from sdk.datachip.formula_chip import pack_formula_bytes
from sdk.datachip.rights import issue_grant,issue_revocation_snapshot,public_key_bytes

RELEASE=ROOT/"native"/"datachip_core"/"target"/"release"
if os.name=="nt":
    NAME="entity_datachip_native.dll"
elif sys.platform=="darwin":
    NAME="libentity_datachip_native.dylib"
else:
    NAME="libentity_datachip_native.so"

class NativeFFITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        library=RELEASE/NAME
        if not library.is_file():
            raise AssertionError(f"Rust host ABI not built: {library}")
        cls.lib=ctypes.CDLL(str(library))
        cls.formula=cls.lib.entity_edc_verify_formula_v1
        cls.formula.argtypes=[ctypes.c_char_p,ctypes.c_void_p,ctypes.c_size_t]
        cls.formula.restype=ctypes.c_int
        cls.grant=cls.lib.entity_edc_verify_delegation_v1
        cls.grant.argtypes=[ctypes.c_char_p,ctypes.c_void_p,ctypes.c_size_t]
        cls.grant.restype=ctypes.c_int

    def setUp(self):
        tmp=tempfile.TemporaryDirectory(prefix="datac-ffi-")
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)

    def test_formula_c_abi(self):
        src=b"BC-SYNTHETIC|"*2000
        path=self.root/"sample.edcf"
        ref=pack_formula_bytes(src,path)
        response=ctypes.create_string_buffer(8192)
        code=self.formula(str(path).encode(),response,len(response))
        self.assertEqual(code,0)
        doc=json.loads(response.value)
        self.assertTrue(doc["integrity_verified"])
        self.assertEqual(doc["content_sha256"],ref["content_sha256"])
        self.assertFalse(doc["rights_authorized"])
        short=ctypes.create_string_buffer(3)
        self.assertEqual(self.formula(str(path).encode(),short,3),-2)
        self.assertEqual(self.formula(None,response,len(response)),-3)

    def test_signed_delegation_c_abi_and_cross_app_denial(self):
        signer=Ed25519PrivateKey.generate()
        status=Ed25519PrivateKey.generate()
        now=1791820000
        chip_id="edc:formula:sha256:"+"f"*64
        grant=issue_grant(signer,authority_key_id="real-test-signing",
                          chip_id=chip_id,subject="demo-operator",audience="HuntAR",
                          rights_passport_ref="rp:synthetic",
                          not_before=now-1,expires_at=now+200)
        rev=issue_revocation_snapshot(status,authority_key_id="test-rev",
                          issued_at=now-1,valid_until=now+200,
                          covered_rights_keys=("real-test-signing",))
        gp=self.root/"grant.json"
        sp=self.root/"status.json"
        gp.write_text(json.dumps(grant))
        sp.write_text(json.dumps(rev))
        request={"grant_path":str(gp),"revocation_path":str(sp),
                 "rights_key_id":"real-test-signing",
                 "rights_public_hex":public_key_bytes(signer).hex(),
                 "status_key_id":"test-rev",
                 "status_public_hex":public_key_bytes(status).hex(),
                 "chip_id":chip_id,"trusted_subject":"demo-operator",
                 "trusted_audience":"HuntAR","now":now}
        result=ctypes.create_string_buffer(8192)
        code=self.grant(json.dumps(request).encode(),result,len(result))
        self.assertEqual(code,0)
        self.assertTrue(json.loads(result.value)["delegated_claim_verified"])
        request["trusted_audience"]="SearchAR"
        self.assertEqual(self.grant(json.dumps(request).encode(),result,len(result)),-3)

if __name__=="__main__":
    unittest.main()
