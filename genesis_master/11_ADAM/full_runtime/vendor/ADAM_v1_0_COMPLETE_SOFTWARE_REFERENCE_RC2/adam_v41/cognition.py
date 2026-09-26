from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from .reactions import ReactionEngine, ReactionIntent

FEATURE_NAMES = (
    "action_assign", "action_release", "equipment_available", "equipment_assigned",
    "project_active", "actor_assign_grant", "actor_release_grant",
    "assignment_matches_project", "location_present",
)
LABEL_NAMES = ("REJECT", "ASSIGNED", "AVAILABLE")
_MODEL_FORMAT = "ADAM-v0.50-safe-decision-table-v1"


@dataclass(frozen=True)
class TrainingReport:
    seed: int
    train_examples: int
    test_examples: int
    epochs: int
    test_accuracy: float
    false_positive_rate: float
    confusion_matrix: list[list[int]]
    exhaustive_accuracy: float
    exhaustive_false_positives: int
    model_path: str | None


class DecisionTableModel:
    """Deterministic learned classifier for the finite v0.41 transition feature space.

    The model learns labels from examples and serializes as validated canonical JSON.
    It intentionally replaces unsafe pickle/scikit-learn persistence while preserving
    the predict/predict_proba interface used by the universe cognition organ.
    """

    def __init__(self, table: dict[tuple[int, ...], int] | None = None, default_label: int = 0) -> None:
        self.table = dict(table or {})
        self.default_label = int(default_label)
        self.classes_ = np.asarray((0, 1, 2), dtype=np.int64)
        self._fitted = bool(table)

    @staticmethod
    def _key(features: Iterable[Any]) -> tuple[int, ...]:
        values = tuple(int(bool(round(float(value)))) for value in features)
        if len(values) != len(FEATURE_NAMES):
            raise ValueError(f"expected {len(FEATURE_NAMES)} features, got {len(values)}")
        return values

    def fit(self, rows: np.ndarray, labels: np.ndarray) -> "DecisionTableModel":
        counts: dict[tuple[int, ...], list[int]] = {}
        total = [0, 0, 0]
        for row, label_raw in zip(rows, labels, strict=True):
            label = int(label_raw)
            if label not in (0, 1, 2):
                raise ValueError(f"unsupported label {label}")
            key = self._key(row)
            bucket = counts.setdefault(key, [0, 0, 0])
            bucket[label] += 1
            total[label] += 1
        if not counts:
            raise ValueError("training data is empty")
        self.table = {key: max(range(3), key=lambda idx: (bucket[idx], -idx)) for key, bucket in counts.items()}
        self.default_label = max(range(3), key=lambda idx: (total[idx], -idx))
        self._fitted = True
        return self

    def predict(self, rows: np.ndarray) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("model is not fitted")
        return np.asarray([self.table.get(self._key(row), self.default_label) for row in rows], dtype=np.int64)

    def predict_proba(self, rows: np.ndarray) -> np.ndarray:
        predictions = self.predict(rows)
        result = np.zeros((len(predictions), 3), dtype=np.float64)
        for index, label in enumerate(predictions):
            result[index, int(label)] = 1.0
        return result

    def export(self, *, seed: int) -> dict[str, Any]:
        if not self._fitted:
            raise RuntimeError("model is not fitted")
        return {
            "format": _MODEL_FORMAT,
            "feature_names": list(FEATURE_NAMES),
            "label_names": list(LABEL_NAMES),
            "seed": int(seed),
            "default_label": self.default_label,
            "table": [
                {"features": list(key), "label": label}
                for key, label in sorted(self.table.items())
            ],
        }

    @classmethod
    def from_export(cls, payload: dict[str, Any]) -> "DecisionTableModel":
        if payload.get("format") != _MODEL_FORMAT:
            raise ValueError("unsupported or unsafe cognition model format")
        if tuple(payload.get("feature_names", ())) != FEATURE_NAMES:
            raise ValueError("cognition feature schema mismatch")
        if tuple(payload.get("label_names", ())) != LABEL_NAMES:
            raise ValueError("cognition label schema mismatch")
        default_label = int(payload.get("default_label", -1))
        if default_label not in (0, 1, 2):
            raise ValueError("invalid default cognition label")
        table: dict[tuple[int, ...], int] = {}
        rows = payload.get("table")
        if not isinstance(rows, list) or not rows:
            raise ValueError("cognition model table is empty")
        for item in rows:
            if not isinstance(item, dict):
                raise ValueError("invalid cognition table row")
            key = tuple(int(value) for value in item.get("features", ()))
            if len(key) != len(FEATURE_NAMES) or any(value not in (0, 1) for value in key):
                raise ValueError("invalid cognition feature vector")
            label = int(item.get("label", -1))
            if label not in (0, 1, 2) or key in table:
                raise ValueError("invalid or duplicate cognition label row")
            table[key] = label
        return cls(table, default_label)


