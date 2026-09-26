from __future__ import annotations

import datetime as dt
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from adam_v41.canonical import digest


class TemporalLearningError(RuntimeError):
    pass


@dataclass(frozen=True)
class TemporalExample:
    channels: tuple[str, ...]
    samples: tuple[tuple[float, ...], ...]
    label: str
    source: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class TemporalPrediction:
    label: str | None
    confidence: float
    ood_score: float
    abstained: bool
    model_id: str
    feature_digest: str


def _linear_slope(values: np.ndarray) -> float:
    if len(values) < 2:
        return 0.0
    x = np.arange(len(values), dtype=np.float64)
    x -= x.mean()
    y = values - values.mean()
    denominator = float((x * x).sum())
    return float((x * y).sum() / denominator) if denominator else 0.0


def window_features(example: TemporalExample) -> tuple[np.ndarray, tuple[str, ...]]:
    matrix = np.asarray(example.samples, dtype=np.float64)
    if matrix.ndim != 2 or matrix.shape[1] != len(example.channels):
        raise TemporalLearningError("sample shape does not match channels")
    features: list[float] = []
    names: list[str] = []
    for index, channel in enumerate(example.channels):
        values = matrix[:, index]
        finite = values[np.isfinite(values)]
        missing_fraction = 1.0 - len(finite) / max(1, len(values))
        if not len(finite):
            finite = np.asarray([0.0])
        stats = {
            "mean": float(finite.mean()),
            "std": float(finite.std()),
            "min": float(finite.min()),
            "max": float(finite.max()),
            "first": float(finite[0]),
            "last": float(finite[-1]),
            "delta": float(finite[-1] - finite[0]),
            "slope": _linear_slope(finite),
            "missing": missing_fraction,
        }
        for suffix, value in stats.items():
            names.append(f"{channel}.{suffix}")
            features.append(value)
    return np.asarray(features, dtype=np.float64), tuple(names)


@dataclass
class _TemporalClass:
    centroid: np.ndarray
    scale: np.ndarray
    threshold: float
    count: int


