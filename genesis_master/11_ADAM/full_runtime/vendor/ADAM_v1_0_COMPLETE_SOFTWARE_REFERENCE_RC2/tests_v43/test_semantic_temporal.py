from __future__ import annotations

import io
import math
import random
import wave
from pathlib import Path

import numpy as np
from PIL import Image

from adam_v41.universe import AtomicUniverse
from adam_v42.perception import MultimodalPerception, PerceptionResult
from adam_v43.semantic_world import default_semantic_system
from adam_v43.temporal_learning import (
    TemporalExample,
    TemporalRegimeModel,
    generate_sensor_corpus,
    operations_one_temporal_examples,
)


def image_bytes(rgb: tuple[int, int, int], size: tuple[int, int] = (32, 32), stripe: bool = False) -> bytes:
    image = Image.new("RGB", size, rgb)
    if stripe:
        for x in range(0, size[0], 4):
            for y in range(size[1]):
                image.putpixel((x, y), tuple(min(255, c + 30) for c in rgb))
    out = io.BytesIO(); image.save(out, format="PNG"); return out.getvalue()


def audio_bytes(frequency: float, amplitude: float = 0.7, rate: int = 8000) -> bytes:
    samples = (np.sin(2 * math.pi * frequency * np.arange(rate) / rate) * amplitude * 32767).astype(np.int16)
    out = io.BytesIO()
    with wave.open(out, "wb") as handle:
        handle.setnchannels(1); handle.setsampwidth(2); handle.setframerate(rate); handle.writeframes(samples.tobytes())
    return out.getvalue()


def test_open_world_semantic_models_are_evidence_linked_and_abstain(tmp_path: Path):
    universe = AtomicUniverse(tmp_path / "universe")
    perception = MultimodalPerception(universe, capability=universe.enable_commit_guard())
    system = default_semantic_system()

    text_samples = []
    for i in range(20):
        text_samples.append((perception.text(f"Project schedule cost forecast number {i}".encode()), "PROJECT_CONTROL"))
        text_samples.append((perception.text(f"Invoice customer purchase order payment {i}".encode()), "COMMERCIAL"))
        text_samples.append((perception.text(f"Equipment inspection safety risk machine {i}".encode()), "EQUIPMENT_SAFETY"))
    system.train("text", text_samples)

    image_samples = []
    for i in range(15):
        image_samples.append((perception.image(image_bytes((220 + i % 10, 20, 20), stripe=i % 2 == 0)), "RED_SCENE"))
        image_samples.append((perception.image(image_bytes((20, 30, 210 + i % 10), stripe=i % 2 == 0)), "BLUE_SCENE"))
    system.train("image", image_samples)

    audio_samples = []
    for i in range(12):
        audio_samples.append((perception.audio(audio_bytes(210 + i)), "LOW_TONE"))
        audio_samples.append((perception.audio(audio_bytes(850 + i)), "HIGH_TONE"))
    system.train("audio", audio_samples)

    program_samples = []
    for i in range(12):
        program_samples.append((perception.program(f"def value_{i}(x):\n    return x + {i}\n".encode()), "LINEAR_PROGRAM"))
        program_samples.append((perception.program(f"def choose_{i}(x):\n    if x > {i}:\n        return x\n    return {i}\n".encode()), "BRANCHING_PROGRAM"))
    system.train("program", program_samples)

    table_samples = []
    for i in range(12):
        table_samples.append((perception.tabular_csv(f"id,value\nA,{i}\nB,{i+1}\n".encode()), "NUMERIC_TABLE"))
        table_samples.append((perception.tabular_csv(f"id,description\nA,alpha{i}\nB,beta{i}\n".encode()), "TEXT_TABLE"))
    system.train("tabular", table_samples)

    checks = [
        (perception.text(b"Project cost schedule change order"), "PROJECT_CONTROL"),
        (perception.image(image_bytes((230, 25, 20), stripe=True)), "RED_SCENE"),
        (perception.audio(audio_bytes(218)), "LOW_TONE"),
        (perception.program(b"def f(x):\n    if <LOCAL_DRIVE>/n        return 1\n    return 0\n"), "BRANCHING_PROGRAM"),
        (perception.tabular_csv(b"id,value\nA,12\nB,13\n"), "NUMERIC_TABLE"),
    ]
    for result, label in checks:
        receipt = system.interpret(result)
        assert not receipt.abstained
        assert receipt.candidates[0].label == label
        assert receipt.evidence_object_id == result.evidence_object_id
        assert receipt.authoritative is False
        assert universe.root_hash

    ood = perception.image(image_bytes((0, 0, 0), size=(512, 8), stripe=True))
    ood_receipt = system.interpret(ood)
    assert ood_receipt.abstained
    assert ood_receipt.ood_score > 1.0

    unknown = system.interpret(PerceptionResult("future_quantum_media", "evidence-x", (), {}, ()))
    assert unknown.abstained and not unknown.candidates

    checkpoint = system.export()
    restored = default_semantic_system()
    restored.import_models(checkpoint)
    restored_receipt = restored.interpret(checks[0][0])
    assert restored_receipt.candidates[0].label == "PROJECT_CONTROL"
    embedded = system.embed_in_universe(perception.alignment)
    assert perception.alignment.verify_claim(embedded["claim_id"])["pass"]
    assert perception.alignment.exact.reconstruct(embedded["evidence_object_id"])


def test_temporal_sensor_learning_and_real_operations_one_event_training():
    corpus = generate_sensor_corpus(seed=43, per_class=160, length=48)
    train = corpus[:512]
    test = corpus[512:]
    model = TemporalRegimeModel().fit(train)
    restored_model = TemporalRegimeModel.from_export(model.export())
    assert restored_model.model_id == model.model_id
    result = restored_model.evaluate(test)
    assert result["accuracy"] >= 0.98
    assert result["abstained"] == 0

    channels = ("temperature", "vibration", "current", "pressure")
    extreme = TemporalExample(channels, tuple((500.0, 50.0, 200.0, -100.0) for _ in range(48)), "UNKNOWN", "adversarial", {})
    assert model.predict(extreme).abstained

    o1 = operations_one_temporal_examples(Path(__file__).parents[1] / "data" / "operations_one_real_records.json")
    assert len(o1) >= 80
    assert {e.label for e in o1} >= {"EVENT_OPEN", "EVENT_ON_TIME"}
    random.Random(43).shuffle(o1)
    train_o1 = o1[:65]
    # Ensure both classes are represented in training.
    if len({x.label for x in train_o1}) < 2:
        train_o1 = o1[::2]
        test_o1 = o1[1::2]
    else:
        test_o1 = o1[65:]
    o1_model = TemporalRegimeModel().fit(train_o1)
    evaluation = o1_model.evaluate(test_o1)
    assert evaluation["accuracy"] >= 0.90
    assert evaluation["by_source"]["operations_one_real_export"]["total"] == len(test_o1)
