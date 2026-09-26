from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Mapping

from adam_v41.canonical import canonical_json_bytes, digest, sha256_bytes
from adam_v44 import AtomicPhysicsKernel, ReactionIntent


@dataclass(frozen=True)
class FieldMapping:
    external_field: str
    predicate: str
    value_type: str = "value"
    identity: bool = False


@dataclass(frozen=True)
class ApplicationManifest:
    application_id: str
    version: str
    entity_types: tuple[str, ...]
    identity_namespace: str
    mappings: tuple[FieldMapping, ...]
    observable_scopes: tuple[str, ...] = ("PUBLIC",)
    permitted_reactions: tuple[str, ...] = ()
    constructible_forms: tuple[str, ...] = ("json",)
    required_purposes: tuple[str, ...] = ()
    adapter_kind: str = "json_rpc"

    @property
    def manifest_id(self) -> str:
        return digest("ADAM46:APPLICATION_MANIFEST", {
            "application_id": self.application_id,
            "version": self.version,
            "entity_types": list(self.entity_types),
            "identity_namespace": self.identity_namespace,
            "mappings": [m.__dict__ for m in self.mappings],
            "observable_scopes": list(self.observable_scopes),
            "permitted_reactions": list(self.permitted_reactions),
            "constructible_forms": list(self.constructible_forms),
            "required_purposes": list(self.required_purposes),
            "adapter_kind": self.adapter_kind,
        })


@dataclass(frozen=True)
class BridgeEvent:
    application_id: str
    event_type: str
    exact_hash: str
    payload: Mapping[str, Any]
    external_identity: str | None
    authority: str
    observed_at: int

    @property
    def event_id(self) -> str:
        return digest("ADAM46:BRIDGE_EVENT", {
            "application_id": self.application_id,
            "event_type": self.event_type,
            "exact_hash": self.exact_hash,
            "payload": dict(self.payload),
            "external_identity": self.external_identity,
            "authority": self.authority,
            "observed_at": self.observed_at,
        })


@dataclass
class FederatedIdentity:
    canonical_id: str
    aliases: dict[tuple[str, str], str] = field(default_factory=dict)


class IdentityFederation:
    def __init__(self) -> None:
        self.by_external: dict[tuple[str, str], str] = {}
        self.identities: dict[str, FederatedIdentity] = {}

    def resolve(self, namespace: str, external_id: str, entity_type: str) -> str:
        key = (namespace, external_id)
        if key in self.by_external:
            return self.by_external[key]
        canonical_id = digest("ADAM46:FEDERATED_IDENTITY", {
            "namespace": namespace,
            "external_id": external_id,
            "entity_type": entity_type,
        })
        identity = FederatedIdentity(canonical_id, {key: entity_type})
        self.identities[canonical_id] = identity
        self.by_external[key] = canonical_id
        return canonical_id

    def merge(self, left: str, right: str, *, authority: str) -> str:
        if left == right:
            return left
        if left not in self.identities or right not in self.identities:
            raise KeyError("identity missing")
        merged_id = digest("ADAM46:IDENTITY_MERGE", {"left": left, "right": right, "authority": authority})
        aliases = {**self.identities[left].aliases, **self.identities[right].aliases}
        self.identities[merged_id] = FederatedIdentity(merged_id, aliases)
        for alias in aliases:
            self.by_external[alias] = merged_id
        return merged_id


class ApplicationAdapter(ABC):
    """Explicit adapter contract; abstract adapters cannot be registered or invoked."""

    kind = "generic"

    @abstractmethod
    def decode(self, raw: bytes) -> Mapping[str, Any]:
        """Decode exact application evidence into a mapped event object."""

    @abstractmethod
    def encode(self, value: Mapping[str, Any]) -> bytes:
        """Construct a deterministic application representation."""