class TemporalRegimeModel:
    """Deterministic temporal classifier with explicit novelty rejection."""

    def __init__(self):
        self.feature_names: tuple[str, ...] = ()
        self.classes: dict[str, _TemporalClass] = {}
        self.model_id = ""

    def fit(self, examples: Iterable[TemporalExample]) -> "TemporalRegimeModel":
        grouped: dict[str, list[np.ndarray]] = {}
        rows: list[np.ndarray] = []
        names: tuple[str, ...] | None = None
        for example in examples:
            vector, current_names = window_features(example)
            if names is None:
                names = current_names
            elif names != current_names:
                raise TemporalLearningError("all examples must share a channel contract")
            grouped.setdefault(example.label, []).append(vector)
            rows.append(vector)
        if names is None or len(grouped) < 2:
            raise TemporalLearningError("at least two temporal classes are required")
        self.feature_names = names
        all_rows = np.vstack(rows)
        global_scale = all_rows.std(axis=0)
        global_scale[global_scale < 1e-9] = 1.0
        self.classes = {}
        for label, vectors in sorted(grouped.items()):
            matrix = np.vstack(vectors)
            centroid = matrix.mean(axis=0)
            distances = np.linalg.norm((matrix - centroid) / global_scale, axis=1)
            threshold = max(3.0, float(np.quantile(distances, 0.995)) * 1.75 + 0.5)
            self.classes[label] = _TemporalClass(centroid, global_scale.copy(), threshold, len(vectors))
        payload = {
            "features": self.feature_names,
            "classes": {
                label: {"centroid": c.centroid.round(12).tolist(), "scale": c.scale.round(12).tolist(), "threshold": c.threshold, "count": c.count}
                for label, c in self.classes.items()
            },
        }
        self.model_id = digest("ADAM43:TEMPORAL_MODEL", payload)
        return self

    def predict(self, example: TemporalExample) -> TemporalPrediction:
        if not self.classes:
            raise TemporalLearningError("model is not trained")
        vector, names = window_features(example)
        if names != self.feature_names:
            raise TemporalLearningError("channel contract differs from training")
        ranked: list[tuple[str, float, float]] = []
        for label, cls in self.classes.items():
            distance = float(np.linalg.norm((vector - cls.centroid) / cls.scale))
            ranked.append((label, distance, cls.threshold))
        ranked.sort(key=lambda item: (item[1] / item[2], item[0]))
        label, distance, threshold = ranked[0]
        score = distance / threshold
        abstained = score > 1.0
        confidence = 0.0 if abstained else math.exp(-score)
        return TemporalPrediction(
            None if abstained else label,
            round(float(confidence), 8),
            round(float(score), 8),
            abstained,
            self.model_id,
            digest("ADAM43:TEMPORAL_FEATURES", vector.round(12).tolist()),
        )

    def evaluate(self, examples: Iterable[TemporalExample]) -> dict[str, Any]:
        total = correct = abstained = 0
        by_source: dict[str, dict[str, int]] = {}
        for example in examples:
            prediction = self.predict(example)
            total += 1
            abstained += int(prediction.abstained)
            correct += int(prediction.label == example.label)
            source = by_source.setdefault(example.source, {"total": 0, "correct": 0, "abstained": 0})
            source["total"] += 1
            source["correct"] += int(prediction.label == example.label)
            source["abstained"] += int(prediction.abstained)
        return {
            "model_id": self.model_id,
            "examples": total,
            "correct": correct,
            "accuracy": correct / max(1, total),
            "abstained": abstained,
            "by_source": by_source,
        }

    def export(self) -> dict[str, Any]:
        if not self.classes:
            raise TemporalLearningError("model is not trained")
        return {
            "format": "ADAM-v0.43-temporal-regime-model",
            "feature_names": list(self.feature_names),
            "model_id": self.model_id,
            "classes": {
                label: {
                    "centroid": cls.centroid.tolist(),
                    "scale": cls.scale.tolist(),
                    "threshold": cls.threshold,
                    "count": cls.count,
                }
                for label, cls in sorted(self.classes.items())
            },
        }

    @classmethod
    def from_export(cls, payload: dict[str, Any]) -> "TemporalRegimeModel":
        if payload.get("format") != "ADAM-v0.43-temporal-regime-model":
            raise TemporalLearningError("unsupported temporal model checkpoint")
        model = cls()
        model.feature_names = tuple(payload["feature_names"])
        for label, raw in payload["classes"].items():
            model.classes[label] = _TemporalClass(
                np.asarray(raw["centroid"], dtype=np.float64),
                np.asarray(raw["scale"], dtype=np.float64),
                float(raw["threshold"]),
                int(raw["count"]),
            )
        identity_payload = {
            "features": model.feature_names,
            "classes": {
                label: {"centroid": c.centroid.round(12).tolist(), "scale": c.scale.round(12).tolist(), "threshold": c.threshold, "count": c.count}
                for label, c in model.classes.items()
            },
        }
        model.model_id = str(payload["model_id"])
        if digest("ADAM43:TEMPORAL_MODEL", identity_payload) != model.model_id:
            raise TemporalLearningError("temporal model checkpoint identity mismatch")
        return model


