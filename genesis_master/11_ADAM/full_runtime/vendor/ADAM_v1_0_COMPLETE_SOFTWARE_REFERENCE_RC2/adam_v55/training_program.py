from __future__ import annotations

import math
from dataclasses import dataclass, asdict, field
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from adam_v41.canonical import digest, sha256_bytes


class TrainingGovernanceError(RuntimeError):
    """Raised when dataset rights, splits or model promotion are invalid."""


@dataclass(frozen=True)
class DatasetGovernance:
    dataset_id: str
    source: str
    owner: str
    licence: str
    permitted_purposes: tuple[str, ...]
    jurisdiction: str
    retention_policy: str
    personal_information: bool
    label_version: str
    limitations: tuple[str, ...]

    @property
    def governance_id(self) -> str:
        return digest("ADAM55:DATASET_GOVERNANCE", asdict(self))


@dataclass(frozen=True)
class TrainingExample:
    example_id: str
    features: tuple[float, ...]
    label: str
    group: str
    observed_at: int
    evidence_hash: str


@dataclass
class GovernedDataset:
    governance: DatasetGovernance
    examples: list[TrainingExample] = field(default_factory=list)

    def add(self, *, features: Sequence[float], label: str, group: str, observed_at: int,
            exact_evidence: bytes) -> TrainingExample:
        if not features or not label or not group:
            raise ValueError("features, label and group are required")
        feature_tuple = tuple(float(value) for value in features)
        evidence_hash = sha256_bytes(exact_evidence)
        example_id = digest("ADAM55:TRAINING_EXAMPLE", {
            "dataset": self.governance.dataset_id,
            "features": feature_tuple,
            "label": label,
            "group": group,
            "observed_at": observed_at,
            "evidence_hash": evidence_hash,
        })
        example = TrainingExample(example_id, feature_tuple, label, group, observed_at, evidence_hash)
        self.examples.append(example)
        return example

    @property
    def dataset_root(self) -> str:
        return digest("ADAM55:GOVERNED_DATASET", {
            "governance": self.governance.governance_id,
            "examples": [example.example_id for example in sorted(self.examples, key=lambda item: item.example_id)],
        })

    def split_by_group(self, *, validation_groups: Iterable[str], test_groups: Iterable[str]) -> tuple[list[TrainingExample], list[TrainingExample], list[TrainingExample]]:
        validation = set(validation_groups)
        test = set(test_groups)
        if validation & test:
            raise TrainingGovernanceError("validation and test groups overlap")
        train_rows: list[TrainingExample] = []
        validation_rows: list[TrainingExample] = []
        test_rows: list[TrainingExample] = []
        for example in self.examples:
            if example.group in test:
                test_rows.append(example)
            elif example.group in validation:
                validation_rows.append(example)
            else:
                train_rows.append(example)
        if not train_rows or not validation_rows or not test_rows:
            raise TrainingGovernanceError("train, validation and test splits must all be non-empty")
        return train_rows, validation_rows, test_rows


@dataclass(frozen=True)
class Prediction:
    label: str | None
    confidence: float
    abstained: bool
    distance: float
    model_id: str
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class ModelReceipt:
    organ_name: str
    model_id: str
    dataset_root: str
    training_examples: int
    validation_examples: int
    test_examples: int
    validation_accuracy: float
    test_accuracy: float
    calibration_error: float
    ood_threshold: float
    code_version: str
    authorized_capability: str
    approved_by: str


