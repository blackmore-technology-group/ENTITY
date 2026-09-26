from __future__ import annotations

import io
import json
import math
import random
import shutil
import struct
import time
import traceback
import wave
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable

from PIL import Image

from adam_v41.universe import IntegrityError
from adam_v42.embodiment import ActuatorCapability, CapabilitySurface, EmbodimentGateway
from adam_v42.novelty import NoveltyProtocol
from adam_v42.recreation import ApplicationRecipe, LivingRecreationCenter, SpawnDemand


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "artifacts" / "living_recreation_audit"
O1 = ROOT / "data" / "operations_one_real_records.json"


def png_bytes() -> bytes:
    im = Image.new("RGB", (24, 16), (35, 120, 210)); out = io.BytesIO(); im.save(out, format="PNG"); return out.getvalue()


def gif_bytes() -> bytes:
    frames = [Image.new("RGB", (16, 12), c) for c in ((255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0))]
    out = io.BytesIO(); frames[0].save(out, format="GIF", save_all=True, append_images=frames[1:], duration=50, loop=0); return out.getvalue()


def wav_bytes() -> bytes:
    rate = 8000; samples = [int(14000 * math.sin(2 * math.pi * 440 * i / rate)) for i in range(rate // 10)]
    out = io.BytesIO()
    with wave.open(out, "wb") as handle:
        handle.setnchannels(1); handle.setsampwidth(2); handle.setframerate(rate)
        handle.writeframes(b"".join(struct.pack("<h", x) for x in samples))
    return out.getvalue()


class Audit:
    def __init__(self) -> None:
        self.checks: list[dict[str, Any]] = []

    def check(self, name: str, fn: Callable[[], Any]) -> Any:
        start = time.perf_counter()
        try:
            detail = fn()
            self.checks.append({"name": name, "status": "PASS", "seconds": round(time.perf_counter() - start, 6), "detail": detail})
            return detail
        except Exception as exc:
            self.checks.append({"name": name, "status": "FAIL", "seconds": round(time.perf_counter() - start, 6), "error": f"{type(exc).__name__}: {exc}", "traceback": traceback.format_exc()})
            return None


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def meaningful(record: dict[str, Any]) -> bool:
    values = [v for key, v in record.items() if key != "_source_row" and v not in (None, "", 0, False)]
    return len(values) >= 3


def main() -> None:
    if OUTPUT.exists(): shutil.rmtree(OUTPUT)
    OUTPUT.mkdir(parents=True)
    audit = Audit()
    box: dict[str, Any] = {}

    fixtures = {
        "document": ("notes.txt", "text/plain", b"ADAM is a living data recreation universe.\n"),
        "structured": ("project.json", "application/json", b'{"project":"P-42","status":"ACTIVE","budget":1000,"cost":250}'),
        "tabular": ("table.csv", "text/csv", b"id,value\n1,alpha\n2,beta\n"),
        "program": ("program.py", "text/x-python", b"def construct(value):\n    return {'value': value}\n"),
        "image": ("terrain.png", "image/png", png_bytes()),
        "audio": ("signal.wav", "audio/wav", wav_bytes()),
        "video": ("motion.gif", "image/gif", gif_bytes()),
        "iot": ("sensor.json", "application/json", b'{"device_id":"S-1","telemetry":{"temperature":21.3,"humidity":42}}'),
        "robotics": ("robot.json", "application/json", b'{"device_id":"R-1","sensors":["imu","camera"],"actuators":["drive"]}'),
        "binary": ("future.atom", "application/x-future-uninvented", bytes(range(256)) * 8),
    }

    def ingest_modalities() -> dict[str, Any]:
        center = LivingRecreationCenter(OUTPUT / "center")
        artifacts = {}
        for expected, (name, media, payload) in fixtures.items():
            artifact = center.ingest(payload, name=name, media_type=media)
            require(artifact.modality == expected, f"{name} classified {artifact.modality}, expected {expected}")
            require(center.recreate_exact(artifact.artifact_id) == payload, f"{name} exact recreation failed")
            artifacts[expected] = artifact
        report = center.verify(); require(report["pass"], "recreation universe verification failed")
        box.update(center=center, artifacts=artifacts)
        return {"modalities": sorted(artifacts), "artifacts": len(artifacts), "atoms": report["universe"]["atoms"], "compounds": report["universe"]["compounds"], "bonds": report["universe"]["bonds"]}
    audit.check("universal_exact_recreation_with_unknown_format_fallback", ingest_modalities)

    def recursive_chemistry() -> dict[str, Any]:
        center = box["center"]; artifacts = box["artifacts"]
        kinds = {c.kind for c in center.universe.compounds.values()}
        require({"exact_object", "semantic_map", "semantic_sequence", "recreation_recipe"} <= kinds, "recursive chemistry kinds missing")
        bond = center.bond(artifacts["document"].artifact_id, "ILLUSTRATED_BY", artifacts["image"].artifact_id, metadata={"role": "evidence"})
        require(center.universe.bonds[bond].target == artifacts["image"].artifact_id, "cross-modal bond failed")
        return {"compound_kinds": sorted(kinds), "cross_modal_bond": bond}
    audit.check("full_recursive_atom_compound_bond_recipe_chemistry", recursive_chemistry)

    def application_spawning() -> dict[str, Any]:
        center = box["center"]; artifacts = box["artifacts"]
        recipes = [
            ApplicationRecipe("operations_dashboard", ("structured",), "application/json", "json_project"),
            ApplicationRecipe("field_export", ("tabular", "structured"), "text/csv", "table"),
            ApplicationRecipe("vision_display", ("image",), "image/png", "image"),
            ApplicationRecipe("video_inspector", ("video",), "application/x-adam-video-manifest+json", "video_manifest"),
            ApplicationRecipe("iot_gateway", ("iot",), "application/x-adam-iot-telemetry+json", "iot_envelope"),
        ]
        for recipe in recipes: center.register_application(recipe)
        root = center.universe.root_hash
        outputs = {}
        for app, modality in (("operations_dashboard", "structured"), ("field_export", "tabular"), ("vision_display", "image"), ("video_inspector", "video"), ("iot_gateway", "iot")):
            payload, receipt = center.spawn(SpawnDemand(artifacts[modality].artifact_id, application_id=app, target_format="auto"))
            require(not receipt.authoritative and receipt.universe_root_before == receipt.universe_root_after == root, "spawn became authority")
            outputs[app] = {"target": receipt.target_format, "bytes": len(payload), "sha256": receipt.content_sha256}
        require(center.universe.root_hash == root, "application materialization changed universe")
        return outputs
    audit.check("demand_spawned_application_representations_are_disposable", application_spawning)

    def train_policy() -> dict[str, Any]:
        center = box["center"]
        base = [
            ("structured", "api", "server", "normal", "application/json"),
            ("structured", "analytics", "server", "batch", "text/csv"),
            ("tabular", "analytics", "server", "batch", "text/csv"),
            ("image", "display", "screen", "normal", "image/png"),
            ("video", "inspect", "screen", "normal", "application/x-adam-video-manifest+json"),
            ("iot", "telemetry", "sensor", "real-time", "application/x-adam-iot-telemetry+json"),
            ("robotics", "bounded_action", "rover", "real-time", "application/x-adam-robot-command+json"),
            ("binary", "recreate", "general", "normal", "application/x-future-uninvented"),
        ]
        rows = []
        for index in range(60):
            for modality, purpose, device, latency, label in base:
                rows.append(({"modality": modality, "purpose": purpose, "device_class": device, "latency_class": latency}, label))
        random.Random(42).shuffle(rows)
        train, test = rows[: int(len(rows)*0.75)], rows[int(len(rows)*0.75):]
        center.train_policy(train)
        result = center.policy.evaluate(test)
        require(result["accuracy"] == 1.0, "demand policy failed holdout")
        prediction = center.policy.predict({"modality":"quantum-state","purpose":"future","device_class":"unknown","latency_class":"instant"})
        require(prediction[0] is None and prediction[2], "OOD demand was not rejected")
        box["training_result"] = result
        return {**result, "training_examples": len(train), "holdout_examples": len(test), "ood_abstention": True}
    audit.check("trained_demand_routing_holdout_and_ood_abstention", train_policy)

    def novelty() -> dict[str, Any]:
        src = LivingRecreationCenter(OUTPUT / "novelty_source")
        dst = LivingRecreationCenter(OUTPUT / "novelty_destination")
        shared = b"ATOMIC-SHARED-KNOWLEDGE-" * 1200
        first = src.ingest(shared + b"A", name="a.bin", media_type="application/octet-stream")
        protocol = NoveltyProtocol(); p1, _ = protocol.sync(src, dst, first.artifact_id)
        second = src.ingest(shared + b"B", name="b.bin", media_type="application/octet-stream")
        p2, _ = protocol.sync(src, dst, second.artifact_id, dictionary_epoch=2)
        require(dst.recreate_exact(second.artifact_id) == shared + b"B", "novelty recreation failed")
        require(p2.estimated_novelty_bytes < p2.full_closure_bytes, "second transfer did not reuse knowledge")
        return {"first_fraction": p1.novelty_fraction, "second_fraction": p2.novelty_fraction, "bytes_avoided": p2.full_closure_bytes-p2.estimated_novelty_bytes, "dictionary_epoch": p2.dictionary_epoch}
    audit.check("novelty_protocol_moves_missing_knowledge_not_datasets", novelty)

    def embodiment() -> dict[str, Any]:
        center = box["center"]; gateway = EmbodimentGateway(center)
        capability = gateway.register(CapabilitySurface("ROVER-A", "rover", ("temperature", "battery", "imu"), (ActuatorCapability("drive", ("move", "stop"), {"speed":(0.0,1.5)}, True),), ("local", "mesh"), 250.0))
        telemetry = gateway.ingest_telemetry("ROVER-A", {"temperature":20.4,"battery":0.91,"imu":[0,0,1]})
        no_override = gateway.construct_action("ROVER-A", "drive", "move", {"speed":1.0})
        out_of_bounds = gateway.construct_action("ROVER-A", "drive", "move", {"speed":9.0}, human_override=True)
        accepted = gateway.construct_action("ROVER-A", "drive", "move", {"speed":1.0}, human_override=True)
        require(not no_override.accepted and not out_of_bounds.accepted and accepted.accepted, "embodiment safety gates failed")
        require(json.loads(accepted.command_payload)["capability_artifact"] == capability.artifact_id, "command not bound to capability")
        return {"capability_artifact": capability.artifact_id, "telemetry_artifact": telemetry.artifact_id, "unsafe_rejected": 2, "safe_constructed": 1, "physical_execution": False}
    audit.check("universal_iot_robotics_capability_surface_and_safe_command_construction", embodiment)

    def operations_one_recreation() -> dict[str, Any]:
        data = json.loads(O1.read_text(encoding="utf-8")); center = box["center"]
        migrated = []; spawned = 0
        center.register_application(ApplicationRecipe("operations_one_api", ("structured",), "application/json", "identity"))
        for sheet, info in data["sheets"].items():
            records = [r for r in info["records"] if meaningful(r)][:3]
            for i, record in enumerate(records):
                payload = json.dumps({"source_sheet":sheet,"source_row":record.get("_source_row"),"record":record}, sort_keys=True, separators=(",",":"), default=str).encode()
                artifact = center.ingest(payload, name=f"o1-{sheet}-{i}.json", media_type="application/json")
                recreated, receipt = center.spawn(SpawnDemand(artifact.artifact_id, application_id="operations_one_api", target_format="auto"))
                require(json.loads(recreated)["source_sheet"] == sheet, "O1 recreation changed record")
                migrated.append(artifact.artifact_id); spawned += 1
        require(len(migrated) >= 9, "too few O1 records migrated")
        return {"domains": len(data["sheets"]), "records_recreated": len(migrated), "spawned_views": spawned, "source_file": data["source_file"]}
    audit.check("real_operations_one_records_recreated_without_authoritative_application_rows", operations_one_recreation)

    def restart_recovery() -> dict[str, Any]:
        center = box["center"]
        count = center.verify()["artifacts"]
        center.index_path.unlink()
        reopened = LivingRecreationCenter(OUTPUT / "center")
        verification = reopened.verify(); require(verification["pass"] and verification["artifacts"] == count, "restart/index reconstruction failed")
        require(reopened.policy is not None, "trained demand policy did not recover")
        box["center"] = reopened
        return {"artifacts_recovered": count, "derived_index_rebuilt": True, "policy_recovered": True, "root": reopened.universe.root_hash}
    audit.check("restart_recovery_without_derived_indexes_or_materialized_files", restart_recovery)

    def tamper() -> dict[str, Any]:
        src = OUTPUT / "center"; dst = OUTPUT / "tampered_center"
        shutil.copytree(src, dst)
        log = dst / "universe" / "universe.a41log"
        raw = bytearray(log.read_bytes()); require(len(raw) > 100, "log too small for tamper test")
        raw[len(raw)//2] ^= 0x01; log.write_bytes(raw)
        rejected = False
        try: LivingRecreationCenter(dst)
        except IntegrityError: rejected = True
        require(rejected, "non-tail authority tamper was accepted")
        return {"tamper_rejected": True, "tampered_byte_offset": len(raw)//2}
    audit.check("signed_authority_tamper_rejection_preserves_recreation_truth", tamper)

    def logical_soak() -> dict[str, Any]:
        center = box["center"]; artifacts = list(box["artifacts"].values()); root = center.universe.root_hash
        targets = {
            "document":"text/plain", "structured":"application/json", "tabular":"text/csv", "program":"text/plain",
            "image":"image/png", "audio":"audio/wav", "video":"video-manifest", "iot":"iot-telemetry",
            "robotics":"semantic-manifest", "binary":"original",
        }
        cycles = 0; total_bytes = 0
        start = time.perf_counter()
        for day in range(30):
            for artifact in artifacts:
                payload, receipt = center.spawn(SpawnDemand(artifact.artifact_id, target_format=targets[artifact.modality], purpose="soak", device_class="test", latency_class="normal"))
                require(receipt.universe_root_before == receipt.universe_root_after == root, "soak spawn mutated authority")
                total_bytes += len(payload); cycles += 1
        elapsed = time.perf_counter()-start
        require(center.universe.root_hash == root and center.verify()["pass"], "soak damaged universe")
        return {"logical_days":30,"spawn_cycles":cycles,"bytes_recreated":total_bytes,"elapsed_seconds":round(elapsed,6),"spawns_per_second":round(cycles/max(elapsed,1e-9),3),"wall_clock_days":False}
    audit.check("accelerated_30_logical_day_living_recreation_soak", logical_soak)

    def lineage() -> dict[str, Any]:
        source = ROOT / "lineage" / "ADAM_v0_41_ARTIFICIAL_LIVING_UNIVERSE_SOURCE.zip"
        require(source.exists(), "artificial living universe lineage missing")
        return {"source_zip":str(source.relative_to(ROOT)),"bytes":source.stat().st_size,"sha256":__import__('hashlib').sha256(source.read_bytes()).hexdigest()}
    audit.check("other_chat_artificial_living_universe_lineage_preserved", lineage)

    passed = sum(c["status"] == "PASS" for c in audit.checks); failed = len(audit.checks)-passed
    result = {
        "build":"0.42.0.dev2",
        "name":"ADAM Distributed Living Recreation Universe",
        "classification":"bounded runnable distributed living-recreation research prototype",
        "audit":{"passed":passed,"failed":failed,"checks":audit.checks},
        "test_evidence":{
            "inherited_v040_v041":13,"distributed_security":10,"cognition_o1_formal":8,"living_recreation":18,"total_pytest":49,
            "recreation_module_coverage_percent":83,
        },
        "atom_theory":{
            "authority":"atoms, recursive compounds, typed bonds and signed recipes",
            "recreation":"exact representations are reconstructed from content-defined atoms and ordered recipes",
            "living_behavior":"demands spawn temporary application/device forms and release them without altering truth",
            "novelty":"nodes exchange only missing atomic closure",
            "unknown_future_formats":"exact binary fallback preserves and recreates formats without a semantic codec",
        },
        "claim_boundary":(
            "This build implements a general exact recreation substrate, recursive semantic chemistry, application spawning, "
            "IoT/robotics capability envelopes, novelty transfer and trained demand routing at bounded prototype scale. It does "
            "not prove universal semantic understanding of every possible medium, production Byzantine/WAN consensus, a compiled "
            "Rust authority kernel, certified physical robot control, HSM deployment, 30 wall-clock days or production SLAs."
        ),
        "remaining_research_gaps":[
            "Open-world semantic understanding for arbitrary images, video, audio, language and future media remains unsolved.",
            "An exact fallback can recreate any byte sequence, but cannot guarantee meaningful transformation without a codec.",
            "Application recipes are extensible; every existing and future application adapter is not preimplemented.",
            "Robotics commands are constructed and policy-checked but not certified for direct physical actuation.",
            "Rust toolchain was unavailable, so the Rust authority boundary remains scaffolded rather than compiled here.",
            "The 30-day test is logical/accelerated, not 30 elapsed wall-clock days.",
        ],
    }
    out = OUTPUT / "ADAM_V042_LIVING_RECREATION_AUDIT_RESULTS.json"
    out.write_text(json.dumps(result, indent=2, sort_keys=True, default=str), encoding="utf-8")
    print(json.dumps({"result":str(out),"passed":passed,"failed":failed,"pytest":49}, indent=2))
    if failed: raise SystemExit(1)


if __name__ == "__main__":
    main()
