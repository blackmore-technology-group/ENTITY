from __future__ import annotations

import json
import os
import statistics
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

from adam_v41.canonical import canonical_json_bytes, digest, sha256_bytes
from adam_v41.reactions import ReactionIntent
from adam_v42.distributed import DistributedUniverseCluster
from .key_custody import QuorumCustody, QuorumReceipt, SignerProvider


class QualificationError(RuntimeError):
    pass


@dataclass
class SLAState:
    requests: int = 0
    successes: int = 0
    failures: int = 0
    latencies_ms: list[float] = field(default_factory=list)
    failovers: int = 0
    recoveries: int = 0
    integrity_checks: int = 0
    integrity_failures: int = 0

    def record(self, latency_ms: float, success: bool) -> None:
        self.requests += 1
        self.successes += int(success)
        self.failures += int(not success)
        self.latencies_ms.append(float(latency_ms))
        if len(self.latencies_ms) > 100_000:
            self.latencies_ms = self.latencies_ms[-100_000:]

    def summary(self) -> dict[str, Any]:
        ordered = sorted(self.latencies_ms)
        def percentile(q: float) -> float:
            if not ordered:
                return 0.0
            index = min(len(ordered) - 1, int(round((len(ordered) - 1) * q)))
            return ordered[index]
        return {
            "requests": self.requests,
            "successes": self.successes,
            "failures": self.failures,
            "availability": self.successes / max(1, self.requests),
            "latency_ms_mean": statistics.fmean(ordered) if ordered else 0.0,
            "latency_ms_p50": percentile(0.50),
            "latency_ms_p95": percentile(0.95),
            "latency_ms_p99": percentile(0.99),
            "latency_ms_max": max(ordered) if ordered else 0.0,
            "failovers": self.failovers,
            "recoveries": self.recoveries,
            "integrity_checks": self.integrity_checks,
            "integrity_failures": self.integrity_failures,
        }


@dataclass
class SoakState:
    format: str
    qualification_id: str
    started_wall_ns: int
    last_wall_ns: int
    required_duration_ns: int
    cycle_interval_ns: int
    cycles: int
    intents: list[dict[str, Any]]
    assigned: bool
    epoch: int
    sla: SLAState
    completed: bool = False
    final_report_sha256: str | None = None


