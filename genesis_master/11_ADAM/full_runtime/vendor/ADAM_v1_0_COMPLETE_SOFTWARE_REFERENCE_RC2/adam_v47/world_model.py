from __future__ import annotations

from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping, Sequence

from adam_v41.canonical import digest
from adam_v44 import AtomicPhysicsKernel, ReactionIntent, ReactionProof


@dataclass(frozen=True)
class TransitionExample:
    state_signature: tuple[str, ...]
    action: str
    environment_signature: tuple[str, ...]
    next_signature: tuple[str, ...]
    outcome_labels: tuple[str, ...] = ()
    evidence_id: str | None = None


@dataclass(frozen=True)
class TransitionPrediction:
    next_signature: tuple[str, ...] | None
    confidence: float
    alternatives: tuple[tuple[tuple[str, ...], float], ...]
    assumptions: tuple[str, ...]
    invalidators: tuple[str, ...]
    abstained: bool


class TemporalDynamicsOrgan:
    def __init__(self, abstain_threshold: float = 0.55) -> None:
        self.counts: dict[tuple[tuple[str, ...], str, tuple[str, ...]], Counter[tuple[str, ...]]] = defaultdict(Counter)
        self.fallback: dict[str, Counter[tuple[str, ...]]] = defaultdict(Counter)
        self.abstain_threshold = abstain_threshold
        self.training_root: str | None = None

    def train(self, examples: Sequence[TransitionExample]) -> dict[str, Any]:
        self.counts.clear()
        self.fallback.clear()
        for example in examples:
            key = (tuple(sorted(example.state_signature)), example.action, tuple(sorted(example.environment_signature)))
            nxt = tuple(sorted(example.next_signature))
            self.counts[key][nxt] += 1
            self.fallback[example.action][nxt] += 1
        self.training_root = digest("ADAM47:TRANSITION_CORPUS", [e.__dict__ for e in examples])
        return {"examples": len(examples), "contexts": len(self.counts), "training_root": self.training_root}

    def predict(self, state: Iterable[str], action: str, environment: Iterable[str]) -> TransitionPrediction:
        key = (tuple(sorted(state)), action, tuple(sorted(environment)))
        counts = self.counts.get(key, self.fallback.get(action, Counter()))
        total = sum(counts.values())
        if not total:
            return TransitionPrediction(None, 0.0, (), ("unknown action/context",), ("new evidence",), True)
        ranked = tuple((signature, count / total) for signature, count in counts.most_common())
        best, confidence = ranked[0]
        abstained = confidence < self.abstain_threshold
        return TransitionPrediction(
            None if abstained else best,
            confidence,
            ranked[:5],
            (f"trained context root {self.training_root}",),
            ("environment differs", "reaction law version changes", "missing observation"),
            abstained,
        )


@dataclass(frozen=True)
class ShadowResult:
    branch_root: str
    proof: ReactionProof | None
    prediction: TransitionPrediction | None
    law_violation: str | None
    uncertainty: float


class ShadowUniverseLab:
    def __init__(self, kernel: AtomicPhysicsKernel, dynamics: TemporalDynamicsOrgan | None = None) -> None:
        self.kernel = kernel
        self.dynamics = dynamics

    def simulate(self, intent: ReactionIntent, *, state_signature: Iterable[str] = (), environment: Iterable[str] = ()) -> ShadowResult:
        branch = self.kernel.branch()
        prediction = None
        if self.dynamics is not None:
            prediction = self.dynamics.predict(state_signature, intent.reaction_name, environment)
        try:
            proof = branch.commit(intent)
            uncertainty = 1.0 - (prediction.confidence if prediction else 1.0)
            return ShadowResult(branch.root, proof, prediction, None, uncertainty)
        except Exception as exc:  # bounded simulator converts validation failure to an explicit result
            return ShadowResult(branch.root, None, prediction, str(exc), 1.0)

    def compare(self, intents: Sequence[ReactionIntent], *, state_signature: Iterable[str] = (), environment: Iterable[str] = ()) -> list[ShadowResult]:
        return [self.simulate(intent, state_signature=state_signature, environment=environment) for intent in intents]


@dataclass(frozen=True)
class Goal:
    goal_id: str
    desired_facts: frozenset[str]
    requested_by: str
    law_set: tuple[str, ...]
    deadline: int | None = None
    priority: int = 0


@dataclass(frozen=True)
class PlanStep:
    action: str
    resulting_facts: frozenset[str]
    cost: float


