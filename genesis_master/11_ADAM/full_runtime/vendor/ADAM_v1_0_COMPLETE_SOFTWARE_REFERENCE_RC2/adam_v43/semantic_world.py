from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass
from typing import Any, Callable, Iterable, Protocol

import numpy as np

from adam_v41.canonical import digest
from adam_v42.perception import PerceptionResult


class SemanticError(RuntimeError):
    pass


class FeatureAdapter(Protocol):
    modality: str

    def vectorize(self, result: PerceptionResult) -> tuple[np.ndarray, tuple[str, ...]]: ...


@dataclass(frozen=True)
class SemanticCandidate:
    label: str
    confidence: float
    distance: float


@dataclass(frozen=True)
class SemanticReceipt:
    modality: str
    evidence_object_id: str
    model_id: str
    candidates: tuple[SemanticCandidate, ...]
    abstained: bool
    ood_score: float
    ambiguity: bool
    authoritative: bool
    receipt_id: str


class NumericFeatureAdapter:
    def __init__(self, modality: str, keys: Iterable[str]):
        self.modality = modality
        self.keys = tuple(keys)

    @staticmethod
    def _flatten(value: Any) -> list[float]:
        if isinstance(value, bool):
            return [1.0 if value else 0.0]
        if isinstance(value, (int, float)) and math.isfinite(float(value)):
            return [float(value)]
        if isinstance(value, (list, tuple)):
            out: list[float] = []
            for item in value:
                out.extend(NumericFeatureAdapter._flatten(item))
            return out
        return []

    def vectorize(self, result: PerceptionResult) -> tuple[np.ndarray, tuple[str, ...]]:
        if result.modality != self.modality:
            raise SemanticError(f"adapter {self.modality!r} cannot vectorize {result.modality!r}")
        values: list[float] = []
        names: list[str] = []
        for key in self.keys:
            flattened = self._flatten(result.features.get(key))
            if not flattened:
                flattened = [0.0]
            for index, value in enumerate(flattened):
                values.append(value)
                names.append(key if len(flattened) == 1 else f"{key}[{index}]")
        return np.asarray(values, dtype=np.float64), tuple(names)


class TextSemanticAdapter:
    modality = "text"

    def __init__(self, vocabulary: Iterable[str]):
        vocab = sorted({word.casefold() for word in vocabulary if word.strip()})
        if not vocab:
            raise ValueError("vocabulary cannot be empty")
        self.vocabulary = tuple(vocab)

    def vectorize(self, result: PerceptionResult) -> tuple[np.ndarray, tuple[str, ...]]:
        if result.modality != self.modality:
            raise SemanticError("text adapter received non-text result")
        # Perception preserves exact evidence separately. The open-world layer uses only
        # grounded extracted candidates and numeric evidence-linked features.
        token_counts = result.features.get("token_counts", {})
        candidates = " ".join(str(x) for x in result.features.get("title_candidates", ())).casefold()
        counts = [float(token_counts.get(word, candidates.count(word))) for word in self.vocabulary]
        counts.extend([
            float(result.features.get("tokens", 0)),
            float(result.features.get("unique_tokens", 0)),
            float(result.features.get("line_count", 0)),
            float(len(result.features.get("numbers", ()))),
        ])
        names = self.vocabulary + ("tokens", "unique_tokens", "line_count", "number_count")
        return np.asarray(counts, dtype=np.float64), names


@dataclass
class _ClassStats:
    label: str
    centroid: np.ndarray
    scale: np.ndarray
    max_training_distance: float
    count: int


