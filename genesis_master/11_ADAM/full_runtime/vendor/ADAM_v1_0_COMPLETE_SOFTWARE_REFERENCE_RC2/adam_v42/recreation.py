from __future__ import annotations

import csv
import hashlib
import io
import json
import mimetypes
import os
import re
import subprocess
import tempfile
import time
import wave
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

import numpy as np
from PIL import Image, UnidentifiedImageError, ImageSequence

from adam_v41.canonical import digest, sha256_bytes
from adam_v41.exact import ExactCodec
from adam_v41.universe import AtomicUniverse, IntegrityError


class RecreationError(RuntimeError):
    pass


@dataclass(frozen=True)
class RecreationArtifact:
    artifact_id: str
    exact_object_id: str
    semantic_root_id: str
    recipe_id: str
    codec_id: str
    media_type: str
    modality: str
    name: str
    content_sha256: str
    size: int
    sequence: int


@dataclass(frozen=True)
class SpawnDemand:
    artifact_id: str
    application_id: str = "generic"
    target_format: str = "auto"
    purpose: str = "consume"
    device_class: str = "general"
    latency_class: str = "normal"
    persist: bool = False
    parameters: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SpawnReceipt:
    spawn_id: str
    artifact_id: str
    application_id: str
    target_format: str
    content_sha256: str
    bytes: int
    materialized_path: str | None
    authoritative: bool
    universe_root_before: str
    universe_root_after: str
    created_ns: int
    released: bool = False


@dataclass(frozen=True)
class ApplicationRecipe:
    application_id: str
    accepted_modalities: tuple[str, ...]
    target_format: str
    constructor: str
    version: int = 1
    field_projection: tuple[str, ...] = ()


class RecreationPolicyModel:
    """Small deterministic categorical Naive Bayes model for demand routing.

    The model learns which representation should be spawned for a demand. It is
    deliberately outside authority: it may choose a constructor, but exact
    recreation and application policy still validate the result.
    """

    def __init__(self) -> None:
        self.labels: list[str] = []
        self.label_counts: dict[str, int] = {}
        self.feature_counts: dict[str, dict[str, dict[str, int]]] = {}
        self.vocab: dict[str, set[str]] = {}
        self.total = 0

    @staticmethod
    def _norm(features: Mapping[str, Any]) -> dict[str, str]:
        return {str(k): str(v).casefold() for k, v in sorted(features.items())}

    def fit(self, examples: Iterable[tuple[Mapping[str, Any], str]]) -> "RecreationPolicyModel":
        rows = [(self._norm(x), str(y)) for x, y in examples]
        if not rows:
            raise RecreationError("training examples required")
        self.total = len(rows)
        self.labels = sorted({label for _, label in rows})
        self.label_counts = {label: 0 for label in self.labels}
        self.feature_counts = {label: {} for label in self.labels}
        self.vocab = {}
        for features, label in rows:
            self.label_counts[label] += 1
            for key, value in features.items():
                self.vocab.setdefault(key, set()).add(value)
                self.feature_counts[label].setdefault(key, {}).setdefault(value, 0)
                self.feature_counts[label][key][value] += 1
        return self

    def predict(self, features: Mapping[str, Any], *, abstain_on_ood: bool = True) -> tuple[str | None, float, bool]:
        if not self.labels:
            raise RecreationError("policy model is not trained")
        x = self._norm(features)
        ood = any(key not in self.vocab or value not in self.vocab[key] for key, value in x.items())
        if ood and abstain_on_ood:
            return None, 0.0, True
        scores: dict[str, float] = {}
        import math
        for label in self.labels:
            score = math.log((self.label_counts[label] + 1) / (self.total + len(self.labels)))
            for key, value in x.items():
                values = max(1, len(self.vocab.get(key, {value})))
                count = self.feature_counts[label].get(key, {}).get(value, 0)
                score += math.log((count + 1) / (self.label_counts[label] + values))
            scores[label] = score
        ordered = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
        best, best_score = ordered[0]
        if len(ordered) == 1:
            return best, 1.0, ood
        margin = best_score - ordered[1][1]
        confidence = 1.0 / (1.0 + math.exp(-margin))
        return best, confidence, ood

    def evaluate(self, examples: Iterable[tuple[Mapping[str, Any], str]]) -> dict[str, Any]:
        rows = list(examples)
        correct = 0
        abstained = 0
        for features, expected in rows:
            predicted, _, ood = self.predict(features, abstain_on_ood=False)
            correct += int(predicted == expected)
            abstained += int(ood)
        return {
            "examples": len(rows),
            "correct": correct,
            "accuracy": correct / max(1, len(rows)),
            "ood_feature_rows": abstained,
        }

    def record(self) -> dict[str, Any]:
        return {
            "format": "ADAM-v0.42-recreation-demand-policy",
            "labels": self.labels,
            "label_counts": self.label_counts,
            "feature_counts": self.feature_counts,
            "vocab": {key: sorted(values) for key, values in self.vocab.items()},
            "total": self.total,
        }

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "RecreationPolicyModel":
        model = cls()
        model.labels = list(record["labels"])
        model.label_counts = {str(k): int(v) for k, v in record["label_counts"].items()}
        model.feature_counts = {
            str(label): {
                str(key): {str(value): int(count) for value, count in values.items()}
                for key, values in features.items()
            }
            for label, features in record["feature_counts"].items()
        }
        model.vocab = {str(key): set(map(str, values)) for key, values in record["vocab"].items()}
        model.total = int(record["total"])
        return model


