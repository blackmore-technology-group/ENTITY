from __future__ import annotations

import json
import statistics
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

from adam_v41.canonical import canonical_json_bytes, digest, sha256_bytes
from .sovereignty import WitnessQuorum


class QualificationError(RuntimeError):
    pass


@dataclass
class SLAMetrics:
    cycles: int = 0
    successes: int = 0
    failures: int = 0
    latencies_ms: list[float] = field(default_factory=list)
    invariant_failures: int = 0
    failovers: int = 0
    recoveries: int = 0

    def summary(self) -> dict[str, Any]:
        values = sorted(self.latencies_ms)
        def pct(q: float) -> float:
            if not values:
                return 0.0
            return values[min(len(values)-1, int((len(values)-1)*q))]
        return {
            "cycles": self.cycles,
            "successes": self.successes,
            "failures": self.failures,
            "availability": self.successes / max(1, self.cycles),
            "latency_ms_mean": statistics.fmean(values) if values else 0.0,
            "latency_ms_p95": pct(0.95),
            "latency_ms_p99": pct(0.99),
            "latency_ms_max": max(values) if values else 0.0,
            "invariant_failures": self.invariant_failures,
            "failovers": self.failovers,
            "recoveries": self.recoveries,
        }


class ProductionQualification50:
    """Resumable real-wall-clock qualification harness; it cannot accelerate certification."""

    def __init__(self, root: Path | str, witnesses: WitnessQuorum, health_probe: Callable[[], dict[str, Any]],
                 cycle: Callable[[], dict[str, Any]], *, duration_days: float = 30.0,
                 interval_seconds: float = 60.0, now_ns: Callable[[], int] = time.time_ns,
                 test_only: bool = False) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.state_path = self.root / "V050_QUALIFICATION_STATE.json"
        self.evidence_path = self.root / "V050_CYCLE_EVIDENCE.jsonl"
        self.final_path = self.root / "V050_FINAL_CERTIFICATE.json"
        self.witnesses = witnesses
        self.health_probe = health_probe
        self.cycle_fn = cycle
        self.now_ns = now_ns
        self.test_only = test_only
        self.required_ns = int(duration_days * 86400 * 1_000_000_000)
        self.interval_ns = int(interval_seconds * 1_000_000_000)
        if self.required_ns <= 0 or self.interval_ns <= 0:
            raise ValueError("duration and interval must be positive")
        if self.state_path.exists():
            raw = json.loads(self.state_path.read_text())
            self.started_ns = int(raw["started_ns"])
            self.last_ns = int(raw["last_ns"])
            self.metrics = SLAMetrics(**raw["metrics"])
            if int(raw["required_ns"]) != self.required_ns or int(raw["interval_ns"]) != self.interval_ns:
                raise QualificationError("qualification parameters cannot change")
        else:
            self.started_ns = int(self.now_ns())
            self.last_ns = self.started_ns
            self.metrics = SLAMetrics()
            self._save()
        self.qualification_id = digest("ADAM50:PRODUCTION_QUALIFICATION", {
            "root": str(self.root.resolve()), "started_ns": self.started_ns,
            "required_ns": self.required_ns, "interval_ns": self.interval_ns,
        })

    def _save(self) -> None:
        data = {
            "format": "ADAM-v0.50-production-qualification-state",
            "started_ns": self.started_ns,
            "last_ns": self.last_ns,
            "required_ns": self.required_ns,
            "interval_ns": self.interval_ns,
            "metrics": asdict(self.metrics),
        }
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, sort_keys=True))
        tmp.replace(self.state_path)

    def run_cycle(self) -> dict[str, Any]:
        now = int(self.now_ns())
        if now < self.last_ns:
            raise QualificationError("wall clock moved backwards")
        started = time.perf_counter_ns()
        success = False
        error = None
        outcome: dict[str, Any] = {}
        try:
            outcome = dict(self.cycle_fn())
            health = dict(self.health_probe())
            if not health.get("physics_root"):
                raise QualificationError("health probe did not return physics root")
            success = True
        except Exception as exc:
            health = {}
            error = f"{type(exc).__name__}: {exc}"
            self.metrics.invariant_failures += 1
        latency = (time.perf_counter_ns() - started) / 1_000_000
        self.metrics.cycles += 1
        self.metrics.successes += int(success)
        self.metrics.failures += int(not success)
        self.metrics.latencies_ms.append(latency)
        self.last_ns = now
        evidence = {
            "cycle": self.metrics.cycles,
            "wall_ns": now,
            "latency_ms": latency,
            "success": success,
            "error": error,
            "outcome": outcome,
            "health": health,
        }
        evidence_hash = sha256_bytes(canonical_json_bytes(evidence))
        statements = self.witnesses.certify(evidence_hash)
        evidence["evidence_hash"] = evidence_hash
        evidence["witness_statement_ids"] = [s.statement_id for s in statements]
        with self.evidence_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(evidence, sort_keys=True) + "\n")
        self._save()
        if not success:
            raise QualificationError(error or "cycle failed")
        return evidence

    def progress(self) -> dict[str, Any]:
        elapsed = max(0, int(self.now_ns()) - self.started_ns)
        return {
            "qualification_id": self.qualification_id,
            "test_only": self.test_only,
            "elapsed_seconds": elapsed / 1_000_000_000,
            "required_seconds": self.required_ns / 1_000_000_000,
            "progress": min(1.0, elapsed / self.required_ns),
            "metrics": self.metrics.summary(),
        }

    def finalize(self, *, minimum_availability: float = 0.999, maximum_p99_ms: float = 1000.0) -> dict[str, Any]:
        if self.test_only:
            raise QualificationError("test-only qualification cannot certify production")
        elapsed = int(self.now_ns()) - self.started_ns
        if elapsed < self.required_ns:
            raise QualificationError("30 real wall-clock days have not elapsed")
        summary = self.metrics.summary()
        minimum_cycles = max(1, self.required_ns // self.interval_ns)
        gates = {
            "duration": elapsed >= self.required_ns,
            "minimum_cycles": self.metrics.cycles >= minimum_cycles,
            "availability": summary["availability"] >= minimum_availability,
            "latency_p99": summary["latency_ms_p99"] <= maximum_p99_ms,
            "invariants": summary["invariant_failures"] == 0,
        }
        certificate = {
            "format": "ADAM-v0.50-production-qualification-certificate",
            "qualification_id": self.qualification_id,
            "passed": all(gates.values()),
            "gates": gates,
            "progress": self.progress(),
        }
        root = sha256_bytes(canonical_json_bytes(certificate))
        certificate["witnesses"] = [s.statement_id for s in self.witnesses.certify(root)]
        self.final_path.write_text(json.dumps(certificate, indent=2, sort_keys=True))
        return certificate