class PrototypeSemanticModel:
    """Deterministic per-modality prototype model with explicit OOD abstention.

    This broadens semantic learning beyond hard-coded codecs while keeping the claim
    boundary precise: it is an evidence-linked classifier, not universal understanding.
    """

    def __init__(self, modality: str, feature_names: tuple[str, ...]):
        self.modality = modality
        self.feature_names = feature_names
        self.classes: dict[str, _ClassStats] = {}
        self.global_scale: np.ndarray | None = None
        self.model_id = ""

    def fit(self, samples: Iterable[tuple[np.ndarray, str]]) -> "PrototypeSemanticModel":
        grouped: dict[str, list[np.ndarray]] = {}
        rows: list[np.ndarray] = []
        for vector, label in samples:
            vector = np.asarray(vector, dtype=np.float64)
            if vector.shape != (len(self.feature_names),):
                raise SemanticError("feature shape mismatch")
            grouped.setdefault(label, []).append(vector)
            rows.append(vector)
        if len(grouped) < 2 or not rows:
            raise SemanticError("at least two labels and one sample per label are required")
        matrix = np.vstack(rows)
        scale = matrix.std(axis=0)
        scale[scale < 1e-9] = 1.0
        self.global_scale = scale
        self.classes = {}
        for label, vectors in sorted(grouped.items()):
            class_matrix = np.vstack(vectors)
            centroid = class_matrix.mean(axis=0)
            distances = np.linalg.norm((class_matrix - centroid) / scale, axis=1)
            # A robust envelope prevents one unstable training sample from making the
            # entire open world appear in-distribution. The field name is preserved
            # for checkpoint compatibility, but stores the 95th-percentile envelope.
            envelope = float(np.quantile(distances, 0.95)) if len(distances) else 0.0
            self.classes[label] = _ClassStats(label, centroid, scale.copy(), envelope, len(vectors))
        payload = {
            "modality": self.modality,
            "features": self.feature_names,
            "classes": {
                label: {
                    "centroid": stats.centroid.round(12).tolist(),
                    "scale": stats.scale.round(12).tolist(),
                    "max_training_distance": round(stats.max_training_distance, 12),
                    "count": stats.count,
                }
                for label, stats in self.classes.items()
            },
        }
        self.model_id = digest("ADAM43:SEMANTIC_MODEL", payload)
        return self

    def predict(self, vector: np.ndarray, *, top_k: int = 3) -> tuple[tuple[SemanticCandidate, ...], bool, float, bool]:
        if not self.classes or self.global_scale is None:
            raise SemanticError("model is not trained")
        vector = np.asarray(vector, dtype=np.float64)
        if vector.shape != (len(self.feature_names),):
            raise SemanticError("feature shape mismatch")
        ranked: list[tuple[str, float, float]] = []
        for label, stats in self.classes.items():
            distance = float(np.linalg.norm((vector - stats.centroid) / stats.scale))
            # Training-envelope threshold plus a minimum geometric margin.
            threshold = max(4.0, stats.max_training_distance * 1.75 + 0.5)
            confidence = math.exp(-distance / max(threshold, 1e-9))
            ranked.append((label, distance, confidence))
        ranked.sort(key=lambda item: (item[1], item[0]))
        best_label, best_distance, _ = ranked[0]
        best_stats = self.classes[best_label]
        best_threshold = max(4.0, best_stats.max_training_distance * 1.75 + 0.5)
        ood_score = best_distance / best_threshold
        abstained = ood_score > 1.0
        # Normalize inverse-distance confidence among returned candidates.
        weights = np.asarray([math.exp(-item[1]) for item in ranked[:top_k]], dtype=np.float64)
        weights = weights / max(float(weights.sum()), 1e-12)
        candidates = tuple(
            SemanticCandidate(label, round(float(weight), 8), round(distance, 8))
            for (label, distance, _), weight in zip(ranked[:top_k], weights)
        )
        ambiguity = len(candidates) > 1 and abs(candidates[0].confidence - candidates[1].confidence) < 0.15
        return candidates, abstained, round(float(ood_score), 8), ambiguity

    def export(self) -> dict[str, Any]:
        if not self.classes:
            raise SemanticError("model is not trained")
        return {
            "format": "ADAM-v0.43-prototype-semantic-model",
            "modality": self.modality,
            "feature_names": list(self.feature_names),
            "model_id": self.model_id,
            "classes": {
                label: {
                    "centroid": stats.centroid.tolist(),
                    "scale": stats.scale.tolist(),
                    "max_training_distance": stats.max_training_distance,
                    "count": stats.count,
                }
                for label, stats in self.classes.items()
            },
        }

    @classmethod
    def from_export(cls, payload: dict[str, Any]) -> "PrototypeSemanticModel":
        if payload.get("format") != "ADAM-v0.43-prototype-semantic-model":
            raise SemanticError("unsupported semantic model checkpoint")
        model = cls(str(payload["modality"]), tuple(payload["feature_names"]))
        for label, raw in payload["classes"].items():
            model.classes[label] = _ClassStats(
                label,
                np.asarray(raw["centroid"], dtype=np.float64),
                np.asarray(raw["scale"], dtype=np.float64),
                float(raw["max_training_distance"]),
                int(raw["count"]),
            )
        model.global_scale = next(iter(model.classes.values())).scale.copy()
        model.model_id = str(payload["model_id"])
        # Recompute the canonical identity to prevent checkpoint substitution.
        identity_payload = {
            "modality": model.modality,
            "features": model.feature_names,
            "classes": {
                label: {
                    "centroid": stats.centroid.round(12).tolist(),
                    "scale": stats.scale.round(12).tolist(),
                    "max_training_distance": round(stats.max_training_distance, 12),
                    "count": stats.count,
                }
                for label, stats in model.classes.items()
            },
        }
        if digest("ADAM43:SEMANTIC_MODEL", identity_payload) != model.model_id:
            raise SemanticError("semantic model checkpoint identity mismatch")
        return model


