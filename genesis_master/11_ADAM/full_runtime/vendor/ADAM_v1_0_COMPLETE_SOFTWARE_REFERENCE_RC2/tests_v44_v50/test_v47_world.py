from __future__ import annotations

from adam_v47 import (
    Goal, IncrementalDependencyEngine, MultiScalePlanner, ShadowUniverseLab,
    TemporalDynamicsOrgan, TransitionExample,
)
from test_v44_physics import make_intent


def test_temporal_dynamics_training_prediction_and_abstention():
    organ = TemporalDynamicsOrgan()
    organ.train([
        TransitionExample(("AVAILABLE",), "ASSIGN", ("NORMAL",), ("ASSIGNED",)),
        TransitionExample(("AVAILABLE",), "ASSIGN", ("NORMAL",), ("ASSIGNED",)),
        TransitionExample(("AVAILABLE",), "ASSIGN", ("FROZEN",), ("DELAYED",)),
    ])
    assert organ.predict(("AVAILABLE",), "ASSIGN", ("NORMAL",)).next_signature == ("ASSIGNED",)
    assert organ.predict((), "UNKNOWN", ()).abstained


def test_shadow_universe_compares_without_commit(assignment_kernel):
    root = assignment_kernel.root
    result = ShadowUniverseLab(assignment_kernel).simulate(make_intent(assignment_kernel))
    assert result.proof is not None
    assert assignment_kernel.root == root


def test_symbolic_planner_proposes_but_does_not_commit():
    planner = MultiScalePlanner({
        "INSPECT": (frozenset({"HAS_EQUIPMENT"}), frozenset({"INSPECTED"}), 1.0),
        "ASSIGN": (frozenset({"INSPECTED"}), frozenset({"ASSIGNED"}), 1.0),
    })
    goal = Goal("G1", frozenset({"ASSIGNED"}), "SHAWN", ("SAFE",))
    plan = planner.plan(frozenset({"HAS_EQUIPMENT"}), goal)
    assert plan.reached and [s.action for s in plan.steps] == ["INSPECT", "ASSIGN"]


def test_incremental_engine_recomputes_only_dependents():
    engine = IncrementalDependencyEngine()
    engine.set_base("COST", 10)
    engine.set_base("BUDGET", 8)
    engine.set_base("WEATHER", "CLEAR")
    engine.add_derived("VARIANCE", ("COST", "BUDGET"), lambda c: c["COST"] - c["BUDGET"])
    engine.add_derived("ALERT", ("VARIANCE",), lambda c: c["VARIANCE"] > 0)
    before = engine.recompute_count
    affected = engine.set_base("WEATHER", "RAIN")
    assert affected == set()
    assert engine.recompute_count == before
    affected = engine.set_base("COST", 7)
    assert affected == {"VARIANCE", "ALERT"}
    assert engine.derived["ALERT"].value is False


def test_goal_is_atomic_but_has_no_commit_authority():
    from adam_v47 import AtomicGoal
    goal = AtomicGoal(("PROJECT_SAFE",), "SHAWN", ("LAW_SET_4",), 100, 5, "OPS")
    assert goal.goal_id == AtomicGoal(**{k: v for k, v in goal.__dict__.items()}).goal_id
    assert goal.canonical()["commit_authority"] is False
