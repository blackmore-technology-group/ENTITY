"""Freeze and cross-check ENTITY v0.2 DataChip interfaces for BTG consumers."""
import hashlib
import json
from pathlib import Path
import unittest
from sdk.datachip import formula_chip, rights, application

ROOT=Path(__file__).resolve().parents[1]
LOCK=ROOT/"docs"/"architecture"/"BTG_DATACHIP_ALIGNMENT_LOCK_V02.json"
LOCK_DIGEST="8be91b6627c8656b14fc24e33374c8a15261cd1cf90111027afa307df1f9c9b0"

def git_blob_sha(data: bytes):
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

class CrossAppDataChipContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw=LOCK.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=LOCK_DIGEST:
            raise ValueError("ENTITY DataChip alignment contract was modified without coordinated version update")
        cls.contract=json.loads(raw)

    def test_formula_version_and_source_pin(self):
        record=self.contract["edc"]
        self.assertEqual(record["formula_schema"],formula_chip.SCHEMA)
        self.assertEqual(set(record["formula_ops"]),formula_chip.OPS)
        self.assertEqual(record["formula_max_output_bytes"],formula_chip.MAX_OUTPUT)
        self.assertEqual(record["formula_git_blob_sha1"],
              git_blob_sha((ROOT/"sdk"/"datachip"/"formula_chip.py").read_bytes()))

    def test_rights_and_bundle_signatures_are_same_interface(self):
        record=self.contract["edc"]
        self.assertEqual(record["signed_grant_schema"],rights.GRANT_SCHEMA)
        self.assertEqual(record["signed_revocation_schema"],rights.REVOCATION_SCHEMA)
        self.assertEqual(record["application_bundle_schema"],application.SCHEMA)
        self.assertEqual(record["delegated_export_action"],"dataplane:export")

    def test_native_abi_names_and_source_pin(self):
        record=self.contract["native"]
        header=(ROOT/"native"/"datachip_core"/"include"/"entity_datachip.h").read_bytes()
        self.assertEqual(record["c_header_git_blob_sha1"],git_blob_sha(header))
        self.assertTrue(all(symbol.encode() in header for symbol in record["entry_points"]))

    def test_not_a_production_entitlement(self):
        p=self.contract["production_gates"]
        self.assertTrue(p and all(flag is False for flag in p.values()))
        geo=self.contract["geography"]
        self.assertEqual(geo["source_count"],34)
        self.assertFalse(geo["native_ios_chip_mount_verified"])
        self.assertFalse(geo["signed_production_entitlement_verified"])
        self.assertFalse(geo["license_and_safety_currency_qualified"])
        self.assertFalse(self.contract["edc"]["legacy_edc_v01_is_formula_v02"])
if __name__=="__main__":
    unittest.main()
