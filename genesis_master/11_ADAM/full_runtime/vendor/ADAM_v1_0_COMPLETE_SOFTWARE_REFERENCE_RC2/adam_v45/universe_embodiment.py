from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from adam_v41.canonical import canonical_json_bytes, digest, sha256_bytes
from adam_v44 import BondFamily, ConfidenceClass, FirstClassBond, HyperBond, HyperRole, TimeScope


@dataclass(frozen=True)
class ModelArtifact:
    model_name: str
    model_version: str
    dataset_id: str
    parameter_bytes: bytes
    metrics: Mapping[str, float]
    capability: str
    authorization: str
    supersedes: str | None = None

    @property
    def model_id(self) -> str:
        return digest("ADAM45:MODEL_ARTIFACT", {
            "model_name": self.model_name,
            "model_version": self.model_version,
            "dataset_id": self.dataset_id,
            "parameter_hash": sha256_bytes(self.parameter_bytes),
            "metrics": dict(self.metrics),
            "capability": self.capability,
            "authorization": self.authorization,
            "supersedes": self.supersedes,
        })

    @property
    def parameter_id(self) -> str:
        return digest("ADAM45:PARAMETER_COMPOUND", {
            "model_id": self.model_id,
            "sha256": sha256_bytes(self.parameter_bytes),
            "length": len(self.parameter_bytes),
        })


@dataclass(frozen=True)
class CognitionEmbeddingProposal:
    entities: Mapping[str, str]
    bonds: tuple[FirstClassBond, ...]
    training_event: HyperBond
    exact_parameter_bytes: bytes


class CognitionUniverseBinder:
    """Creates governed atomic proposals for models, datasets, parameters and metrics."""

    def propose(self, artifact: ModelArtifact, *, authority: str, logical_time: int, evidence_id: str) -> CognitionEmbeddingProposal:
        dataset = artifact.dataset_id
        metric_id = digest("ADAM45:EVALUATION", dict(artifact.metrics))
        capability_id = digest("ADAM45:CAPABILITY", artifact.capability)
        entities = {
            artifact.model_id: "MODEL",
            dataset: "DATASET",
            artifact.parameter_id: "PARAMETER_COMPOUND",
            metric_id: "EVALUATION",
            capability_id: "CAPABILITY",
            evidence_id: "EVIDENCE",
        }
        time = TimeScope(logical_time, None, logical_time)
        def bond(predicate: str, target: str, family: BondFamily) -> FirstClassBond:
            return FirstClassBond(
                artifact.model_id,
                predicate,
                target,
                family,
                authority=authority,
                time=time,
                supporting_evidence=(evidence_id,),
                confidence_class=ConfidenceClass.VERIFIED_DERIVATION,
            )
        bonds = [
            bond("TRAINED_ON", dataset, BondFamily.COGNITIVE),
            bond("HAS_PARAMETERS", artifact.parameter_id, BondFamily.STRUCTURAL),
            bond("ACHIEVED_METRIC", metric_id, BondFamily.EVIDENTIARY),
            bond("AUTHORIZED_FOR", capability_id, BondFamily.SECURITY),
        ]
        if artifact.supersedes:
            entities[artifact.supersedes] = "MODEL"
            bonds.append(bond("SUPERSEDES", artifact.supersedes, BondFamily.TEMPORAL))
        event = HyperBond(
            "MODEL_TRAINING_EVENT",
            (
                HyperRole("MODEL", artifact.model_id),
                HyperRole("DATASET", dataset),
                HyperRole("PARAMETERS", artifact.parameter_id),
                HyperRole("EVALUATION", metric_id),
                HyperRole("EVIDENCE", evidence_id),
            ),
            authority=authority,
            time=time,
            provenance=(evidence_id,),
        )
        return CognitionEmbeddingProposal(entities, tuple(bonds), event, artifact.parameter_bytes)


@dataclass(frozen=True)
class ConceptAtom:
    concept_type: str
    subject: str
    support_nodes: tuple[str, ...]
    model_id: str
    confidence: float
    authority: str
    valid_from: int

    @property
    def concept_id(self) -> str:
        return digest("ADAM45:CONCEPT_ATOM", {
            "concept_type": self.concept_type,
            "subject": self.subject,
            "support_nodes": sorted(self.support_nodes),
            "model_id": self.model_id,
            "confidence": round(self.confidence, 12),
            "authority": self.authority,
            "valid_from": self.valid_from,
        })

    def explanatory_hyperbond(self) -> HyperBond:
        roles = [HyperRole("SUBJECT", self.subject), HyperRole("MODEL", self.model_id)]
        roles.extend(HyperRole(f"SUPPORT_{i}", node, i) for i, node in enumerate(self.support_nodes))
        return HyperBond(
            f"CONCEPT::{self.concept_type}",
            tuple(roles),
            authority=self.authority,
            time=TimeScope(self.valid_from),
            confidence=self.confidence,
            metadata={"concept_id": self.concept_id},
        )