class OpenWorldSemanticSystem:
    """Registry of evidence-linked modality models with non-authoritative inference."""

    def __init__(self):
        self.adapters: dict[str, FeatureAdapter] = {}
        self.models: dict[str, PrototypeSemanticModel] = {}

    def register_adapter(self, adapter: FeatureAdapter) -> None:
        if adapter.modality in self.adapters:
            raise SemanticError(f"adapter already registered: {adapter.modality}")
        self.adapters[adapter.modality] = adapter

    def train(self, modality: str, samples: Iterable[tuple[PerceptionResult, str]]) -> PrototypeSemanticModel:
        adapter = self.adapters.get(modality)
        if adapter is None:
            raise SemanticError(f"no adapter registered for {modality}")
        vectors: list[tuple[np.ndarray, str]] = []
        feature_names: tuple[str, ...] | None = None
        for result, label in samples:
            vector, names = adapter.vectorize(result)
            if feature_names is None:
                feature_names = names
            elif names != feature_names:
                raise SemanticError("adapter returned unstable feature names")
            vectors.append((vector, label))
        if feature_names is None:
            raise SemanticError("no training samples")
        model = PrototypeSemanticModel(modality, feature_names).fit(vectors)
        self.models[modality] = model
        return model

    def interpret(self, result: PerceptionResult) -> SemanticReceipt:
        adapter = self.adapters.get(result.modality)
        model = self.models.get(result.modality)
        if adapter is None or model is None:
            payload = {
                "modality": result.modality,
                "evidence_object_id": result.evidence_object_id,
                "model_id": "UNAVAILABLE",
                "abstained": True,
                "reason": "NO_TRAINED_MODEL",
            }
            return SemanticReceipt(
                result.modality, result.evidence_object_id, "UNAVAILABLE", (), True, float("inf"), False, False,
                digest("ADAM43:SEMANTIC_RECEIPT", payload),
            )
        vector, names = adapter.vectorize(result)
        if names != model.feature_names:
            raise SemanticError("inference feature contract mismatch")
        candidates, abstained, ood_score, ambiguity = model.predict(vector)
        payload = {
            "modality": result.modality,
            "evidence_object_id": result.evidence_object_id,
            "model_id": model.model_id,
            "candidates": [asdict(x) for x in candidates],
            "abstained": abstained,
            "ood_score": ood_score,
            "ambiguity": ambiguity,
            "authoritative": False,
        }
        return SemanticReceipt(
            result.modality,
            result.evidence_object_id,
            model.model_id,
            candidates,
            abstained,
            ood_score,
            ambiguity,
            False,
            digest("ADAM43:SEMANTIC_RECEIPT", payload),
        )

    def export(self) -> dict[str, Any]:
        return {
            "format": "ADAM-v0.43-open-world-semantic-system",
            "models": {modality: model.export() for modality, model in sorted(self.models.items())},
        }

    def import_models(self, payload: dict[str, Any]) -> None:
        if payload.get("format") != "ADAM-v0.43-open-world-semantic-system":
            raise SemanticError("unsupported semantic system checkpoint")
        for modality, raw in payload.get("models", {}).items():
            if modality not in self.adapters:
                raise SemanticError(f"checkpoint requires unregistered adapter {modality}")
            self.models[modality] = PrototypeSemanticModel.from_export(raw)

    def embed_in_universe(self, alignment: Any, *, name: str = "adam-v043-semantic-system.json") -> dict[str, Any]:
        payload = json.dumps(self.export(), sort_keys=True, separators=(",", ":")).encode("utf-8")
        evidence = alignment.ingest_evidence(payload, media_type="application/vnd.adam.semantic-model+json", name=name)
        claim = alignment.assert_claim(
            "cognition_model_system",
            {"model_ids": {k: v.model_id for k, v in sorted(self.models.items())}, "format": "ADAM-v0.43-open-world-semantic-system"},
            evidence_object_id=evidence.object_id,
            extractor="adam-v0.43-model-vault",
            confidence=1.0,
            authoritative=True,
        )
        return {"evidence_object_id": evidence.object_id, "claim_id": claim.claim_id, "proof_id": claim.proof_id, "bytes": len(payload)}


def default_semantic_system() -> OpenWorldSemanticSystem:
    system = OpenWorldSemanticSystem()
    system.register_adapter(NumericFeatureAdapter("image", ("width", "height", "mean_rgb", "std_rgb", "edge_energy", "aspect_ratio")))
    system.register_adapter(NumericFeatureAdapter("audio", ("channels", "sample_rate", "duration_seconds", "rms", "zero_crossing_rate", "spectral_centroid_hz")))
    system.register_adapter(NumericFeatureAdapter("program", ("ast_nodes", "branch_points")))
    system.register_adapter(NumericFeatureAdapter("tabular", ("rows", "columns", "nonempty_cells", "numeric_fraction")))
    system.register_adapter(TextSemanticAdapter((
        "project", "invoice", "equipment", "employee", "customer", "safety", "river", "bank",
        "inspection", "purchase", "schedule", "cost", "risk", "change", "order",
    )))
    return system
