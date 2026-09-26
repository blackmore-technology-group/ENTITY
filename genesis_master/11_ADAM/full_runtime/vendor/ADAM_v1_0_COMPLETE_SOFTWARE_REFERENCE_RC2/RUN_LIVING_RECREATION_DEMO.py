from pathlib import Path
import json
from adam_v42.recreation import ApplicationRecipe, LivingRecreationCenter, SpawnDemand

root = Path("artifacts/demo_recreation")
center = LivingRecreationCenter(root)
artifact = center.ingest(
    json.dumps({"device_id":"DEMO-1","telemetry":{"temperature":21.5}}).encode(),
    name="telemetry.json", media_type="application/json",
)
center.register_application(ApplicationRecipe(
    "demo_iot", ("iot",), "application/x-adam-iot-telemetry+json", "iot_envelope"
))
payload, receipt = center.spawn(SpawnDemand(
    artifact.artifact_id, application_id="demo_iot", target_format="auto"
))
print(payload.decode())
print(json.dumps(receipt.__dict__, indent=2))
print(json.dumps(center.verify(), indent=2))
