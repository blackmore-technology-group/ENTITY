from __future__ import annotations

from pathlib import Path
from typing import Any

from .brain import AtomicBrain
from .exact import ExactCodec
from .reactions import ReactionEngine, ReactionIntent, ReactionReceipt
from .schema import TypeRegistry, TypeSpec
from .semantic import SemanticCodec
from .universe import AtomicUniverse


class UniverseKernel:
    """Guarded v0.41 facade.

    The raw substrate is intentionally private. Normal callers receive only
    controlled ingestion, registration, simulation, reaction and read methods.
    Python privacy is not a process security boundary; production must isolate
    this kernel behind an authenticated service boundary.
    """

    def __init__(self, root: Path | str):
        self._universe = AtomicUniverse(root)
        self._capability = self._universe.enable_commit_guard()
        self.reactions = ReactionEngine(
            self._universe,
            TypeRegistry(),
            capability=self._capability,
        )
        self._exact = ExactCodec(self._universe, capability=self._capability)
        self._semantic = SemanticCodec(self._universe, capability=self._capability)
        self._brain = AtomicBrain(self._universe, capability=self._capability)

    @property
    def sequence(self) -> int:
        return self._universe.sequence

    @property
    def root_hash(self) -> str:
        return self._universe.root_hash

    def register_type(self, spec: TypeSpec) -> str:
        return self.reactions.register_type(spec)

    def register_reaction(self, definition) -> str:
        return self.reactions.register_reaction(definition)

    def genesis_entity(self, entity_type: str, key: str, facts: dict[str, Any]) -> tuple[str, int]:
        return self.reactions.genesis_entity(entity_type, key, facts)

    def simulate(self, intent: ReactionIntent) -> ReactionReceipt:
        return self.reactions.simulate(intent)

    def apply(self, intent: ReactionIntent) -> ReactionReceipt:
        return self.reactions.apply(intent)

    def ingest_exact(self, data: bytes, *, media_type: str = "application/octet-stream", name: str | None = None):
        return self._exact.ingest(data, media_type=media_type, name=name)

    def reconstruct_exact(self, object_id: str) -> bytes:
        return self._exact.reconstruct(object_id)

    def ingest_semantic(self, value: Any) -> str:
        return self._semantic.ingest(value)

    def reconstruct_semantic(self, ref: str) -> Any:
        return self._semantic.reconstruct(ref)

    def entity_view(self, entity_id: str, *, at_seq: int | None = None) -> dict[str, Any]:
        return self._universe.entity_view(entity_id, at_seq=at_seq)

    def verify(self) -> dict[str, Any]:
        return self._universe.verify()

    def compact_authority(self) -> dict[str, Any]:
        return self._universe.compact_authority()
