from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from adam_v41.authority import Authority
from adam_v41.canonical import canonical_json_bytes, digest
from adam_v41.demo_domain import install_equipment_domain
from adam_v41.kernel import UniverseKernel
from adam_v41.reactions import ReactionIntent

from .erasure import Fragment, ReedSolomonCodec
from .time_model import HybridLogicalClock


class ConsensusError(RuntimeError):
    pass


@dataclass(frozen=True)
class Vote:
    node_id: str
    authority_id: str
    public_key_hex: str
    signature: str


@dataclass(frozen=True)
class QuorumCertificate:
    term: int
    index: int
    proposal_digest: str
    state_digest_before: str
    votes: tuple[Vote, ...]
    hlc: dict[str, int | str]


class ReplicaNode:
    def __init__(self, node_id: str, root: Path, bootstrap: Callable[[UniverseKernel], dict[str, str]]):
        self.node_id = node_id
        self.root = root
        self.kernel = UniverseKernel(root)
        install_equipment_domain(self.kernel.reactions)
        self.ids = bootstrap(self.kernel)
        self.live = True
        self.clock = HybridLogicalClock(node_id)

    @property
    def authority(self) -> Authority:
        return self.kernel._universe.authority

    def semantic_state(self) -> dict[str, Any]:
        universe = self.kernel._universe
        views = {}
        for atom_id, atom in sorted(universe.atoms.items()):
            if atom.kind == "entity":
                views[atom_id] = universe.entity_view(atom_id)
        return {"views": views, "versions": dict(sorted(universe.entity_versions.items()))}

    def state_digest(self) -> str:
        return digest("ADAM42:REPLICA_STATE", self.semantic_state())

    def prepare(self, payload: dict[str, Any], intent: ReactionIntent) -> Vote:
        if not self.live:
            raise ConsensusError(f"node {self.node_id} offline")
        self.kernel.simulate(intent)
        data = canonical_json_bytes(payload)
        return Vote(self.node_id, self.authority.authority_id, self.authority.public_key_hex, self.authority.sign(data))


class DistributedUniverseCluster:
    """Bounded majority-certified ADAM state machine with failover and replay recovery."""

    def __init__(self, root: Path | str, node_count: int = 3):
        if node_count < 3:
            raise ValueError("node_count must be >= 3")
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.term = 1
        self.index = 0
        self.leader_id = "n0"
        self.history: list[dict[str, Any]] = []
        self.certificates: list[QuorumCertificate] = []
        self.nodes: dict[str, ReplicaNode] = {}
        for i in range(node_count):
            node_id = f"n{i}"
            self.nodes[node_id] = ReplicaNode(node_id, self.root / node_id, self._bootstrap)
        self._verify_convergence()

    @staticmethod
    def _bootstrap(kernel: UniverseKernel) -> dict[str, str]:
        e, _ = kernel.genesis_entity("equipment", "EQ-001", {"status": "AVAILABLE", "location": "YARD"})
        p1, _ = kernel.genesis_entity("project", "P-001", {"status": "ACTIVE", "budget": 100000, "cost": 25000})
        p2, _ = kernel.genesis_entity("project", "P-002", {"status": "ACTIVE"})
        actor, _ = kernel.genesis_entity(
            "person", "U-001", {"name": "Distributed Operator", "grant::ASSIGN_EQUIPMENT": True, "grant::RELEASE_EQUIPMENT": True}
        )
        return {"equipment": e, "project": p1, "project2": p2, "actor": actor}

    @property
    def quorum(self) -> int:
        return len(self.nodes) // 2 + 1

    @property
    def leader(self) -> ReplicaNode:
        node = self.nodes[self.leader_id]
        if not node.live:
            raise ConsensusError("leader offline")
        return node

    def _verify_convergence(self) -> str:
        digests = {n.state_digest() for n in self.nodes.values() if n.live}
        if len(digests) != 1:
            raise ConsensusError(f"replica divergence: {digests}")
        return next(iter(digests))

    def elect(self) -> str:
        candidates = sorted(node_id for node_id, node in self.nodes.items() if node.live)
        if len(candidates) < self.quorum:
            raise ConsensusError("no quorum for election")
        self.term += 1
        self.leader_id = candidates[0]
        return self.leader_id

    def stop_node(self, node_id: str) -> None:
        self.nodes[node_id].live = False
        if node_id == self.leader_id:
            self.elect()

    def start_node(self, node_id: str) -> None:
        self.recover_node(node_id)

    def recover_node(self, node_id: str) -> None:
        node_root = self.root / node_id
        if node_root.exists():
            shutil.rmtree(node_root)
        node = ReplicaNode(node_id, node_root, self._bootstrap)
        for record in self.history:
            node.kernel.apply(ReactionIntent(**record["intent"]))
        node.live = True
        self.nodes[node_id] = node
        self._verify_convergence()

    def apply(self, intent: ReactionIntent, *, expected_term: int | None = None) -> QuorumCertificate:
        if expected_term is not None and expected_term != self.term:
            raise ConsensusError(f"stale term {expected_term}; active term {self.term}")
        live = [node for node in self.nodes.values() if node.live]
        if len(live) < self.quorum:
            raise ConsensusError("write quorum unavailable")
        before = self._verify_convergence()
        proposal = {
            "term": self.term,
            "index": self.index + 1,
            "leader": self.leader_id,
            "state_digest_before": before,
            "intent": intent.canonical(),
        }
        proposal_digest = digest("ADAM42:CONSENSUS_PROPOSAL", proposal)
        signed_payload = {**proposal, "proposal_digest": proposal_digest}
        votes: list[Vote] = []
        for node in live:
            try:
                votes.append(node.prepare(signed_payload, intent))
            except (ConsensusError, ValueError, PermissionError):
                continue
        if len(votes) < self.quorum:
            raise ConsensusError("proposal did not receive quorum validation")
        payload_bytes = canonical_json_bytes(signed_payload)
        for vote in votes:
            if not Authority.verify(vote.public_key_hex, payload_bytes, vote.signature):
                raise ConsensusError("invalid quorum signature")
        # Commit only after a valid certificate exists.
        for node in live:
            node.kernel.apply(intent)
        self.index += 1
        self._verify_convergence()
        certificate = QuorumCertificate(
            self.term, self.index, proposal_digest, before, tuple(votes), self.leader.clock.tick().canonical()
        )
        self.certificates.append(certificate)
        self.history.append({
            "intent": {"reaction": intent.reaction, "bindings": dict(intent.bindings), "args": dict(intent.args)},
            "certificate": asdict(certificate),
        })
        (self.root / "consensus_history.json").write_text(json.dumps(self.history, indent=2, sort_keys=True), encoding="utf-8")
        return certificate

    def verify_certificate(self, certificate: QuorumCertificate) -> bool:
        if len(certificate.votes) < self.quorum:
            return False
        record = self.history[certificate.index - 1] if 0 < certificate.index <= len(self.history) else None
        if record is None:
            return False
        intent = ReactionIntent(**record["intent"])
        payload = {
            "term": certificate.term, "index": certificate.index, "leader": record["certificate"]["hlc"]["node_id"],
            "state_digest_before": certificate.state_digest_before, "intent": intent.canonical(),
            "proposal_digest": certificate.proposal_digest,
        }
        # Leader is encoded in proposal; recover from stored certificate record if available.
        original = self.history[certificate.index - 1]["certificate"]
        leader = original.get("hlc", {}).get("node_id", self.leader_id)
        payload["leader"] = leader
        expected_digest = digest("ADAM42:CONSENSUS_PROPOSAL", {k: payload[k] for k in ("term", "index", "leader", "state_digest_before", "intent")})
        if expected_digest != certificate.proposal_digest:
            return False
        data = canonical_json_bytes(payload)
        return all(Authority.verify(v.public_key_hex, data, v.signature) for v in certificate.votes)


