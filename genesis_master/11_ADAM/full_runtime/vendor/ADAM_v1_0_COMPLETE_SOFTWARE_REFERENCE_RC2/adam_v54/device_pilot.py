from __future__ import annotations

from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Any, Mapping, Protocol

from adam_v41.canonical import digest


class DeviceSafetyError(RuntimeError):
    """Raised when a device action violates a capability or safety contract."""


class PilotStage(str, Enum):
    SIMULATION = "SIMULATION"
    DIGITAL_TWIN = "DIGITAL_TWIN"
    HARDWARE_IN_LOOP = "HARDWARE_IN_LOOP"
    POWERED_ACTUATORS_DISABLED = "POWERED_ACTUATORS_DISABLED"
    RESTRICTED_OPERATION = "RESTRICTED_OPERATION"
    SUPERVISED_OPERATION = "SUPERVISED_OPERATION"


@dataclass(frozen=True)
class ParameterRule:
    name: str
    minimum: float
    maximum: float
    required: bool = True


@dataclass(frozen=True)
class DeviceCapabilityContract:
    device_id: str
    device_class: str
    jurisdiction: str
    sensors: tuple[str, ...]
    actuators: tuple[str, ...]
    commands: Mapping[str, tuple[ParameterRule, ...]]
    safe_state: Mapping[str, Any]
    command_ttl_seconds: int
    human_override_required: bool
    emergency_stop_required: bool
    maximum_command_rate_hz: float

    @property
    def contract_id(self) -> str:
        return digest("ADAM54:CAPABILITY_CONTRACT", {
            **asdict(self),
            "commands": {
                name: [asdict(rule) for rule in rules]
                for name, rules in sorted(self.commands.items())
            },
        })


@dataclass(frozen=True)
class SensorObservation:
    device_id: str
    sensor: str
    value: Any
    observed_at: int
    received_at: int
    sequence: int
    exact_evidence_hash: str

    @property
    def observation_id(self) -> str:
        return digest("ADAM54:SENSOR_OBSERVATION", asdict(self))


@dataclass(frozen=True)
class CommandRequest:
    device_id: str
    command: str
    parameters: Mapping[str, float]
    issued_at: int
    expires_at: int
    authority: str
    goal_id: str
    expected_twin_root: str
    human_override_token: str | None = None

    @property
    def request_id(self) -> str:
        return digest("ADAM54:COMMAND_REQUEST", asdict(self))


@dataclass(frozen=True)
class CommandReceipt:
    request_id: str
    device_id: str
    accepted: bool
    stage: PilotStage
    pre_root: str
    post_root: str
    reason: str
    executed: bool
    hardware_execution: bool

    @property
    def receipt_id(self) -> str:
        material = asdict(self)
        material["stage"] = self.stage.value
        return digest("ADAM54:COMMAND_RECEIPT", material)


class DeviceAdapter(Protocol):
    def observe(self) -> Mapping[str, Any]: ...
    def execute(self, command: str, parameters: Mapping[str, float]) -> Mapping[str, Any]: ...
    def emergency_stop(self) -> None: ...


@dataclass
class DigitalTwin:
    contract: DeviceCapabilityContract
    state: dict[str, Any] = field(default_factory=dict)
    last_sensor_sequence: dict[str, int] = field(default_factory=dict)
    emergency_stopped: bool = False
    manual_override_active: bool = False
    actuators_enabled: bool = False
    command_count: int = 0

    @property
    def root(self) -> str:
        return digest("ADAM54:DIGITAL_TWIN", {
            "contract_id": self.contract.contract_id,
            "state": self.state,
            "sensor_sequences": self.last_sensor_sequence,
            "emergency_stopped": self.emergency_stopped,
            "manual_override_active": self.manual_override_active,
            "actuators_enabled": self.actuators_enabled,
            "command_count": self.command_count,
        })

    def ingest(self, observation: SensorObservation, *, maximum_age_seconds: int) -> str:
        if observation.device_id != self.contract.device_id:
            raise DeviceSafetyError("observation device identity mismatch")
        if observation.sensor not in self.contract.sensors:
            raise DeviceSafetyError("undeclared sensor")
        if observation.received_at - observation.observed_at > maximum_age_seconds:
            raise DeviceSafetyError("stale telemetry")
        prior = self.last_sensor_sequence.get(observation.sensor, 0)
        if observation.sequence <= prior:
            raise DeviceSafetyError("duplicate or reordered telemetry")
        self.last_sensor_sequence[observation.sensor] = observation.sequence
        self.state[observation.sensor] = observation.value
        return self.root

    def enter_safe_state(self) -> str:
        self.state.update(dict(self.contract.safe_state))
        self.actuators_enabled = False
        return self.root


class SimulatedDeviceAdapter:
    """Deterministic device adapter used for simulation and hardware-in-loop contracts."""

    def __init__(self, initial_state: Mapping[str, Any] | None = None) -> None:
        self.state = dict(initial_state or {})
        self.stopped = False

    def observe(self) -> Mapping[str, Any]:
        return dict(self.state)

    def execute(self, command: str, parameters: Mapping[str, float]) -> Mapping[str, Any]:
        if self.stopped:
            raise DeviceSafetyError("simulated device is emergency-stopped")
        self.state["last_command"] = command
        self.state.update({f"parameter:{name}": value for name, value in parameters.items()})
        return dict(self.state)

    def emergency_stop(self) -> None:
        self.stopped = True
        self.state["emergency_stop"] = True