class LivingRecreationCenter:
    """Demand-driven exact and semantic recreation fabric.

    Durable authority consists of reusable atoms, bonds, compounds and recipes.
    Conventional files, messages, device envelopes and application objects are
    spawned only when requested and remain disposable projections.
    """

    INDEX_FORMAT = "ADAM-v0.42-derived-recreation-index"

    def __init__(self, root: Path | str, universe: AtomicUniverse | None = None, *, capability: object | None = None):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.universe = universe or AtomicUniverse(self.root / "universe")
        if capability is None:
            capability = self.universe.enable_commit_guard()
        self.capability = capability
        self.exact = ExactCodec(self.universe, capability=capability)
        self.materialized = self.root / "spawned"
        self.materialized.mkdir(exist_ok=True)
        self.index_path = self.root / "derived_index.json"
        self.event_path = self.root / "spawn_events.ndjson"
        self.recipes_path = self.root / "application_recipes.json"
        self.policy_path = self.root / "demand_policy.json"
        self._index: dict[str, dict[str, Any]] = {}
        self._recipes: dict[str, ApplicationRecipe] = {}
        self.policy: RecreationPolicyModel | None = None
        self._load_or_rebuild_index()
        self._load_recipes()
        if self.policy_path.exists():
            self.policy = RecreationPolicyModel.from_record(json.loads(self.policy_path.read_text(encoding="utf-8")))

    @staticmethod
    def classify(media_type: str, name: str, payload: bytes) -> str:
        mt = media_type.casefold()
        suffix = Path(name).suffix.casefold()
        if mt in {"application/json", "application/ld+json"} or suffix == ".json":
            try:
                value = json.loads(payload.decode("utf-8"))
                if isinstance(value, dict):
                    keys = {str(k).casefold() for k in value}
                    if {"sensors", "actuators"} & keys or {"joints", "motors", "pose"} & keys:
                        return "robotics"
                    if {"device_id", "sensor_id", "telemetry", "measurements"} & keys:
                        return "iot"
            except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
                return "structured"
            return "structured"
        if mt.startswith("image/"):
            if mt in {"image/gif", "image/webp"}:
                try:
                    image = Image.open(io.BytesIO(payload))
                    if getattr(image, "n_frames", 1) > 1:
                        return "video"
                except (UnidentifiedImageError, OSError):
                    return "image"
            return "image"
        if mt.startswith("video/") or suffix in {".mp4", ".mov", ".mkv", ".webm", ".avi"}:
            return "video"
        if mt.startswith("audio/") or suffix in {".wav", ".mp3", ".flac", ".ogg"}:
            return "audio"
        if suffix in {".py", ".js", ".ts", ".rs", ".c", ".cpp", ".java", ".go"}:
            return "program"
        if mt in {"text/csv", "application/csv"} or suffix == ".csv":
            return "tabular"
        if mt.startswith("text/") or suffix in {".md", ".txt", ".xml", ".html"}:
            return "document"
        if mt in {"application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}:
            return "document"
        return "binary"

    @staticmethod
    def _basic_features(payload: bytes, media_type: str, name: str) -> dict[str, Any]:
        return {
            "name": name,
            "media_type": media_type,
            "bytes": len(payload),
            "sha256": sha256_bytes(payload),
            "prefix_hex": payload[:16].hex(),
        }

    @classmethod
    def analyze(cls, payload: bytes, media_type: str, name: str, modality: str) -> dict[str, Any]:
        features = cls._basic_features(payload, media_type, name)
        if modality in {"structured", "iot", "robotics"}:
            value = json.loads(payload.decode("utf-8"))
            features.update({
                "json_type": type(value).__name__,
                "top_level_keys": sorted(map(str, value.keys())) if isinstance(value, dict) else [],
                "item_count": len(value) if hasattr(value, "__len__") else 1,
                "canonical_value": value,
            })
        elif modality == "tabular":
            rows = list(csv.reader(io.StringIO(payload.decode("utf-8-sig"))))
            features.update({"rows": len(rows), "columns": max((len(row) for row in rows), default=0), "headers": rows[0] if rows else [], "table": rows})
        elif modality in {"document", "program"} and (media_type.startswith("text/") or Path(name).suffix.casefold() in {".md", ".txt", ".py", ".js", ".ts", ".rs", ".c", ".cpp", ".java", ".go", ".xml", ".html"}):
            text = payload.decode("utf-8")
            tokens = re.findall(r"[\w'-]+", text, flags=re.UNICODE)
            features.update({"encoding": "utf-8", "characters": len(text), "lines": text.count("\n") + 1, "tokens": len(tokens), "unique_tokens": len(set(t.casefold() for t in tokens))})
            if modality == "program":
                features["language"] = Path(name).suffix.casefold().lstrip(".") or "unknown"
        elif modality == "image":
            image = Image.open(io.BytesIO(payload)).convert("RGB")
            arr = np.asarray(image, dtype=np.float32)
            features.update({"width": image.width, "height": image.height, "mode": "RGB", "mean_rgb": [round(float(x), 6) for x in arr.mean(axis=(0, 1))]})
        elif modality == "video":
            if media_type == "image/gif" or Path(name).suffix.casefold() == ".gif":
                image = Image.open(io.BytesIO(payload))
                durations = [frame.info.get("duration", 0) for frame in ImageSequence.Iterator(image)]
                features.update({"container": "gif", "frames": getattr(image, "n_frames", 1), "width": image.width, "height": image.height, "duration_ms": sum(durations)})
            else:
                features.update(cls._ffprobe(payload, Path(name).suffix or ".bin"))
        elif modality == "audio" and (media_type in {"audio/wav", "audio/x-wav"} or Path(name).suffix.casefold() == ".wav"):
            with wave.open(io.BytesIO(payload), "rb") as wav:
                features.update({"channels": wav.getnchannels(), "sample_rate": wav.getframerate(), "sample_width": wav.getsampwidth(), "frames": wav.getnframes(), "duration_seconds": wav.getnframes() / max(1, wav.getframerate())})
        return features

    @staticmethod
    def _ffprobe(payload: bytes, suffix: str) -> dict[str, Any]:
        path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
                handle.write(payload)
                path = handle.name
            run = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path], capture_output=True, text=True, timeout=10, check=True)
            info = json.loads(run.stdout)
            streams = info.get("streams", [])
            video = next((s for s in streams if s.get("codec_type") == "video"), {})
            return {
                "container": info.get("format", {}).get("format_name", "unknown"),
                "codec": video.get("codec_name", "unknown"),
                "width": int(video.get("width", 0) or 0),
                "height": int(video.get("height", 0) or 0),
                "duration_seconds": float(info.get("format", {}).get("duration", 0) or 0),
                "streams": len(streams),
            }
        except (FileNotFoundError, subprocess.SubprocessError, ValueError, json.JSONDecodeError):
            return {"container": "opaque-video", "codec": "unknown", "streams": 0}
        finally:
            if path:
                try:
                    os.unlink(path)
                except OSError:
                    pass

    def _atomize_semantic(self, value: Any, ops: list[dict[str, Any] | None]) -> str:
        if isinstance(value, Mapping):
            members: list[dict[str, Any]] = []
            for index, key in enumerate(sorted(value, key=lambda item: str(item))):
                key_id, key_op = self.universe.atom_op("semantic_key", str(key))
                ops.append(key_op)
                child = self._atomize_semantic(value[key], ops)
                members.extend([
                    {"role": "key", "order": index * 2, "ref": key_id},
                    {"role": "value", "order": index * 2 + 1, "ref": child},
                ])
            ref, op = self.universe.compound_op("semantic_map", members, {"entries": len(value)})
            ops.append(op)
            return ref
        if isinstance(value, (list, tuple)):
            members = []
            for index, child_value in enumerate(value):
                child = self._atomize_semantic(child_value, ops)
                members.append({"role": "item", "order": index, "ref": child})
            ref, op = self.universe.compound_op("semantic_sequence", members, {"items": len(value)})
            ops.append(op)
            return ref
        ref, op = self.universe.atom_op("semantic_scalar", value, {"value_type": type(value).__name__})
        ops.append(op)
        return ref

    def ingest(self, payload: bytes, *, name: str, media_type: str | None = None) -> RecreationArtifact:
        media_type = media_type or mimetypes.guess_type(name)[0] or "application/octet-stream"
        modality = self.classify(media_type, name, payload)
        exact = self.exact.ingest(payload, media_type=media_type, name=name)
        features = self.analyze(payload, media_type, name, modality)
        ops: list[dict[str, Any] | None] = []
        semantic_root = self._atomize_semantic(features, ops)
        codec_value = {"modality": modality, "media_type": media_type, "codec_version": 1, "fallback": "exact"}
        codec_id, codec_op = self.universe.atom_op("recreation_codec", codec_value)
        ops.append(codec_op)
        artifact_value = {"name": name, "media_type": media_type, "modality": modality, "content_sha256": exact.content_hash, "size": exact.size}
        artifact_id, artifact_op = self.universe.atom_op("recreation_artifact", artifact_value)
        ops.append(artifact_op)
        recipe_members = [
            {"role": "artifact", "order": 0, "ref": artifact_id},
            {"role": "exact", "order": 1, "ref": exact.object_id},
            {"role": "semantic", "order": 2, "ref": semantic_root},
            {"role": "codec", "order": 3, "ref": codec_id},
        ]
        recipe_metadata = {"media_type": media_type, "modality": modality, "content_sha256": exact.content_hash, "size": exact.size, "reconstructable": True}
        recipe_id, recipe_op = self.universe.compound_op("recreation_recipe", recipe_members, recipe_metadata)
        ops.append(recipe_op)
        for predicate, target, metadata in (
            ("EXACTLY_RECREATED_FROM", exact.object_id, {"mandatory": True}),
            ("HAS_SEMANTIC_STRUCTURE", semantic_root, {"evidence": exact.object_id}),
            ("USES_RECREATION_CODEC", codec_id, {"version": 1}),
            ("HAS_RECREATION_RECIPE", recipe_id, {"authoritative": True}),
        ):
            _, bond = self.universe.bond_op(artifact_id, predicate, target, context="AUTHORITY", metadata=metadata)
            ops.append(bond)
        self.universe.commit(ops, metadata={"action": "REGISTER_RECREATION_RECIPE", "modality": modality}, capability=self.capability)
        artifact = RecreationArtifact(artifact_id, exact.object_id, semantic_root, recipe_id, codec_id, media_type, modality, name, exact.content_hash, exact.size, self.universe.sequence)
        self._index[artifact_id] = asdict(artifact)
        self._write_index()
        if self.recreate_exact(artifact_id) != payload:
            raise IntegrityError("recreation recipe failed immediate exact verification")
        return artifact

    def bond(self, source_artifact_id: str, predicate: str, target_artifact_id: str, *, metadata: Mapping[str, Any] | None = None) -> str:
        if source_artifact_id not in self._index or target_artifact_id not in self._index:
            raise RecreationError("artifact bond references unknown artifact")
        bond_id, op = self.universe.bond_op(source_artifact_id, predicate, target_artifact_id, context="SEMANTIC", metadata=dict(metadata or {}))
        self.universe.commit([op], metadata={"action": "BOND_RECREATION_ARTIFACTS", "predicate": predicate}, capability=self.capability)
        return bond_id

    def recreate_exact(self, artifact_id: str) -> bytes:
        artifact = self.artifact(artifact_id)
        payload = self.exact.reconstruct(artifact.exact_object_id)
        if sha256_bytes(payload) != artifact.content_sha256 or len(payload) != artifact.size:
            raise IntegrityError("recreated artifact failed content proof")
        return payload

    def artifact(self, artifact_id: str) -> RecreationArtifact:
        record = self._index.get(artifact_id)
        if record is None:
            self.rebuild_index()
            record = self._index.get(artifact_id)
        if record is None:
            raise KeyError(artifact_id)
        return RecreationArtifact(**record)

    def semantic_features(self, artifact_id: str) -> dict[str, Any]:
        payload = self.recreate_exact(artifact_id)
        artifact = self.artifact(artifact_id)
        return self.analyze(payload, artifact.media_type, artifact.name, artifact.modality)

    def register_application(self, recipe: ApplicationRecipe) -> str:
        if not recipe.application_id or not recipe.accepted_modalities:
            raise RecreationError("application recipe requires id and accepted modalities")
        self._recipes[recipe.application_id] = recipe
        self._write_recipes()
        return digest("ADAM42:APPLICATION_RECIPE", asdict(recipe))

    def train_policy(self, examples: Iterable[tuple[Mapping[str, Any], str]]) -> dict[str, Any]:
        rows = list(examples)
        self.policy = RecreationPolicyModel().fit(rows)
        result = self.policy.evaluate(rows)
        self.policy_path.write_text(json.dumps(self.policy.record(), indent=2, sort_keys=True), encoding="utf-8")
        return result

    def spawn(self, demand: SpawnDemand) -> tuple[bytes, SpawnReceipt]:
        artifact = self.artifact(demand.artifact_id)
        root_before = self.universe.root_hash
        target = demand.target_format
        recipe = self._recipes.get(demand.application_id)
        if recipe and artifact.modality not in recipe.accepted_modalities:
            raise RecreationError(
                f"application {demand.application_id} does not accept modality {artifact.modality}"
            )
        if target == "auto":
            if recipe:
                target = recipe.target_format
            elif self.policy:
                predicted, confidence, ood = self.policy.predict({
                    "modality": artifact.modality,
                    "purpose": demand.purpose,
                    "device_class": demand.device_class,
                    "latency_class": demand.latency_class,
                })
                target = predicted or artifact.media_type
                if ood:
                    target = artifact.media_type
            else:
                target = artifact.media_type
        payload = self._construct(artifact, target, demand)
        root_after = self.universe.root_hash
        if root_after != root_before:
            raise IntegrityError("disposable spawning mutated authoritative universe")
        core = {
            "artifact_id": artifact.artifact_id,
            "application_id": demand.application_id,
            "target_format": target,
            "content_sha256": sha256_bytes(payload),
            "bytes": len(payload),
            "root": root_before,
            "parameters": dict(demand.parameters),
        }
        spawn_id = digest("ADAM42:SPAWN", core)
        path: Path | None = None
        if demand.persist:
            suffix = self._suffix(target)
            path = self.materialized / f"{spawn_id}{suffix}"
            path.write_bytes(payload)
        receipt = SpawnReceipt(spawn_id, artifact.artifact_id, demand.application_id, target, core["content_sha256"], len(payload), None if path is None else str(path), False, root_before, root_after, time.time_ns())
        self._append_event({"event": "SPAWNED", "receipt": asdict(receipt), "demand": asdict(demand)})
        return payload, receipt

    def release(self, receipt: SpawnReceipt) -> SpawnReceipt:
        path = Path(receipt.materialized_path) if receipt.materialized_path else None
        if path and path.exists():
            path.unlink()
        released = SpawnReceipt(**{**asdict(receipt), "released": True})
        self._append_event({"event": "RELEASED", "receipt": asdict(released), "released_ns": time.time_ns()})
        return released

    def _construct(self, artifact: RecreationArtifact, target: str, demand: SpawnDemand) -> bytes:
        original = self.recreate_exact(artifact.artifact_id)
        normalized = target.casefold()
        if normalized in {"original", artifact.media_type.casefold(), "application/octet-stream"}:
            return original
        features = self.semantic_features(artifact.artifact_id)
        if normalized in {"application/json", "json", "api-json", "application/ld+json"}:
            if artifact.modality in {"structured", "iot", "robotics"}:
                value = json.loads(original.decode("utf-8"))
            elif artifact.modality == "tabular":
                rows = features.get("table", [])
                headers = rows[0] if rows else []
                value = [dict(zip(headers, row)) for row in rows[1:]]
            else:
                value = {"artifact": asdict(artifact), "features": features}
            projection = tuple(demand.parameters.get("fields", ()))
            if projection and isinstance(value, dict):
                value = {key: value.get(key) for key in projection}
            return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        if normalized in {"text/csv", "csv"}:
            out = io.StringIO(newline="")
            writer = csv.writer(out)
            if artifact.modality == "tabular":
                writer.writerows(features.get("table", []))
            else:
                writer.writerow(["field", "value"])
                for key, value in sorted(features.items()):
                    writer.writerow([key, json.dumps(value, ensure_ascii=False, sort_keys=True)])
            return out.getvalue().encode("utf-8")
        if normalized in {"text/plain", "text", "markdown"}:
            if artifact.modality in {"document", "program"}:
                return original
            return json.dumps(features, indent=2, ensure_ascii=False, sort_keys=True).encode("utf-8")
        if normalized in {"image/png", "png", "image/jpeg", "jpeg", "jpg", "image/webp", "webp"}:
            if artifact.modality != "image":
                raise RecreationError("image target requires image artifact")
            image = Image.open(io.BytesIO(original))
            out = io.BytesIO()
            fmt = {"image/png": "PNG", "png": "PNG", "image/jpeg": "JPEG", "jpeg": "JPEG", "jpg": "JPEG", "image/webp": "WEBP", "webp": "WEBP"}[normalized]
            image.convert("RGB").save(out, format=fmt)
            return out.getvalue()
        if normalized in {"application/x-adam-video-manifest+json", "video-manifest"}:
            if artifact.modality != "video":
                raise RecreationError("video manifest requires video artifact")
            return json.dumps({"artifact": asdict(artifact), "features": features, "exact_recreatable": True}, sort_keys=True, separators=(",", ":")).encode("utf-8")
        if normalized in {"application/x-adam-iot-telemetry+json", "iot-telemetry"}:
            if artifact.modality not in {"iot", "structured"}:
                raise RecreationError("IoT telemetry target requires structured artifact")
            source = json.loads(original.decode("utf-8"))
            envelope = {"protocol": "ADAM-IOT-1", "device": source.get("device_id", source.get("sensor_id", "unknown")), "telemetry": source, "provenance": artifact.recipe_id}
            return json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode("utf-8")
        if normalized in {"application/x-adam-robot-command+json", "robot-command"}:
            command = dict(demand.parameters.get("command", {}))
            if not command:
                raise RecreationError("robot command demand requires parameters.command")
            envelope = {"protocol": "ADAM-ROBOT-1", "capability_artifact": artifact.artifact_id, "command": command, "provenance": artifact.recipe_id}
            return json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode("utf-8")
        if normalized in {"application/x-adam-semantic-manifest+json", "semantic-manifest"}:
            return json.dumps({"artifact": asdict(artifact), "features": features, "recipe": artifact.recipe_id}, sort_keys=True, separators=(",", ":")).encode("utf-8")
        raise RecreationError(f"unsupported spawn target: {target}")

    @staticmethod
    def _suffix(target: str) -> str:
        target = target.casefold()
        if "json" in target:
            return ".json"
        if "csv" in target:
            return ".csv"
        if target in {"image/png", "png"}:
            return ".png"
        if target in {"image/jpeg", "jpeg", "jpg"}:
            return ".jpg"
        if target in {"text/plain", "text", "markdown"}:
            return ".txt"
        return ".bin"

    def rebuild_index(self) -> dict[str, dict[str, Any]]:
        rebuilt: dict[str, dict[str, Any]] = {}
        for atom_id, atom in self.universe.atoms.items():
            if atom.kind != "recreation_artifact":
                continue
            bonds = {bond.predicate: bond.target for bond in self.universe.active_bonds(source=atom_id)}
            exact_id = bonds.get("EXACTLY_RECREATED_FROM")
            semantic_id = bonds.get("HAS_SEMANTIC_STRUCTURE")
            codec_id = bonds.get("USES_RECREATION_CODEC")
            recipe_id = bonds.get("HAS_RECREATION_RECIPE")
            if not all((exact_id, semantic_id, codec_id, recipe_id)):
                continue
            exact = self.universe.compounds.get(str(exact_id))
            if exact is None:
                continue
            rebuilt[atom_id] = asdict(RecreationArtifact(
                atom_id, str(exact_id), str(semantic_id), str(recipe_id), str(codec_id),
                str(atom.value["media_type"]), str(atom.value["modality"]), str(atom.value["name"]),
                str(atom.value["content_sha256"]), int(atom.value["size"]), atom.created_seq,
            ))
        self._index = rebuilt
        self._write_index()
        return rebuilt

    def verify(self) -> dict[str, Any]:
        failures = []
        for artifact_id in sorted(self._index):
            try:
                self.recreate_exact(artifact_id)
            except Exception as exc:
                failures.append({"artifact_id": artifact_id, "error": f"{type(exc).__name__}: {exc}"})
        universe = self.universe.verify()
        return {
            "pass": universe["pass"] and not failures,
            "artifacts": len(self._index),
            "recipes": len(self._recipes),
            "universe": universe,
            "recreation_failures": failures,
            "classification": "living recreation fabric; materializations are disposable",
        }

    def _load_or_rebuild_index(self) -> None:
        if self.index_path.exists():
            try:
                doc = json.loads(self.index_path.read_text(encoding="utf-8"))
                if doc.get("format") == self.INDEX_FORMAT:
                    self._index = dict(doc.get("artifacts", {}))
                    return
            except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError):
                self._index = {}
        self.rebuild_index()

    def _write_index(self) -> None:
        self.index_path.write_text(json.dumps({"format": self.INDEX_FORMAT, "authoritative": False, "artifacts": self._index}, indent=2, sort_keys=True), encoding="utf-8")

    def _load_recipes(self) -> None:
        if not self.recipes_path.exists():
            return
        doc = json.loads(self.recipes_path.read_text(encoding="utf-8"))
        self._recipes = {key: ApplicationRecipe(**value) for key, value in doc.get("recipes", {}).items()}

    def _write_recipes(self) -> None:
        self.recipes_path.write_text(json.dumps({"format": "ADAM-v0.42-application-recipe-registry", "recipes": {key: asdict(value) for key, value in self._recipes.items()}}, indent=2, sort_keys=True), encoding="utf-8")

    def _append_event(self, event: Mapping[str, Any]) -> None:
        with self.event_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True, default=str) + "\n")
