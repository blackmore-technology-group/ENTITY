from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Mapping, Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from adam_v41.canonical import canonical_json_bytes, digest
from adam_v44 import AtomicPhysicsKernel, ReactionIntent, ReactionProof


class DistributedPhysicsError(RuntimeError):
    pass


@dataclass(frozen=True)
class PhysicsVote:
    node_id: str
    public_key: bytes
    signature: bytes
    predicted_root: str


@dataclass(frozen=True)
class PhysicsQuorumCertificate:
    term: int
    index: int
    leader_id: str
    previous_root: str
    new_root: str
    proposal_id: str
    proof_id: str
    membership: tuple[tuple[str, str], ...]
    quorum: int
    votes: tuple[PhysicsVote, ...]
    proposal_payload: Mapping[str, Any]


class PhysicsReplica:
    def __init__(self, node_id: str, kernel: AtomicPhysicsKernel) -> None:
        self.node_id = node_id
        self.kernel = kernel
        self.live = True
        self._private = Ed25519PrivateKey.generate()
        self.public_key = self._private.public_key()

    def prepare(self, proposal: Mapping[str, Any], intent: ReactionIntent) -> PhysicsVote:
        if not self.live:
            raise DistributedPhysicsError(f"replica {self.node_id} offline")
        _, proof = self.kernel.simulate(intent)
        if proof.new_root != proposal["new_root"]:
            raise DistributedPhysicsError("replica predicted a different root")
        signature = self._private.sign(canonical_json_bytes(dict(proposal)))
        return PhysicsVote(
            self.node_id,
            self.public_key.public_bytes_raw(),
            signature,
            proof.new_root,
        )

    def commit(self, intent: ReactionIntent) -> ReactionProof:
        return self.kernel.commit(intent)


