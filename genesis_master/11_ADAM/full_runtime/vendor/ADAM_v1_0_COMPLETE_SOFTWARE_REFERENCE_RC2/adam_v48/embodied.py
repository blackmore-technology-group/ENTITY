from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from adam_v41.canonical import digest


@dataclass(frozen=True)
class SpatialAtom:
    frame_id: str
    x: float
    y: float
    z: float
    orientation: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0)
    uncertainty_m: float = 0.0
    observed_at: int = 0

    @property
    def spatial_id(self) -> str:
        return digest("ADAM48:SPATIAL_ATOM", self.__dict__)


@dataclass(frozen=True)
class SensorCapability:
    name: str
    modality: str
    unit: str
    frequency_hz: float
    reliability: float = 1.0
    security_scope: str = "DEVICE"


@dataclass(frozen=True)
class ActuatorCapability:
    name: str
    action_type: str
    reversible: bool
    requires_human_confirmation: bool = False
    maximum_rate: float | None = None
    safety_class: str = "LOW"


@dataclass(frozen=True)
class DeviceCapabilitySurface:
    device_id: str
    device_type: str
    sensors: tuple[SensorCapability, ...]
    actuators: tuple[ActuatorCapability, ...]
    latency_limit_ms: int
    power_budget_w: float
    allowed_networks: tuple[str, ...]
    authority_scope: str
    human_override_required: bool = True

    @property
    def surface_id(self) -> str:
        return digest("ADAM48:CAPABILITY_SURFACE", {
            "device_id": self.device_id,
            "device_type": self.device_type,
            "sensors": [s.__dict__ for s in self.sensors],
            "actuators": [a.__dict__ for a in self.actuators],
            "latency_limit_ms": self.latency_limit_ms,
            "power_budget_w": self.power_budget_w,
            "allowed_networks": list(self.allowed_networks),
            "authority_scope": self.authority_scope,
            "human_override_required": self.human_override_required,
        })


@dataclass(frozen=True)
class SensorObservation:
    device_id: str
    sensor: str
    value: Any
    unit: str
    observed_at: int
    exact_evidence_hash: str
    location: SpatialAtom | None = None
    confidence: float = 1.0

    @property
    def observation_id(self) -> str:
        return digest("ADAM48:SENSOR_OBSERVATION", {
            "device_id": self.device_id,
            "sensor": self.sensor,
            "value": self.value,
            "unit": self.unit,
            "observed_at": self.observed_at,
            "exact_evidence_hash": self.exact_evidence_hash,
            "location": None if self.location is None else self.location.spatial_id,
            "confidence": self.confidence,
        })


@dataclass(frozen=True)
class ActionCommand:
    device_id: str
    actuator: str
    parameters: Mapping[str, Any]
    requested_by: str
    purpose: str
    authority: str
    expected_twin_version: int
    human_confirmed: bool = False

    @property
    def command_id(self) -> str:
        return digest("ADAM48:ACTION_COMMAND", {
            "device_id": self.device_id,
            "actuator": self.actuator,
            "parameters": dict(self.parameters),
            "requested_by": self.requested_by,
            "purpose": self.purpose,
            "authority": self.authority,
            "expected_twin_version": self.expected_twin_version,
            "human_confirmed": self.human_confirmed,
        })


@dataclass(frozen=True)
class ActionReceipt:
    command_id: str
    accepted: bool
    reason: str
    twin_version_before: int
    twin_version_after: int
    bounded_parameters: Mapping[str, Any]


@dataclass
class DigitalTwin:
    device_id: str
    version: int = 0
    state: dict[str, Any] = field(default_factory=dict)
    observations: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    emergency_stopped: bool = False

    def observe(self, observation: SensorObservation) -> None:
        self.state[f"sensor:{observation.sensor}"] = observation.value
        self.observations.append(observation.observation_id)
        self.version += 1


