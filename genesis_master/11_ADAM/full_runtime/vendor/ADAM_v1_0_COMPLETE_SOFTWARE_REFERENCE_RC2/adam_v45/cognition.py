from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from math import log2
from typing import Any, Iterable, Mapping, Sequence

from adam_v41.canonical import digest
from adam_v44 import BondAlgebra, FirstClassBond, HyperBond


@dataclass(frozen=True)
class Prediction:
    value: str | None
    confidence: float
    alternatives: tuple[tuple[str, float], ...]
    abstained: bool = False
    explanation: tuple[str, ...] = ()


@dataclass(frozen=True)
class TrainingRun:
    organ: str
    dataset_id: str
    examples: int
    metrics: Mapping[str, float]
    parent_model: str | None = None
    authorization: str = "RESEARCH"

    @property
    def run_id(self) -> str:
        return digest("ADAM45:TRAINING_RUN", {
            "organ": self.organ,
            "dataset_id": self.dataset_id,
            "examples": self.examples,
            "metrics": dict(self.metrics),
            "parent_model": self.parent_model,
            "authorization": self.authorization,
        })


@dataclass
class ModelWorldline:
    model_name: str
    versions: list[tuple[str, TrainingRun]] = field(default_factory=list)

    def promote(self, parameters: Mapping[str, Any], run: TrainingRun) -> str:
        model_id = digest("ADAM45:MODEL_VERSION", {
            "name": self.model_name,
            "parameters": dict(parameters),
            "run": run.run_id,
            "supersedes": self.versions[-1][0] if self.versions else None,
        })
        self.versions.append((model_id, run))
        return model_id


class MaskedBondOrgan:
    """Deterministic graph learner for masked predicate reconstruction."""

    def __init__(self, abstain_threshold: float = 0.60) -> None:
        self.abstain_threshold = abstain_threshold
        self.by_types: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
        self.global_counts: Counter[str] = Counter()
        self.model_id: str | None = None
        self.worldline = ModelWorldline("masked_bond_organ")

    def train(self, algebra: BondAlgebra) -> TrainingRun:
        self.by_types.clear()
        self.global_counts.clear()
        for bond in algebra.bonds.values():
            source_type = algebra.entity_types.get(bond.source, "BOND" if bond.source in algebra.bonds else "UNKNOWN")
            target_type = algebra.entity_types.get(bond.target, "BOND" if bond.target in algebra.bonds else "UNKNOWN")
            self.by_types[(source_type, target_type)][bond.predicate] += 1
            self.global_counts[bond.predicate] += 1
        total = sum(self.global_counts.values())
        dataset_id = digest("ADAM45:BOND_DATASET", {
            "root": algebra.root(),
            "count": total,
        })
        run = TrainingRun(
            organ="masked_bond",
            dataset_id=dataset_id,
            examples=total,
            metrics={"coverage": 1.0 if total else 0.0, "distinct_predicates": float(len(self.global_counts))},
        )
        params = {
            "by_types": {f"{k[0]}->{k[1]}": dict(v) for k, v in sorted(self.by_types.items())},
            "global": dict(self.global_counts),
            "abstain_threshold": self.abstain_threshold,
        }
        self.model_id = self.worldline.promote(params, run)
        return run

    def predict(self, source_type: str, target_type: str) -> Prediction:
        counts = self.by_types.get((source_type, target_type), self.global_counts)
        total = sum(counts.values())
        if not total:
            return Prediction(None, 0.0, (), True, ("no matching training structure",))
        ranked = tuple((name, count / total) for name, count in counts.most_common())
        best, confidence = ranked[0]
        return Prediction(
            None if confidence < self.abstain_threshold else best,
            confidence,
            ranked[:5],
            confidence < self.abstain_threshold,
            (f"conditioned on {source_type}->{target_type}", f"support={counts[best]}/{total}"),
        )


