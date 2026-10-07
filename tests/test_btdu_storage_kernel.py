from __future__ import annotations
import concurrent.futures
import hashlib
import importlib.util
import os
import pathlib
import sqlite3
import tempfile
import tracemalloc
import unittest

REPO=pathlib.Path(__file__).resolve().parents[1]
KERNEL_PATH=REPO/"src"/"40_BTDU"/"storage_kernel.py"

def load_kernel():
    spec=importlib.util.spec_from_file_location("btdu_storage_kernel_test",KERNEL_PATH)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

kmod=load_kernel()

def deterministic_bytes(n:int, salt:bytes=b"BTDU")->bytes:
    out=bytearray()
    i=0
    while len(out)<n:
        out.extend(hashlib.sha256(salt+i.to_bytes(8,"big")).digest())
        i+=1
    return bytes(out[:n])

class BTDUStorageKernelTests(unittest.TestCase):
    def make(self,path,**kwargs):
        return kmod.BTDUStorageKernel(
            path,min_chunk=16*1024,avg_chunk=64*1024,max_chunk=256*1024,
            target_segment_bytes=2*1024*1024,**kwargs)

    def test_exact_roundtrip_and_duplicate_payload_is_single_copy(self):
        with tempfile.TemporaryDirectory(prefix="btdu-store-") as td:
            s=self.make(td)
            data=deterministic_bytes(3*1024*1024)
            a=s.put_bytes(data); before=s.stats()
            b=s.put_bytes(data); after=s.stats()
            self.assertEqual(a["storage_object_id"],b["storage_object_id"])
            self.assertEqual(s.read_all(a["storage_object_id"]),data)
            self.assertEqual(before["unique_chunks"],after["unique_chunks"])
            self.assertEqual(before["segment_bytes"],after["segment_bytes"])
            self.assertEqual(after["payloads"],1)
            self.assertTrue(s.verify(deep=True)["pass"])

    def test_content_defined_chunking_resynchronizes_after_prefix_insertion(self):
        with tempfile.TemporaryDirectory(prefix="btdu-cdc-") as td:
            s=self.make(td)
            base=deterministic_bytes(6*1024*1024,b"base")
            first=s.put_bytes(base)
            chunks_before=s.stats()["unique_chunks"]
            prefix=b"BTDU-PREFIX-INSERT-"*53
            second=s.put_bytes(prefix+base)
            stats=s.stats()
            self.assertNotEqual(first["storage_object_id"],second["storage_object_id"])
            added=stats["unique_chunks"]-chunks_before
            self.assertLess(added,second["chunk_count"]//2+4)
            self.assertGreater(stats["dedup_fraction"],0.30)

    def test_range_reads_cross_chunk_boundaries(self):
        with tempfile.TemporaryDirectory(prefix="btdu-range-") as td:
            s=self.make(td)
            data=deterministic_bytes(2*1024*1024,b"range")
            p=s.put_bytes(data)
            for offset,length in [(0,1),(17,999),(65500,200000),(len(data)-12345,20000),(len(data)+1,10)]:
                self.assertEqual(s.read_range(p["storage_object_id"],offset,length),data[offset:offset+length])

    def test_streaming_file_ingest_is_memory_bounded(self):
        with tempfile.TemporaryDirectory(prefix="btdu-stream-") as td:
            root=pathlib.Path(td)
            src=root/"large.bin"
            block=deterministic_bytes(1024*1024,b"stream")
            with src.open("wb") as f:
                for _ in range(24): f.write(block)
            s=self.make(root/"store")
            tracemalloc.start()
            p=s.put_path(src)
            _,peak=tracemalloc.get_traced_memory()
            tracemalloc.stop()
            self.assertEqual(p["size_bytes"],src.stat().st_size)
            self.assertLess(peak,40*1024*1024)
            out=root/"restored.bin"
            s.materialize(p["storage_object_id"],out)
            self.assertEqual(hashlib.sha256(out.read_bytes()).hexdigest(),hashlib.sha256(src.read_bytes()).hexdigest())

    def test_compression_is_selective_and_lossless(self):
        with tempfile.TemporaryDirectory(prefix="btdu-compress-") as td:
            s=self.make(td)
            data=(b"ENTITY-BTDU-"*65536)
            p=s.put_bytes(data)
            stats=s.stats()
            self.assertLess(stats["stored_chunk_bytes"],stats["unique_raw_chunk_bytes"])
            self.assertEqual(s.read_all(p["storage_object_id"]),data)

    def test_aes256_gcm_at_rest_roundtrip_and_wrong_key_rejected(self):
        with tempfile.TemporaryDirectory(prefix="btdu-enc-") as td:
            key=hashlib.sha256(b"test-key").digest()
            data=deterministic_bytes(1024*1024,b"enc")
            s=self.make(td,encryption_key=key)
            p=s.put_bytes(data)
            self.assertEqual(s.read_all(p["storage_object_id"]),data)
            bad=self.make(td,encryption_key=hashlib.sha256(b"wrong").digest())
            with self.assertRaises(kmod.BTDUStorageIntegrityError):
                bad.read_all(p["storage_object_id"])

    def test_corruption_is_detected(self):
        with tempfile.TemporaryDirectory(prefix="btdu-corrupt-") as td:
            s=self.make(td)
            p=s.put_bytes(deterministic_bytes(1024*1024,b"corrupt"))
            manifest=s.payload_manifest(p["storage_object_id"])
            digest=manifest["chunks"][0]["chunk_sha256"]
            with s._db() as db:
                row=db.execute("""SELECT c.record_offset,c.stored_bytes,se.path
                                  FROM chunks c JOIN segments se ON se.segment_id=c.segment_id
                                  WHERE c.chunk_sha256=?""",(digest,)).fetchone()
            path=s.root/row["path"]
            payload_offset=int(row["record_offset"])+kmod._HEADER.size
            with path.open("r+b") as f:
                f.seek(payload_offset)
                one=f.read(1)
                f.seek(payload_offset)
                f.write(bytes([one[0]^0x01]))
                f.flush(); os.fsync(f.fileno())
            with self.assertRaises(kmod.BTDUStorageIntegrityError):
                s.read_chunk(digest)

    def test_index_can_be_rebuilt_from_segments_and_manifests(self):
        with tempfile.TemporaryDirectory(prefix="btdu-recover-") as td:
            s=self.make(td)
            a=s.put_bytes(deterministic_bytes(2*1024*1024,b"one"))
            b=s.put_bytes(deterministic_bytes(3*1024*1024,b"two"))
            root_before=s.storage_root()
            s.close()
            s2=self.make(td)
            result=s2.recover_index()
            self.assertTrue(result["pass"])
            self.assertEqual(s2.storage_root(),root_before)
            self.assertEqual(hashlib.sha256(s2.read_all(a["storage_object_id"])).hexdigest(),a["content_sha256"])
            self.assertEqual(hashlib.sha256(s2.read_all(b["storage_object_id"])).hexdigest(),b["content_sha256"])

    def test_concurrent_writers_deduplicate_safely(self):
        with tempfile.TemporaryDirectory(prefix="btdu-concurrent-") as td:
            s=self.make(td)
            shared=deterministic_bytes(2*1024*1024,b"shared")
            unique=[deterministic_bytes(512*1024,f"u{i}".encode()) for i in range(8)]
            def worker(i):
                return s.put_bytes(shared+unique[i])
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
                results=list(ex.map(worker,range(8)))
            self.assertEqual(len({r["storage_object_id"] for r in results}),8)
            self.assertTrue(s.verify(deep=True)["pass"])
            stats=s.stats()
            self.assertGreater(stats["dedup_fraction"],0.45)

    def test_delete_is_logical_and_reports_compaction_reclaim(self):
        with tempfile.TemporaryDirectory(prefix="btdu-delete-") as td:
            s=self.make(td)
            p=s.put_bytes(deterministic_bytes(1024*1024,b"delete"))
            result=s.delete_payload(p["storage_object_id"])
            self.assertTrue(result["deleted"])
            self.assertGreater(result["gc"]["reclaimable_chunks"],0)
            self.assertTrue(result["gc"]["segment_compaction_required"])
            with self.assertRaises(KeyError): s.payload_manifest(p["storage_object_id"])

    def test_storage_root_ignores_physical_segment_layout(self):
        data=[deterministic_bytes(1024*1024,b"A"),deterministic_bytes(1024*1024,b"B")]
        with tempfile.TemporaryDirectory(prefix="btdu-root-a-") as a, tempfile.TemporaryDirectory(prefix="btdu-root-b-") as b:
            s1=self.make(a)
            s2=kmod.BTDUStorageKernel(b,min_chunk=16*1024,avg_chunk=64*1024,max_chunk=256*1024,target_segment_bytes=16*1024*1024)
            for item in data:
                s1.put_bytes(item); s2.put_bytes(item)
            self.assertEqual(s1.storage_root(),s2.storage_root())
            self.assertTrue(s1.verify(deep=True)["pass"]); self.assertTrue(s2.verify(deep=True)["pass"])

    def test_atom_tape_recipe_reconstructs_without_payload_object(self):
        with tempfile.TemporaryDirectory(prefix="btdu-atom-recipe-") as td:
            root=pathlib.Path(td)
            src=root/"source.bin"
            data=(b'{"type":"Feature","coordinates":[-118.5,49.0]}\n'*50000)+deterministic_bytes(512*1024,b"tail")
            src.write_bytes(data)
            s=self.make(root/"store")
            recipe=s.put_atom_tape_path(src)
            with s._db() as db:
                payloads=int(db.execute("select count(*) from payloads").fetchone()[0])
            self.assertEqual(payloads,0)
            self.assertFalse(recipe["conventional_payload_object_created"])
            src.unlink()
            out=root/"restored.bin"
            receipt=s.materialize_atom_tape_recipe(recipe,out)
            self.assertTrue(out.is_file())
            self.assertEqual(receipt["sha256"],hashlib.sha256(data).hexdigest())
            self.assertEqual(out.read_bytes(),data)
            self.assertGreater(recipe["chunk_count"],0)

if __name__=="__main__":
    unittest.main()