@dataclass
class StorageNode:
    node_id: str
    jurisdiction: str
    root: Path


class SovereignErasureStore:
    """Jurisdiction-aware fragment placement with real 3+2 RS reconstruction."""

    def __init__(self, root: Path | str, nodes: list[tuple[str, str]], k: int = 3, m: int = 2):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.nodes = [StorageNode(node_id, jurisdiction, self.root / node_id) for node_id, jurisdiction in nodes]
        for node in self.nodes:
            node.root.mkdir(parents=True, exist_ok=True)
        self.codec = ReedSolomonCodec(k, m)
        self.manifest: dict[str, Any] = {}

    def put(self, data: bytes, *, allowed_jurisdictions: set[str]) -> str:
        eligible = [n for n in self.nodes if n.jurisdiction in allowed_jurisdictions]
        fragments = self.codec.encode(data)
        if len(eligible) < len(fragments):
            raise ConsensusError("insufficient policy-eligible storage nodes")
        placements = []
        for fragment, node in zip(fragments, eligible):
            path = node.root / f"{fragment.object_sha256}.{fragment.index}.frag"
            path.write_bytes(fragment.payload)
            placements.append({"node_id": node.node_id, "jurisdiction": node.jurisdiction, "index": fragment.index, "path": str(path)})
        object_id = fragments[0].object_sha256
        self.manifest[object_id] = {
            "k": fragments[0].k, "m": fragments[0].m, "original_length": fragments[0].original_length,
            "shard_size": fragments[0].shard_size, "placements": placements,
            "allowed_jurisdictions": sorted(allowed_jurisdictions),
        }
        (self.root / "manifest.json").write_text(json.dumps(self.manifest, indent=2, sort_keys=True), encoding="utf-8")
        return object_id

    def reconstruct(self, object_id: str, unavailable_nodes: set[str] | None = None) -> bytes:
        item = self.manifest[object_id]
        unavailable_nodes = unavailable_nodes or set()
        fragments = []
        for p in item["placements"]:
            if p["node_id"] in unavailable_nodes:
                continue
            payload = Path(p["path"]).read_bytes()
            fragments.append(Fragment(p["index"], item["k"], item["m"], item["original_length"], item["shard_size"], object_id, payload))
        return self.codec.reconstruct(fragments)