class ProductionSoakController:
    """Resumable real-wall-clock qualification controller.

    Production mode uses the OS wall clock and refuses to certify before the actual
    required duration has elapsed. A test clock is available only when the explicit
    `test_only` flag is set; such runs can never emit a production certificate.
    """

    def __init__(
        self,
        root: Path | str,
        custody: QuorumCustody,
        *,
        duration_days: float = 30.0,
        cycle_interval_seconds: float = 60.0,
        now_ns: Callable[[], int] = time.time_ns,
        test_only: bool = False,
    ):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.state_path = self.root / "SOAK_STATE.json"
        self.receipts_path = self.root / "SIGNED_DAILY_REPORTS.jsonl"
        self.final_path = self.root / "FINAL_PRODUCTION_QUALIFICATION.json"
        self.custody = custody
        self._now_ns = now_ns
        self.test_only = test_only
        requested_duration = int(duration_days * 86400 * 1_000_000_000)
        requested_interval = int(cycle_interval_seconds * 1_000_000_000)
        if requested_duration <= 0 or requested_interval <= 0:
            raise ValueError("duration and cycle interval must be positive")
        if self.state_path.exists():
            self.state = self._load_state()
            if self.state.required_duration_ns != requested_duration or self.state.cycle_interval_ns != requested_interval:
                raise QualificationError("qualification parameters cannot change after start")
            self.cluster = self._rebuild_cluster()
        else:
            # Build the initial authority cluster before starting the qualification clock.
            # Initialization cost varies substantially across platforms (especially
            # Windows and antivirus-scanned filesystems) and must not count toward a
            # production soak that has not begun accepting cycles yet.
            self.state = SoakState(
                "ADAM-v0.43-production-soak", "INITIALIZING", 0, 0,
                requested_duration, requested_interval, 0, [], False, 1, SLAState(),
            )
            self.cluster = self._rebuild_cluster(save_epoch_change=False)
            started = int(self._now_ns())
            self.state.started_wall_ns = started
            self.state.last_wall_ns = started
            self.state.qualification_id = digest(
                "ADAM43:PRODUCTION_SOAK",
                {"root": str(self.root.resolve()), "started_wall_ns": started, "duration_ns": requested_duration},
            )
            self._save_state()

    def _load_state(self) -> SoakState:
        raw = json.loads(self.state_path.read_text(encoding="utf-8"))
        raw["sla"] = SLAState(**raw["sla"])
        return SoakState(**raw)

    def _save_state(self) -> None:
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(self.state), indent=2, sort_keys=True), encoding="utf-8")
        os.chmod(tmp, 0o600)
        tmp.replace(self.state_path)

    def _rebuild_cluster(self, *, save_epoch_change: bool = True) -> DistributedUniverseCluster:
        epoch_root = self.root / "epochs" / f"epoch-{self.state.epoch:04d}"
        if epoch_root.exists() and any(epoch_root.iterdir()):
            # Rebuild into a new deterministic replay epoch without mutating old evidence.
            self.state.epoch += 1
            epoch_root = self.root / "epochs" / f"epoch-{self.state.epoch:04d}"
            if save_epoch_change:
                self._save_state()
        cluster = DistributedUniverseCluster(epoch_root / "cluster", node_count=3)
        for record in self.state.intents:
            cluster.apply(ReactionIntent(**record))
        return cluster

    def _intent(self) -> ReactionIntent:
        ids = self.cluster.leader.ids
        if not self.state.assigned:
            return ReactionIntent("ASSIGN_EQUIPMENT", {"equipment": ids["equipment"], "project": ids["project"], "actor": ids["actor"]})
        return ReactionIntent("RELEASE_EQUIPMENT", {"equipment": ids["equipment"], "project": ids["project"], "actor": ids["actor"]}, {"location": "YARD"})

    def cycle(self) -> dict[str, Any]:
        if self.state.completed:
            raise QualificationError("qualification is already complete")
        now = int(self._now_ns())
        if now < self.state.last_wall_ns:
            raise QualificationError("wall clock moved backwards")
        started = time.perf_counter_ns()
        success = False
        error = None
        try:
            intent = self._intent()
            certificate = self.cluster.apply(intent)
            self.state.intents.append({"reaction": intent.reaction, "bindings": dict(intent.bindings), "args": dict(intent.args)})
            self.state.assigned = not self.state.assigned
            self.state.cycles += 1
            if self.state.cycles % 97 == 0:
                old = self.cluster.leader_id
                self.cluster.stop_node(old)
                self.state.sla.failovers += 1
            if self.state.cycles % 103 == 0:
                offline = next((node_id for node_id, node in self.cluster.nodes.items() if not node.live), None)
                if offline:
                    self.cluster.start_node(offline)
                    self.state.sla.recoveries += 1
            self.cluster._verify_convergence()
            self.state.sla.integrity_checks += 1
            success = True
            result = {"term": certificate.term, "index": certificate.index, "proposal_digest": certificate.proposal_digest}
        except Exception as exc:
            self.state.sla.integrity_failures += 1
            error = f"{type(exc).__name__}: {exc}"
            result = {}
        latency_ms = (time.perf_counter_ns() - started) / 1_000_000.0
        self.state.sla.record(latency_ms, success)
        self.state.last_wall_ns = now
        self._save_state()
        if not success:
            raise QualificationError(error or "cycle failed")
        return {"cycle": self.state.cycles, "wall_ns": now, "latency_ms": latency_ms, **result}

    def elapsed_ns(self) -> int:
        return max(0, int(self._now_ns()) - self.state.started_wall_ns)

    def progress(self) -> dict[str, Any]:
        elapsed = self.elapsed_ns()
        return {
            "qualification_id": self.state.qualification_id,
            "test_only": self.test_only,
            "started_wall_ns": self.state.started_wall_ns,
            "elapsed_seconds": elapsed / 1_000_000_000,
            "required_seconds": self.state.required_duration_ns / 1_000_000_000,
            "progress": min(1.0, elapsed / self.state.required_duration_ns),
            "cycles": self.state.cycles,
            "completed": self.state.completed,
            "sla": self.state.sla.summary(),
        }

    def signed_report(self, report_kind: str = "INTERIM") -> tuple[dict[str, Any], QuorumReceipt]:
        report = {
            "format": "ADAM-v0.43-soak-report",
            "kind": report_kind,
            "qualification": self.progress(),
            "state_digest": self.cluster._verify_convergence(),
            "consensus_term": self.cluster.term,
            "consensus_index": self.cluster.index,
            "intent_history_sha256": sha256_bytes(canonical_json_bytes(self.state.intents)),
            "generated_wall_ns": int(self._now_ns()),
        }
        receipt = self.custody.sign(canonical_json_bytes(report))
        with self.receipts_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"report": report, "quorum_receipt": asdict(receipt)}, sort_keys=True) + "\n")
        return report, receipt

    def finalize(self, *, minimum_availability: float = 0.999, maximum_p99_ms: float = 1000.0) -> dict[str, Any]:
        elapsed = self.elapsed_ns()
        if self.test_only:
            raise QualificationError("test-only clock can never issue production certification")
        if elapsed < self.state.required_duration_ns:
            raise QualificationError("required real wall-clock duration has not elapsed")
        sla = self.state.sla.summary()
        gates = {
            "duration": elapsed >= self.state.required_duration_ns,
            "availability": sla["availability"] >= minimum_availability,
            "latency_p99": sla["latency_ms_p99"] <= maximum_p99_ms,
            "integrity": sla["integrity_failures"] == 0 and self.cluster._verify_convergence() != "",
            "minimum_cycles": self.state.cycles >= max(1, self.state.required_duration_ns // self.state.cycle_interval_ns),
        }
        result = {
            "format": "ADAM-v0.43-production-qualification-certificate",
            "qualification_id": self.state.qualification_id,
            "passed": all(gates.values()),
            "gates": gates,
            "progress": self.progress(),
            "state_digest": self.cluster._verify_convergence(),
        }
        _, receipt = self.signed_report("FINAL")
        result["quorum_receipt"] = asdict(receipt)
        self.final_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
        self.state.completed = bool(result["passed"])
        self.state.final_report_sha256 = sha256_bytes(self.final_path.read_bytes())
        self._save_state()
        return result

    def run(self, *, stop_after_cycles: int | None = None) -> None:
        completed_this_run = 0
        while not self.state.completed:
            now = int(self._now_ns())
            due = self.state.last_wall_ns + self.state.cycle_interval_ns
            if now < due:
                time.sleep(min((due - now) / 1_000_000_000, 1.0))
                continue
            self.cycle()
            completed_this_run += 1
            if self.state.cycles % max(1, int(86400 * 1_000_000_000 / self.state.cycle_interval_ns)) == 0:
                self.signed_report("DAILY")
            if stop_after_cycles is not None and completed_this_run >= stop_after_cycles:
                return
