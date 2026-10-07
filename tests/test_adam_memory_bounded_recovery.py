from __future__ import annotations
import importlib.util
import os
import pathlib
import struct
import sys
import tempfile
import unittest

REPO=pathlib.Path(__file__).resolve().parents[1]
RECOVERY=REPO/"src"/"11_ADAM"/"full_runtime"/"memory_bounded_recovery.py"

@unittest.skipUnless(os.environ.get("ENTITY_ADAM_V1_ROOT"),"verified ADAM source required")
class MemoryBoundedAdamRecoveryTests(unittest.TestCase):
    def test_large_signed_frame_recovers_with_identical_state(self):
        adam=pathlib.Path(os.environ["ENTITY_ADAM_V1_ROOT"])
        if str(adam) not in sys.path:
            sys.path.insert(0,str(adam))

        spec=importlib.util.spec_from_file_location("test_memory_bounded_recovery",RECOVERY)
        mod=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.install_memory_bounded_recovery(threshold_bytes=1024)

        from adam_v41.universe import AtomicUniverse

        with tempfile.TemporaryDirectory(prefix="adam-memory-bounded-") as td:
            root=pathlib.Path(td)/"universe"
            u=AtomicUniverse(root)
            ops=[]
            # One signed frame well above the test threshold.
            for i in range(400):
                value={"index":i,"payload":("ENTITY-BTDU-%06d-"%i)*20}
                _atom_id,op=u.atom_op("stream-recovery-test",value,{"group":"large-frame"})
                if op is not None:
                    ops.append(op)
            u.commit(ops,metadata={"test":"memory-bounded-recovery"})
            expected={
                "sequence":u.sequence,
                "root_hash":u.root_hash,
                "atoms":len(u.atoms),
                "bonds":len(u.bonds),
                "compounds":len(u.compounds),
            }
            log=root/"universe.a41log"
            with log.open("rb") as fh:
                (frame_len,)=struct.unpack(">I",fh.read(4))
            self.assertGreater(frame_len,1024)

            recovered=AtomicUniverse(root)
            actual={
                "sequence":recovered.sequence,
                "root_hash":recovered.root_hash,
                "atoms":len(recovered.atoms),
                "bonds":len(recovered.bonds),
                "compounds":len(recovered.compounds),
            }
            self.assertEqual(actual,expected)
            self.assertTrue(recovered.verify()["pass"])

    def test_streaming_checkpoint_high_expansion_reopens(self):
        adam=pathlib.Path(os.environ["ENTITY_ADAM_V1_ROOT"])
        if str(adam) not in sys.path:
            sys.path.insert(0,str(adam))

        spec=importlib.util.spec_from_file_location("test_high_expansion_checkpoint",RECOVERY)
        mod=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.install_memory_bounded_recovery(threshold_bytes=1024)

        from adam_v41.universe import AtomicUniverse
        mod.install_streaming_checkpoint(AtomicUniverse)

        with tempfile.TemporaryDirectory(prefix="adam-high-expansion-checkpoint-") as td:
            root=pathlib.Path(td)/"universe"
            u=AtomicUniverse(root)
            ops=[]
            # Highly repetitive metadata makes the signed checkpoint compress very
            # aggressively while its decoded record stream is many MB.
            repeated="ENTITY-BTDU-HIGH-EXPANSION-"*80
            for i in range(12000):
                _atom_id,op=u.atom_op(
                    "high-expansion-test",
                    {"i":i,"payload":repeated},
                    {"group":"checkpoint-expansion","tag":"X"*256},
                )
                if op is not None:
                    ops.append(op)
                if len(ops)>=500:
                    u.commit(ops,metadata={"test":"high-expansion"}); ops=[]
            if ops:
                u.commit(ops,metadata={"test":"high-expansion"})
            expected=(u.sequence,u.root_hash,len(u.atoms))
            receipt=u.compact_authority()
            self.assertEqual(receipt["format"],"ADAM-v0.41-streaming-checkpoint-v2-receipt")
            self.assertEqual((root/"universe.a41log").stat().st_size,0)
            u2=AtomicUniverse(root)
            self.assertEqual((u2.sequence,u2.root_hash,len(u2.atoms)),expected)
            self.assertTrue(u2.verify()["pass"])

    def test_streaming_checkpoint_preserves_root_sequence_and_state(self):
        adam=pathlib.Path(os.environ["ENTITY_ADAM_V1_ROOT"])
        if str(adam) not in sys.path:
            sys.path.insert(0,str(adam))

        spec=importlib.util.spec_from_file_location("test_streaming_checkpoint",RECOVERY)
        mod=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.install_memory_bounded_recovery(threshold_bytes=1024)

        from adam_v41.universe import AtomicUniverse
        mod.install_streaming_checkpoint(AtomicUniverse)

        with tempfile.TemporaryDirectory(prefix="adam-stream-checkpoint-") as td:
            root=pathlib.Path(td)/"universe"
            u=AtomicUniverse(root)
            ops=[]
            for i in range(600):
                _atom_id,op=u.atom_op(
                    "checkpoint-test",
                    {"i":i,"payload":("BTDU-CHECKPOINT-%04d-"%i)*12},
                    {"group":"streaming"},
                )
                if op is not None:
                    ops.append(op)
            u.commit(ops,metadata={"test":"streaming-checkpoint"})
            expected={
                "sequence":u.sequence,
                "root_hash":u.root_hash,
                "atoms":len(u.atoms),
                "bonds":len(u.bonds),
                "compounds":len(u.compounds),
            }
            receipt=u.compact_authority()
            self.assertEqual(receipt["format"],"ADAM-v0.41-streaming-checkpoint-v2-receipt")
            self.assertEqual((root/"universe.a41log").stat().st_size,0)

            recovered=AtomicUniverse(root)
            actual={
                "sequence":recovered.sequence,
                "root_hash":recovered.root_hash,
                "atoms":len(recovered.atoms),
                "bonds":len(recovered.bonds),
                "compounds":len(recovered.compounds),
            }
            self.assertEqual(actual,expected)
            self.assertEqual(recovered.checkpoint_sequence,expected["sequence"])
            self.assertEqual(recovered.checkpoint_root,expected["root_hash"])
            self.assertTrue(recovered.verify()["pass"])

if __name__=="__main__":
    unittest.main()