class MaskedAtomOrgan:
    """Predicts a missing target type/value identity from source and predicate context."""

    def __init__(self, abstain_threshold: float = 0.55) -> None:
        self.counts: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
        self.abstain_threshold = abstain_threshold
        self.model_id: str | None = None
        self.worldline = ModelWorldline("masked_atom_organ")

    def train(self, algebra: BondAlgebra) -> TrainingRun:
        self.counts.clear()
        examples = 0
        for bond in algebra.bonds.values():
            st = algebra.entity_types.get(bond.source, "UNKNOWN")
            tt = algebra.entity_types.get(bond.target, "BOND" if bond.target in algebra.bonds else "UNKNOWN")
            self.counts[(st, bond.predicate)][tt] += 1
            examples += 1
        dataset_id = digest("ADAM45:ATOM_DATASET", {"root": algebra.root(), "examples": examples})
        run = TrainingRun("masked_atom", dataset_id, examples, {"contexts": float(len(self.counts))})
        params = {f"{k[0]}::{k[1]}": dict(v) for k, v in sorted(self.counts.items())}
        self.model_id = self.worldline.promote(params, run)
        return run

    def predict(self, source_type: str, predicate: str) -> Prediction:
        counts = self.counts.get((source_type, predicate), Counter())
        total = sum(counts.values())
        if not total:
            return Prediction(None, 0.0, (), True, ("out-of-distribution context",))
        ranked = tuple((k, v / total) for k, v in counts.most_common())
        best, confidence = ranked[0]
        return Prediction(best if confidence >= self.abstain_threshold else None, confidence, ranked, confidence < self.abstain_threshold)


@dataclass(frozen=True)
class CompoundCandidate:
    signature: tuple[str, ...]
    occurrences: int
    participants: tuple[str, ...]
    estimated_saved_edges: int

    @property
    def candidate_id(self) -> str:
        return digest("ADAM45:COMPOUND_CANDIDATE", {
            "signature": list(self.signature),
            "occurrences": self.occurrences,
            "participants": list(self.participants),
            "estimated_saved_edges": self.estimated_saved_edges,
        })


class CompoundDiscoveryOrgan:
    def discover(self, hyperbonds: Iterable[HyperBond], minimum_occurrences: int = 2) -> list[CompoundCandidate]:
        groups: dict[tuple[str, ...], list[HyperBond]] = defaultdict(list)
        for hb in hyperbonds:
            signature = (hb.event_type, *sorted(role.role for role in hb.roles))
            groups[signature].append(hb)
        candidates = []
        for signature, items in groups.items():
            if len(items) < minimum_occurrences:
                continue
            participants = tuple(sorted({role.participant for hb in items for role in hb.roles}))
            edges = sum(len(hb.roles) for hb in items)
            candidates.append(CompoundCandidate(signature, len(items), participants, max(0, edges - len(items))))
        return sorted(candidates, key=lambda c: (-c.estimated_saved_edges, c.signature))


@dataclass(frozen=True)
class CausalClaim:
    cause: str
    effect: str
    support: int
    baseline_rate: float
    conditional_rate: float
    lift: float
    classification: str
    evidence_ids: tuple[str, ...]

    @property
    def claim_id(self) -> str:
        return digest("ADAM45:CAUSAL_CLAIM", self.__dict__)


class CausalDiscoveryOrgan:
    """Bounded causal-evidence classifier; it never upgrades correlation without intervention evidence."""

    def discover(self, episodes: Sequence[Mapping[str, Any]], cause: str, effect: str) -> CausalClaim:
        if not episodes:
            raise ValueError("episodes required")
        cause_rows = [e for e in episodes if cause in e.get("features", ())]
        base_effect = sum(effect in e.get("outcomes", ()) for e in episodes) / len(episodes)
        cond_effect = (sum(effect in e.get("outcomes", ()) for e in cause_rows) / len(cause_rows)) if cause_rows else 0.0
        lift = cond_effect / base_effect if base_effect else (float("inf") if cond_effect else 0.0)
        interventions = [e for e in cause_rows if e.get("intervention") == cause]
        verified = [e for e in interventions if e.get("verified_causal") is True and effect in e.get("outcomes", ())]
        if verified:
            classification = "verified_cause"
        elif interventions and cond_effect > base_effect:
            classification = "contributing_cause"
        elif cond_effect > base_effect * 1.25 and len(cause_rows) >= 2:
            classification = "possible_cause"
        else:
            classification = "correlation_only"
        evidence_ids = tuple(str(e.get("id", i)) for i, e in enumerate(cause_rows))
        return CausalClaim(cause, effect, len(cause_rows), base_effect, cond_effect, lift, classification, evidence_ids)


