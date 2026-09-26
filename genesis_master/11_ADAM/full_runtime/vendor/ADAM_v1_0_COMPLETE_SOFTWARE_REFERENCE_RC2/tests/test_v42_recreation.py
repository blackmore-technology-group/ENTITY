from __future__ import annotations

import io
import json
import math
import struct
import wave
from pathlib import Path

import pytest
from PIL import Image

from adam_v42.embodiment import ActuatorCapability, CapabilitySurface, EmbodimentGateway
from adam_v42.recreation import (
    ApplicationRecipe,
    LivingRecreationCenter,
    RecreationError,
    RecreationPolicyModel,
    SpawnDemand,
)


def png_bytes() -> bytes:
    image = Image.new("RGB", (12, 8), (25, 100, 210))
    out = io.BytesIO(); image.save(out, format="PNG")
    return out.getvalue()


def gif_bytes() -> bytes:
    frames = [Image.new("RGB", (8, 6), color) for color in ((255, 0, 0), (0, 255, 0), (0, 0, 255))]
    out = io.BytesIO(); frames[0].save(out, format="GIF", save_all=True, append_images=frames[1:], duration=40, loop=0)
    return out.getvalue()


def wav_bytes() -> bytes:
    rate = 8000
    samples = [int(16000 * math.sin(2 * math.pi * 440 * i / rate)) for i in range(rate // 20)]
    out = io.BytesIO()
    with wave.open(out, "wb") as handle:
        handle.setnchannels(1); handle.setsampwidth(2); handle.setframerate(rate)
        handle.writeframes(b"".join(struct.pack("<h", sample) for sample in samples))
    return out.getvalue()


@pytest.mark.parametrize("name,media,payload,modality", [
    ("notes.txt", "text/plain", b"ADAM recreates data on demand.\n", "document"),
    ("state.json", "application/json", b'{"project":"P-1","status":"ACTIVE","cost":12.5}', "structured"),
    ("table.csv", "text/csv", b"id,value\n1,alpha\n2,beta\n", "tabular"),
    ("program.py", "text/x-python", b"def add(a,b):\n    return a+b\n", "program"),
    ("image.png", "image/png", png_bytes(), "image"),
    ("audio.wav", "audio/wav", wav_bytes(), "audio"),
    ("clip.gif", "image/gif", gif_bytes(), "video"),
    ("sensor.json", "application/json", b'{"device_id":"T-1","telemetry":{"temperature":21.2}}', "iot"),
    ("robot.json", "application/json", b'{"device_id":"R-1","sensors":["imu"],"actuators":["drive"]}', "robotics"),
    ("unknown.bin", "application/x-future-format", bytes(range(256)) * 4, "binary"),
])
def test_exact_recreation_across_modalities(tmp_path: Path, name: str, media: str, payload: bytes, modality: str):
    center = LivingRecreationCenter(tmp_path / "center")
    artifact = center.ingest(payload, name=name, media_type=media)
    assert artifact.modality == modality
    assert center.recreate_exact(artifact.artifact_id) == payload
    bonds = {b.predicate for b in center.universe.active_bonds(source=artifact.artifact_id)}
    assert {"EXACTLY_RECREATED_FROM", "HAS_SEMANTIC_STRUCTURE", "USES_RECREATION_CODEC", "HAS_RECREATION_RECIPE"} <= bonds
    assert center.verify()["pass"]


def test_deduplication_and_index_rebuild(tmp_path: Path):
    center = LivingRecreationCenter(tmp_path / "center")
    payload = b"repeated atomic knowledge " * 300
    first = center.ingest(payload, name="a.bin", media_type="application/octet-stream")
    seq = center.universe.sequence
    second = center.ingest(payload, name="a.bin", media_type="application/octet-stream")
    assert first.artifact_id == second.artifact_id
    assert first.exact_object_id == second.exact_object_id
    assert center.universe.sequence == seq
    center.index_path.unlink()
    reopened = LivingRecreationCenter(tmp_path / "center")
    assert reopened.recreate_exact(first.artifact_id) == payload
    assert first.artifact_id in reopened.rebuild_index()


def test_spawn_release_and_authority_separation(tmp_path: Path):
    center = LivingRecreationCenter(tmp_path / "center")
    artifact = center.ingest(b'{"id":1,"name":"alpha","value":7}', name="item.json", media_type="application/json")
    root = center.universe.root_hash
    payload, receipt = center.spawn(SpawnDemand(artifact.artifact_id, target_format="application/json", persist=True))
    assert json.loads(payload) == {"id": 1, "name": "alpha", "value": 7}
    assert receipt.authoritative is False
    assert receipt.universe_root_before == receipt.universe_root_after == root
    assert Path(receipt.materialized_path).exists()
    released = center.release(receipt)
    assert released.released
    assert not Path(receipt.materialized_path).exists()
    assert center.universe.root_hash == root


def test_application_recipe_and_trained_demand_policy(tmp_path: Path):
    center = LivingRecreationCenter(tmp_path / "center")
    center.register_application(ApplicationRecipe("dashboard", ("structured",), "application/json", "json_project"))
    artifact = center.ingest(b'{"project":"P-7","status":"ACTIVE"}', name="project.json", media_type="application/json")
    payload, receipt = center.spawn(SpawnDemand(artifact.artifact_id, application_id="dashboard", target_format="auto"))
    assert receipt.target_format == "application/json"
    assert json.loads(payload)["project"] == "P-7"

    examples = []
    for modality, purpose, device, latency, label in [
        ("structured", "api", "server", "normal", "application/json"),
        ("structured", "analytics", "server", "batch", "text/csv"),
        ("image", "display", "screen", "normal", "image/png"),
        ("video", "inspect", "screen", "normal", "application/x-adam-video-manifest+json"),
        ("iot", "telemetry", "sensor", "real-time", "application/x-adam-iot-telemetry+json"),
    ]:
        for _ in range(20):
            examples.append(({"modality": modality, "purpose": purpose, "device_class": device, "latency_class": latency}, label))
    report = center.train_policy(examples)
    assert report["accuracy"] == 1.0
    label, confidence, ood = center.policy.predict({"modality": "structured", "purpose": "api", "device_class": "server", "latency_class": "normal"})
    assert label == "application/json" and confidence > 0.5 and not ood
    label, _, ood = center.policy.predict({"modality": "future", "purpose": "unknown", "device_class": "quantum", "latency_class": "instant"})
    assert label is None and ood


def test_cross_modal_bonding_and_semantic_spawning(tmp_path: Path):
    center = LivingRecreationCenter(tmp_path / "center")
    document = center.ingest(b"Inspection report for equipment EQ-9", name="inspection.txt", media_type="text/plain")
    image = center.ingest(png_bytes(), name="inspection.png", media_type="image/png")
    bond_id = center.bond(document.artifact_id, "ILLUSTRATED_BY", image.artifact_id, metadata={"role": "evidence"})
    assert center.universe.bonds[bond_id].target == image.artifact_id
    manifest, receipt = center.spawn(SpawnDemand(image.artifact_id, target_format="semantic-manifest"))
    doc = json.loads(manifest)
    assert doc["artifact"]["artifact_id"] == image.artifact_id
    assert receipt.authoritative is False


def test_video_and_image_derivative_construction(tmp_path: Path):
    center = LivingRecreationCenter(tmp_path / "center")
    video = center.ingest(gif_bytes(), name="clip.gif", media_type="image/gif")
    manifest, _ = center.spawn(SpawnDemand(video.artifact_id, target_format="video-manifest"))
    assert json.loads(manifest)["features"]["frames"] == 3
    image = center.ingest(png_bytes(), name="source.png", media_type="image/png")
    jpeg, _ = center.spawn(SpawnDemand(image.artifact_id, target_format="image/jpeg"))
    assert Image.open(io.BytesIO(jpeg)).format == "JPEG"


def test_embodiment_capability_surface_and_safe_action_bus(tmp_path: Path):
    center = LivingRecreationCenter(tmp_path / "center")
    gateway = EmbodimentGateway(center)
    capability = gateway.register(CapabilitySurface(
        "ROVER-1", "rover", ("temperature", "battery"),
        (ActuatorCapability("drive", ("move", "stop"), {"speed": (0.0, 1.5)}, requires_human_override=True),),
        ("local", "mesh"), 250.0,
    ))
    telemetry = gateway.ingest_telemetry("ROVER-1", {"temperature": 22.1, "battery": 0.85})
    assert telemetry.modality == "iot"
    denied = gateway.construct_action("ROVER-1", "drive", "move", {"speed": 1.0}, human_override=False)
    assert not denied.accepted and "override" in denied.reason
    unsafe = gateway.construct_action("ROVER-1", "drive", "move", {"speed": 9.0}, human_override=True)
    assert not unsafe.accepted and "bounds" in unsafe.reason
    allowed = gateway.construct_action("ROVER-1", "drive", "move", {"speed": 1.0}, human_override=True)
    assert allowed.accepted
    command = json.loads(allowed.command_payload)
    assert command["command"]["device_id"] == "ROVER-1"
    assert command["capability_artifact"] == capability.artifact_id


def test_application_rejects_wrong_modality(tmp_path: Path):
    center = LivingRecreationCenter(tmp_path / "center")
    center.register_application(ApplicationRecipe("vision", ("image",), "image/png", "image"))
    text = center.ingest(b"not an image", name="note.txt", media_type="text/plain")
    with pytest.raises(RecreationError):
        center.spawn(SpawnDemand(text.artifact_id, application_id="vision", target_format="auto"))


def test_novelty_protocol_moves_missing_atoms_not_full_dataset(tmp_path: Path):
    from adam_v42.novelty import NoveltyProtocol

    source = LivingRecreationCenter(tmp_path / "source")
    destination = LivingRecreationCenter(tmp_path / "destination")
    common = (b"COMMON-ATOMIC-CONTEXT-" * 1000)
    first = source.ingest(common + b"FIRST", name="first.bin", media_type="application/octet-stream")
    protocol = NoveltyProtocol()
    first_plan, _ = protocol.sync(source, destination, first.artifact_id)
    assert destination.recreate_exact(first.artifact_id) == common + b"FIRST"
    assert first_plan.estimated_novelty_bytes == first_plan.full_closure_bytes

    second = source.ingest(common + b"SECOND", name="second.bin", media_type="application/octet-stream")
    second_plan = protocol.plan(source, destination, second.artifact_id, dictionary_epoch=2)
    protocol.apply(source, destination, second_plan)
    assert destination.recreate_exact(second.artifact_id) == common + b"SECOND"
    assert second_plan.estimated_novelty_bytes < second_plan.full_closure_bytes
    assert second_plan.novelty_fraction < 1.0
