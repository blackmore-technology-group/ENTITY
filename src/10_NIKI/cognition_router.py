from __future__ import annotations

from typing import Any


class AdaptiveCognitionRouter:
    """Selects bounded reasoning stages; it never grants authority or executes actions."""

    VERSION = "1.0"

    def route(self, *, analysis: dict[str, Any], evidence_count: int, conflicts: dict[str, Any] | None,
              domain_intelligence: dict[str, Any] | None, metadata: dict[str, Any] | None,
              causal_available: bool) -> dict[str, Any]:
        md = metadata or {}
        conflicts = conflicts or {}
        domain_intelligence = domain_intelligence or {}
        intent = str((analysis or {}).get("intent") or "situational_awareness")
        risk = str(md.get("risk_level") or "normal").lower()
        uncertainty = float(md.get("uncertainty_hint", 0.0) or 0.0)
        conflict_ratio = max(float(conflicts.get("explicit_conflict_ratio", 0.0) or 0.0),
                             float(conflicts.get("polarity_disagreement", 0.0) or 0.0))
        stages = ["deterministic_request_analysis"]
        reasons = ["request classified before optional reasoning stages"]

        if evidence_count > 0:
            stages.append("adam_evidence_reasoning")
            reasons.append("ADAM evidence is available")
        if (analysis or {}).get("requires_spatial_context"):
            stages.append("bsie_spatial_reasoning")
            reasons.append("request requires spatial/world context")
        if domain_intelligence.get("present"):
            stages.append("application_domain_model_reasoning")
            reasons.append("application-owned domain signals supplied")

        wants_causal = bool(md.get("causal_analysis")) or intent in {"diagnosis", "prediction", "planning", "comparison", "safety"}
        if causal_available and wants_causal:
            stages.append("causal_intervention_reasoning")
            stages.append("counterfactual_reasoning")
            reasons.append("qualified causal model supplied for an intervention-relevant request")

        if conflict_ratio >= 0.15 or uncertainty >= 0.35 or risk in {"high", "critical"}:
            stages.append("qualified_critique")
            reasons.append("risk, uncertainty, or evidence conflict requires extra critique")

        stages.append("synthesis")
        return {
            "schema": "niki-adaptive-cognition-route-v1",
            "router_version": self.VERSION,
            "intent": intent,
            "risk_level": risk,
            "stages": stages,
            "reasons": reasons,
            "authority": "NIKI_ROUTING_ONLY",
            "execution_authority": "ENTITY",
            "executor": "ADAM",
            "autonomous_side_effects": False,
            "model_selection_is_not_authority": True,
        }

    def status(self) -> dict[str, Any]:
        return {
            "schema": "niki-adaptive-cognition-router-status-v1",
            "version": self.VERSION,
            "dynamic_stage_selection": True,
            "uses_risk_uncertainty_conflict": True,
            "autonomous_side_effects": False,
            "authority_owner": "NIKI_REASONING_ONLY",
        }