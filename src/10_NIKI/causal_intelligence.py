from __future__ import annotations

import hashlib
import json
import math
import statistics
from copy import deepcopy
from pathlib import Path
from threading import RLock
from typing import Any


MODEL_SCHEMA = "niki-causal-model-v1"
ANALYSIS_SCHEMA = "niki-causal-analysis-v1"
_ALLOWED_EQUATIONS = {"input", "constant", "linear", "logistic", "threshold", "lookup", "min", "max", "sum", "mean"}


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _clamp(value: float, bounds: list | tuple | None) -> float:
    if not bounds or len(bounds) != 2:
        return value
    return max(float(bounds[0]), min(float(bounds[1]), value))


class CausalModelError(ValueError):
    pass


class CausalModelRegistry:
    """Stores only explicitly ENTITY-approved causal model specifications.

    The registry never learns or activates models by itself.  A model may also be
    supplied ephemerally by an application for one reasoning call, but that does
    not make the model authoritative or persistent.
    """

    def __init__(self, state_dir: str | Path):
        self.root = Path(state_dir) / "niki_intelligence"
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "causal_models.json"
        self._lock = RLock()
        self.models: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.is_file():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                self.models = {str(k): v for k, v in data.items() if isinstance(v, dict)}
        except Exception:
            self.models = {}

    def _save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.models, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(self.path)

    def register(self, spec: dict[str, Any], approval: dict[str, Any]) -> dict[str, Any]:
        validate_model_spec(spec)
        if not isinstance(approval, dict) or approval.get("approved") is not True:
            raise PermissionError("causal model activation requires explicit approval")
        if str(approval.get("authority") or "").upper() != "ENTITY":
            raise PermissionError("causal model activation authority must be ENTITY")
        if not str(approval.get("approval_id") or "").strip():
            raise PermissionError("causal model activation requires approval_id")
        record = deepcopy(spec)
        record["activation"] = {
            "authority": "ENTITY",
            "approval_id": str(approval["approval_id"]),
            "approved": True,
        }
        with self._lock:
            self.models[str(spec["model_id"])] = record
            self._save()
        return {"registered": True, "model_id": spec["model_id"], "model_sha256": _digest(spec)}

    def get(self, model_id: str) -> dict[str, Any] | None:
        item = self.models.get(str(model_id))
        return deepcopy(item) if item else None

    def status(self) -> dict[str, Any]:
        return {
            "schema": "niki-causal-model-registry-status-v1",
            "model_count": len(self.models),
            "activation_authority": "ENTITY",
            "autonomous_activation": False,
        }


