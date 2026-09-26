from __future__ import annotations

import json
import tempfile
from pathlib import Path

from adam_v1 import ArtificialLivingUniverseV1Candidate
from adam_v54 import DeviceCapabilityContract, ParameterRule


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="adam-v1-demo-") as directory:
        with ArtificialLivingUniverseV1Candidate.create(directory) as runtime:
            contract = DeviceCapabilityContract(
                device_id="bounded-pump-1",
                device_class="SIMULATED_LOW_ENERGY_PUMP",
                jurisdiction="CA-BC",
                sensors=("pressure", "flow"),
                actuators=("pump",),
                commands={"SET_OUTPUT": (ParameterRule("percent", 0.0, 25.0),)},
                safe_state={"output_percent": 0.0},
                command_ttl_seconds=5,
                human_override_required=True,
                emergency_stop_required=True,
                maximum_command_rate_hz=1.0,
            )
            runtime.register_device(contract)
            training = runtime.train_bounded_sensor_organ()
            status = runtime.local_status()
            print(json.dumps({"training": training, "status": status}, indent=2, default=str))


if __name__ == "__main__":
    main()
