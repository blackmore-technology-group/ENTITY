from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

from adam_v41.canonical import digest

from .recreation import LivingRecreationCenter, RecreationArtifact, RecreationError, SpawnDemand, SpawnReceipt


class EmbodimentError(RuntimeError):
    pass


@dataclass(frozen=True)
class ActuatorCapability:
    name: str
    actions: tuple[str, ...]
    numeric_limits: Mapping[str, tuple[float, float]] = field(default_factory=dict)
    requires_human_override: bool = False


@dataclass(frozen=True)
class CapabilitySurface:
    device_id: str
    device_class: str
    sensors: tuple[str, ...]
    actuators: tuple[ActuatorCapability, ...]
    communication_channels: tuple[str, ...] = ("local",)
    power_budget_watts: float | None = None
    safety_policy: str = "deny-by-default"


@dataclass(frozen=True)
class ActionDecision:
    accepted: bool
    reason: str
    proof_id: str
    command_payload: bytes | None
    spawn_receipt: SpawnReceipt | None


class EmbodimentGateway:
    """Safe universal capability surface for IoT and robotics bodies.

    This gateway constructs commands but does not directly drive hardware. A
    downstream device adapter must independently authenticate and enforce the
    same bounds before execution.
    """

    def __init__(self, recreation: LivingRecreationCenter):
        self.recreation = recreation
        self.surfaces: dict[str, tuple[CapabilitySurface, RecreationArtifact]] = {}

    def register(self, surface: CapabilitySurface) -> RecreationArtifact:
        payload = json.dumps({
            "device_id": surface.device_id,
            "device_class": surface.device_class,
            "sensors": list(surface.sensors),
            "actuators": [asdict(item) for item in surface.actuators],
            "communication_channels": list(surface.communication_channels),
            "power_budget_watts": surface.power_budget_watts,
            "safety_policy": surface.safety_policy,
        }, sort_keys=True, separators=(",", ":")).encode("utf-8")
        artifact = self.recreation.ingest(payload, name=f"{surface.device_id}.robot-capabilities.json", media_type="application/json")
        self.surfaces[surface.device_id] = (surface, artifact)
        return artifact

    def ingest_telemetry(self, device_id: str, telemetry: Mapping[str, Any]) -> RecreationArtifact:
        if device_id not in self.surfaces:
            raise EmbodimentError("unknown device")
        surface, capability_artifact = self.surfaces[device_id]
        unknown = sorted(set(telemetry) - set(surface.sensors) - {"timestamp", "device_id"})
        if unknown:
            raise EmbodimentError(f"telemetry contains undeclared sensors: {unknown}")
        payload = json.dumps({"device_id": device_id, "telemetry": dict(telemetry)}, sort_keys=True, separators=(",", ":")).encode("utf-8")
        artifact = self.recreation.ingest(payload, name=f"{device_id}.telemetry.json", media_type="application/json")
        self.recreation.bond(artifact.artifact_id, "OBSERVED_BY_CAPABILITY_SURFACE", capability_artifact.artifact_id)
        return artifact

    def construct_action(self, device_id: str, actuator_name: str, action: str, parameters: Mapping[str, Any], *, human_override: bool = False, persist: bool = False) -> ActionDecision:
        if device_id not in self.surfaces:
            return self._deny(device_id, actuator_name, action, "unknown device")
        surface, artifact = self.surfaces[device_id]
        actuator = next((item for item in surface.actuators if item.name == actuator_name), None)
        if actuator is None:
            return self._deny(device_id, actuator_name, action, "undeclared actuator")
        if action not in actuator.actions:
            return self._deny(device_id, actuator_name, action, "action not permitted")
        if actuator.requires_human_override and not human_override:
            return self._deny(device_id, actuator_name, action, "human override required")
        for key, bounds in actuator.numeric_limits.items():
            if key not in parameters:
                continue
            try:
                value = float(parameters[key])
            except (TypeError, ValueError):
                return self._deny(device_id, actuator_name, action, f"parameter {key} is not numeric")
            if not (float(bounds[0]) <= value <= float(bounds[1])):
                return self._deny(device_id, actuator_name, action, f"parameter {key} outside safety bounds")
        command = {"device_id": device_id, "actuator": actuator_name, "action": action, "parameters": dict(parameters), "human_override": human_override}
        try:
            payload, receipt = self.recreation.spawn(SpawnDemand(
                artifact.artifact_id,
                application_id=f"embodiment::{surface.device_class}",
                target_format="application/x-adam-robot-command+json",
                purpose="bounded_action",
                device_class=surface.device_class,
                latency_class="real-time",
                persist=persist,
                parameters={"command": command},
            ))
        except RecreationError as exc:
            return self._deny(device_id, actuator_name, action, str(exc))
        proof = digest("ADAM42:EMBODIMENT_ACTION", {"surface": asdict(surface), "command": command, "receipt": asdict(receipt)})
        return ActionDecision(True, "validated and constructed; not physically executed", proof, payload, receipt)

    @staticmethod
    def _deny(device_id: str, actuator: str, action: str, reason: str) -> ActionDecision:
        proof = digest("ADAM42:EMBODIMENT_DENIAL", {"device": device_id, "actuator": actuator, "action": action, "reason": reason})
        return ActionDecision(False, reason, proof, None, None)