@dataclass(frozen=True)
class CalibrationReport:
    examples: int
    accuracy: float
    brier_score: float
    expected_calibration_error: float


class ConfidenceCalibrator:
    def evaluate(self, predictions: Sequence[tuple[float, bool]], bins: int = 10) -> CalibrationReport:
        if not predictions:
            return CalibrationReport(0, 0.0, 0.0, 0.0)
        accuracy = sum((confidence >= 0.5) == bool(ok) for confidence, ok in predictions) / len(predictions)
        brier = sum((confidence - float(ok)) ** 2 for confidence, ok in predictions) / len(predictions)
        ece = 0.0
        for i in range(bins):
            low, high = i / bins, (i + 1) / bins
            group = [(c, ok) for c, ok in predictions if low <= c <= high if i == bins - 1 or c < high]
            if not group:
                continue
            avg_c = sum(c for c, _ in group) / len(group)
            avg_a = sum(ok for _, ok in group) / len(group)
            ece += len(group) / len(predictions) * abs(avg_c - avg_a)
        return CalibrationReport(len(predictions), accuracy, brier, ece)


class ProofGuidedScorer:
    def score(self, *, validation_passed: bool, evidence_coverage: float, authority_valid: bool,
              reconstruction_preserved: bool, predictive_gain: float, cost_reduction: float) -> float:
        if not validation_passed or not authority_valid or not reconstruction_preserved:
            return 0.0
        return max(0.0, min(1.0, 0.30 * evidence_coverage + 0.30 * predictive_gain + 0.20 * cost_reduction + 0.20))


class NeuralSymbolicCognitionFabric:
    def __init__(self) -> None:
        self.masked_bond = MaskedBondOrgan()
        self.masked_atom = MaskedAtomOrgan()
        self.compounds = CompoundDiscoveryOrgan()
        self.causality = CausalDiscoveryOrgan()
        self.calibration = ConfidenceCalibrator()
        self.proof_guidance = ProofGuidedScorer()
        self.graph_embedding = GraphEmbeddingOrgan()

    def train(self, algebra: BondAlgebra) -> dict[str, TrainingRun]:
        return {
            "masked_bond": self.masked_bond.train(algebra),
            "masked_atom": self.masked_atom.train(algebra),
            "graph_embedding": self.graph_embedding.train(algebra),
        }

