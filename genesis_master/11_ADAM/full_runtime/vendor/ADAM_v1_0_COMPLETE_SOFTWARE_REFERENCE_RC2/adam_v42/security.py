from __future__ import annotations

import json
import time
from dataclasses import dataclass
from enum import IntEnum
from typing import Iterable

from adam_v41.authority import Authority
from adam_v41.canonical import canonical_json_bytes, digest


class SecurityLabel(IntEnum):
    PUBLIC = 0
    INTERNAL = 1
    CONFIDENTIAL = 2
    RESTRICTED = 3


class AuthorizationError(PermissionError):
    pass


@dataclass(frozen=True)
class PurposeGrant:
    subject: str
    purposes: tuple[str, ...]
    maximum_label: SecurityLabel
    expires_ns: int
    nonce: str
    authority_id: str
    signature: str

    def unsigned(self) -> dict[str, object]:
        return {
            "subject": self.subject,
            "purposes": list(self.purposes),
            "maximum_label": int(self.maximum_label),
            "expires_ns": self.expires_ns,
            "nonce": self.nonce,
            "authority_id": self.authority_id,
        }


class ClosureAuthorization:
    """Purpose-bound graph-closure authorization with inference labels."""

    def __init__(self, authority: Authority):
        self.authority = authority
        self.node_labels: dict[str, SecurityLabel] = {}
        self.edges: dict[str, set[str]] = {}
        self.restricted_combinations: dict[frozenset[str], SecurityLabel] = {}

    def issue(self, subject: str, purposes: Iterable[str], maximum_label: SecurityLabel, ttl_seconds: int = 300) -> PurposeGrant:
        unsigned = {
            "subject": subject,
            "purposes": sorted(set(purposes)),
            "maximum_label": int(maximum_label),
            "expires_ns": time.time_ns() + int(ttl_seconds * 1e9),
            "nonce": digest("ADAM42:GRANT_NONCE", [subject, time.time_ns()]),
            "authority_id": self.authority.authority_id,
        }
        sig = self.authority.sign(canonical_json_bytes(unsigned))
        return PurposeGrant(
            subject, tuple(unsigned["purposes"]), maximum_label, int(unsigned["expires_ns"]),
            str(unsigned["nonce"]), self.authority.authority_id, sig,
        )

    def verify_grant(self, grant: PurposeGrant, purpose: str) -> None:
        if grant.authority_id != self.authority.authority_id:
            raise AuthorizationError("Grant authority mismatch")
        if time.time_ns() >= grant.expires_ns:
            raise AuthorizationError("Grant expired")
        if purpose not in grant.purposes:
            raise AuthorizationError("Purpose not granted")
        if not Authority.verify(self.authority.public_key_hex, canonical_json_bytes(grant.unsigned()), grant.signature):
            raise AuthorizationError("Grant signature invalid")

    def label(self, node: str, level: SecurityLabel) -> None:
        self.node_labels[node] = level

    def connect(self, source: str, target: str) -> None:
        self.edges.setdefault(source, set()).add(target)

    def protect_combination(self, members: Iterable[str], resulting_label: SecurityLabel = SecurityLabel.RESTRICTED) -> None:
        self.restricted_combinations[frozenset(members)] = resulting_label

    def closure(self, seeds: Iterable[str], max_depth: int = 8) -> set[str]:
        seen = set(seeds)
        frontier = set(seen)
        for _ in range(max_depth):
            nxt = {target for node in frontier for target in self.edges.get(node, ()) if target not in seen}
            if not nxt:
                break
            seen.update(nxt)
            frontier = nxt
        return seen

    def authorize(self, grant: PurposeGrant, purpose: str, requested_nodes: Iterable[str]) -> set[str]:
        self.verify_grant(grant, purpose)
        requested = set(requested_nodes)
        closure = self.closure(requested)
        required = max((self.node_labels.get(node, SecurityLabel.PUBLIC) for node in closure), default=SecurityLabel.PUBLIC)
        for members, label in self.restricted_combinations.items():
            if members.issubset(closure):
                required = max(required, label)
        if required > grant.maximum_label:
            raise AuthorizationError(
                f"Inference closure requires {required.name}, grant permits {grant.maximum_label.name}"
            )
        return closure