class DevicePilot:
    def __init__(self, contract: DeviceCapabilityContract, adapter: DeviceAdapter | None = None) -> None:
        self.contract = contract
        self.twin = DigitalTwin(contract, state=dict(contract.safe_state))
        self.adapter = adapter or SimulatedDeviceAdapter(contract.safe_state)
        self.stage = PilotStage.SIMULATION
        self.receipts: list[CommandReceipt] = []
        self.last_command_at: int | None = None

    def advance_stage(self, stage: PilotStage, *, safety_approval: bool, hardware_present: bool = False) -> PilotStage:
        order = list(PilotStage)
        current_index = order.index(self.stage)
        requested_index = order.index(stage)
        if requested_index > current_index + 1:
            raise DeviceSafetyError("pilot stages cannot be skipped")
        if requested_index > current_index and not safety_approval:
            raise PermissionError("stage advancement requires safety approval")
        if stage in {PilotStage.HARDWARE_IN_LOOP, PilotStage.POWERED_ACTUATORS_DISABLED,
                     PilotStage.RESTRICTED_OPERATION, PilotStage.SUPERVISED_OPERATION} and not hardware_present:
            raise DeviceSafetyError("requested stage requires declared hardware presence")
        self.stage = stage
        self.twin.actuators_enabled = stage in {PilotStage.RESTRICTED_OPERATION, PilotStage.SUPERVISED_OPERATION}
        return self.stage

    def ingest_observation(self, observation: SensorObservation, *, maximum_age_seconds: int = 5) -> str:
        return self.twin.ingest(observation, maximum_age_seconds=maximum_age_seconds)

    def _validate_parameters(self, command: str, parameters: Mapping[str, float]) -> None:
        rules = self.contract.commands.get(command)
        if rules is None:
            raise DeviceSafetyError("command is not declared by the capability contract")
        allowed = {rule.name for rule in rules}
        unknown = set(parameters) - allowed
        if unknown:
            raise DeviceSafetyError(f"undeclared command parameters: {sorted(unknown)}")
        for rule in rules:
            if rule.required and rule.name not in parameters:
                raise DeviceSafetyError(f"missing required parameter {rule.name}")
            if rule.name in parameters:
                value = float(parameters[rule.name])
                if value < rule.minimum or value > rule.maximum:
                    raise DeviceSafetyError(f"parameter {rule.name} outside safe bounds")

    def evaluate(self, request: CommandRequest, *, now: int, authority_allowed: bool,
                 safety_laws_passed: bool, shadow_prediction_safe: bool) -> CommandReceipt:
        pre_root = self.twin.root
        reason = "accepted"
        accepted = True
        if request.device_id != self.contract.device_id:
            accepted, reason = False, "device identity mismatch"
        elif request.expected_twin_root != pre_root:
            accepted, reason = False, "stale digital twin root"
        elif request.expires_at <= now or request.issued_at > now:
            accepted, reason = False, "command expired or issued in the future"
        elif request.expires_at - request.issued_at > self.contract.command_ttl_seconds:
            accepted, reason = False, "command TTL exceeds capability contract"
        elif self.twin.emergency_stopped:
            accepted, reason = False, "emergency stop is active"
        elif not authority_allowed:
            accepted, reason = False, "authority denied"
        elif not safety_laws_passed:
            accepted, reason = False, "safety laws rejected command"
        elif not shadow_prediction_safe:
            accepted, reason = False, "shadow simulation predicts unsafe outcome"
        elif self.contract.human_override_required and not request.human_override_token:
            accepted, reason = False, "human override token required"
        elif self.last_command_at is not None and self.contract.maximum_command_rate_hz > 0:
            minimum_interval = 1.0 / self.contract.maximum_command_rate_hz
            if now - self.last_command_at < minimum_interval:
                accepted, reason = False, "command rate limit exceeded"
        if accepted:
            self._validate_parameters(request.command, request.parameters)
        executed = False
        hardware_execution = False
        if accepted:
            self.twin.command_count += 1
            self.twin.state["planned_command"] = request.command
            self.twin.state["planned_parameters"] = dict(request.parameters)
            self.last_command_at = now
            if self.stage in {PilotStage.SIMULATION, PilotStage.DIGITAL_TWIN, PilotStage.HARDWARE_IN_LOOP}:
                self.adapter.execute(request.command, request.parameters)
                executed = True
            elif self.stage == PilotStage.POWERED_ACTUATORS_DISABLED:
                reason = "accepted but actuators intentionally disabled"
            elif self.twin.actuators_enabled:
                self.adapter.execute(request.command, request.parameters)
                executed = True
                hardware_execution = not isinstance(self.adapter, SimulatedDeviceAdapter)
        receipt = CommandReceipt(
            request_id=request.request_id,
            device_id=request.device_id,
            accepted=accepted,
            stage=self.stage,
            pre_root=pre_root,
            post_root=self.twin.root,
            reason=reason,
            executed=executed,
            hardware_execution=hardware_execution,
        )
        self.receipts.append(receipt)
        return receipt

    def emergency_stop(self) -> str:
        self.adapter.emergency_stop()
        self.twin.emergency_stopped = True
        return self.twin.enter_safe_state()

    def clear_emergency_stop(self, *, independent_approval: bool) -> str:
        if not independent_approval:
            raise PermissionError("independent approval is required to clear emergency stop")
        self.twin.emergency_stopped = False
        return self.twin.root
