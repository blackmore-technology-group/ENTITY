from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from adam_v41.authority import Authority
from adam_v42.chemistry import ChemistryCandidate, ChemistryLab
from adam_v42.operations_one import DeterministicO1Cognition, OperationsOneAuthority
from adam_v42.query import DistributedAQL

DATA = Path(__file__).parents[1] / "data" / "operations_one_real_records.json"


def test_operations_one_bounded_authority_migration_and_real_training(tmp_path: Path):
    o1 = OperationsOneAuthority(tmp_path / "o1")
    report = o1.migrate(DATA, max_records_per_domain=18)
    assert report.records_migrated >= 50
    assert report.aligned_entities == report.records_migrated
    assert report.exact_roundtrip and report.view_equivalence
    assert o1.aligned_entity_count() == report.records_migrated

    model_path = tmp_path / "o1_model.json"
    model, training = DeterministicO1Cognition.train(o1.records(), model_path)
    assert training.accuracy >= 0.80
    assert training.rejected_ood
    loaded = DeterministicO1Cognition.load(model_path)
    label, margin, ood = loaded.predict(o1.records()[0][1])
    assert label == o1.records()[0][0] and margin >= 0 and not ood

    # Independent interpreter process must produce the same canonical prediction.
    probe = tmp_path / "probe.json"
    probe.write_text(json.dumps(o1.records()[0][1], default=str), encoding="utf-8")
    code = "from adam_v42.operations_one import DeterministicO1Cognition;import json,sys;m=DeterministicO1Cognition.load(sys.argv[1]);r=json.load(open(sys.argv[2]));print(json.dumps(m.predict(r)))"
    env = dict(__import__('os').environ); env['PYTHONPATH'] = str(Path(__file__).parents[1])
    p1 = subprocess.check_output([sys.executable, "-c", code, str(model_path), str(probe)], env=env, text=True).strip()
    p2 = subprocess.check_output([sys.executable, "-c", code, str(model_path), str(probe)], env=env, text=True).strip()
    assert p1 == p2


def test_declarative_query_planner_and_cache(tmp_path: Path):
    o1 = OperationsOneAuthority(tmp_path / "o1")
    o1.migrate(DATA, max_records_per_domain=10)
    engine = DistributedAQL(o1.records(), sequence_provider=lambda: o1.universe.sequence)
    plan, result = engine.execute('MATCH "Invoice Register" WHERE invoice_type == "Progress" RETURN invoice_no,amount_before_tax')
    assert plan.strategy == "SHARD_PRUNED_SCAN" and result
    _, cached = engine.execute('MATCH "Invoice Register" WHERE invoice_type == "Progress" RETURN invoice_no,amount_before_tax')
    assert cached == result


def test_shadow_replay_chemistry_promotion_and_rejection(tmp_path: Path):
    states = [
        {"project": "P1", "status": "ACTIVE", "budget": 100},
        {"project": "P1", "status": "CLOSED", "budget": 100},
    ]
    authorities = [Authority(tmp_path / f"a{i}") for i in range(3)]
    lab = ChemistryLab(tmp_path / "lab", authorities)
    good = ChemistryCandidate("rename_project", 1, 2, {"project": "project_id"})
    receipt = lab.evaluate(good, states)
    assert receipt.status == "PROMOTED" and len(receipt.approvals) == 3
    bad = ChemistryCandidate("drop_budget", 2, 3, {}, ("budget",))
    rejected = lab.evaluate(bad, states)
    assert rejected.status == "REJECTED_EQUIVALENCE" and rejected.equivalence_failures == len(states)
