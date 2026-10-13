"""Shard set integrity, authorization, streaming and failure regressions."""
import hashlib
import json
from pathlib import Path
import random
import tempfile
import unittest

from sdk.datachip.shardset import (
    pack_shardset, verify_shardset, export_shardset, SCHEMA
)
from sdk.datachip.processor import DataChipError


class DataChipShardSetTests(unittest.TestCase):
    def setUp(self):
        self.dir=tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.root=Path(self.dir.name)
        self.src=self.root/"original.bin"
        self.package=self.root/"data.edcs"
        self.out=self.root/"reconstructed.bin"

    def _pack(self, data, chunk=1024*1024):
        self.src.write_bytes(data)
        record=pack_shardset(self.src,self.package,shard_bytes=chunk)
        return record

    def test_empty_asset(self):
        record=self._pack(b"")
        self.assertEqual(record["shards"], [])
        self.assertEqual(verify_shardset(self.package)["shards"],0)
        export_shardset(self.package,self.out,authorize=lambda *_: True)
        self.assertEqual(self.out.read_bytes(),b"")

    def test_mixed_five_shards_exact_and_default_deny(self):
        data=(random.Random(17).randbytes(1024*1024) +
              (b"British Columbia trail,water,slope\n"*200000)[:3*1024*1024] +
              b"last")
        manifest=self._pack(data)
        self.assertEqual(len(manifest["shards"]),5)
        proof=verify_shardset(self.package)
        self.assertTrue(proof["integrity_verified"])
        self.assertFalse(proof["rights_authorized"])
        self.assertEqual(proof["source_sha256"],hashlib.sha256(data).hexdigest())
        with self.assertRaises(PermissionError):
            export_shardset(self.package,self.out,authorize=None)
        self.assertFalse(self.out.exists())
        export_shardset(self.package,self.out,authorize=lambda *_: True)
        self.assertEqual(self.out.read_bytes(),data)

    def test_revoke_between_shards_no_output(self):
        self._pack(b"x"*(3*1024*1024+3))
        times=[0]
        def policy(*_):
            times[0]+=1
            return times[0]<3
        with self.assertRaises(PermissionError):
            export_shardset(self.package,self.out,authorize=policy)
        self.assertFalse(self.out.exists())
        self.assertFalse(any(x.name.startswith(".edc-shardset-export-") for x in self.root.iterdir()))

    def test_tamper_shard_fails_and_no_output(self):
        doc=self._pack(random.Random(1).randbytes(2*1024*1024))
        path=self.package/doc["shards"][0]["name"]
        raw=bytearray(path.read_bytes())
        raw[len(raw)//2]^=1
        path.write_bytes(raw)
        with self.assertRaises(DataChipError):
            verify_shardset(self.package)
        with self.assertRaises(DataChipError):
            export_shardset(self.package,self.out,authorize=lambda *_:True)
        self.assertFalse(self.out.exists())

    def test_manifest_traversal_rejected_even_with_updated_root(self):
        doc=self._pack(b"one"*400000)
        doc["shards"][0]["name"]="../external.bin"
        from sdk.datachip.processor import _canon
        doc.pop("root_id")
        doc["root_id"]="edc:shardset:sha256:"+hashlib.sha256(_canon(doc)).hexdigest()
        (self.package/"manifest.json").write_bytes(_canon(doc))
        with self.assertRaises(DataChipError):
            verify_shardset(self.package)

    def test_no_original_mutation_or_replacement(self):
        payload=b"KEEP-ME"*80000
        self._pack(payload)
        self.out.write_bytes(b"PREEXISTING")
        with self.assertRaises(FileExistsError):
            export_shardset(self.package,self.out,authorize=lambda *_:True)
        self.assertEqual(self.out.read_bytes(),b"PREEXISTING")
        self.assertEqual(self.src.read_bytes(),payload)
        with self.assertRaises(FileExistsError):
            pack_shardset(self.src,self.package)

    def test_extra_member_rejected(self):
        self._pack(b"Z"*1024)
        (self.package/"chunks"/"untracked.edcf").write_bytes(b"not authorized")
        with self.assertRaises(DataChipError):
            verify_shardset(self.package)

    def test_invalid_shard_size_fail_no_package(self):
        self.src.write_bytes(b"small")
        for chunk in [False,0,100,3*1024*1024,65*1024*1024]:
            with self.subTest(chunk=chunk):
                with self.assertRaises((ValueError,DataChipError)):
                    pack_shardset(self.src,self.package,shard_bytes=chunk)
        self.assertFalse(self.package.exists())


if __name__=="__main__":
    unittest.main()
