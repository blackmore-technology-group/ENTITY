from __future__ import annotations

import pytest

from adam_v54 import (
    CommandRequest,
    DeviceCapabilityContract,
    DevicePilot,
    DeviceSafetyError,
    ParameterRule,
    PilotStage,
    SensorObservation,
)


def contract() -> DeviceCapabilityContract:
    return DeviceCapabilityContract(
        device_id="pilot-1",
        device_class="LOW_ENERGY_SIMULATOR",
        jurisdiction="CA-BC",
        sensors=("pressure",),
        actuators=("output",),
        commands={"SET_OUTPUT": (ParameterRule("percent", 0.0, 25.0),)},
        safe_state={"output": 0.0},
        command_ttl_seconds=5,
        human_override_required=True,
        emergency_stop_required=True,
        maximum_command_rate_hz=1.0,
    )


def test_device_pilot_observation_command_and_estop():
    pilot = DevicePilot(contract())
    pilot.ingest_observation(SensorObservation("pilot-1", "pressure", 2.0, 100, 101, 1, "evidence"))
    request = CommandRequest("pilot-1", "SET_OUTPUT", {"percent": 10.0}, 101, 105, "operator", "goal", pilot.twin.root, "human")
    receipt = pilot.evaluate(request, now=102, authority_allowed=True, safety_laws_passed=True, shadow_prediction_safe=True)
    assert receipt.accepted and receipt.executed and not receipt.hardware_execution
    pilot.emergency_stop()
    stopped = CommandRequest("pilot-1", "SET_OUTPUT", {"percent": 5.0}, 103, 106, "operator", "goal", pilot.twin.root, "human")
    assert not pilot.evaluate(stopped, now=103, authority_allowed=True, safety_laws_passed=True, shadow_prediction_safe=True).accepted


def test_device_pilot_rejects_bounds_stale_and_missing_human():
    pilot = DevicePilot(contract())
    with pytest.raises(DeviceSafetyError):
        pilot.ingest_observation(SensorObservation("pilot-1", "pressure", 2.0, 1, 20, 1, "evidence"), maximum_age_seconds=5)
    request = CommandRequest("pilot-1", "SET_OUTPUT", {"percent": 50.0}, 10, 12, "operator", "goal", pilot.twin.root, "human")
    with pytest.raises(DeviceSafetyError):
        pilot.evaluate(request, now=10, authority_allowed=True, safety_laws_passed=True, shadow_prediction_safe=True)
    missing_human = CommandRequest("pilot-1", "SET_OUTPUT", {"percent": 10.0}, 10, 12, "operator", "goal", pilot.twin.root)
    assert not pilot.evaluate(missing_human, now=10, authority_allowed=True, safety_laws_passed=True, shadow_prediction_safe=True).accepted


def test_device_stage_progression_is_governed():
    pilot = DevicePilot(contract())
    with pytest.raises(DeviceSafetyError):
        pilot.advance_stage(PilotStage.HARDWARE_IN_LOOP, safety_approval=True, hardware_present=True)
    assert pilot.advance_stage(PilotStage.DIGITAL_TWIN, safety_approval=True) == PilotStage.DIGITAL_TWIN
    with pytest.raises(DeviceSafetyError):
        pilot.advance_stage(PilotStage.HARDWARE_IN_LOOP, safety_approval=True, hardware_present=False)
    assert pilot.advance_stage(PilotStage.HARDWARE_IN_LOOP, safety_approval=True, hardware_present=True) == PilotStage.HARDWARE_IN_LOOP