def generate_sensor_corpus(*, seed: int = 43, per_class: int = 1200, length: int = 64) -> list[TemporalExample]:
    rng = np.random.default_rng(seed)
    examples: list[TemporalExample] = []
    channels = ("temperature", "vibration", "current", "pressure")
    x = np.linspace(0.0, 1.0, length)
    for label in ("NORMAL", "HEATING", "BEARING_DEGRADATION", "PRESSURE_LOSS"):
        for index in range(per_class):
            noise = rng.normal(0.0, 1.0, (length, 4))
            base = np.column_stack([
                22.0 + noise[:, 0] * 0.25,
                1.0 + noise[:, 1] * 0.05,
                8.0 + noise[:, 2] * 0.12,
                100.0 + noise[:, 3] * 0.4,
            ])
            if label == "HEATING":
                base[:, 0] += 18.0 * x
                base[:, 2] += 2.5 * x
            elif label == "BEARING_DEGRADATION":
                base[:, 1] += 2.0 * x + 0.35 * np.sin(x * 36.0)
                base[:, 2] += 1.0 * x
            elif label == "PRESSURE_LOSS":
                base[:, 3] -= 32.0 * x
                base[:, 2] += 0.5 * x
            examples.append(TemporalExample(channels, tuple(tuple(float(v) for v in row) for row in base), label, "generated_physical_regime", {"seed": seed, "index": index}))
    rng.shuffle(examples)
    return examples


def _parse_date(value: Any) -> dt.datetime | None:
    if value in (None, "", "None"):
        return None
    if isinstance(value, (int, float)):
        # Excel serial date, using the common 1899-12-30 epoch.
        return dt.datetime(1899, 12, 30) + dt.timedelta(days=float(value))
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y", "%d-%b-%Y", "%Y/%m/%d"):
        try:
            return dt.datetime.strptime(text[:19], fmt)
        except ValueError:
            continue
    try:
        return dt.datetime.fromisoformat(text)
    except ValueError:
        return None


def operations_one_temporal_examples(path: Path | str) -> list[TemporalExample]:
    """Builds a real temporal event corpus from the supplied Operations One export.

    These are real application records, not physical sensor streams. The source label
    remains explicit so evaluations cannot blur that distinction.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    examples: list[TemporalExample] = []
    channels = ("planned_days", "actual_days", "value", "status_code")
    date_pairs = (
        ("Issue Date", "Due Date"), ("Date Raised", "Response Due"),
        ("Notice Sent", "Pricing Due"), ("Bid Due", "Expected Award"),
    )
    for sheet, info in data.get("sheets", {}).items():
        for index, record in enumerate(info.get("records", [])):
            start = end = None
            for start_key, end_key in date_pairs:
                start = _parse_date(record.get(start_key))
                end = _parse_date(record.get(end_key))
                if start and end:
                    break
            if not (start and end):
                continue
            planned = max(0.0, (end - start).total_seconds() / 86400.0)
            response = _parse_date(record.get("Response Date") or record.get("Submitted Date") or record.get("Required Date"))
            actual = max(0.0, ((response or end) - start).total_seconds() / 86400.0)
            numeric_values = []
            for value in record.values():
                try:
                    number = float(value)
                    if math.isfinite(number):
                        numeric_values.append(abs(number))
                except (TypeError, ValueError):
                    pass
            value = float(np.median(numeric_values)) if numeric_values else 0.0
            status_text = " ".join(str(record.get(k, "")) for k in ("Status", "Stage", "Approval Status", "Payment Status")).casefold()
            status_code = 2.0 if any(x in status_text for x in ("late", "overdue", "rejected", "cancelled")) else 1.0 if any(x in status_text for x in ("open", "pending", "submitted", "draft", "issued", "lead", "active")) else 0.0
            label = "EVENT_LATE" if actual > planned * 1.05 or status_code == 2.0 else "EVENT_OPEN" if status_code == 1.0 else "EVENT_ON_TIME"
            # Repeat the event as a small causal trajectory rather than a single row.
            trajectory = []
            for step in np.linspace(0.0, 1.0, 16):
                trajectory.append((planned, actual * step, value, status_code * step))
            examples.append(TemporalExample(channels, tuple(trajectory), label, "operations_one_real_export", {"sheet": sheet, "row": index}))
    return examples


def split_examples(examples: list[TemporalExample], fraction: float = 0.8) -> tuple[list[TemporalExample], list[TemporalExample]]:
    if not 0 < fraction < 1:
        raise ValueError("fraction must be between 0 and 1")
    cutoff = max(1, min(len(examples) - 1, int(len(examples) * fraction)))
    return examples[:cutoff], examples[cutoff:]