class EmbodiedPolicyKernel:
    def __init__(self) -> None:
        self.denied_purposes: set[str] = set()
        self.required_authorities: dict[str, set[str]] = {}
        self.parameter_bounds: dict[tuple[str, str], tuple[float, float]] = {}

    def set_bounds(self, actuator: str, parameter: str, minimum: float, maximum: float) -> None:
        self.parameter_bounds[(actuator, parameter)] = (minimum, maximum)

    def validate(self, surface: DeviceCapabilitySurface, twin: DigitalTwin, command: ActionCommand) -> tuple[bool, str, dict[str, Any]]:
        if twin.emergency_stopped:
            return False, "device is emergency-stopped", {}
        if command.expected_twin_version != twin.version:
            return False, "stale digital-twin version", {}
        if command.purpose in self.denied_purposes:
            return False, "purpose denied", {}
        actuator = next((a for a in surface.actuators if a.name == command.actuator), None)
        if actuator is None:
            return False, "unknown actuator", {}
        if actuator.requires_human_confirmation and not command.human_confirmed:
            return False, "human confirmation required", {}
        permitted = self.required_authorities.get(command.actuator)
        if permitted and command.authority not in permitted:
            return False, "authority not permitted", {}
        bounded = dict(command.parameters)
        for (actuator_name, parameter), (minimum, maximum) in self.parameter_bounds.items():
            if actuator_name != command.actuator or parameter not in bounded:
                continue
            value = float(bounded[parameter])
            if value < minimum or value > maximum:
                return False, f"parameter {parameter} outside safety bounds", {}
        return True, "validated", bounded


class EmbodiedUniverseGateway:
    """Safe device nervous system. It validates command envelopes but does not drive hardware directly."""

    def __init__(self, policy: EmbodiedPolicyKernel | None = None) -> None:
        self.policy = policy or EmbodiedPolicyKernel()
        self.surfaces: dict[str, DeviceCapabilitySurface] = {}
        self.twins: dict[str, DigitalTwin] = {}
        self.receipts: list[ActionReceipt] = []

    def register(self, surface: DeviceCapabilitySurface) -> str:
        self.surfaces[surface.device_id] = surface
        self.twins.setdefault(surface.device_id, DigitalTwin(surface.device_id))
        return surface.surface_id

    def ingest(self, observation: SensorObservation) -> int:
        if observation.device_id not in self.surfaces:
            raise KeyError("device not registered")
        sensor = next((s for s in self.surfaces[observation.device_id].sensors if s.name == observation.sensor), None)
        if sensor is None:
            raise PermissionError("sensor not declared")
        if sensor.unit != observation.unit:
            raise ValueError("sensor unit mismatch")
        self.twins[observation.device_id].observe(observation)
        return self.twins[observation.device_id].version

    def simulate_action(self, command: ActionCommand) -> ActionReceipt:
        surface = self.surfaces[command.device_id]
        twin = self.twins[command.device_id]
        accepted, reason, bounded = self.policy.validate(surface, twin, command)
        after = twin.version + (1 if accepted else 0)
        return ActionReceipt(command.command_id, accepted, reason, twin.version, after, bounded)

    def execute_governed(self, command: ActionCommand) -> ActionReceipt:
        receipt = self.simulate_action(command)
        twin = self.twins[command.device_id]
        if receipt.accepted:
            twin.state[f"actuator:{command.actuator}"] = dict(receipt.bounded_parameters)
            twin.actions.append(command.command_id)
            twin.version += 1
        self.receipts.append(receipt)
        return receipt

    def emergency_stop(self, device_id: str, authority: str) -> None:
        if not authority:
            raise PermissionError("authority required")
        twin = self.twins[device_id]
        twin.emergency_stopped = True
        twin.version += 1

    def reset_stop(self, device_id: str, *, authority: str, human_confirmed: bool) -> None:
        if not authority or not human_confirmed:
            raise PermissionError("authorized human confirmation required")
        twin = self.twins[device_id]
        twin.emergency_stopped = False
        twin.version += 1


@dataclass
class EdgeCognitionNode:
    node_id: str
    jurisdiction: str
    online: bool = True
    queued_observations: list[SensorObservation] = field(default_factory=list)
    synchronized_observations: set[str] = field(default_factory=set)

    def observe(self, observation: SensorObservation) -> None:
        self.queued_observations.append(observation)

    def synchronize(self, gateway: EmbodiedUniverseGateway) -> int:
        if not self.online:
            return 0
        count = 0
        remaining: list[SensorObservation] = []
        for observation in self.queued_observations:
            if observation.observation_id in self.synchronized_observations:
                continue
            try:
                gateway.ingest(observation)
            except (KeyError, ValueError, PermissionError):
                remaining.append(observation)
                continue
            self.synchronized_observations.add(observation.observation_id)
            count += 1
        self.queued_observations = remaining
        return count
