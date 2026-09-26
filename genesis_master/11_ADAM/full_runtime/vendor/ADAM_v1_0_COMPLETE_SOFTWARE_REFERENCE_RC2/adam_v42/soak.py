from __future__ import annotations

import json
import time
import tracemalloc
from dataclasses import asdict, dataclass
from pathlib import Path

from adam_v41.reactions import ReactionIntent
from .distributed import DistributedUniverseCluster


@dataclass(frozen=True)
class SoakReport:
    logical_days: int
    cycles: int
    commits: int
    failovers: int
    recoveries: int
    invariant_failures: int
    elapsed_seconds: float
    peak_memory_bytes: int
    final_term: int
    final_index: int
    final_state_digest: str


def run_logical_soak(root: Path | str, *, logical_days: int = 30, cycles_per_day: int = 24) -> SoakReport:
    root = Path(root)
    cluster = DistributedUniverseCluster(root / "cluster", node_count=3)
    ids = cluster.leader.ids
    tracemalloc.start()
    started = time.perf_counter()
    commits = failovers = recoveries = failures = 0
    total = logical_days * cycles_per_day
    assigned = False
    for cycle in range(total):
        try:
            if not assigned:
                intent = ReactionIntent("ASSIGN_EQUIPMENT", {"equipment": ids["equipment"], "project": ids["project"], "actor": ids["actor"]})
            else:
                intent = ReactionIntent("RELEASE_EQUIPMENT", {"equipment": ids["equipment"], "project": ids["project"], "actor": ids["actor"]}, {"location": "YARD"})
            cluster.apply(intent)
            commits += 1
            assigned = not assigned
            if cycle and cycle % 97 == 0:
                old = cluster.leader_id
                cluster.stop_node(old)
                failovers += 1
            if cycle and cycle % 103 == 0:
                offline = next((node_id for node_id, node in cluster.nodes.items() if not node.live), None)
                if offline:
                    cluster.start_node(offline)
                    recoveries += 1
            cluster._verify_convergence()
        except Exception:
            failures += 1
            raise
    elapsed = time.perf_counter() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    report = SoakReport(
        logical_days, total, commits, failovers, recoveries, failures, elapsed, peak,
        cluster.term, cluster.index, cluster._verify_convergence(),
    )
    (root / "SOAK_REPORT.json").write_text(json.dumps(asdict(report), indent=2, sort_keys=True), encoding="utf-8")
    return report
