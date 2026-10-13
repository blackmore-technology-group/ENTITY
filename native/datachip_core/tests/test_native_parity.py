"""Independent Rust CLI interoperability vectors against Python EDC v0.2.

Requires a compiled Rust binary; purposely fails rather than skipping when
the native reader is missing from the dedicated CI build worker.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from sdk.datachip.formula_chip import pack_formula_bytes, verify_formula
from sdk.datachip.rights import (
    issue_grant,issue_revocation_snapshot,public_key_bytes,
)

BIN=ROOT/"native"/"datachip_core"/"target"/"release"/(
    "entity-datachip-verify.exe" if os.name=="nt" else "entity-datachip-verify"
)

class RustParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not BIN.is_file():
            raise AssertionError(f"native Rust verification binary not built: {BIN}")
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix="edc-native-vectors-")
        self.addCleanup(temp.cleanup)
        self.dir=Path(temp.name)
    def run_cli(self,*args,good=True):
        r=subprocess.run([str(BIN),*map(str,args)],capture_output=True,text=True,timeout=30)
        if good:
            self.assertEqual(r.returncode,0,r.stderr)
            return json.loads(r.stdout)
        self.assertNotEqual(r.returncode,0)
        return r.stderr
    def test_empty_repeat_entropy_and_utf8_formula(self):
        for i,payload in enumerate((b"",b"x",
                     b"BC-Trail|"*12000,os.urandom(97000),
                     "Données côtières – Österreich".encode()*500)):
            chip=self.dir/f"sample{i}.edcf"
            info=pack_formula_bytes(payload,chip)
            self.assertTrue(verify_formula(chip)["integrity_verified"])
            parsed=self.run_cli("verify-formula",chip)
            self.assertEqual(parsed["content_sha256"],info["content_sha256"])
            self.assertEqual(parsed["content_bytes"],len(payload))
            self.assertTrue(parsed["native_rust_verifier"])
            self.assertFalse(parsed["rights_authorized"])
    def test_corrupted_entropy_fails_in_rust(self):
        chip=self.dir/"good.edcf"
        pack_formula_bytes(b"ENTROPY-NOT-REPETITION:123456",chip)
        bad=self.dir/"bad.edcf"
        with zipfile.ZipFile(chip) as src,zipfile.ZipFile(bad,"w") as dst:
            for member in src.infolist():
                blob=src.read(member.filename)
                if member.filename.startswith("entropy/"):
                    blob=b"\0"*len(blob)
                dst.writestr(member,blob)
        self.run_cli("verify-formula",bad,good=False)
    def test_valid_delegated_rights_and_app_scope(self):
        signer=Ed25519PrivateKey.generate()
        status=Ed25519PrivateKey.generate()
        now=1791820000
        chip="edc:formula:sha256:"+ "a"*64
        grant=issue_grant(signer,authority_key_id="grant-key-1",
               chip_id=chip,subject="test-principal",audience="HuntAR",
               rights_passport_ref="rp:synthetic",not_before=now-10,
               expires_at=now+500)
        snapshot=issue_revocation_snapshot(status,authority_key_id="rev-key-1",
               issued_at=now-10,valid_until=now+500,
               covered_rights_keys=("grant-key-1",))
        gp=self.dir/"grant.json"
        sp=self.dir/"status.json"
        gp.write_text(json.dumps(grant))
        sp.write_text(json.dumps(snapshot))
        args=["verify-delegated-grant",gp,sp,"grant-key-1",
              public_key_bytes(signer).hex(),"rev-key-1",
              public_key_bytes(status).hex(),chip,"test-principal","HuntAR",now]
        response=self.run_cli(*args)
        self.assertTrue(response["delegated_claim_verified"])
        self.assertFalse(response["full_entity_rights_passport_state_verified"])
        altered=args.copy()
        altered[-2]="HikeAR"
        self.run_cli(*altered,good=False)
        revoked=issue_revocation_snapshot(status,authority_key_id="rev-key-1",
             issued_at=now-10,valid_until=now+500,
             covered_rights_keys=("grant-key-1",),
             revoked_grant_ids=(grant["body"]["grant_id"],))
        sp.write_text(json.dumps(revoked))
        self.run_cli(*args,good=False)
    def test_wrong_schema_fails_in_rust(self):
        chip=self.dir/"good.edcf"
        pack_formula_bytes(b"ABC"*80,chip)
        bad=self.dir/"schema.edcf"
        with zipfile.ZipFile(chip) as src,zipfile.ZipFile(bad,"w") as dst:
            for item in src.infolist():
                raw=src.read(item.filename)
                if item.filename=="manifest.json":
                    doc=json.loads(raw)
                    doc["schema"]="executable-danger"
                    raw=json.dumps(doc,sort_keys=True,separators=(",",":"),
                                   ensure_ascii=False).encode()
                dst.writestr(item,raw)
        self.run_cli("verify-formula",bad,good=False)

if __name__=="__main__":
    unittest.main()
