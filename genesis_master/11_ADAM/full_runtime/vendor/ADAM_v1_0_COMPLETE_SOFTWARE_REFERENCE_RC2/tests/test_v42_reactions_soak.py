from __future__ import annotations

from pathlib import Path

import pytest

from adam_v41.reactions import Effect, ReactionDefinition, ReactionEngine, ReactionError, ReactionIntent
from adam_v41.schema import TypeRegistry, TypeSpec, ValenceRule
from adam_v41.universe import AtomicUniverse
from adam_v42.reactions_ext import AdvancedCondition, AdvancedPolicy, AdvancedReactionEngine, ComputedArgument
from adam_v42.soak import run_logical_soak


def test_aggregate_arithmetic_cross_field_reaction_policy(tmp_path: Path):
    u = AtomicUniverse(tmp_path / "u")
    cap = u.enable_commit_guard()
    base = ReactionEngine(u, TypeRegistry(), capability=cap)
    base.register_type(TypeSpec("account", (
        ValenceRule("balance", 1, 1, value_type="number"),
        ValenceRule("budget", 1, 1, value_type="number"),
    )))
    base.register_type(TypeSpec("person", (), allow_unlisted_predicates=True))
    base.register_reaction(ReactionDefinition(
        "POST_COST", 1, {"account": "account", "actor": "person"}, "actor", ("POST_COST",), (),
        (Effect("account", "balance", "set_arg", value_arg="new_balance"),),
    ))
    account, _ = base.genesis_entity("account", "A", {"balance": 60, "budget": 100})
    actor, _ = base.genesis_entity("person", "U", {"grant::POST_COST": True})
    advanced = AdvancedReactionEngine(base)
    advanced.register_policy(AdvancedPolicy(
        "POST_COST",
        (AdvancedCondition("account", "balance", "sum_plus_arg_lte", {"arg": "amount", "role": "account", "predicate": "budget"}),),
        (ComputedArgument("new_balance", "account", "balance", "add", operand_arg="amount"),),
    ))
    advanced.apply(ReactionIntent("POST_COST", {"account": account, "actor": actor}, {"amount": 25}))
    assert u.entity_view(account)["balance"] == 85.0
    root = u.root_hash
    with pytest.raises(ReactionError):
        advanced.apply(ReactionIntent("POST_COST", {"account": account, "actor": actor}, {"amount": 20}))
    assert u.root_hash == root


def test_accelerated_logical_soak(tmp_path: Path):
    report = run_logical_soak(tmp_path / "soak", logical_days=2, cycles_per_day=12)
    assert report.commits == 24
    assert report.invariant_failures == 0
    assert report.final_index == 24