class NearestCentroidOrgan:
    """Small, deterministic specialist organ with calibrated abstention.

    This is an operational bounded reference, not a foundation model.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self.centroids: dict[str, np.ndarray] = {}
        self.scales: np.ndarray | None = None
        self.ood_threshold = 0.0
        self.model_id = "UNTRAINED"
        self.receipt: ModelReceipt | None = None
        self.training_evidence: tuple[str, ...] = ()

    def _fit(self, examples: Sequence[TrainingExample]) -> None:
        matrix = np.asarray([row.features for row in examples], dtype=np.float64)
        if matrix.ndim != 2 or matrix.shape[0] < 2:
            raise TrainingGovernanceError("at least two compatible training examples are required")
        scales = matrix.std(axis=0)
        scales[scales < 1e-9] = 1.0
        self.scales = scales
        labels = sorted({row.label for row in examples})
        self.centroids = {
            label: np.asarray([row.features for row in examples if row.label == label], dtype=np.float64).mean(axis=0)
            for label in labels
        }
        distances = [self._distance(np.asarray(row.features, dtype=np.float64), self.centroids[row.label]) for row in examples]
        self.ood_threshold = max(distances) * 1.5 + 1e-9
        self.training_evidence = tuple(sorted(row.evidence_hash for row in examples))

    def _distance(self, vector: np.ndarray, centroid: np.ndarray) -> float:
        if self.scales is None:
            raise TrainingGovernanceError("model is not trained")
        return float(np.linalg.norm((vector - centroid) / self.scales))

    def predict(self, features: Sequence[float], *, evidence_ids: Iterable[str] = ()) -> Prediction:
        if not self.centroids or self.scales is None:
            raise TrainingGovernanceError("model is not trained")
        vector = np.asarray(tuple(float(value) for value in features), dtype=np.float64)
        if vector.shape != self.scales.shape:
            raise ValueError("feature dimension does not match model")
        scored = sorted((self._distance(vector, centroid), label) for label, centroid in self.centroids.items())
        distance, label = scored[0]
        second = scored[1][0] if len(scored) > 1 else distance + 1.0
        confidence = max(0.0, min(1.0, (second - distance) / max(second, 1e-9)))
        abstained = distance > self.ood_threshold
        return Prediction(None if abstained else label, confidence if not abstained else 0.0, abstained, distance,
                          self.model_id, tuple(sorted(set(evidence_ids))))

    def _accuracy(self, examples: Sequence[TrainingExample]) -> float:
        correct = 0
        for row in examples:
            prediction = self.predict(row.features, evidence_ids=(row.evidence_hash,))
            correct += int(not prediction.abstained and prediction.label == row.label)
        return correct / len(examples)

    def _calibration_error(self, examples: Sequence[TrainingExample], bins: int = 5) -> float:
        buckets: list[list[tuple[float, bool]]] = [[] for _ in range(bins)]
        for row in examples:
            prediction = self.predict(row.features)
            confidence = prediction.confidence
            index = min(bins - 1, int(confidence * bins))
            buckets[index].append((confidence, prediction.label == row.label and not prediction.abstained))
        total = len(examples)
        error = 0.0
        for bucket in buckets:
            if not bucket:
                continue
            avg_confidence = sum(item[0] for item in bucket) / len(bucket)
            accuracy = sum(int(item[1]) for item in bucket) / len(bucket)
            error += len(bucket) / total * abs(avg_confidence - accuracy)
        return error

    def train(self, dataset: GovernedDataset, *, validation_groups: Iterable[str], test_groups: Iterable[str],
              authorized_capability: str, approved_by: str, code_version: str = "adam-v0.55-centroid-v1") -> ModelReceipt:
        if "TRAIN_MODEL" not in dataset.governance.permitted_purposes:
            raise TrainingGovernanceError("dataset licence does not permit training")
        train_rows, validation_rows, test_rows = dataset.split_by_group(
            validation_groups=validation_groups,
            test_groups=test_groups,
        )
        self._fit(train_rows)
        validation_distances = [
            self._distance(np.asarray(row.features, dtype=np.float64), self.centroids[row.label])
            for row in validation_rows
        ]
        if validation_distances:
            self.ood_threshold = max(self.ood_threshold, max(validation_distances) * 1.5 + 1e-9)
        model_material = {
            "name": self.name,
            "dataset_root": dataset.dataset_root,
            "centroids": {label: centroid.tolist() for label, centroid in sorted(self.centroids.items())},
            "scales": self.scales.tolist(),
            "ood_threshold": self.ood_threshold,
            "code_version": code_version,
        }
        self.model_id = digest("ADAM55:SPECIALIST_MODEL", model_material)
        receipt = ModelReceipt(
            organ_name=self.name,
            model_id=self.model_id,
            dataset_root=dataset.dataset_root,
            training_examples=len(train_rows),
            validation_examples=len(validation_rows),
            test_examples=len(test_rows),
            validation_accuracy=self._accuracy(validation_rows),
            test_accuracy=self._accuracy(test_rows),
            calibration_error=self._calibration_error(validation_rows),
            ood_threshold=self.ood_threshold,
            code_version=code_version,
            authorized_capability=authorized_capability,
            approved_by=approved_by,
        )
        self.receipt = receipt
        return receipt


@dataclass
class DriftMonitor:
    baseline_mean: np.ndarray
    baseline_std: np.ndarray
    threshold: float = 3.0

    @classmethod
    def from_examples(cls, examples: Sequence[TrainingExample], threshold: float = 3.0) -> "DriftMonitor":
        matrix = np.asarray([row.features for row in examples], dtype=np.float64)
        std = matrix.std(axis=0)
        std[std < 1e-9] = 1.0
        return cls(matrix.mean(axis=0), std, threshold)

    def score(self, features: Sequence[float]) -> float:
        vector = np.asarray(features, dtype=np.float64)
        return float(np.max(np.abs((vector - self.baseline_mean) / self.baseline_std)))

    def drifted(self, features: Sequence[float]) -> bool:
        return self.score(features) > self.threshold


@dataclass
class ShadowDeployment:
    organ: NearestCentroidOrgan
    monitor: DriftMonitor
    outcomes: list[dict[str, Any]] = field(default_factory=list)

    def observe(self, features: Sequence[float], *, actual_label: str | None = None,
                evidence_ids: Iterable[str] = ()) -> Prediction:
        prediction = self.organ.predict(features, evidence_ids=evidence_ids)
        self.outcomes.append({
            "prediction": prediction.label,
            "confidence": prediction.confidence,
            "abstained": prediction.abstained,
            "actual": actual_label,
            "correct": actual_label is None or prediction.label == actual_label,
            "drift_score": self.monitor.score(features),
            "authority_committed": False,
        })
        return prediction

    def summary(self) -> Mapping[str, Any]:
        evaluated = [row for row in self.outcomes if row["actual"] is not None]
        return {
            "observations": len(self.outcomes),
            "evaluated": len(evaluated),
            "accuracy": (sum(int(row["correct"]) for row in evaluated) / len(evaluated)) if evaluated else None,
            "abstentions": sum(int(row["abstained"]) for row in self.outcomes),
            "drift_events": sum(int(row["drift_score"] > self.monitor.threshold) for row in self.outcomes),
            "authority_commits": 0,
        }


def synthetic_sensor_dataset() -> GovernedDataset:
    governance = DatasetGovernance(
        dataset_id="bounded-sensor-reference",
        source="deterministic synthetic production-like sensor generator",
        owner="ADAM development qualification",
        licence="internal qualification use",
        permitted_purposes=("TRAIN_MODEL", "EVALUATE_MODEL"),
        jurisdiction="CA-BC",
        retention_policy="RETAIN_QUALIFICATION_EVIDENCE",
        personal_information=False,
        label_version="1",
        limitations=("synthetic", "not open-world", "not a physical safety certification corpus"),
    )
    dataset = GovernedDataset(governance)
    for group_index, group in enumerate(("site-a", "site-b", "site-c", "site-d", "site-e", "site-f")):
        for index in range(20):
            normal = index < 10
            base = 1.0 if normal else 8.0
            features = (base + group_index * 0.05, base * 0.5 + index * 0.01, 0.1 if normal else 0.9)
            label = "NORMAL" if normal else "ANOMALY"
            dataset.add(
                features=features,
                label=label,
                group=group,
                observed_at=group_index * 100 + index,
                exact_evidence=f"{group}:{index}:{features}:{label}".encode("utf-8"),
            )
    return dataset