@dataclass(frozen=True)
class Plan:
    goal_id: str
    steps: tuple[PlanStep, ...]
    total_cost: float
    reached: bool


class MultiScalePlanner:
    """Bounded symbolic planner. It proposes action sequences but has no commit authority."""

    def __init__(self, action_model: Mapping[str, tuple[frozenset[str], frozenset[str], float]]) -> None:
        # action -> (requires, adds, cost)
        self.action_model = dict(action_model)

    def plan(self, start: frozenset[str], goal: Goal, max_depth: int = 8) -> Plan:
        queue = deque([(start, tuple(), 0.0)])
        seen = {start: 0.0}
        while queue:
            state, steps, cost = queue.popleft()
            if goal.desired_facts <= state:
                return Plan(goal.goal_id, steps, cost, True)
            if len(steps) >= max_depth:
                continue
            for action, (requires, adds, action_cost) in sorted(self.action_model.items()):
                if not requires <= state:
                    continue
                nxt = frozenset(set(state) | set(adds))
                nxt_cost = cost + action_cost
                if seen.get(nxt, float("inf")) <= nxt_cost:
                    continue
                seen[nxt] = nxt_cost
                queue.append((nxt, (*steps, PlanStep(action, nxt, action_cost)), nxt_cost))
        return Plan(goal.goal_id, tuple(), float("inf"), False)


@dataclass
class DerivedNode:
    node_id: str
    dependencies: set[str]
    compute: Callable[[Mapping[str, Any]], Any]
    value: Any = None
    version: int = 0


class IncrementalDependencyEngine:
    """Updates only structures downstream of changed atoms/bonds/laws."""

    def __init__(self) -> None:
        self.base: dict[str, Any] = {}
        self.derived: dict[str, DerivedNode] = {}
        self.reverse: dict[str, set[str]] = defaultdict(set)
        self.recompute_count = 0

    def set_base(self, node_id: str, value: Any) -> set[str]:
        self.base[node_id] = value
        return self.invalidate_and_recompute({node_id})

    def add_derived(self, node_id: str, dependencies: Iterable[str], compute: Callable[[Mapping[str, Any]], Any]) -> Any:
        deps = set(dependencies)
        node = DerivedNode(node_id, deps, compute)
        self.derived[node_id] = node
        for dep in deps:
            self.reverse[dep].add(node_id)
        self._recompute(node_id)
        return node.value

    def _context(self) -> dict[str, Any]:
        return {**self.base, **{k: v.value for k, v in self.derived.items()}}

    def _recompute(self, node_id: str) -> None:
        node = self.derived[node_id]
        missing = [dep for dep in node.dependencies if dep not in self.base and dep not in self.derived]
        if missing:
            raise KeyError(f"missing dependencies {missing}")
        node.value = node.compute(self._context())
        node.version += 1
        self.recompute_count += 1

    def invalidate_and_recompute(self, changed: set[str]) -> set[str]:
        affected: set[str] = set()
        queue = deque(changed)
        while queue:
            dep = queue.popleft()
            for child in self.reverse.get(dep, ()):
                if child in affected:
                    continue
                affected.add(child)
                queue.append(child)
        # deterministic topological retry for small bounded graphs
        pending = set(affected)
        for _ in range(len(pending) + 1):
            progressed = False
            for node_id in sorted(list(pending)):
                if all(dep not in pending for dep in self.derived[node_id].dependencies):
                    self._recompute(node_id)
                    pending.remove(node_id)
                    progressed = True
            if not pending or not progressed:
                break
        if pending:
            raise ValueError(f"cyclic dependency graph: {sorted(pending)}")
        return affected

@dataclass(frozen=True)
class AtomicGoal:
    desired_state: tuple[str, ...]
    requested_by: str
    must_satisfy: tuple[str, ...]
    deadline: int | None
    priority: int
    authority: str
    security_scope: str = "PRIVATE"

    @property
    def goal_id(self) -> str:
        return digest("ADAM47:ATOMIC_GOAL", {
            "desired_state": sorted(self.desired_state),
            "requested_by": self.requested_by,
            "must_satisfy": sorted(self.must_satisfy),
            "deadline": self.deadline,
            "priority": self.priority,
            "authority": self.authority,
            "security_scope": self.security_scope,
        })

    def canonical(self) -> dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "desired_state": list(self.desired_state),
            "requested_by": self.requested_by,
            "must_satisfy": list(self.must_satisfy),
            "deadline": self.deadline,
            "priority": self.priority,
            "authority": self.authority,
            "security_scope": self.security_scope,
            "commit_authority": False,
        }