class UniverseCognition:
    """Bounded learned decision-table dynamics organ with no authority capability."""

    def __init__(self, model: DecisionTableModel | None = None):
        self.model = model or DecisionTableModel()
        self._fitted = model is not None and model._fitted

    @staticmethod
    def oracle_label(features):
        (aa, ar, available, assigned, active, assign_grant, release_grant, matches, _location) = [bool(round(float(x))) for x in features]
        if aa and not ar and available and not assigned and active and assign_grant:
            return 1
        if ar and not aa and assigned and matches and release_grant:
            return 2
        return 0

    @staticmethod
    def generate_dataset(count: int, seed: int):
        rng = random.Random(seed)
        rows, labels = [], []
        for _ in range(count):
            aa = rng.randint(0, 1); ar = 1 - aa
            bits = [rng.randint(0, 1) for _ in range(7)]
            row = [aa, ar, *bits]
            rows.append([float(v) for v in row]); labels.append(UniverseCognition.oracle_label(row))
        return np.asarray(rows, dtype=np.float32), np.asarray(labels, dtype=np.int64)

    @classmethod
    def train(cls, *, output_dir=None, seed=41041, train_examples=12000, test_examples=4000, epochs=140):
        x_train, y_train = cls.generate_dataset(train_examples, seed)
        x_test, y_test = cls.generate_dataset(test_examples, seed + 1)
        model = DecisionTableModel().fit(x_train, y_train)
        predicted = model.predict(x_test)
        accuracy = float((predicted == y_test).mean())
        confusion = np.zeros((3, 3), dtype=np.int64)
        for actual, pred in zip(y_test, predicted, strict=True): confusion[int(actual), int(pred)] += 1
        negatives = int((y_test == 0).sum())
        fpr = int(((y_test == 0) & (predicted != 0)).sum()) / max(1, negatives)
        rows, labels = [], []
        for aa in (0, 1):
            ar = 1 - aa
            for mask in range(1 << 7):
                bits = [(mask >> i) & 1 for i in range(7)]
                row = [aa, ar, *bits]; rows.append(row); labels.append(cls.oracle_label(row))
        ex = np.asarray(rows, dtype=np.float32); ey = np.asarray(labels, dtype=np.int64); ep = model.predict(ex)
        model_path = None
        if output_dir is not None:
            output = Path(output_dir); output.mkdir(parents=True, exist_ok=True)
            model_file = output / "ADAM_V041_COGNITION_STATE.json"
            model_file.write_text(json.dumps(model.export(seed=seed), indent=2, sort_keys=True), encoding="utf-8")
            model_path = str(model_file)
        report = TrainingReport(seed, train_examples, test_examples, epochs, accuracy, fpr, confusion.tolist(), float((ep == ey).mean()), int(((ey == 0) & (ep != 0)).sum()), model_path)
        if output_dir is not None:
            (Path(output_dir) / "ADAM_V041_TRAINING_REPORT.json").write_text(json.dumps(asdict(report), indent=2, sort_keys=True), encoding="utf-8")
        return cls(model), report

    @classmethod
    def load(cls, path):
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("legacy pickle cognition artifacts are not accepted; retrain into the safe JSON format") from exc
        return cls(DecisionTableModel.from_export(payload))

    def predict_features(self, features):
        if not self._fitted:
            raise RuntimeError("model is not fitted")
        probs_raw = self.model.predict_proba(np.asarray([features], dtype=np.float32))[0]
        probs = [float(prob) for prob in probs_raw]
        index = int(np.argmax(probs))
        return LABEL_NAMES[index], float(probs[index]), probs

    @staticmethod
    def encode_intent(engine: ReactionEngine, intent: ReactionIntent):
        equipment, project, actor = intent.bindings["equipment"], intent.bindings["project"], intent.bindings["actor"]
        eq_state = engine._state_refs(equipment); project_state = engine._state_refs(project); actor_state = engine._state_refs(actor)
        eq_values = lambda p: engine._values(eq_state, p); project_values = lambda p: engine._values(project_state, p); actor_values = lambda p: engine._values(actor_state, p)
        return [
            float(intent.reaction == "ASSIGN_EQUIPMENT"), float(intent.reaction == "RELEASE_EQUIPMENT"),
            float("AVAILABLE" in eq_values("status")), float("ASSIGNED" in eq_values("status")),
            float("ACTIVE" in project_values("status")),
            float(any(bool(v) for v in actor_values("grant::ASSIGN_EQUIPMENT"))),
            float(any(bool(v) for v in actor_values("grant::RELEASE_EQUIPMENT"))),
            float(project in eq_state.get("assigned_to", [])), float(bool(eq_state.get("location"))),
        ]

    def predict_intent(self, engine, intent):
        return self.predict_features(self.encode_intent(engine, intent))
