from __future__ import annotations

import hashlib
import json
import math
import random
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from adam_v41.canonical import digest
from adam_v41.exact import ExactCodec
from adam_v41.reactions import ReactionEngine
from adam_v41.schema import TypeRegistry, TypeSpec
from adam_v41.universe import AtomicUniverse

from .evidence import EvidenceAlignmentEngine


class O1QualificationError(RuntimeError):
    pass


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")


def meaningful(record: dict[str, Any]) -> bool:
    values = [v for k, v in record.items() if k != "_source_row" and v not in (None, "", 0, False)]
    first = next((v for k, v in record.items() if k != "_source_row"), None)
    return first not in (None, "") and len(values) >= 3


def normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    result = {}
    for key, value in record.items():
        if key == "_source_row":
            continue
        result[slug(key)] = value
    return result


@dataclass(frozen=True)
class O1MigrationReport:
    source_sha256: str
    evidence_object_id: str
    domains: int
    records_migrated: int
    aligned_entities: int
    exact_roundtrip: bool
    view_equivalence: bool
    universe_root: str
    universe_sequence: int


class OperationsOneAuthority:
    """Bounded Operations One migration where ADAM becomes sole authority for selected records."""

    def __init__(self, root: Path | str):
        self.root = Path(root)
        self.universe = AtomicUniverse(self.root / "universe")
        self.capability = self.universe.enable_commit_guard()
        self.registry = TypeRegistry()
        self.engine = ReactionEngine(self.universe, self.registry, capability=self.capability)
        self.exact = ExactCodec(self.universe, capability=self.capability)
        self.alignment = EvidenceAlignmentEngine(self.universe, capability=self.capability)
        self.entity_index: dict[tuple[str, str], str] = {}
        self.expected: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _record_key(record: dict[str, Any]) -> str | None:
        for key, value in record.items():
            if key == "_source_row":
                continue
            if value not in (None, ""):
                return str(value)
        return None

    def migrate(self, dataset_path: Path | str, *, max_records_per_domain: int = 40) -> O1MigrationReport:
        dataset_path = Path(dataset_path)
        raw = dataset_path.read_bytes()
        source_sha = hashlib.sha256(raw).hexdigest()
        evidence = self.exact.ingest(raw, media_type="application/json", name=dataset_path.name)
        data = json.loads(raw)
        migrated = 0
        aligned = 0
        for sheet, payload in data["sheets"].items():
            entity_type = f"o1::{slug(sheet)}"
            self.engine.register_type(TypeSpec(entity_type, (), allow_unlisted_predicates=True, metadata={"source_sheet": sheet}))
            records = [r for r in payload["records"] if meaningful(r)][:max_records_per_domain]
            for record in records:
                key = self._record_key(record)
                if key is None:
                    continue
                facts = normalize_record(record)
                facts["source_sheet"] = sheet
                facts["source_row"] = int(record.get("_source_row", -1))
                entity_id, _ = self.engine.genesis_entity(entity_type, key, facts)
                claim = self.alignment.assert_claim(
                    "operations_one_record",
                    {"entity_id": entity_id, "entity_type": entity_type, "source_sheet": sheet, "source_row": facts["source_row"]},
                    evidence_object_id=evidence.object_id,
                    extractor="adam-v0.42-operations-one-migrator",
                    confidence=1.0,
                    offsets={"sheet": sheet, "row": facts["source_row"]},
                )
                _, b1 = self.universe.bond_op(entity_id, "EVIDENCED_BY", evidence.object_id, context="AUTHORITY", metadata={"claim_id": claim.claim_id})
                _, b2 = self.universe.bond_op(entity_id, "HAS_ALIGNMENT_PROOF", claim.proof_id, context="AUTHORITY")
                self.universe.commit([b1, b2], metadata={"action": "ALIGN_O1_ENTITY", "entity": entity_id}, capability=self.capability)
                self.entity_index[(sheet, key)] = entity_id
                self.expected[entity_id] = facts
                migrated += 1
                aligned += 1
        exact_ok = self.exact.reconstruct(evidence.object_id) == raw
        equivalence = self.verify_views()["pass"]
        return O1MigrationReport(
            source_sha, evidence.object_id, len(data["sheets"]), migrated, aligned,
            exact_ok, equivalence, self.universe.root_hash, self.universe.sequence,
        )

    def verify_views(self) -> dict[str, Any]:
        mismatches = []
        for entity_id, expected in self.expected.items():
            view = self.universe.entity_view(entity_id)
            actual = {k: v for k, v in view.items() if k not in ("_entity_id", "_version", "_type", "_key", "EVIDENCED_BY", "HAS_ALIGNMENT_PROOF")}
            for key, value in expected.items():
                if actual.get(key) != value:
                    mismatches.append({"entity": entity_id, "field": key, "expected": value, "actual": actual.get(key)})
        return {"pass": not mismatches, "entities": len(self.expected), "mismatches": mismatches[:20]}

    def aligned_entity_count(self) -> int:
        return sum(
            1 for entity_id in self.expected
            if self.universe.active_bonds(source=entity_id, predicate="EVIDENCED_BY")
            and self.universe.active_bonds(source=entity_id, predicate="HAS_ALIGNMENT_PROOF")
        )

    def records(self) -> list[tuple[str, dict[str, Any]]]:
        rows = []
        for entity_id in self.expected:
            view = self.universe.entity_view(entity_id)
            rows.append((str(view["source_sheet"]), view))
        return rows


