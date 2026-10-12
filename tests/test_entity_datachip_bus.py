from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from sdk.datachip.bus import DataChipProcessor, BUS_SCHEMA
from sdk.datachip.processor import DataChipError, pack_stream


class DataChipBusTests(unittest.TestCase):
    def setUp(self):
        td=tempfile.TemporaryDirectory(prefix="edp-bus-")
        self.addCleanup(td.cleanup)
        self.root=Path(td.name)
        self.chip=self.root/"asset.edc"
        pack_stream([b"CONTRACT"],self.chip,rights_passport_ref="unverified:passport")

    def request(self,op,**extra):
        return {"schema":BUS_SCHEMA,"operation":op,"chip":str(self.chip),**extra}

    def test_capabilities(self):
        p=DataChipProcessor()
        c=p.capabilities()
        self.assertFalse(c["rights_verification"])
        self.assertFalse(c["signing"])
        self.assertFalse(c["formula_execution"])
        self.assertEqual(c["operations"],["edc.export","edc.inspect","edc.verify"])

    def test_inspect_and_verify(self):
        p=DataChipProcessor()
        doc=p.dispatch(self.request("edc.inspect"))["result"]
        self.assertEqual(doc["content_bytes"],8)
        outcome=p.dispatch(self.request("edc.verify"))["result"]
        self.assertTrue(outcome["integrity_verified"])
        self.assertFalse(outcome["rights_authorized"])
        self.assertFalse(outcome["issuer_authenticated"])

    def test_export_denied(self):
        p=DataChipProcessor()
        dest=self.root/"denied"
        with self.assertRaises(PermissionError):
            p.dispatch(self.request("edc.export",destination=str(dest)))
        self.assertFalse(dest.exists())

    def test_export_explicit_local_test_policy(self):
        authorized=DataChipProcessor(authorize=lambda action,doc:
                                     action=="dataplane:export" and
                                     doc["content_bytes"]==8)
        dest=self.root/"restored"
        out=authorized.dispatch(self.request("edc.export",destination=str(dest)))
        self.assertEqual(out["result"]["bytes"],8)
        self.assertEqual(dest.read_bytes(),b"CONTRACT")

    def test_unknown_operations_and_fields(self):
        p=DataChipProcessor()
        for op in ("edc.execute","edc.mint","edc.trade","edc.sign","edc.restore"):
            with self.assertRaises(DataChipError):
                p.dispatch(self.request(op))
        with self.assertRaises(DataChipError):
            p.dispatch(self.request("edc.verify",extra="not-permitted"))
        with self.assertRaises(DataChipError):
            p.dispatch({"schema":"future-mutation","operation":"edc.inspect",
                        "chip":str(self.chip)})


if __name__=="__main__":
    unittest.main()
