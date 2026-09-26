from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, order=True)
class HLCTimestamp:
    physical_ns: int
    logical: int
    node_id: str

    def canonical(self) -> dict[str, int | str]:
        return {"physical_ns": self.physical_ns, "logical": self.logical, "node_id": self.node_id}


class HybridLogicalClock:
    """Thread-safe HLC suitable for causal ordering across bounded ADAM nodes."""

    def __init__(self, node_id: str, now_ns=time.time_ns):
        self.node_id = node_id
        self._now_ns = now_ns
        self._physical = 0
        self._logical = 0
        self._lock = threading.Lock()

    def tick(self) -> HLCTimestamp:
        with self._lock:
            now = int(self._now_ns())
            if now > self._physical:
                self._physical, self._logical = now, 0
            else:
                self._logical += 1
            return HLCTimestamp(self._physical, self._logical, self.node_id)

    def merge(self, remote: HLCTimestamp) -> HLCTimestamp:
        with self._lock:
            now = int(self._now_ns())
            maximum = max(now, self._physical, remote.physical_ns)
            if maximum == self._physical == remote.physical_ns:
                logical = max(self._logical, remote.logical) + 1
            elif maximum == self._physical:
                logical = self._logical + 1
            elif maximum == remote.physical_ns:
                logical = remote.logical + 1
            else:
                logical = 0
            self._physical, self._logical = maximum, logical
            return HLCTimestamp(maximum, logical, self.node_id)


@dataclass(frozen=True)
class UncertainInstant:
    earliest_ns: int
    latest_ns: int

    def __post_init__(self) -> None:
        if self.latest_ns < self.earliest_ns:
            raise ValueError("latest_ns must be >= earliest_ns")


@dataclass(frozen=True)
class ValidInterval:
    start_ns: int
    end_ns: int | None = None

    def contains(self, instant_ns: int) -> bool:
        return instant_ns >= self.start_ns and (self.end_ns is None or instant_ns < self.end_ns)

    def relation(self, other: "ValidInterval") -> Literal[
        "BEFORE", "AFTER", "MEETS", "MET_BY", "OVERLAPS", "OVERLAPPED_BY", "STARTS", "STARTED_BY",
        "DURING", "CONTAINS", "FINISHES", "FINISHED_BY", "EQUALS"
    ]:
        inf = 2**127
        a1, a2 = self.start_ns, self.end_ns if self.end_ns is not None else inf
        b1, b2 = other.start_ns, other.end_ns if other.end_ns is not None else inf
        if a2 < b1: return "BEFORE"
        if a2 == b1: return "MEETS"
        if a1 > b2: return "AFTER"
        if a1 == b2: return "MET_BY"
        if a1 == b1 and a2 == b2: return "EQUALS"
        if a1 == b1 and a2 < b2: return "STARTS"
        if a1 == b1 and a2 > b2: return "STARTED_BY"
        if a2 == b2 and a1 > b1: return "FINISHES"
        if a2 == b2 and a1 < b1: return "FINISHED_BY"
        if b1 < a1 and a2 < b2: return "DURING"
        if a1 < b1 and b2 < a2: return "CONTAINS"
        if a1 < b1 < a2 < b2: return "OVERLAPS"
        return "OVERLAPPED_BY"

    def intersects_uncertainty(self, instant: UncertainInstant) -> bool:
        end = self.end_ns if self.end_ns is not None else 2**127
        return instant.latest_ns >= self.start_ns and instant.earliest_ns < end
