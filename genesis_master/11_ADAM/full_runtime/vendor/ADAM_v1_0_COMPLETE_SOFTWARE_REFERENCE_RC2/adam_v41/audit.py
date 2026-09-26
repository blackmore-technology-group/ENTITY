from __future__ import annotations

import json
import os
import random
import shutil
import sqlite3
import statistics
import tempfile
import time
from pathlib import Path
from typing import Any

from .brain import AtomicBrain
from .canonical import canonical_json_bytes, sha256_bytes
from .constructors import Constructor
from .exact import ExactCodec
from .query import AtomicQueryEngine
from .semantic import SemanticCodec
from .universe import AtomicUniverse, ConflictError, IntegrityError


def _size_tree(path: Path) -> int:
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def _dataset(mode: str, count: int, seed: int) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    rows = []
    for i in range(count):
        if mode == "repetitive":
            location = ["Grand Forks", "Christina Lake", "Boundary"] [i % 3]
            status = ["open", "active", "closed"][i % 3]
            crew = f"crew-{i % 8}"
            note = "standard project operating record"
        elif mode == "mixed":
            location = ["Grand Forks", "Christina Lake", "Boundary", f"site-{rng.randrange(max(2, count // 10))}"][i % 4]
            status = ["open", "active", "closed", f"state-{rng.randrange(20)}"][i % 4]
            crew = f"crew-{rng.randrange(max(8, count // 20))}"
            note = "standard" if i % 2 else f"note-{rng.randrange(count // 2 + 1)}"
        elif mode == "unique":
            location = f"loc-{rng.getrandbits(64):016x}"
            status = f"state-{rng.getrandbits(64):016x}"
            crew = f"crew-{rng.getrandbits(64):016x}"
            note = os.urandom(24).hex()
        else:
            raise ValueError(mode)
        budget = 100_000 + (i % 50) * 1000
        cost = budget + (-5000 if i % 3 else 10000)
        rows.append({
            "project_id": f"P-{i:07d}",
            "location": location,
            "status": status,
            "crew": crew,
            "budget": budget,
            "cost": cost,
            "note": note,
        })
    return rows


def _sqlite_baseline(path: Path, rows: list[dict[str, Any]]) -> int:
    con = sqlite3.connect(path)
    try:
        con.execute("PRAGMA journal_mode=DELETE")
        con.execute("PRAGMA page_size=4096")
        con.execute("CREATE TABLE projects(project_id TEXT PRIMARY KEY, location TEXT, status TEXT, crew TEXT, budget INTEGER, cost INTEGER, note TEXT)")
        con.executemany(
            "INSERT INTO projects VALUES(:project_id,:location,:status,:crew,:budget,:cost,:note)", rows
        )
        con.commit()
        con.execute("VACUUM")
        con.commit()
    finally:
        con.close()
    return path.stat().st_size