class DistributedPhysicsCluster:
    """Generic majority-certified cluster for v0.44+ atomic physics kernels."""

    def __init__(self, kernel_factory: Callable[[], AtomicPhysicsKernel], node_count: int = 3) -> None:
        if node_count < 3:
            raise ValueError("node_count must be at least 3")
        self.kernel_factory = kernel_factory
        self.replicas = {f"p{i}": PhysicsReplica(f"p{i}", kernel_factory()) for i in range(node_count)}
        self.term = 1
        self.index = 0
        self.leader_id = "p0"
        self.certificates: list[PhysicsQuorumCertificate] = []
        self.history: list[ReactionIntent] = []
        self._assert_converged()

    @property
    def quorum(self) -> int:
        return len(self.replicas) // 2 + 1

    @property
    def leader(self) -> PhysicsReplica:
        replica = self.replicas[self.leader_id]
        if not replica.live:
            raise DistributedPhysicsError("leader offline")
        return replica

    def roots(self) -> set[str]:
        return {replica.kernel.root for replica in self.replicas.values() if replica.live}

    def _assert_converged(self) -> str:
        roots = self.roots()
        if len(roots) != 1:
            raise DistributedPhysicsError(f"replica divergence: {roots}")
        return next(iter(roots))

    def elect(self) -> str:
        live = sorted(node_id for node_id, replica in self.replicas.items() if replica.live)
        if len(live) < self.quorum:
            raise DistributedPhysicsError("no election quorum")
        self.term += 1
        self.leader_id = live[0]
        return self.leader_id

    def stop(self, node_id: str) -> None:
        self.replicas[node_id].live = False
        if node_id == self.leader_id:
            self.elect()

    def recover(self, node_id: str) -> None:
        replica = PhysicsReplica(node_id, self.kernel_factory())
        for historical in self.history:
            replay_intent = ReactionIntent(**{**historical.__dict__, "expected_root": replica.kernel.root})
            replica.commit(replay_intent)
        self.replicas[node_id] = replica
        self._assert_converged()

    def apply(self, intent: ReactionIntent, *, expected_term: int | None = None) -> PhysicsQuorumCertificate:
        if expected_term is not None and expected_term != self.term:
            raise DistributedPhysicsError("stale authority term")
        live = [replica for replica in self.replicas.values() if replica.live]
        if len(live) < self.quorum:
            raise DistributedPhysicsError("write quorum unavailable")
        previous_root = self._assert_converged()
        if intent.expected_root != previous_root:
            raise DistributedPhysicsError("stale universe root")
        _, leader_proof = self.leader.kernel.simulate(intent)
        membership = tuple(sorted(
            (node_id, replica.public_key.public_bytes_raw().hex())
            for node_id, replica in self.replicas.items()
        ))
        proposal = {
            "term": self.term,
            "index": self.index + 1,
            "leader_id": self.leader_id,
            "previous_root": previous_root,
            "new_root": leader_proof.new_root,
            "proof_id": leader_proof.proof_id,
            "reaction_id": leader_proof.reaction_id,
            "membership": [list(item) for item in membership],
            "quorum": self.quorum,
        }
        proposal_id = digest("ADAM50:DISTRIBUTED_PHYSICS_PROPOSAL", proposal)
        signed_proposal = {**proposal, "proposal_id": proposal_id}
        votes: list[PhysicsVote] = []
        for replica in live:
            try:
                votes.append(replica.prepare(signed_proposal, intent))
            except (DistributedPhysicsError, ValueError, PermissionError):
                continue
        if len(votes) < self.quorum:
            raise DistributedPhysicsError("proposal validation quorum not reached")
        payload = canonical_json_bytes(signed_proposal)
        for vote in votes:
            try:
                Ed25519PublicKey.from_public_bytes(vote.public_key).verify(vote.signature, payload)
            except InvalidSignature as exc:
                raise DistributedPhysicsError("invalid replica vote") from exc
        proofs = [replica.commit(intent) for replica in live]
        if len({proof.new_root for proof in proofs}) != 1:
            raise DistributedPhysicsError("commit divergence")
        self.index += 1
        self.history.append(intent)
        self._assert_converged()
        certificate = PhysicsQuorumCertificate(
            self.term,
            self.index,
            self.leader_id,
            previous_root,
            proofs[0].new_root,
            proposal_id,
            proofs[0].proof_id,
            membership,
            self.quorum,
            tuple(votes),
            signed_proposal,
        )
        self.certificates.append(certificate)
        return certificate

    def verify_certificate(self, certificate: PhysicsQuorumCertificate) -> bool:
        return self.verify_certificate_with_proposal(certificate, certificate.proposal_payload)

    @staticmethod
    def verify_certificate_with_proposal(certificate: PhysicsQuorumCertificate, proposal: Mapping[str, Any]) -> bool:
        proposal = dict(proposal)
        required = {
            "term", "index", "leader_id", "previous_root", "new_root", "proof_id",
            "reaction_id", "membership", "quorum", "proposal_id",
        }
        if not required <= proposal.keys():
            return False
        if proposal.get("proposal_id") != certificate.proposal_id:
            return False
        if proposal.get("new_root") != certificate.new_root or proposal.get("previous_root") != certificate.previous_root:
            return False
        try:
            membership = tuple((str(node), str(key_hex)) for node, key_hex in proposal["membership"])
            quorum = int(proposal["quorum"])
        except (TypeError, ValueError):
            return False
        if membership != certificate.membership or quorum != certificate.quorum:
            return False
        if len(membership) < 3 or len({node for node, _ in membership}) != len(membership):
            return False
        if len({key for _, key in membership}) != len(membership):
            return False
        expected_quorum = len(membership) // 2 + 1
        if quorum != expected_quorum:
            return False
        unsigned = {key: proposal[key] for key in (
            "term", "index", "leader_id", "previous_root", "new_root", "proof_id",
            "reaction_id", "membership", "quorum",
        )}
        if digest("ADAM50:DISTRIBUTED_PHYSICS_PROPOSAL", unsigned) != certificate.proposal_id:
            return False
        member_keys = dict(membership)
        payload = canonical_json_bytes(proposal)
        valid = 0
        seen: set[str] = set()
        for vote in certificate.votes:
            expected_key = member_keys.get(vote.node_id)
            if vote.node_id in seen or expected_key is None:
                continue
            if vote.public_key.hex() != expected_key or vote.predicted_root != certificate.new_root:
                continue
            try:
                Ed25519PublicKey.from_public_bytes(vote.public_key).verify(vote.signature, payload)
            except (InvalidSignature, ValueError):
                continue
            seen.add(vote.node_id)
            valid += 1
        return valid >= quorum

