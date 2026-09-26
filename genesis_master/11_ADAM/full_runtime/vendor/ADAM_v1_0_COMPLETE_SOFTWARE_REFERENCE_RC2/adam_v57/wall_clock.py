from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from adam_v41.canonical import canonical_json_bytes, digest, sha256_bytes


class WallClockQualificationError(RuntimeError):
    """Raised when real-time qualification evidence is invalid or tampered."""


@dataclass(frozen=True)
class DailyWitness:
    day_index: int
    observed_at_utc: int
    monotonic_elapsed_seconds: float
    universe_root: str
    candidate_id: str
    deployment_digest: str
    metrics_digest: str
    previous_witness: str | None
    witness_id: str
    signature: bytes

    def unsigned(self) -> dict[str, Any]:
        return {
            "day_index": self.day_index,
            "observed_at_utc": self.observed_at_utc,
            "monotonic_elapsed_seconds": self.monotonic_elapsed_seconds,
            "universe_root": self.universe_root,
            "candidate_id": self.candidate_id,
            "deployment_digest": self.deployment_digest,
            "metrics_digest": self.metrics_digest,
            "previous_witness": self.previous_witness,
            "witness_id": self.witness_id,
        }

    @property
    def record_id(self) -> str:
        return digest("ADAM57:DAILY_WITNESS", {**self.unsigned(), "signature": self.signature})

    @classmethod
    def issue(
        cls,
        *,
        private_key: Ed25519PrivateKey,
        witness_id: str,
        day_index: int,
        observed_at_utc: int,
        monotonic_elapsed_seconds: float,
        universe_root: str,
        candidate_id: str,
        deployment_digest: str,
        metrics: Mapping[str, Any],
        previous_witness: str | None,
    ) -> "DailyWitness":
        unsigned = {
            "day_index": int(day_index),
            "observed_at_utc": int(observed_at_utc),
            "monotonic_elapsed_seconds": float(monotonic_elapsed_seconds),
            "universe_root": universe_root,
            "candidate_id": candidate_id,
            "deployment_digest": deployment_digest,
            "metrics_digest": digest("ADAM57:DAILY_METRICS", dict(metrics)),
            "previous_witness": previous_witness,
            "witness_id": witness_id,
        }
        return cls(**unsigned, signature=private_key.sign(canonical_json_bytes(unsigned)))