def run_audit(output_root: Path | str, *, records: int = 1500, seed: int = 20260804) -> dict[str, Any]:
    output_root = Path(output_root)
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True)
    started = time.time()
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, detail: Any) -> None:
        checks.append({"name": name, "pass": bool(passed), "detail": detail})
        if not passed:
            raise AssertionError(f"{name}: {detail}")

    # Core functional universe.
    core_root = output_root / "core_universe"
    u = AtomicUniverse(core_root)
    exact = ExactCodec(u)
    semantic = SemanticCodec(u)
    brain = AtomicBrain(u)
    constructor = Constructor(u)
    query = AtomicQueryEngine(u)

    samples = [
        b"",
        b"hello atomic universe" * 100,
        bytes(range(256)) * 20,
        os.urandom(8192),
        canonical_json_bytes({"name": "Project 204", "active": True, "values": list(range(100))}),
    ]
    exact_details = []
    for i, sample in enumerate(samples):
        obj = exact.ingest(sample, media_type="application/octet-stream", name=f"sample-{i}")
        rebuilt = exact.reconstruct(obj.object_id)
        exact_details.append({"bytes": len(sample), "chunks": obj.chunks, "hash": obj.content_hash})
        check(f"exact_roundtrip_{i}", rebuilt == sample and sha256_bytes(rebuilt) == sha256_bytes(sample), exact_details[-1])

    semantic_value = {
        "project": "P-204",
        "location": {"city": "Grand Forks", "province": "BC"},
        "crew": ["Shawn", "Alex"],
        "active": True,
        "nullable": None,
    }
    semantic_root = semantic.ingest(semantic_value)
    check("semantic_roundtrip", semantic.reconstruct(semantic_root) == semantic_value, {"root": semantic_root})

    p1, v1 = u.assert_entity("project", "P-204", {"location": "Grand Forks", "budget": 100000, "cost": 90000, "status": "active"})
    seq_before_rebond = u.sequence
    p2, _ = u.assert_entity("project", "P-205", {"location": "Boundary", "budget": 100000, "cost": 120000, "status": "active"})
    current_version = u.entity_versions[p1]
    _, v2 = u.assert_entity("project", "P-204", {"location": "Christina Lake", "budget": 100000, "cost": 105000, "status": "active"}, expected_version=current_version)
    check("rebond_current_view", u.entity_view(p1)["location"] == "Christina Lake", u.entity_view(p1))
    check("time_travel_view", u.entity_view(p1, at_seq=seq_before_rebond)["location"] == "Grand Forks", u.entity_view(p1, at_seq=seq_before_rebond))
    over = query.over_budget()
    check("direct_atomic_compute", {x["_key"] for x in over} == {"P-204", "P-205"}, over)

    json_form = constructor.entity_json(p1)
    csv_form = constructor.entities_csv([p1, p2])
    md_form = constructor.entity_markdown(p1)
    check("multi_form_construction", "P-204" in json_form and "P-205" in csv_form and "Christina Lake" in md_form, {"json": len(json_form), "csv": len(csv_form), "markdown": len(md_form)})

    conflict_pass = False
    try:
        u.assert_entity("project", "P-204", {"cost": 1}, expected_version=v1)
    except ConflictError:
        conflict_pass = True
    check("mvcc_conflict_rejection", conflict_pass, {"stale_version": v1, "current_version": v2})

    repeated = [{"project_id": f"L-{i}", "location": "Grand Forks", "status": "active", "budget": 10, "cost": i} for i in range(30)]
    proposals = brain.discover_compounds(repeated, name_prefix="PROJECT_PATTERN", min_support=5)
    check("learned_compound_promotion", any(x.accepted for x in proposals), [x.__dict__ for x in proposals])

    verify_before = u.verify()
    check("universe_integrity", verify_before["pass"], verify_before)

    # Restart and torn-tail recovery.
    pre_restart_root = u.root_hash
    pre_restart_view = u.entity_view(p1)
    del u
    reopened = AtomicUniverse(core_root)
    check("restart_persistence", reopened.root_hash == pre_restart_root and reopened.entity_view(p1) == pre_restart_view, reopened.verify())
    log_path = core_root / "universe.a41log"
    good_bytes = log_path.read_bytes()
    log_path.write_bytes(good_bytes + b"\x00\x00\x01\x00torn-tail")
    recovered = AtomicUniverse(core_root)
    check("torn_tail_recovery", log_path.read_bytes() == good_bytes and recovered.log.recovered_torn_bytes > 0, recovered.verify())

    # Tamper test: corrupt an interior payload and require rejection.
    tamper_root = output_root / "tamper_universe"
    shutil.copytree(core_root, tamper_root)
    tamper_log = tamper_root / "universe.a41log"
    raw = bytearray(tamper_log.read_bytes())
    if len(raw) > 100:
        raw[50] ^= 0x01
    tamper_log.write_bytes(raw)
    tamper_rejected = False
    try:
        AtomicUniverse(tamper_root)
    except IntegrityError:
        tamper_rejected = True
    check("tamper_rejection", tamper_rejected, {"log_bytes": len(raw)})

    # Workload storage and correctness matrix.
    workloads = []
    for offset, mode in enumerate(("repetitive", "mixed", "unique")):
        rows = _dataset(mode, records, seed + offset)
        logical_bytes = sum(len(canonical_json_bytes(r)) for r in rows)
        wr = output_root / f"workload_{mode}"
        wu = AtomicUniverse(wr / "adam")
        wb = AtomicBrain(wu)
        t0 = time.perf_counter()
        ids = wb.ingest_records(rows, entity_type="project", id_field="project_id")
        ingest_seconds = time.perf_counter() - t0
        props = wb.discover_compounds(rows, name_prefix=f"{mode.upper()}_SCHEMA", min_support=5)
        views_equal = all(
            {k: v for k, v in wu.entity_view(entity_id).items() if not k.startswith("_")} == {k: v for k, v in row.items() if k != "project_id"}
            for entity_id, row in zip(ids, rows)
        )
        sqlite_bytes = _sqlite_baseline(wr / "baseline.sqlite", rows)
        journal_bytes = (wr / "adam" / "universe.a41log").stat().st_size
        compact_bytes = len(wu.compact_state_bytes())
        native_packed_bytes = len(wu.native_packed_state_bytes())
        native_factored_bytes = len(wu.native_factored_state_bytes())
        pre_compaction_root = wu.root_hash
        sample_before_compaction = wu.entity_view(ids[-1])
        wu.compact_authority()
        compacted_reopen = AtomicUniverse(wr / "adam")
        checkpoint_restart_pass = (
            compacted_reopen.root_hash == pre_compaction_root
            and compacted_reopen.entity_view(ids[-1]) == sample_before_compaction
            and compacted_reopen.verify()["pass"]
        )
        authoritative_compacted_bytes = _size_tree(wr / "adam")
        verification = wu.verify()
        workloads.append({
            "mode": mode,
            "records": records,
            "logical_json_bytes": logical_bytes,
            "sqlite_current_bytes": sqlite_bytes,
            "adam_authoritative_journal_bytes": journal_bytes,
            "adam_compact_state_bytes": compact_bytes,
            "adam_native_packed_state_bytes": native_packed_bytes,
            "adam_native_factored_state_bytes": native_factored_bytes,
            "adam_authoritative_compacted_tree_bytes": authoritative_compacted_bytes,
            "checkpoint_restart_pass": checkpoint_restart_pass,
            "journal_vs_sqlite_reduction_percent": 100.0 * (sqlite_bytes - journal_bytes) / sqlite_bytes,
            "compact_vs_sqlite_reduction_percent": 100.0 * (sqlite_bytes - compact_bytes) / sqlite_bytes,
            "native_packed_vs_sqlite_reduction_percent": 100.0 * (sqlite_bytes - native_packed_bytes) / sqlite_bytes,
            "native_factored_vs_sqlite_reduction_percent": 100.0 * (sqlite_bytes - native_factored_bytes) / sqlite_bytes,
            "authoritative_compacted_vs_sqlite_reduction_percent": 100.0 * (sqlite_bytes - authoritative_compacted_bytes) / sqlite_bytes,
            "ingest_seconds": ingest_seconds,
            "views_equal": views_equal,
            "integrity": verification["pass"],
            "atoms": verification["atoms"],
            "bonds": verification["bonds"],
            "compounds": verification["compounds"],
            "accepted_compounds": sum(1 for x in props if x.accepted),
        })
        check(f"workload_{mode}_correctness", views_equal and verification["pass"] and checkpoint_restart_pass, workloads[-1])

    # High entropy exact input demonstrates no universal compression claim.
    entropy_root = output_root / "high_entropy"
    eu = AtomicUniverse(entropy_root)
    ec = ExactCodec(eu)
    random_blob = os.urandom(256 * 1024)
    eobj = ec.ingest(random_blob, name="random.bin")
    exact_physical = _size_tree(entropy_root)
    check("high_entropy_exactness", ec.reconstruct(eobj.object_id) == random_blob, {"logical": len(random_blob), "physical": exact_physical})

    latency_samples = []
    for _ in range(200):
        t0 = time.perf_counter_ns()
        recovered.entity_view(p1)
        latency_samples.append((time.perf_counter_ns() - t0) / 1000.0)

    gaps = [
        {
            "severity": "CRITICAL",
            "gap": "Universal semantic atomization is not solved",
            "finding": "The prototype can atomize exact bytes, recursive JSON and typed entity facts, but images, audio, arbitrary programs and ambiguous natural language still require domain codecs or learned perception models.",
        },
        {
            "severity": "CRITICAL",
            "gap": "No distributed consensus integration",
            "finding": "The event log is single-authority and single-process. v0.39 Raft/BFT/sharding code was not fully available in this environment, so v0.40 does not yet prove multi-node safety, failover or sovereignty placement.",
        },
        {
            "severity": "HIGH",
            "gap": "Learned chemistry is heuristic",
            "finding": "The brain discovers repeated schemas and validates promotion, but does not yet learn arbitrary bonding laws or emergent compounds with a neural or program-synthesis model.",
        },
        {
            "severity": "HIGH",
            "gap": "History and signatures can dominate storage",
            "finding": "The authoritative event journal deliberately retains signed history. Compact current state may be smaller, while the full journal can be larger than SQLite; the audit reports both rather than hiding this cost.",
        },
        {
            "severity": "HIGH",
            "gap": "Inference security",
            "finding": "Atom- and bond-level access control is not implemented. Combining individually visible atoms can reveal a restricted compound, so authorization must govern closure and inference, not only direct reads.",
        },
        {
            "severity": "HIGH",
            "gap": "Reaction and conservation-law language incomplete",
            "finding": "Rebonding and MVCC exist, but a formal typed reaction language with domain invariants, reversibility and conservation proofs remains to be built.",
        },
        {
            "severity": "MEDIUM",
            "gap": "Query language is minimal",
            "finding": "Direct graph computation is demonstrated through Python predicates and an over-budget query, not a complete declarative optimizer or distributed execution engine.",
        },
        {
            "severity": "MEDIUM",
            "gap": "Private-key handling is development-only",
            "finding": "The prototype persists an unencrypted Ed25519 private key. Production requires HSM/KMS integration, key rotation and multi-authority governance.",
        },
        {
            "severity": "MEDIUM",
            "gap": "Garbage collection and legal deletion",
            "finding": "Content addressing and historical authority complicate deletion. Reachability, retention, redaction and cryptographic erasure policies are not implemented.",
        },
        {
            "severity": "MEDIUM",
            "gap": "No production performance claim",
            "finding": "Python and per-transaction fsync prioritize auditability. Performance requires packed indexes, batching, native code, incremental dataflow and workload-specific materialization.",
        },
    ]

    result = {
        "format": "ADAM-v0.41-full-development-audit",
        "version": "0.40.0.dev1",
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)),
        "completed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "duration_seconds": time.time() - started,
        "records_per_workload": records,
        "checks": checks,
        "checks_passed": sum(1 for c in checks if c["pass"]),
        "checks_total": len(checks),
        "overall_pass": all(c["pass"] for c in checks),
        "core_verification": recovered.verify(),
        "workloads": workloads,
        "entity_view_latency_us": {
            "mean": statistics.mean(latency_samples),
            "median": statistics.median(latency_samples),
            "p95": sorted(latency_samples)[int(len(latency_samples) * 0.95) - 1],
        },
        "high_entropy": {
            "logical_bytes": len(random_blob),
            "physical_tree_bytes": exact_physical,
            "expansion_percent": 100.0 * (exact_physical - len(random_blob)) / len(random_blob),
        },
        "gaps": gaps,
        "claim_boundary": (
            "This is a runnable single-node development prototype proving exact atomization, recursive semantic compounds, "
            "event-sourced rebonding, history, direct graph computation, multi-form construction, deterministic compound promotion, "
            "restart recovery and tamper detection. It does not prove universal semantic understanding, production performance, "
            "multi-node consensus, universal storage reduction or replacement of all databases."
        ),
    }
    result_path = output_root / "ADAM_V040_AUDIT_RESULTS.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return result