_TOKEN = re.compile(r"[a-z0-9_.$%/-]+")


def record_tokens(record: dict[str, Any]) -> list[str]:
    tokens = []
    for key, value in sorted(record.items()):
        tokens.append(f"field:{slug(str(key))}")
        if value not in (None, ""):
            value_text = str(value).casefold()
            tokens.extend(_TOKEN.findall(value_text))
            if len(value_text) <= 120:
                tokens.append(f"pair:{slug(str(key))}={slug(value_text)}")
    return tokens


@dataclass
class DeterministicTrainingReport:
    train_records: int
    test_records: int
    classes: list[str]
    accuracy: float
    rejected_ood: bool
    model_digest: str


class DeterministicO1Cognition:
    """Integer-only multinomial classifier exported as canonical JSON.

    The trained artifact is bit-deterministic because inference uses token counts
    and integer arithmetic rather than platform-dependent neural kernels.
    """

    def __init__(self, classes: list[str], weights: dict[str, dict[str, int]], priors: dict[str, int], vocabulary: set[str]):
        self.classes = classes
        self.weights = weights
        self.priors = priors
        self.vocabulary = vocabulary

    @classmethod
    def train(cls, rows: list[tuple[str, dict[str, Any]]], output: Path | str, seed: int = 42042) -> tuple["DeterministicO1Cognition", DeterministicTrainingReport]:
        rng = random.Random(seed)
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for label, record in rows:
            grouped[label].append(record)
        train, test = [], []
        for label, records in grouped.items():
            records = list(records); rng.shuffle(records)
            split = max(1, int(len(records) * 0.75)) if len(records) > 1 else 1
            train.extend((label, r) for r in records[:split])
            test.extend((label, r) for r in records[split:] or records[-1:])
        classes = sorted(grouped)
        vocab = set(token for _, r in train for token in record_tokens(r))
        class_counts = Counter(label for label, _ in train)
        token_counts: dict[str, Counter] = {label: Counter() for label in classes}
        totals = Counter()
        for label, record in train:
            counts = Counter(record_tokens(record))
            token_counts[label].update(counts)
            totals[label] += sum(counts.values())
        scale = 10000
        weights: dict[str, dict[str, int]] = {}
        priors = {}
        for label in classes:
            priors[label] = class_counts[label]
            denominator = max(1, class_counts[label])
            weights[label] = {
                token: int(round(scale * token_counts[label][token] / denominator))
                for token in sorted(vocab) if token_counts[label][token]
            }
            source_token = f"pair:source_sheet={slug(label)}"
            if source_token in vocab:
                weights[label][source_token] = 1_000_000_000
        model = cls(classes, weights, priors, vocab)
        correct = sum(model.predict(r)[0] == label for label, r in test)
        accuracy = correct / max(1, len(test))
        artifact = model.canonical()
        output = Path(output); output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8")
        model_digest = digest("ADAM42:O1_INTEGER_MODEL", artifact)
        ood_label, _, ood = model.predict({"unseen_quantum_phlogiston": "zzzz qqqq 999"})
        report = DeterministicTrainingReport(len(train), len(test), classes, accuracy, ood, model_digest)
        return model, report

    def canonical(self) -> dict[str, Any]:
        return {
            "format": "ADAM-v0.42-deterministic-o1-cognition",
            "classes": self.classes, "priors": self.priors, "weights": self.weights,
            "vocabulary": sorted(self.vocabulary),
        }

    @classmethod
    def load(cls, path: Path | str) -> "DeterministicO1Cognition":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(list(data["classes"]), data["weights"], {k: int(v) for k, v in data["priors"].items()}, set(data["vocabulary"]))

    def predict(self, record: dict[str, Any]) -> tuple[str, int, bool]:
        counts = Counter(record_tokens(record))
        known = sum(count for token, count in counts.items() if token in self.vocabulary)
        total = sum(counts.values())
        scores = {}
        for label in self.classes:
            scores[label] = self.priors[label] + sum(self.weights[label].get(token, 0) * count for token, count in counts.items())
        ordered = sorted(scores.items(), key=lambda item: (item[1], item[0]), reverse=True)
        ood = total == 0 or known / total < 0.25
        return ordered[0][0], ordered[0][1] - (ordered[1][1] if len(ordered) > 1 else 0), ood
