from __future__ import annotations

import json
import multiprocessing as mp
import os
import socket
import struct
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from adam_v41.canonical import canonical_json_bytes, digest


class NetworkAuthorityError(RuntimeError):
    """Raised when the network authority reference loses safety or quorum."""


_GENESIS_ROOT = digest("ADAM53:NETWORK_GENESIS", {"version": 2})
_MAX_FRAME = 8 * 1024 * 1024


def _recv_exact(sock: socket.socket, length: int) -> bytes:
    chunks: list[bytes] = []
    remaining = length
    while remaining:
        chunk = sock.recv(remaining)
        if not chunk:
            raise ConnectionError("connection closed while receiving frame")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _send_frame(sock: socket.socket, payload: Mapping[str, Any]) -> None:
    encoded = canonical_json_bytes(dict(payload))
    if len(encoded) > _MAX_FRAME:
        raise ValueError("network authority frame exceeds maximum size")
    sock.sendall(struct.pack(">I", len(encoded)) + encoded)


def _recv_frame(sock: socket.socket) -> dict[str, Any]:
    size = struct.unpack(">I", _recv_exact(sock, 4))[0]
    if size > _MAX_FRAME:
        raise ValueError("network authority frame exceeds maximum size")
    decoded = json.loads(_recv_exact(sock, size).decode("utf-8"))
    if not isinstance(decoded, dict):
        raise ValueError("network authority frame must be an object")
    return decoded


def _record_root(sequence: int, previous_root: str, payload: Mapping[str, Any]) -> str:
    return digest(
        "ADAM53:NETWORK_COMMIT",
        {"sequence": sequence, "previous_root": previous_root, "payload": dict(payload)},
    )


def _payload_hash(payload: Mapping[str, Any]) -> str:
    return digest("ADAM53:PAYLOAD", dict(payload))


def _membership_digest(epoch: int, members: Mapping[str, bytes]) -> str:
    return digest(
        "ADAM53:MEMBERSHIP_EPOCH",
        {"epoch": epoch, "members": sorted((node_id, key.hex()) for node_id, key in members.items())},
    )


