from __future__ import annotations

from adam_v48 import (
    ActionCommand, ActuatorCapability, DeviceCapabilitySurface, EdgeCognitionNode,
    EmbodiedPolicyKernel, EmbodiedUniverseGateway, SensorCapability, SensorObservation,
)


def surface():
    return DeviceCapabilitySurface(
        device_id="ROVER1", device_type="ROVER",
        sensors=(SensorCapability("temperature", "scalar", "C", 1.0),),
        actuators=(ActuatorCapability("drive", "motion", reversible=True, requires_human_confirmation=True),),
        latency_limit_ms=100, power_budget_w=200, allowed_networks=("EDGE",), authority_scope="FIELD",
    )


def test_sensor_observation_updates_digital_twin():
    gateway = EmbodiedUniverseGateway()
    gateway.register(surface())
    obs = SensorObservation("ROVER1", "temperature", 21.5, "C", 1, "hash")
    assert gateway.ingest(obs) == 1
    assert gateway.twins["ROVER1"].state["sensor:temperature"] == 21.5


def test_physical_action_requires_confirmation_and_current_twin():
    policy = EmbodiedPolicyKernel()
    policy.set_bounds("drive", "speed", 0.0, 1.0)
    gateway = EmbodiedUniverseGateway(policy)
    gateway.register(surface())
    cmd = ActionCommand("ROVER1", "drive", {"speed": 0.5}, "PLANNER", "NAVIGATION", "FIELD", 0, False)
    assert not gateway.execute_governed(cmd).accepted
    cmd2 = ActionCommand("ROVER1", "drive", {"speed": 0.5}, "PLANNER", "NAVIGATION", "FIELD", 0, True)
    assert gateway.execute_governed(cmd2).accepted
    stale = ActionCommand("ROVER1", "drive", {"speed": 0.5}, "PLANNER", "NAVIGATION", "FIELD", 0, True)
    assert not gateway.execute_governed(stale).accepted


def test_safety_bounds_and_emergency_stop():
    policy = EmbodiedPolicyKernel()
    policy.set_bounds("drive", "speed", 0.0, 1.0)
    gateway = EmbodiedUniverseGateway(policy)
    gateway.register(surface())
    unsafe = ActionCommand("ROVER1", "drive", {"speed": 2.0}, "PLANNER", "NAVIGATION", "FIELD", 0, True)
    assert not gateway.execute_governed(unsafe).accepted
    gateway.emergency_stop("ROVER1", "FIELD")
    stopped = ActionCommand("ROVER1", "drive", {"speed": 0.2}, "PLANNER", "NAVIGATION", "FIELD", 1, True)
    assert not gateway.execute_governed(stopped).accepted


def test_edge_node_queues_offline_and_reconverges():
    gateway = EmbodiedUniverseGateway()
    gateway.register(surface())
    node = EdgeCognitionNode("EDGE1", "CA", online=False)
    node.observe(SensorObservation("ROVER1", "temperature", 20, "C", 1, "h1"))
    assert node.synchronize(gateway) == 0
    node.online = True
    assert node.synchronize(gateway) == 1
    assert not node.queued_observations
