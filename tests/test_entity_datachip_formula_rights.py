"""Experimental v0.2: formula-native fidelity, bounded DAG and delegated rights."""
from __future__ import annotations
from pathlib import Path
import hashlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
import zipfile

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO))
from sdk.datachip import formula_chip as fc
from sdk.datachip import rights
from sdk.datachip.processor import DataChipError,_canon,_zipinfo


class FormulaTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root=Path(t.name)
        self.chip=self.root/"data.edcf"

    def test_repeat_is_formula_native_and_smaller_than_raw(self):
        raw=b"BC-TRAIL-01|"*16000
        doc=fc.pack_formula_bytes(raw,self.chip)
        self.assertTrue(fc.verify_formula(self.chip)["formula_native"])
        self.assertIn("REPEAT",[n["op"] for n in doc["nodes"]])
        self.assertLess(self.chip.stat().st_size,len(raw))
        target=self.root/"export.bin"
        fc.export_formula(self.chip,target,authorize=lambda *_:True)
        self.assertEqual(target.read_bytes(),raw)

    def test_entropy_is_retained_for_incompressible_data(self):
        raw=os.urandom(150000)
        doc=fc.pack_formula_bytes(raw,self.chip)
        self.assertTrue(any(n["op"]=="ENTROPY" for n in doc["nodes"]))
        self.assertEqual(fc.verify_formula(self.chip)["content_sha256"],hashlib.sha256(raw).hexdigest())
        self.assertGreaterEqual(self.chip.stat().st_size,len(raw))

    def test_empty_and_single_atom(self):
        for raw in (b"",b"Z"):
            path=self.root/("empty" if not raw else "one")
            fc.pack_formula_bytes(raw,path)
            self.assertTrue(fc.verify_formula(path)["integrity_verified"])
            out=self.root/("restored-empty" if not raw else "restored-one")
            fc.export_formula(path,out,authorize=lambda *_:True)
            self.assertEqual(out.read_bytes(),raw)

    def test_deterministic_file(self):
        a=b"ABC"*10000
        fc.pack_formula_bytes(a,self.root/"a")
        fc.pack_formula_bytes(a,self.root/"b")
        self.assertEqual((self.root/"a").read_bytes(),(self.root/"b").read_bytes())

    def test_no_unauthorized_extract(self):
        fc.pack_formula_bytes(b"TOP-SECRET"*20,self.chip)
        dest=self.root/"no-file"
        with self.assertRaises(PermissionError):
            fc.export_formula(self.chip,dest,authorize=None)
        self.assertFalse(dest.exists())
        with self.assertRaises(PermissionError):
            fc.export_formula(self.chip,dest,authorize=lambda *_:False)
        self.assertFalse(dest.exists())

    def _alter(self, src:Path, dst:Path, mod):
        with zipfile.ZipFile(src) as zi,zipfile.ZipFile(dst,"w") as zo:
            for entry in zi.infolist():
                body=zi.read(entry.filename)
                zo.writestr(entry,mod(entry.filename,body))

    def test_mutated_entropy_detected_and_no_output_leak(self):
        fc.pack_formula_bytes(b"heterogeneous-one-2-3-4-5",self.chip)
        broken=self.root/"broken"
        self._alter(self.chip,broken,lambda name,data: b"\x00"*len(data) if name.startswith("entropy/") else data)
        with self.assertRaises(DataChipError):
            fc.verify_formula(broken)
        target=self.root/"target"
        with self.assertRaises(DataChipError):
            fc.export_formula(broken,target,authorize=lambda *_:True)
        self.assertFalse(target.exists())

    def test_missing_entropy_fails_closed(self):
        fc.pack_formula_bytes(b"nondeterministic-data-stream",self.chip)
        missing=self.root/"missing"
        with zipfile.ZipFile(self.chip) as zi,zipfile.ZipFile(missing,"w") as zo:
            for entry in zi.infolist():
                if entry.filename=="manifest.json":
                    zo.writestr(entry,zi.read(entry.filename))
        with self.assertRaises(DataChipError):
            fc.verify_formula(missing)

    def test_expansion_bomb_rejected(self):
        fc.pack_formula_bytes(b"ABC"*80,self.chip)
        bad=self.root/"bad"
        def edit(name,data):
            if name!="manifest.json":
                return data
            doc=json.loads(data)
            for node in doc["nodes"]:
                if node["op"]=="REPEAT":
                    node["count"]=1000000000
                    node["bytes"]=1000000000*3
            doc["chip_id"]="edc:formula:sha256:"+fc._sha(_canon({k:v for k,v in doc.items() if k!="chip_id"}))
            return _canon(doc)
        self._alter(self.chip,bad,edit)
        with self.assertRaises(DataChipError):
            fc.inspect_formula(bad)

    def test_unsupported_opcode_is_not_executable(self):
        fc.pack_formula_bytes(b"ABC"*80,self.chip)
        bad=self.root/"unknown"
        def edit(name,data):
            if name!="manifest.json":return data
            doc=json.loads(data)
            doc["nodes"][0]["op"]="PYTHON_EVAL"
            doc["chip_id"]="edc:formula:sha256:"+fc._sha(_canon({k:v for k,v in doc.items() if k!="chip_id"}))
            return _canon(doc)
        self._alter(self.chip,bad,edit)
        with self.assertRaises(DataChipError):
            fc.inspect_formula(bad)

    def test_offline_btdu_graph_interoperability(self):
        spec=importlib.util.spec_from_file_location(
            "edc_v2_btdu_kernel",REPO/"src"/"40_BTDU"/"formula_kernel.py")
        module=importlib.util.module_from_spec(spec)
        sys.modules[spec.name]=module
        spec.loader.exec_module(module)
        kernel=module.BTDUFormulaKernel(self.root/"kernel",
                                       min_chunk=16384,avg_chunk=65536,max_chunk=262144)
        raw=b"TRAILLINE|"*18000
        try:
            record=kernel.put_bytes(raw)
            doc=fc.pack_formula_from_btdu(kernel,record["formula_object_id"],self.chip)
            self.assertEqual(doc["content_sha256"],hashlib.sha256(raw).hexdigest())
            self.assertEqual(doc["formula_object_ref"],record["formula_object_id"])
        finally:
            kernel.close()
        self.assertTrue(fc.verify_formula(self.chip)["integrity_verified"])
        restored=self.root/"restored"
        fc.export_formula(self.chip,restored,authorize=lambda *_:True)
        self.assertEqual(restored.read_bytes(),raw)


class SignedRightsTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root=Path(t.name)
        self.chip=self.root/"data.edcf"
        self.doc=fc.pack_formula_bytes(b"authorized-btg-geographic-data"*80,self.chip)
        self.signer=Ed25519PrivateKey.generate()
        self.status_signer=Ed25519PrivateKey.generate()
        self.rights_keys={"btg-delegate-1":rights.public_key_bytes(self.signer)}
        self.status_keys={"btg-status-1":rights.public_key_bytes(self.status_signer)}
        self.now=1791820000
        self.grant=rights.issue_grant(self.signer,
                    authority_key_id="btg-delegate-1",
                    chip_id=self.doc["chip_id"],subject="test-user",
                    audience="HuntAR",
                    rights_passport_ref="rp:synthetic:public-trails",
                    not_before=self.now-30,expires_at=self.now+3600)
        self.rev=rights.issue_revocation_snapshot(self.status_signer,
                    authority_key_id="btg-status-1",
                    issued_at=self.now-30,valid_until=self.now+3600,
                    covered_rights_keys=('btg-delegate-1',))

    def verify(self,**changes):
        args=dict(pinned_rights_keys=self.rights_keys,
                  pinned_revocation_keys=self.status_keys,
                  trusted_subject="test-user",trusted_audience="HuntAR",
                  expected_chip_id=self.doc["chip_id"],now=self.now)
        args.update(changes)
        return rights.verify_grant(self.grant,self.rev,**args)

    def test_signed_grant_verifies_with_external_trust_roots(self):
        r=self.verify()
        self.assertTrue(r["issuer_signature_valid"])
        self.assertTrue(r["revocation_signature_valid"])
        self.assertEqual(r["chip_id"],self.doc["chip_id"])

    def test_signed_export_requires_valid_grant(self):
        dest=self.root/"out"
        receipt=rights.authorized_formula_export(
            str(self.chip),str(dest),grant=self.grant,revocations=self.rev,
            pinned_rights_keys=self.rights_keys,
            pinned_revocation_keys=self.status_keys,
            trusted_subject="test-user",trusted_audience="HuntAR",now=self.now)
        self.assertTrue(receipt["signed_delegation_verified"])
        self.assertEqual(dest.read_bytes(),b"authorized-btg-geographic-data"*80)

    def test_signature_tamper_is_rejected(self):
        altered=json.loads(json.dumps(self.grant))
        altered["body"]["rights_passport_ref"]="rp:synthetic:admin"
        with self.assertRaises(PermissionError):
            rights.verify_grant(altered,self.rev,
                pinned_rights_keys=self.rights_keys,
                pinned_revocation_keys=self.status_keys,
                trusted_subject="test-user",trusted_audience="HuntAR",
                expected_chip_id=self.doc["chip_id"],now=self.now)

    def test_wrong_app_user_and_chip_rejected(self):
        for field,wrong in (("trusted_subject","other-user"),
                            ("trusted_audience","SearchAR"),
                            ("expected_chip_id","edc:formula:sha256:"+"a"*64)):
            with self.assertRaises(PermissionError):
                self.verify(**{field:wrong})

    def test_wrong_public_key_rejected(self):
        with self.assertRaises(PermissionError):
            self.verify(pinned_rights_keys={"btg-delegate-1":
                        rights.public_key_bytes(Ed25519PrivateKey.generate())})

    def test_expiration_and_not_before(self):
        with self.assertRaises(PermissionError):
            self.verify(now=self.now+4000)
        with self.assertRaises(PermissionError):
            self.verify(now=self.now-100)

    def test_revocation_and_stale_status(self):
        revoked=rights.issue_revocation_snapshot(self.status_signer,
                    authority_key_id="btg-status-1",
                    issued_at=self.now-20,valid_until=self.now+60,
                    revoked_grant_ids=(self.grant["body"]["grant_id"],),
                    covered_rights_keys=('btg-delegate-1',))
        with self.assertRaises(PermissionError):
            rights.verify_grant(self.grant,revoked,
                    pinned_rights_keys=self.rights_keys,
                    pinned_revocation_keys=self.status_keys,
                    trusted_subject="test-user",trusted_audience="HuntAR",
                    expected_chip_id=self.doc["chip_id"],now=self.now)
        with self.assertRaises(PermissionError):
            self.verify(now=self.now+4000)

    def test_false_int_timestamp_rejected(self):
        with self.assertRaises(DataChipError):
            self.verify(now=True)

if __name__=="__main__":
    unittest.main()
