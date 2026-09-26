from __future__ import annotations

from pathlib import Path

from .models import ActionRequest, CapabilitySpec, PolicyDecision, RiskLevel


class PolicyEngine:
    def __init__(self, roles: dict[str, int], allowed_roots: list[str]) -> None:
        self.roles = roles
        self.allowed_roots = [Path(p).resolve() for p in allowed_roots]

    def decide(self, request: ActionRequest, spec: CapabilitySpec) -> PolicyDecision:
        max_risk = self.roles.get(request.role)
        if max_risk is None:
            return PolicyDecision(allowed=False, reason="unknown role")
        if spec.risk > max_risk:
            return PolicyDecision(allowed=False, reason="role risk ceiling exceeded")
        if spec.requires_approval and not request.approval_id:
            return PolicyDecision(
                allowed=False,
                reason="explicit approval required",
                requires_approval=True,
            )
        if request.capability.startswith("file."):
            raw_path = request.params.get("path")
            if raw_path and not self.path_allowed(str(raw_path)):
                return PolicyDecision(allowed=False, reason="path outside authorized roots")
        return PolicyDecision(allowed=True, reason="policy allowed")

    def path_allowed(self, candidate: str) -> bool:
        path = Path(candidate).resolve()
        for root in self.allowed_roots:
            try:
                path.relative_to(root)
                return True
            except ValueError:
                continue
        return False


DEFAULT_ROLE_LIMITS = {
    "field_app": int(RiskLevel.DIAGNOSTIC),
    "sar_operator": int(RiskLevel.DIAGNOSTIC),
    "qa_engineer": int(RiskLevel.CHANGE),
    "chatgpt_engineer": int(RiskLevel.CHANGE),
    "niki_engineer": int(RiskLevel.CHANGE),
    "chatgpt_privileged_engineer": int(RiskLevel.PRIVILEGED),
    "niki_privileged_engineer": int(RiskLevel.PRIVILEGED),
    "blackmore_admin": int(RiskLevel.PRIVILEGED),
}