class RealTimeQualificationController:
    """Signed, restart-safe controller with independently signed daily witnesses.

    The state envelope is signed by a stable controller identity supplied by the
    caller.  Daily witness records are verified against a separate trusted
    witness registry; the controller key is explicitly forbidden from acting as
    a witness key.  Elapsed time cannot jump forward across restarts because the
    signed monotonic floor resumes from the last persisted session value.
    """

    FORMAT = "ADAM57_REAL_TIME_QUALIFICATION_V2"

    def __init__(
        self,
        state_path: str | os.PathLike[str],
        *,
        candidate_id: str,
        deployment_digest: str,
        required_seconds: int = 30 * 24 * 60 * 60,
        minimum_witnesses: int = 30,
        private_key: Ed25519PrivateKey | None = None,
        controller_key_id: str = "qualification-controller",
        trusted_witnesses: Mapping[str, bytes | Ed25519PublicKey] | None = None,
    ) -> None:
        if required_seconds < 24 * 60 * 60:
            raise ValueError("production qualification cannot be configured below one real day")
        if minimum_witnesses < 1:
            raise ValueError("minimum_witnesses must be positive")
        if private_key is None:
            raise ValueError("a stable controller private key is required")
        self.state_path = Path(state_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.candidate_id = candidate_id
        self.deployment_digest = deployment_digest
        self.required_seconds = int(required_seconds)
        self.minimum_witnesses = int(minimum_witnesses)
        self._private = private_key
        self.public_key = self._private.public_key()
        self.controller_key_id = controller_key_id
        self.trusted_witnesses = {
            key: (value.public_bytes_raw() if isinstance(value, Ed25519PublicKey) else bytes(value))
            for key, value in dict(trusted_witnesses or {}).items()
        }
        controller_public = self.public_key.public_bytes_raw()
        if any(value == controller_public for value in self.trusted_witnesses.values()):
            raise ValueError("controller key cannot also be a trusted independent witness key")
        if any(len(value) != 32 for value in self.trusted_witnesses.values()):
            raise ValueError("trusted witness keys must be 32-byte Ed25519 public keys")

        self.started_utc = int(time.time())
        self._session_started_monotonic = time.monotonic()
        self._elapsed_floor_seconds = 0.0
        self._state_sequence = 0
        self._previous_state_hash: str | None = None
        self.witnesses: list[DailyWitness] = []
        self.invalidations: list[dict[str, Any]] = []
        if self.state_path.exists():
            self._load()
        else:
            self._persist()

    def _current_elapsed(self) -> float:
        session = max(0.0, time.monotonic() - self._session_started_monotonic)
        monotonic_total = self._elapsed_floor_seconds + session
        utc_total = max(0.0, time.time() - self.started_utc)
        if utc_total + 300 < monotonic_total:
            raise WallClockQualificationError("wall clock moved backward beyond tolerance")
        return min(utc_total, monotonic_total)

    def _state_payload(self, *, elapsed_floor: float | None = None, sequence: int | None = None) -> dict[str, Any]:
        return {
            "format": self.FORMAT,
            "candidate_id": self.candidate_id,
            "deployment_digest": self.deployment_digest,
            "required_seconds": self.required_seconds,
            "minimum_witnesses": self.minimum_witnesses,
            "started_utc": self.started_utc,
            "elapsed_floor_seconds": self._current_elapsed() if elapsed_floor is None else float(elapsed_floor),
            "state_sequence": self._state_sequence + 1 if sequence is None else int(sequence),
            "previous_state_hash": self._previous_state_hash,
            "controller_key_id": self.controller_key_id,
            "controller_public_key_sha256": sha256_bytes(self.public_key.public_bytes_raw()),
            "trusted_witnesses": {
                witness_id: sha256_bytes(public_key)
                for witness_id, public_key in sorted(self.trusted_witnesses.items())
            },
            "witnesses": [
                {**witness.unsigned(), "signature": witness.signature.hex(), "record_id": witness.record_id}
                for witness in self.witnesses
            ],
            "invalidations": list(self.invalidations),
        }

    def _persist(self) -> None:
        elapsed = self._current_elapsed()
        payload = self._state_payload(elapsed_floor=elapsed, sequence=self._state_sequence + 1)
        signature = self._private.sign(canonical_json_bytes(payload))
        envelope = {
            "payload": payload,
            "signature": signature.hex(),
            "state_hash": digest("ADAM57:SIGNED_STATE", {**payload, "signature": signature}),
        }
        temporary = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
        with temporary.open("wb") as handle:
            handle.write(canonical_json_bytes(envelope))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, self.state_path)
        self._elapsed_floor_seconds = elapsed
        self._session_started_monotonic = time.monotonic()
        self._state_sequence = int(payload["state_sequence"])
        self._previous_state_hash = str(envelope["state_hash"])

    def _load(self) -> None:
        try:
            envelope = json.loads(self.state_path.read_text("utf-8"))
            state = envelope["payload"]
            signature = bytes.fromhex(envelope["signature"])
            self.public_key.verify(signature, canonical_json_bytes(state))
        except (OSError, KeyError, ValueError, json.JSONDecodeError, InvalidSignature) as exc:
            raise WallClockQualificationError("qualification state signature is invalid") from exc
        expected_hash = digest("ADAM57:SIGNED_STATE", {**state, "signature": signature})
        if envelope.get("state_hash") != expected_hash:
            raise WallClockQualificationError("qualification state identity mismatch")
        if state.get("format") != self.FORMAT:
            raise WallClockQualificationError("unsupported qualification state")
        if state.get("candidate_id") != self.candidate_id or state.get("deployment_digest") != self.deployment_digest:
            raise WallClockQualificationError("qualification state belongs to another candidate or deployment")
        if state.get("controller_key_id") != self.controller_key_id:
            raise WallClockQualificationError("qualification controller identity changed")
        if state.get("controller_public_key_sha256") != sha256_bytes(self.public_key.public_bytes_raw()):
            raise WallClockQualificationError("qualification controller key changed")
        trusted_hashes = {key: sha256_bytes(value) for key, value in sorted(self.trusted_witnesses.items())}
        if state.get("trusted_witnesses") != trusted_hashes:
            raise WallClockQualificationError("trusted witness registry changed")
        if int(state["required_seconds"]) != self.required_seconds or int(state["minimum_witnesses"]) != self.minimum_witnesses:
            raise WallClockQualificationError("signed qualification policy differs from requested policy")
        self.started_utc = int(state["started_utc"])
        self._elapsed_floor_seconds = float(state["elapsed_floor_seconds"])
        self._session_started_monotonic = time.monotonic()
        self._state_sequence = int(state["state_sequence"])
        self._previous_state_hash = str(envelope["state_hash"])
        self.witnesses = []
        for row in state.get("witnesses", []):
            witness = DailyWitness(
                day_index=int(row["day_index"]),
                observed_at_utc=int(row["observed_at_utc"]),
                monotonic_elapsed_seconds=float(row["monotonic_elapsed_seconds"]),
                universe_root=str(row["universe_root"]),
                candidate_id=str(row["candidate_id"]),
                deployment_digest=str(row["deployment_digest"]),
                metrics_digest=str(row["metrics_digest"]),
                previous_witness=row.get("previous_witness"),
                witness_id=str(row["witness_id"]),
                signature=bytes.fromhex(row["signature"]),
            )
            if witness.record_id != row.get("record_id"):
                raise WallClockQualificationError("stored witness identity mismatch")
            self.witnesses.append(witness)
        self.invalidations = list(state.get("invalidations", []))
        if not self.verify_witness_chain():
            raise WallClockQualificationError("stored witness chain is invalid")

    def elapsed_seconds(self) -> float:
        return self._current_elapsed()

    def witness_template(
        self,
        *,
        universe_root: str,
        metrics: Mapping[str, Any],
        witness_id: str,
        observed_at_utc: int | None = None,
    ) -> dict[str, Any]:
        if witness_id not in self.trusted_witnesses:
            raise WallClockQualificationError("witness is not present in the trusted registry")
        now = int(time.time()) if observed_at_utc is None else int(observed_at_utc)
        elapsed = self.elapsed_seconds()
        day_index = int(elapsed // (24 * 60 * 60)) + 1
        return {
            "witness_id": witness_id,
            "day_index": day_index,
            "observed_at_utc": now,
            "monotonic_elapsed_seconds": elapsed,
            "universe_root": universe_root,
            "candidate_id": self.candidate_id,
            "deployment_digest": self.deployment_digest,
            "metrics": dict(metrics),
            "previous_witness": self.witnesses[-1].record_id if self.witnesses else None,
        }

    def submit_daily_witness(self, witness: DailyWitness) -> DailyWitness:
        public_raw = self.trusted_witnesses.get(witness.witness_id)
        if public_raw is None:
            raise WallClockQualificationError("witness is not trusted")
        if witness.candidate_id != self.candidate_id or witness.deployment_digest != self.deployment_digest:
            raise WallClockQualificationError("witness belongs to another qualification")
        if witness.previous_witness != (self.witnesses[-1].record_id if self.witnesses else None):
            raise WallClockQualificationError("witness chain link is invalid")
        if self.witnesses and witness.day_index <= self.witnesses[-1].day_index:
            raise WallClockQualificationError("only one witness is accepted per elapsed qualification day")
        expected_day = int(max(0, witness.observed_at_utc - self.started_utc) // (24 * 60 * 60)) + 1
        if witness.day_index != expected_day:
            raise WallClockQualificationError("witness day index is inconsistent with signed start time")
        current_elapsed = self.elapsed_seconds()
        if witness.monotonic_elapsed_seconds > current_elapsed + 300:
            raise WallClockQualificationError("witness claims elapsed time beyond controller evidence")
        try:
            Ed25519PublicKey.from_public_bytes(public_raw).verify(
                witness.signature, canonical_json_bytes(witness.unsigned())
            )
        except (InvalidSignature, ValueError) as exc:
            raise WallClockQualificationError("witness signature is invalid") from exc
        self.witnesses.append(witness)
        self._persist()
        return witness

    def verify_witness_chain(self) -> bool:
        previous = None
        last_day = 0
        last_observed = self.started_utc - 1
        for witness in self.witnesses:
            public_raw = self.trusted_witnesses.get(witness.witness_id)
            if public_raw is None:
                return False
            if witness.candidate_id != self.candidate_id or witness.deployment_digest != self.deployment_digest:
                return False
            if witness.previous_witness != previous or witness.day_index <= last_day:
                return False
            if witness.observed_at_utc <= last_observed:
                return False
            expected_day = int(max(0, witness.observed_at_utc - self.started_utc) // (24 * 60 * 60)) + 1
            if witness.day_index != expected_day:
                return False
            try:
                Ed25519PublicKey.from_public_bytes(public_raw).verify(
                    witness.signature, canonical_json_bytes(witness.unsigned())
                )
            except (InvalidSignature, ValueError):
                return False
            previous = witness.record_id
            last_day = witness.day_index
            last_observed = witness.observed_at_utc
        return True

    def invalidate(self, reason: str) -> None:
        if not reason.strip():
            raise ValueError("invalidation reason is required")
        self.invalidations.append({"observed_at": int(time.time()), "reason": reason})
        self._persist()

    def certification_status(self) -> Mapping[str, Any]:
        elapsed = self.elapsed_seconds()
        blockers: list[str] = []
        if elapsed < self.required_seconds:
            blockers.append("required real elapsed time has not completed")
        if len(self.witnesses) < self.minimum_witnesses:
            blockers.append("insufficient daily witness records")
        if not self.verify_witness_chain():
            blockers.append("daily witness chain is invalid")
        if not self.trusted_witnesses:
            blockers.append("no independent trusted witnesses configured")
        if self.witnesses and self.witnesses[-1].observed_at_utc - self.started_utc < self.required_seconds:
            blockers.append("independent witness span does not cover the required duration")
        if self.invalidations:
            blockers.append("qualification has recorded invalidating incidents")
        return {
            "candidate_id": self.candidate_id,
            "elapsed_seconds": elapsed,
            "required_seconds": self.required_seconds,
            "witnesses": len(self.witnesses),
            "minimum_witnesses": self.minimum_witnesses,
            "trusted_witness_registry_size": len(self.trusted_witnesses),
            "state_sequence": self._state_sequence,
            "certified": not blockers,
            "blockers": blockers,
        }