def _load_log(path: Path) -> tuple[list[dict[str, Any]], str, int]:
    records: list[dict[str, Any]] = []
    root = _GENESIS_ROOT
    sequence = 0
    if not path.exists():
        return records, root, sequence
    for line_number, raw in enumerate(path.read_bytes().splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            record = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise NetworkAuthorityError(f"invalid node log record at line {line_number}") from exc
        expected_seq = sequence + 1
        expected_root = _record_root(expected_seq, root, record["payload"])
        if (
            record.get("sequence") != expected_seq
            or record.get("previous_root") != root
            or record.get("new_root") != expected_root
        ):
            raise NetworkAuthorityError(f"node log chain invalid at line {line_number}")
        records.append(record)
        root = expected_root
        sequence = expected_seq
    return records, root, sequence


def _replace_log(path: Path, records: Iterable[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], str, int]:
    normalized: list[dict[str, Any]] = []
    root = _GENESIS_ROOT
    sequence = 0
    for source in records:
        record = dict(source)
        sequence += 1
        expected = _record_root(sequence, root, record["payload"])
        if record.get("sequence") != sequence or record.get("previous_root") != root or record.get("new_root") != expected:
            raise NetworkAuthorityError("synchronization log is not a valid authority chain")
        normalized.append(record)
        root = expected
    temporary = path.with_suffix(".tmp")
    with temporary.open("wb") as handle:
        for record in normalized:
            handle.write(canonical_json_bytes(record) + b"\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    return normalized, root, sequence


def _node_server(
    node_id: str,
    host: str,
    port: int,
    storage_dir: str,
    node_private_raw: bytes,
    coordinator_public_raw: bytes,
    initial_membership_epoch: int,
    initial_membership_digest: str,
    ready: Any,
) -> None:
    directory = Path(storage_dir)
    directory.mkdir(parents=True, exist_ok=True)
    log_path = directory / "authority.jsonl"
    records, root, sequence = _load_log(log_path)
    membership_epoch = initial_membership_epoch
    membership_digest = initial_membership_digest
    node_private = Ed25519PrivateKey.from_private_bytes(node_private_raw)
    coordinator_public = Ed25519PublicKey.from_public_bytes(coordinator_public_raw)
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind((host, port))
    listener.listen(16)
    listener.settimeout(0.5)
    ready.set()
    running = True
    while running:
        try:
            connection, _ = listener.accept()
        except socket.timeout:
            continue
        with connection:
            connection.settimeout(5.0)
            try:
                request = _recv_frame(connection)
                signature_hex = request.pop("coordinator_signature", None)
                if not isinstance(signature_hex, str):
                    raise PermissionError("missing coordinator signature")
                coordinator_public.verify(bytes.fromhex(signature_hex), canonical_json_bytes(request))
                command = request.get("command")
                if command == "health":
                    response = {
                        "ok": True,
                        "node_id": node_id,
                        "root": root,
                        "sequence": sequence,
                        "membership_epoch": membership_epoch,
                        "membership_digest": membership_digest,
                    }
                elif command in {"prepare", "commit"}:
                    if int(request.get("membership_epoch", -1)) != membership_epoch:
                        raise NetworkAuthorityError("membership epoch mismatch")
                    if request.get("membership_digest") != membership_digest:
                        raise NetworkAuthorityError("membership digest mismatch")
                    expected_sequence = sequence + 1
                    if request.get("previous_root") != root or request.get("sequence") != expected_sequence:
                        raise NetworkAuthorityError("stale root or sequence")
                    payload = request.get("payload")
                    if not isinstance(payload, dict):
                        raise ValueError("payload must be an object")
                    predicted = _record_root(expected_sequence, root, payload)
                    payload_hash = _payload_hash(payload)
                    if request.get("new_root") not in {None, predicted}:
                        raise NetworkAuthorityError("proposed root does not match deterministic prediction")
                    if request.get("payload_hash") != payload_hash:
                        raise NetworkAuthorityError("payload hash mismatch")
                    if command == "commit":
                        record = {
                            "sequence": expected_sequence,
                            "previous_root": root,
                            "payload": payload,
                            "new_root": predicted,
                            "membership_epoch": membership_epoch,
                            "membership_digest": membership_digest,
                        }
                        with log_path.open("ab") as handle:
                            handle.write(canonical_json_bytes(record) + b"\n")
                            handle.flush()
                            os.fsync(handle.fileno())
                        records.append(record)
                        root = predicted
                        sequence = expected_sequence
                    response = {
                        "ok": True,
                        "node_id": node_id,
                        "root": root if command == "commit" else predicted,
                        "previous_root": request["previous_root"],
                        "payload_hash": payload_hash,
                        "sequence": sequence if command == "commit" else expected_sequence,
                        "phase": command,
                        "membership_epoch": membership_epoch,
                        "membership_digest": membership_digest,
                    }
                elif command == "membership_update":
                    next_epoch = int(request.get("membership_epoch", -1))
                    next_digest = request.get("membership_digest")
                    if next_epoch != membership_epoch + 1 or not isinstance(next_digest, str):
                        raise NetworkAuthorityError("invalid membership transition")
                    membership_epoch = next_epoch
                    membership_digest = next_digest
                    response = {
                        "ok": True,
                        "node_id": node_id,
                        "root": root,
                        "sequence": sequence,
                        "phase": "membership_update",
                        "membership_epoch": membership_epoch,
                        "membership_digest": membership_digest,
                    }
                elif command == "snapshot":
                    response = {
                        "ok": True,
                        "node_id": node_id,
                        "root": root,
                        "sequence": sequence,
                        "records": records,
                        "membership_epoch": membership_epoch,
                        "membership_digest": membership_digest,
                    }
                elif command == "sync":
                    if int(request.get("membership_epoch", -1)) != membership_epoch:
                        raise NetworkAuthorityError("membership epoch mismatch during sync")
                    source_records = request.get("records")
                    if not isinstance(source_records, list):
                        raise ValueError("sync records must be an array")
                    records, root, sequence = _replace_log(log_path, source_records)
                    response = {
                        "ok": True,
                        "node_id": node_id,
                        "root": root,
                        "sequence": sequence,
                        "phase": "sync",
                        "membership_epoch": membership_epoch,
                        "membership_digest": membership_digest,
                    }
                elif command == "shutdown":
                    response = {
                        "ok": True,
                        "node_id": node_id,
                        "root": root,
                        "sequence": sequence,
                        "membership_epoch": membership_epoch,
                        "membership_digest": membership_digest,
                    }
                    running = False
                else:
                    raise ValueError("unsupported network authority command")
            except (ValueError, KeyError, PermissionError, NetworkAuthorityError, InvalidSignature) as exc:
                response = {"ok": False, "node_id": node_id, "error": type(exc).__name__, "message": str(exc)}
            unsigned = dict(response)
            response["node_signature"] = node_private.sign(canonical_json_bytes(unsigned)).hex()
            _send_frame(connection, response)
    listener.close()


@dataclass(frozen=True)
class NodeEndpoint:
    node_id: str
    host: str
    port: int
    public_key: bytes
    storage_dir: str


@dataclass(frozen=True)
class NetworkVote:
    node_id: str
    phase: str
    sequence: int
    previous_root: str
    new_root: str
    payload_hash: str
    membership_epoch: int
    membership_digest: str
    signature: bytes

    def signed_payload(self) -> dict[str, Any]:
        return {
            "ok": True,
            "node_id": self.node_id,
            "root": self.new_root,
            "previous_root": self.previous_root,
            "payload_hash": self.payload_hash,
            "sequence": self.sequence,
            "phase": self.phase,
            "membership_epoch": self.membership_epoch,
            "membership_digest": self.membership_digest,
        }


@dataclass(frozen=True)
class MembershipApproval:
    node_id: str
    proposal_hash: str
    signature: bytes


@dataclass(frozen=True)
class MembershipEpoch:
    epoch: int
    members: tuple[tuple[str, str], ...]
    membership_digest: str
    previous_digest: str | None
    approvals: tuple[MembershipApproval, ...]


@dataclass(frozen=True)
class NetworkQuorumCertificate:
    sequence: int
    previous_root: str
    new_root: str
    payload_hash: str
    membership_epoch: int
    membership_digest: str
    membership: tuple[tuple[str, str], ...]
    quorum: int
    prepare_votes: tuple[NetworkVote, ...]
    commit_votes: tuple[NetworkVote, ...]

    @property
    def votes(self) -> tuple[NetworkVote, ...]:
        """Compatibility view: durable commit votes are the authoritative votes."""
        return self.commit_votes

    @property
    def certificate_id(self) -> str:
        return digest(
            "ADAM53:NETWORK_CERTIFICATE_V2",
            {
                **asdict(self),
                "prepare_votes": [asdict(vote) for vote in self.prepare_votes],
                "commit_votes": [asdict(vote) for vote in self.commit_votes],
            },
        )


class GovernedMembership:
    def __init__(self, members: Mapping[str, bytes]) -> None:
        if len(members) < 3:
            raise ValueError("at least three members are required")
        if any(len(value) != 32 for value in members.values()):
            raise ValueError("member public keys must be 32-byte Ed25519 keys")
        self.epoch = 1
        self.members = dict(members)
        digest_value = _membership_digest(1, self.members)
        self.history: list[MembershipEpoch] = [
            MembershipEpoch(1, tuple(sorted((k, v.hex()) for k, v in self.members.items())), digest_value, None, ())
        ]

    @property
    def quorum(self) -> int:
        return len(self.members) // 2 + 1

    @property
    def membership_digest(self) -> str:
        return self.history[-1].membership_digest

    def snapshot(self, epoch: int) -> MembershipEpoch | None:
        return next((entry for entry in self.history if entry.epoch == epoch), None)

    def proposal_hash(self, *, add: Mapping[str, bytes] | None = None, remove: Iterable[str] = ()) -> str:
        return digest(
            "ADAM53:MEMBERSHIP_CHANGE",
            {
                "current_epoch": self.epoch,
                "current_digest": self.membership_digest,
                "add": sorted((k, v.hex()) for k, v in dict(add or {}).items()),
                "remove": sorted(set(remove)),
            },
        )

    def change(
        self,
        *,
        add: Mapping[str, bytes] | None = None,
        remove: Iterable[str] = (),
        approvals: Iterable[MembershipApproval],
    ) -> int:
        proposal_hash = self.proposal_hash(add=add, remove=remove)
        valid: set[str] = set()
        for approval in approvals:
            public = self.members.get(approval.node_id)
            if public is None or approval.node_id in valid or approval.proposal_hash != proposal_hash:
                continue
            try:
                Ed25519PublicKey.from_public_bytes(public).verify(
                    approval.signature,
                    canonical_json_bytes({"node_id": approval.node_id, "proposal_hash": proposal_hash}),
                )
            except (InvalidSignature, ValueError):
                continue
            valid.add(approval.node_id)
        if len(valid) < self.quorum:
            raise PermissionError("membership change lacks cryptographic current-member quorum")
        updated = dict(self.members)
        for node_id in remove:
            updated.pop(node_id, None)
        updated.update(dict(add or {}))
        if len(updated) < 3:
            raise ValueError("membership cannot fall below three nodes")
        if any(len(value) != 32 for value in updated.values()):
            raise ValueError("member public keys must be 32-byte Ed25519 keys")
        previous_digest = self.membership_digest
        self.epoch += 1
        self.members = updated
        next_digest = _membership_digest(self.epoch, updated)
        self.history.append(
            MembershipEpoch(
                self.epoch,
                tuple(sorted((k, v.hex()) for k, v in updated.items())),
                next_digest,
                previous_digest,
                tuple(sorted(approvals, key=lambda item: item.node_id)),
            )
        )
        return self.epoch


class NetworkAuthorityCluster:
    """Socket/process authority reference with durable commit certificates."""

    def __init__(self, directory: str | os.PathLike[str], *, node_count: int = 3, start_timeout: float = 8.0) -> None:
        if node_count < 3:
            raise ValueError("node_count must be at least three")
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.host = "127.0.0.1"
        self._coordinator_private = Ed25519PrivateKey.generate()
        self._context = mp.get_context("spawn")
        self._processes: dict[str, mp.Process] = {}
        self._private_keys: dict[str, bytes] = {}
        self.endpoints: dict[str, NodeEndpoint] = {}
        self.partitioned: set[str] = set()
        self.certificates: list[NetworkQuorumCertificate] = []
        for index in range(node_count):
            node_id = f"net-{index}"
            private = Ed25519PrivateKey.generate()
            self._private_keys[node_id] = private.private_bytes(
                serialization.Encoding.Raw,
                serialization.PrivateFormat.Raw,
                serialization.NoEncryption(),
            )
            port = self._free_port()
            self.endpoints[node_id] = NodeEndpoint(
                node_id,
                self.host,
                port,
                private.public_key().public_bytes_raw(),
                str(self.directory / node_id),
            )
        self.membership = GovernedMembership({node_id: ep.public_key for node_id, ep in self.endpoints.items()})
        for node_id in self.endpoints:
            self._start_node(node_id, start_timeout)
        self._assert_converged()

    def _free_port(self) -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((self.host, 0))
            return int(sock.getsockname()[1])

    def _start_node(self, node_id: str, timeout: float) -> None:
        endpoint = self.endpoints[node_id]
        ready = self._context.Event()
        process = self._context.Process(
            target=_node_server,
            args=(
                node_id,
                endpoint.host,
                endpoint.port,
                endpoint.storage_dir,
                self._private_keys[node_id],
                self._coordinator_private.public_key().public_bytes_raw(),
                self.membership.epoch,
                self.membership.membership_digest,
                ready,
            ),
            name=f"adam53-{node_id}",
        )
        process.start()
        if not ready.wait(timeout):
            process.terminate()
            process.join(2)
            raise NetworkAuthorityError(f"node {node_id} failed to start")
        self._processes[node_id] = process

    def _signed_request(self, request: Mapping[str, Any]) -> dict[str, Any]:
        unsigned = dict(request)
        return {**unsigned, "coordinator_signature": self._coordinator_private.sign(canonical_json_bytes(unsigned)).hex()}

    def _request(self, node_id: str, request: Mapping[str, Any], *, timeout: float = 3.0) -> dict[str, Any]:
        if node_id in self.partitioned:
            raise NetworkAuthorityError(f"node {node_id} is partitioned")
        endpoint = self.endpoints[node_id]
        process = self._processes.get(node_id)
        if process is None or not process.is_alive():
            raise NetworkAuthorityError(f"node {node_id} is offline")
        with socket.create_connection((endpoint.host, endpoint.port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            _send_frame(sock, self._signed_request(request))
            response = _recv_frame(sock)
        signature_hex = response.pop("node_signature", None)
        if not isinstance(signature_hex, str):
            raise NetworkAuthorityError("node response lacks signature")
        try:
            Ed25519PublicKey.from_public_bytes(endpoint.public_key).verify(
                bytes.fromhex(signature_hex), canonical_json_bytes(response)
            )
        except (InvalidSignature, ValueError) as exc:
            raise NetworkAuthorityError("node response signature is invalid") from exc
        response["node_signature"] = signature_hex
        if not response.get("ok"):
            raise NetworkAuthorityError(f"node {node_id} rejected request: {response.get('message')}")
        return response

    def health(self) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for node_id in self.endpoints:
            try:
                result[node_id] = self._request(node_id, {"command": "health"})
            except NetworkAuthorityError as exc:
                result[node_id] = {"ok": False, "message": str(exc)}
        return result

    def _assert_converged(self) -> tuple[str, int]:
        states = [value for value in self.health().values() if value.get("ok")]
        if len(states) < self.membership.quorum:
            raise NetworkAuthorityError("network authority lacks a live quorum")
        roots = {(state["root"], state["sequence"]) for state in states}
        epochs = {(state["membership_epoch"], state["membership_digest"]) for state in states}
        if len(roots) != 1 or epochs != {(self.membership.epoch, self.membership.membership_digest)}:
            raise NetworkAuthorityError(f"network authority nodes diverged: roots={roots} epochs={epochs}")
        return next(iter(roots))

    @staticmethod
    def _vote_from_response(response: Mapping[str, Any]) -> NetworkVote:
        return NetworkVote(
            node_id=str(response["node_id"]),
            phase=str(response["phase"]),
            sequence=int(response["sequence"]),
            previous_root=str(response["previous_root"]),
            new_root=str(response["root"]),
            payload_hash=str(response["payload_hash"]),
            membership_epoch=int(response["membership_epoch"]),
            membership_digest=str(response["membership_digest"]),
            signature=bytes.fromhex(str(response["node_signature"])),
        )

    def apply(self, payload: Mapping[str, Any]) -> NetworkQuorumCertificate:
        if not isinstance(payload, Mapping) or not payload:
            raise ValueError("commit payload must be a non-empty mapping")
        previous_root, previous_sequence = self._assert_converged()
        sequence = previous_sequence + 1
        new_root = _record_root(sequence, previous_root, payload)
        payload_hash = _payload_hash(payload)
        common = {
            "sequence": sequence,
            "previous_root": previous_root,
            "new_root": new_root,
            "payload": dict(payload),
            "payload_hash": payload_hash,
            "membership_epoch": self.membership.epoch,
            "membership_digest": self.membership.membership_digest,
        }
        prepare_votes: list[NetworkVote] = []
        prepared: list[str] = []
        for node_id in sorted(self.membership.members):
            try:
                response = self._request(node_id, {"command": "prepare", **common})
            except NetworkAuthorityError:
                continue
            vote = self._vote_from_response(response)
            if vote.phase == "prepare" and vote.new_root == new_root:
                prepared.append(node_id)
                prepare_votes.append(vote)
        if len(prepared) < self.membership.quorum:
            raise NetworkAuthorityError("prepare quorum was not reached")
        commit_votes: list[NetworkVote] = []
        for node_id in prepared:
            try:
                response = self._request(node_id, {"command": "commit", **common})
            except NetworkAuthorityError:
                continue
            vote = self._vote_from_response(response)
            if vote.phase == "commit" and vote.new_root == new_root:
                commit_votes.append(vote)
        if len(commit_votes) < self.membership.quorum:
            raise NetworkAuthorityError("durable commit quorum was not reached")
        membership = tuple(sorted((node_id, public.hex()) for node_id, public in self.membership.members.items()))
        certificate = NetworkQuorumCertificate(
            sequence,
            previous_root,
            new_root,
            payload_hash,
            self.membership.epoch,
            self.membership.membership_digest,
            membership,
            self.membership.quorum,
            tuple(prepare_votes),
            tuple(commit_votes),
        )
        if not self.verify_certificate(certificate, payload):
            raise NetworkAuthorityError("internally produced durable certificate failed verification")
        self.certificates.append(certificate)
        return certificate

    def _verify_votes(
        self,
        votes: Iterable[NetworkVote],
        *,
        phase: str,
        certificate: NetworkQuorumCertificate,
        members: Mapping[str, str],
    ) -> set[str]:
        valid: set[str] = set()
        for vote in votes:
            if vote.node_id in valid or vote.node_id not in members:
                continue
            if (
                vote.phase != phase
                or vote.sequence != certificate.sequence
                or vote.previous_root != certificate.previous_root
                or vote.new_root != certificate.new_root
                or vote.payload_hash != certificate.payload_hash
                or vote.membership_epoch != certificate.membership_epoch
                or vote.membership_digest != certificate.membership_digest
            ):
                continue
            try:
                Ed25519PublicKey.from_public_bytes(bytes.fromhex(members[vote.node_id])).verify(
                    vote.signature, canonical_json_bytes(vote.signed_payload())
                )
            except (InvalidSignature, ValueError):
                continue
            valid.add(vote.node_id)
        return valid

    def verify_certificate(self, certificate: NetworkQuorumCertificate, payload: Mapping[str, Any]) -> bool:
        if certificate.payload_hash != _payload_hash(payload):
            return False
        if certificate.new_root != _record_root(certificate.sequence, certificate.previous_root, payload):
            return False
        epoch = self.membership.snapshot(certificate.membership_epoch)
        if epoch is None or epoch.membership_digest != certificate.membership_digest:
            return False
        if epoch.members != certificate.membership:
            return False
        members = dict(certificate.membership)
        if certificate.quorum != len(members) // 2 + 1 or len(members) < 3:
            return False
        prepare = self._verify_votes(certificate.prepare_votes, phase="prepare", certificate=certificate, members=members)
        commit = self._verify_votes(certificate.commit_votes, phase="commit", certificate=certificate, members=members)
        return len(prepare) >= certificate.quorum and len(commit) >= certificate.quorum

    def create_membership_approval(
        self, node_id: str, *, add: Mapping[str, bytes] | None = None, remove: Iterable[str] = ()
    ) -> MembershipApproval:
        if node_id not in self.membership.members:
            raise KeyError(node_id)
        proposal = self.membership.proposal_hash(add=add, remove=remove)
        private = Ed25519PrivateKey.from_private_bytes(self._private_keys[node_id])
        signature = private.sign(canonical_json_bytes({"node_id": node_id, "proposal_hash": proposal}))
        return MembershipApproval(node_id, proposal, signature)

    def change_membership(
        self,
        *,
        add: Mapping[str, bytes] | None = None,
        remove: Iterable[str] = (),
        approvals: Iterable[MembershipApproval],
    ) -> int:
        old_members = set(self.membership.members)
        epoch = self.membership.change(add=add, remove=remove, approvals=approvals)
        for node_id in sorted(old_members & set(self.endpoints)):
            if self._processes[node_id].is_alive() and node_id not in self.partitioned:
                self._request(
                    node_id,
                    {
                        "command": "membership_update",
                        "membership_epoch": epoch,
                        "membership_digest": self.membership.membership_digest,
                    },
                )
        return epoch

    def partition(self, node_ids: Iterable[str]) -> None:
        for node_id in node_ids:
            if node_id not in self.endpoints:
                raise KeyError(node_id)
            self.partitioned.add(node_id)

    def heal(self, node_ids: Iterable[str] | None = None) -> None:
        targets = set(node_ids or self.partitioned)
        self.partitioned -= targets
        live_sources = [
            node_id
            for node_id in self.endpoints
            if node_id not in targets and self._processes[node_id].is_alive()
        ]
        if not live_sources:
            live_sources = [node_id for node_id in self.endpoints if self._processes[node_id].is_alive()]
        if not live_sources:
            raise NetworkAuthorityError("no live source available for healing")
        snapshot = self._request(live_sources[0], {"command": "snapshot"})
        for node_id in targets:
            if self._processes[node_id].is_alive():
                state = self._request(node_id, {"command": "health"})
                while state["membership_epoch"] < self.membership.epoch:
                    self._request(
                        node_id,
                        {
                            "command": "membership_update",
                            "membership_epoch": state["membership_epoch"] + 1,
                            "membership_digest": self.membership.snapshot(state["membership_epoch"] + 1).membership_digest,
                        },
                    )
                    state = self._request(node_id, {"command": "health"})
                self._request(
                    node_id,
                    {
                        "command": "sync",
                        "records": snapshot["records"],
                        "membership_epoch": self.membership.epoch,
                    },
                )
        self._assert_converged()

    def stop_node(self, node_id: str) -> None:
        process = self._processes[node_id]
        if process.is_alive():
            process.terminate()
            process.join(3)
        if process.is_alive():
            process.kill()
            process.join(2)

    def restart_node(self, node_id: str) -> None:
        self.stop_node(node_id)
        self._start_node(node_id, 8.0)

    def recover_node(self, node_id: str) -> None:
        self.restart_node(node_id)
        sources = [
            other
            for other in self.endpoints
            if other != node_id and self._processes[other].is_alive() and other not in self.partitioned
        ]
        if not sources:
            raise NetworkAuthorityError("no source node available for recovery")
        snapshot = self._request(sources[0], {"command": "snapshot"})
        self._request(
            node_id,
            {"command": "sync", "records": snapshot["records"], "membership_epoch": self.membership.epoch},
        )
        self._assert_converged()

    def close(self) -> None:
        for node_id, process in list(self._processes.items()):
            if process.is_alive():
                try:
                    self._request(node_id, {"command": "shutdown"}, timeout=1.0)
                except (NetworkAuthorityError, OSError):
                    process.terminate()
                process.join(3)
            if process.is_alive():
                process.kill()
                process.join(2)

    def __enter__(self) -> "NetworkAuthorityCluster":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()