def validate_model_spec(spec: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(spec, dict) or spec.get("schema") != MODEL_SCHEMA:
        raise CausalModelError(f"causal model must use schema {MODEL_SCHEMA}")
    if not str(spec.get("model_id") or "").strip():
        raise CausalModelError("causal model requires model_id")
    variables = spec.get("variables")
    if not isinstance(variables, dict) or not variables:
        raise CausalModelError("causal model requires variables")
    provenance = spec.get("provenance")
    if not isinstance(provenance, dict) or not str(provenance.get("source") or "").strip():
        raise CausalModelError("causal model requires provenance.source")
    for name, node in variables.items():
        if not isinstance(node, dict):
            raise CausalModelError(f"causal variable {name} must be an object")
        parents = node.get("parents") or []
        if not isinstance(parents, list):
            raise CausalModelError(f"causal variable {name} parents must be a list")
        unknown = [p for p in parents if p not in variables]
        if unknown:
            raise CausalModelError(f"causal variable {name} has unknown parents: {unknown}")
        equation = node.get("equation") or {"kind": "input"}
        kind = str(equation.get("kind") or "input")
        if kind not in _ALLOWED_EQUATIONS:
            raise CausalModelError(f"unsupported causal equation kind: {kind}")
    _topological_order(variables)
    return spec


def _topological_order(variables: dict[str, dict[str, Any]]) -> list[str]:
    visiting: set[str] = set()
    visited: set[str] = set()
    order: list[str] = []

    def visit(name: str) -> None:
        if name in visited:
            return
        if name in visiting:
            raise CausalModelError("causal model contains a cycle")
        visiting.add(name)
        for parent in variables[name].get("parents") or []:
            visit(parent)
        visiting.remove(name)
        visited.add(name)
        order.append(name)

    for name in sorted(variables):
        visit(name)
    return order


def _evaluate_equation(name: str, node: dict[str, Any], state: dict[str, Any]) -> Any:
    eq = node.get("equation") or {"kind": "input"}
    kind = str(eq.get("kind") or "input")
    parents = list(node.get("parents") or [])
    values = {p: state.get(p) for p in parents}
    if kind == "input":
        return state.get(name, eq.get("default"))
    if kind == "constant":
        return eq.get("value")
    if kind in {"linear", "logistic"}:
        value = _num(eq.get("intercept", 0.0))
        weights = eq.get("weights") or {}
        for parent in parents:
            value += _num(weights.get(parent, 0.0)) * _num(values.get(parent), 0.0)
        if kind == "logistic":
            value = 1.0 / (1.0 + math.exp(-max(-60.0, min(60.0, value))))
        return _clamp(value, eq.get("clamp"))
    if kind == "threshold":
        source = str(eq.get("source") or (parents[0] if parents else ""))
        value = values.get(source, state.get(source))
        threshold = eq.get("threshold", 0)
        comparator = str(eq.get("comparator") or "gte")
        if comparator == "gt": passed = _num(value) > _num(threshold)
        elif comparator == "lt": passed = _num(value) < _num(threshold)
        elif comparator == "lte": passed = _num(value) <= _num(threshold)
        elif comparator == "eq": passed = value == threshold
        else: passed = _num(value) >= _num(threshold)
        return eq.get("true_value", True) if passed else eq.get("false_value", False)
    if kind == "lookup":
        source = str(eq.get("source") or (parents[0] if parents else ""))
        key = str(values.get(source, state.get(source)))
        return (eq.get("map") or {}).get(key, eq.get("default"))
    nums = [_num(values.get(p), 0.0) for p in parents]
    if kind == "min": return min(nums) if nums else eq.get("default")
    if kind == "max": return max(nums) if nums else eq.get("default")
    if kind == "sum": return sum(nums)
    if kind == "mean": return sum(nums) / len(nums) if nums else eq.get("default")
    raise CausalModelError(f"unhandled causal equation kind: {kind}")


class CausalIntelligenceEngine:
    """Bounded causal/counterfactual reasoning with no execution authority."""

    VERSION = "1.0"

    def __init__(self, state_dir: str | Path):
        self.registry = CausalModelRegistry(state_dir)

    def evaluate(self, spec: dict[str, Any], observed: dict[str, Any], interventions: dict[str, Any] | None = None) -> dict[str, Any]:
        validate_model_spec(spec)
        variables = spec["variables"]
        order = _topological_order(variables)
        result = deepcopy(observed or {})
        forced = dict(interventions or {})
        unknown = [name for name in forced if name not in variables]
        if unknown:
            raise CausalModelError(f"intervention targets unknown variables: {unknown}")
        for name in order:
            if name in forced:
                result[name] = forced[name]
            else:
                result[name] = _evaluate_equation(name, variables[name], result)
        return result

    @staticmethod
    def compare(baseline: dict[str, Any], counterfactual: dict[str, Any], variables: list[str]) -> dict[str, Any]:
        differences: dict[str, Any] = {}
        for name in variables:
            before, after = baseline.get(name), counterfactual.get(name)
            if before == after:
                continue
            delta = after - before if isinstance(before, (int, float)) and isinstance(after, (int, float)) else None
            differences[name] = {"baseline": before, "counterfactual": after, "delta": delta}
        return differences

    @staticmethod
    def _objective_effect(baseline: Any, after: Any, direction: str) -> tuple[float | None, str]:
        if not isinstance(baseline, (int, float)) or not isinstance(after, (int, float)):
            return None, "not_numeric"
        raw = float(after) - float(baseline)
        improvement = raw if direction == "maximize" else -raw
        if improvement > 1e-12:
            return improvement, "improves"
        if improvement < -1e-12:
            return improvement, "degrades"
        return 0.0, "no_effect"

    def analyze(self, request: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(request, dict):
            return {"schema": ANALYSIS_SCHEMA, "performed": False, "reason": "no_causal_request"}
        spec = request.get("model")
        if spec is None and request.get("model_id"):
            spec = self.registry.get(str(request["model_id"]))
        if not isinstance(spec, dict):
            return {"schema": ANALYSIS_SCHEMA, "performed": False, "reason": "no_qualified_causal_model"}
        validate_model_spec(spec)
        observed = request.get("observed") or {}
        baseline = self.evaluate(spec, observed)
        scenarios = request.get("interventions") or []
        objectives = request.get("objectives") or []
        if not isinstance(scenarios, list):
            raise CausalModelError("interventions must be a list")
        if not isinstance(objectives, list):
            raise CausalModelError("objectives must be a list")
        variable_names = list(spec["variables"].keys())
        outcomes = []
        for idx, scenario in enumerate(scenarios[:32]):
            if not isinstance(scenario, dict):
                continue
            changes = scenario.get("set") or scenario.get("interventions") or {}
            if not isinstance(changes, dict) or not changes:
                continue
            cf = self.evaluate(spec, observed, changes)
            effects = []
            total_positive = 0.0
            total_negative = 0.0
            for objective in objectives[:16]:
                if not isinstance(objective, dict):
                    continue
                name = str(objective.get("variable") or "")
                if name not in spec["variables"]:
                    continue
                direction = str(objective.get("direction") or "maximize").lower()
                if direction not in {"maximize", "minimize"}:
                    direction = "maximize"
                improvement, classification = self._objective_effect(baseline.get(name), cf.get(name), direction)
                weight = max(0.0, _num(objective.get("weight", 1.0), 1.0))
                if improvement is not None:
                    weighted = improvement * weight
                    if weighted > 0: total_positive += weighted
                    elif weighted < 0: total_negative += weighted
                effects.append({
                    "variable": name, "direction": direction, "weight": weight,
                    "baseline": baseline.get(name), "counterfactual": cf.get(name),
                    "improvement": improvement, "classification": classification,
                })
            net = total_positive + total_negative
            classification = "improves" if net > 1e-12 else ("degrades" if net < -1e-12 else "no_effect")
            outcomes.append({
                "scenario_id": str(scenario.get("scenario_id") or f"cf-{idx+1}"),
                "interventions": deepcopy(changes),
                "state": cf,
                "differences": self.compare(baseline, cf, variable_names),
                "objective_effects": effects,
                "net_improvement": net,
                "classification": classification,
                "recommended": classification == "improves",
            })
        outcomes.sort(key=lambda row: (row["net_improvement"], row["scenario_id"]), reverse=True)
        provenance = deepcopy(spec.get("provenance") or {})
        return {
            "schema": ANALYSIS_SCHEMA,
            "performed": True,
            "model_id": spec["model_id"],
            "model_version": str(spec.get("model_version") or "unspecified"),
            "model_sha256": _digest(spec),
            "model_provenance": provenance,
            "baseline": baseline,
            "counterfactuals": outcomes,
            "best_positive_intervention": next((x for x in outcomes if x["recommended"]), None),
            "authority": "NIKI_REASONING_ONLY",
            "authoritative_state_mutation": False,
            "execution_authority": "ENTITY",
            "executor": "ADAM",
            "claim_boundary": "counterfactual output is model-dependent analytical evidence, not proof of causation or authority to act",
        }

    @staticmethod
    def stability(feature: str, environments: list[dict[str, Any]]) -> dict[str, Any]:
        samples = []
        for env in environments or []:
            metrics = env.get("metrics") if isinstance(env, dict) else None
            if isinstance(metrics, dict) and isinstance(metrics.get(feature), (int, float)):
                samples.append(float(metrics[feature]))
        if not samples:
            return {"feature": feature, "sample_count": 0, "stable": False, "method": "empirical_stability_heuristic_not_IRM_proof"}
        mean = statistics.fmean(samples)
        std = statistics.pstdev(samples) if len(samples) > 1 else 0.0
        scale = max(abs(mean), 1e-9)
        cv = std / scale
        return {
            "feature": feature,
            "sample_count": len(samples),
            "mean": mean,
            "std_dev": std,
            "coefficient_of_variation": cv,
            "stable": len(samples) >= 2 and cv <= 0.05,
            "method": "empirical_stability_heuristic_not_IRM_proof",
        }

    def status(self) -> dict[str, Any]:
        return {
            "schema": "niki-causal-intelligence-status-v1",
            "version": self.VERSION,
            "structural_causal_models": True,
            "hard_interventions": True,
            "counterfactuals": True,
            "objective_ranking": True,
            "invariant_stability_heuristic": True,
            "arbitrary_code_equations": False,
            "autonomous_model_activation": False,
            "autonomous_execution": False,
            "registry": self.registry.status(),
        }