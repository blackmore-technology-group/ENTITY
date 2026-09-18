import hashlib
import importlib.util
import pathlib
import tempfile
import unittest


REPO = pathlib.Path(__file__).resolve().parents[1]
SIMPLE = REPO / "sdk" / "simple_sdk" / "canonical_simple_entity_sdk.py"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


simple_mod = load_module("entity_public_simple_sdk", SIMPLE)


class PublicContractTests(unittest.TestCase):
    def test_principal_bound_hash_only_flow(self):
        with tempfile.TemporaryDirectory() as tmp:
            sdk = simple_mod.SimpleEntitySDK(tmp)

            principal = sdk.create_entity(
                "Example Principal",
                entity_type="person",
                alias="example.principal.entity",
            )
            device = sdk.create_entity(
                "Example Device",
                entity_type="system",
                alias="example.device.entity",
            )
            app = sdk.create_application(
                "Example Application",
                "example.application.entity",
                controller_entity_id=principal["entity_id"],
            )

            binding = sdk.pair_device(
                principal_entity_id=principal["entity_id"],
                application_entity_id=app["application_entity_id"],
                device_entity_id=device["entity_id"],
                display_name="Example Application Installation",
                alias="example.application.installation.entity",
            )

            verified = sdk.verify_pairing(binding)
            self.assertTrue(verified["valid"])
            self.assertEqual(verified["principal_entity_id"], principal["entity_id"])

            digest = hashlib.sha256(b"synthetic public example").hexdigest()
            asset = sdk.register_asset(
                binding,
                content_sha256=digest,
                size_bytes=24,
                media_type="application/octet-stream",
                title="Synthetic public example",
                asset_kind="DATA",
                source_subject_ref=principal["entity_id"],
                metadata={"test": True},
            )
            self.assertFalse(asset["ownership_not_inferred"] is False)
            self.assertFalse(asset["economic_value_not_inferred"] is False)
            self.assertFalse(asset["raw_content_stored"])

            event = sdk.record_event(
                binding,
                event_type="data.example.mutation",
                payload_sha256=hashlib.sha256(b"synthetic event").hexdigest(),
                subject_ids=[principal["entity_id"]],
            )
            self.assertTrue(event["non_authoritative_application_event"])
            self.assertFalse(event["rights_state_mutated"])
            self.assertFalse(event["economic_state_mutated"])

            with self.assertRaises(PermissionError):
                sdk.record_event(
                    binding,
                    event_type="payment.recorded",
                    payload_sha256=hashlib.sha256(b"forbidden").hexdigest(),
                )

            export_dir = pathlib.Path(tmp) / "portable_export"
            sdk.export_entity(principal["entity_id"], export_dir)
            export_check = sdk.verify_export(export_dir)
            self.assertTrue(export_check["valid"])
            self.assertTrue(export_check["provider_independent"])

    def test_status_declares_non_ownership_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            status = simple_mod.SimpleEntitySDK(tmp).status()
            self.assertTrue(status["provider_neutral"])
            self.assertTrue(status["registration_not_ownership"])
            self.assertTrue(status["economic_mutation_not_exposed"])


if __name__ == "__main__":
    unittest.main()