class GraphEmbeddingOrgan:
    """A small deterministic TransE-style neural-symbolic organ for bounded link prediction.

    Parameters are learned from graph triples and remain non-authoritative. The organ
    abstains when the nearest candidate score is insufficiently separated.
    """

    def __init__(self, dimensions: int = 12, epochs: int = 120, learning_rate: float = 0.03,
                 margin: float = 1.0, seed: int = 45, abstain_gap: float = 0.05) -> None:
        self.dimensions = dimensions
        self.epochs = epochs
        self.learning_rate = learning_rate
        self.margin = margin
        self.seed = seed
        self.abstain_gap = abstain_gap
        self.node_vectors: dict[str, Any] = {}
        self.relation_vectors: dict[str, Any] = {}
        self.nodes: tuple[str, ...] = ()
        self.model_id: str | None = None
        self.worldline = ModelWorldline("graph_embedding_organ")

    @staticmethod
    def _normalise(vector):
        import numpy as np
        norm = float(np.linalg.norm(vector))
        return vector if norm == 0 else vector / norm

    def train(self, algebra: BondAlgebra) -> TrainingRun:
        import numpy as np
        triples = [(b.source, b.predicate, b.target) for b in algebra.bonds.values()]
        nodes = sorted({n for triple in triples for n in (triple[0], triple[2])})
        relations = sorted({triple[1] for triple in triples})
        rng = np.random.default_rng(self.seed)
        self.node_vectors = {node: self._normalise(rng.normal(0, 0.2, self.dimensions)) for node in nodes}
        self.relation_vectors = {rel: self._normalise(rng.normal(0, 0.2, self.dimensions)) for rel in relations}
        if triples and len(nodes) > 1:
            for epoch in range(self.epochs):
                for index, (head, relation, tail) in enumerate(triples):
                    negative = nodes[(nodes.index(tail) + epoch + index + 1) % len(nodes)]
                    if negative == tail:
                        negative = nodes[(nodes.index(negative) + 1) % len(nodes)]
                    h = self.node_vectors[head]
                    r = self.relation_vectors[relation]
                    t = self.node_vectors[tail]
                    nt = self.node_vectors[negative]
                    positive_delta = h + r - t
                    negative_delta = h + r - nt
                    positive_score = float(np.dot(positive_delta, positive_delta))
                    negative_score = float(np.dot(negative_delta, negative_delta))
                    loss = self.margin + positive_score - negative_score
                    if loss <= 0:
                        continue
                    grad_pos = 2.0 * positive_delta
                    grad_neg = 2.0 * negative_delta
                    lr = self.learning_rate / (1.0 + epoch / max(1, self.epochs))
                    self.node_vectors[head] = self._normalise(h - lr * (grad_pos - grad_neg))
                    self.relation_vectors[relation] = self._normalise(r - lr * (grad_pos - grad_neg))
                    self.node_vectors[tail] = self._normalise(t + lr * grad_pos)
                    self.node_vectors[negative] = self._normalise(nt - lr * grad_neg)
        self.nodes = tuple(nodes)
        training_correct = 0
        for head, relation, tail in triples:
            prediction = self.predict_tail(head, relation)
            training_correct += int(prediction.value == tail)
        accuracy = training_correct / max(1, len(triples))
        dataset_id = digest("ADAM45:GRAPH_EMBEDDING_DATASET", {"root": algebra.root(), "triples": triples})
        run = TrainingRun("graph_embedding", dataset_id, len(triples), {"training_top1_accuracy": accuracy})
        params = {
            "dimensions": self.dimensions,
            "nodes": {k: [round(float(x), 8) for x in v] for k, v in sorted(self.node_vectors.items())},
            "relations": {k: [round(float(x), 8) for x in v] for k, v in sorted(self.relation_vectors.items())},
        }
        self.model_id = self.worldline.promote(params, run)
        return run

    def predict_tail(self, head: str, relation: str) -> Prediction:
        import numpy as np
        if head not in self.node_vectors or relation not in self.relation_vectors or not self.nodes:
            return Prediction(None, 0.0, (), True, ("out-of-distribution graph symbol",))
        target = self.node_vectors[head] + self.relation_vectors[relation]
        distances = []
        for node in self.nodes:
            delta = target - self.node_vectors[node]
            distances.append((node, float(np.linalg.norm(delta))))
        distances.sort(key=lambda item: (item[1], item[0]))
        scores = [(node, 1.0 / (1.0 + distance)) for node, distance in distances]
        total = sum(score for _, score in scores) or 1.0
        ranked = tuple((node, score / total) for node, score in scores)
        best = ranked[0]
        gap = best[1] - (ranked[1][1] if len(ranked) > 1 else 0.0)
        abstained = gap < self.abstain_gap
        return Prediction(None if abstained else best[0], best[1], ranked[:5], abstained,
                          (f"embedding distance gap={gap:.6f}",))