class JsonAdapter(ApplicationAdapter):
    kind = "json_rpc"

    def decode(self, raw: bytes) -> Mapping[str, Any]:
        value = json.loads(raw.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("JSON application event must be an object")
        return value

    def encode(self, value: Mapping[str, Any]) -> bytes:
        return canonical_json_bytes(dict(value))


class DocumentAdapter(ApplicationAdapter):
    kind = "document"

    def decode(self, raw: bytes) -> Mapping[str, Any]:
        text = raw.decode("utf-8")
        return {"text": text, "lines": text.splitlines()}

    def encode(self, value: Mapping[str, Any]) -> bytes:
        return str(value.get("text", "")).encode("utf-8")


class UniversalApplicationNervousSystem:
    """Applications are governed senses, constructors and actuators—not data owners."""

    def __init__(self, physics: AtomicPhysicsKernel) -> None:
        self.physics = physics
        self.manifests: dict[str, ApplicationManifest] = {}
        self.adapters: dict[str, ApplicationAdapter] = {
            "json_rpc": JsonAdapter(),
            "document": DocumentAdapter(),
        }
        self.federation = IdentityFederation()
        self.events: list[BridgeEvent] = []
        self.exact_evidence: dict[str, bytes] = {}
        self.application_state: dict[str, dict[str, dict[str, Any]]] = {}

    def register_adapter(self, adapter: ApplicationAdapter) -> None:
        self.adapters[adapter.kind] = adapter

    def register(self, manifest: ApplicationManifest) -> str:
        if manifest.adapter_kind not in self.adapters:
            raise ValueError(f"adapter {manifest.adapter_kind!r} is not installed")
        self.manifests[manifest.application_id] = manifest
        self.application_state.setdefault(manifest.application_id, {})
        return manifest.manifest_id

    def ingest(self, application_id: str, raw: bytes, *, entity_type: str, external_id: str,
               authority: str, observed_at: int, event_type: str = "observation") -> BridgeEvent:
        manifest = self.manifests[application_id]
        if entity_type not in manifest.entity_types:
            raise PermissionError(f"{application_id} may not observe entity type {entity_type}")
        payload = dict(self.adapters[manifest.adapter_kind].decode(raw))
        exact_hash = sha256_bytes(raw)
        self.exact_evidence[exact_hash] = bytes(raw)
        canonical_id = self.federation.resolve(manifest.identity_namespace, external_id, entity_type)
        event = BridgeEvent(application_id, event_type, exact_hash, payload, external_id, authority, observed_at)
        self.events.append(event)
        self.application_state[application_id][canonical_id] = {
            "entity_type": entity_type,
            "payload": payload,
            "evidence": exact_hash,
            "event_id": event.event_id,
        }
        return event

    def propose_reaction(self, application_id: str, intent: ReactionIntent):
        manifest = self.manifests[application_id]
        if intent.reaction_name not in manifest.permitted_reactions:
            raise PermissionError(f"{application_id} may not propose {intent.reaction_name}")
        return self.physics.simulate(intent)

    def commit_reaction(self, application_id: str, intent: ReactionIntent):
        manifest = self.manifests[application_id]
        if intent.reaction_name not in manifest.permitted_reactions:
            raise PermissionError(f"{application_id} may not commit {intent.reaction_name}")
        return self.physics.commit(intent)

    def construct(self, application_id: str, canonical_id: str, form: str = "json") -> bytes:
        manifest = self.manifests[application_id]
        if form not in manifest.constructible_forms:
            raise PermissionError(f"{application_id} may not construct {form}")
        state = self.application_state[application_id][canonical_id]
        if form == "json":
            return canonical_json_bytes(state)
        if form == "document":
            return self.adapters["document"].encode(state["payload"])
        if form == "object":
            return canonical_json_bytes({"object": state})
        if form == "sql_row":
            flat = {"canonical_id": canonical_id, **state["payload"]}
            return canonical_json_bytes(flat)
        raise ValueError(f"unsupported construction form {form}")

    def release(self, constructed: bytes) -> None:
        # Constructed representations are deliberately not retained by this interface.
        del constructed

    def health(self) -> dict[str, Any]:
        return {
            "applications": len(self.manifests),
            "events": len(self.events),
            "evidence_objects": len(self.exact_evidence),
            "physics_root": self.physics.root,
        }
