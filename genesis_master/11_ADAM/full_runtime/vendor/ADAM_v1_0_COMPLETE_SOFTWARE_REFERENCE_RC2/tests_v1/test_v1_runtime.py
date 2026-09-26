from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from adam_v1 import ArtificialLivingUniverseV1Candidate
from adam_v54 import DeviceCapabilityContract, ParameterRule


def test_v1_candidate_integrates_local_layers_and_reports_external_blockers(tmp_path):
    with ArtificialLivingUniverseV1Candidate.create(tmp_path) as runtime:
        runtime.register_device(DeviceCapabilityContract(
            device_id="device-1",
            device_class="SIMULATOR",
            jurisdiction="CA-BC",
            sensors=("sensor",),
            actuators=("actuator",),
            commands={"SET": (ParameterRule("value", 0, 1),)},
            safe_state={"value": 0},
            command_ttl_seconds=5,
            human_override_required=True,
            emergency_stop_required=True,
            maximum_command_rate_hz=1,
        ))
        trained = runtime.train_bounded_sensor_organ()
        assert trained["test_accuracy"] == 1.0
        status = runtime.local_status()
        assert status["classification"] == "ADAM v1.0 Complete Software Reference / External Certification Required"
        assert status["version"] == "1.0.0-rc2"
        assert status["promotion"]["promotable_to_v1"] is False
        assert status["custody"]["hardware_backed"] is False


def test_v1_persistent_runtime_reopens_same_custody_identity(tmp_path):
    with ArtificialLivingUniverseV1Candidate.create(tmp_path) as first:
        handle = first.key_hierarchy.require("CA-BC", "REACTION_SIGNING")
        public = first.custody.get_public_key(handle)
        signer_fingerprint = first.local_status()["release_signer"]["public_key_sha256"]
    with ArtificialLivingUniverseV1Candidate.create(tmp_path) as second:
        reopened = second.key_hierarchy.require("CA-BC", "REACTION_SIGNING")
        assert reopened == handle
        assert second.custody.get_public_key(reopened) == public
        assert second.local_status()["release_signer"]["public_key_sha256"] == signer_fingerprint
        receipt = second.custody.sign(reopened, b"restart", purpose="REACTION_SIGNING", context={})
        assert second.custody.verify_receipt(receipt, b"restart")


def test_v1_cli_persistent_status_runs_twice(tmp_path):
    env = dict(os.environ)
    project_root = str(Path(__file__).resolve().parents[1])
    env["PYTHONPATH"] = project_root + os.pathsep + env.get("PYTHONPATH", "")
    command = [sys.executable, "-m", "adam_v1.cli", "--state-dir", str(tmp_path / "state"), "--status"]
    outputs = []
    for _ in range(2):
        completed = subprocess.run(
            command,
            cwd=project_root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            timeout=30,
            text=True,
        )
        outputs.append(json.loads(completed.stdout))
    assert outputs[0]["version"] == outputs[1]["version"] == "1.0.0-rc2"
    assert outputs[0]["release_signer"] == outputs[1]["release_signer"]
