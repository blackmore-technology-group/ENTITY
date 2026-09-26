from __future__ import annotations

import platform

from .audit import AuditLog
from .capabilities import CapabilityRegistry
from .config import load_config
from .engineering_terminal import EngineeringTerminal
from .models import ActionRequest, ActionResult
from .policy import PolicyEngine


class BECPCore:
    def __init__(self, config_path: str | None = None) -> None:
        self.config = load_config(config_path)
        self.audit = AuditLog(str(self.config["audit_path"]))
        terminal_config = dict(self.config.get("engineering_terminal", {}))
        self.engineering_terminal = (
            EngineeringTerminal(terminal_config, self.audit)
            if terminal_config.get("enabled")
            else None
        )
        self.registry = CapabilityRegistry(
            self.config.get("approved_commands", {}),
            engineering_terminal=self.engineering_terminal,
        )
        self.policy = PolicyEngine(
            self.config.get("roles", {}),
            self.config.get("allowed_roots", []),
        )

    def execute(self, request: ActionRequest) -> ActionResult:
        if request.capability.startswith("engineering.terminal."):
            local_names = {
                "local",
                platform.node().casefold(),
                str(self.config.get("device_id", "")).casefold(),
            }
            if request.target.casefold() not in local_names:
                return ActionResult(
                    ok=False,
                    capability=request.capability,
                    target=request.target,
                    correlation_id=request.correlation_id,
                    error="engineering terminal target does not match this enrolled workstation",
                )
        spec = self.registry.specs.get(request.capability)
        if spec is None:
            return ActionResult(
                ok=False,
                capability=request.capability,
                target=request.target,
                correlation_id=request.correlation_id,
                error="unknown capability",
            )
        decision = self.policy.decide(request, spec)
        self.audit.append({
            "event": "becp.policy_decision",
            "actor": request.actor,
            "role": request.role,
            "capability": request.capability,
            "target": request.target,
            "correlation_id": request.correlation_id,
            "allowed": decision.allowed,
            "reason": decision.reason,
            "approval_id": request.approval_id,
        })
        if not decision.allowed:
            return ActionResult(
                ok=False,
                capability=request.capability,
                target=request.target,
                correlation_id=request.correlation_id,
                error=decision.reason,
            )
        params = dict(request.params)
        if request.capability == "engineering.terminal.start":
            params["actor"] = request.actor
        try:
            data = self.registry.execute(request.capability, params)
            result = ActionResult(
                ok=True,
                capability=request.capability,
                target=request.target,
                correlation_id=request.correlation_id,
                data=data,
            )
        except Exception as exc:
            result = ActionResult(
                ok=False,
                capability=request.capability,
                target=request.target,
                correlation_id=request.correlation_id,
                error=f"{type(exc).__name__}: {exc}",
            )
        self.audit.append({
            "event": "becp.action_result",
            "actor": request.actor,
            "role": request.role,
            "capability": request.capability,
            "target": request.target,
            "correlation_id": request.correlation_id,
            "ok": result.ok,
            "error": result.error,
        })
        return result
