from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from adam_v41.canonical import digest, sha256_bytes
from adam_v50 import SovereignArtificialUniverse, WitnessNode, WitnessQuorum
from adam_v52 import (
    AuthorityKeyHierarchy,
    EncryptedSoftwareCustodyProvider,
    load_or_create_ed25519_private_key,
    load_or_create_master_key,
)
from adam_v53 import NetworkAuthorityCluster
from adam_v54 import DeviceCapabilityContract, DevicePilot
from adam_v55 import DriftMonitor, NearestCentroidOrgan, ShadowDeployment, synthetic_sensor_dataset
from adam_v56 import CandidateFreezer, ProductionCandidateManifest, QualificationRecorder, SLOThresholds
from adam_v57 import RealTimeQualificationController
from adam_v58 import AssuranceCase, AssessorRegistry, ExternalGate


@dataclass
class ArtificialLivingUniverseV1Candidate:
    base_dir: Path
    universe: SovereignArtificialUniverse
    custody: EncryptedSoftwareCustodyProvider
    key_hierarchy: AuthorityKeyHierarchy
    network: NetworkAuthorityCluster | None
    device_pilots: dict[str, DevicePilot]
    models: dict[str, NearestCentroidOrgan]
    shadow_deployments: dict[str, ShadowDeployment]
    candidate_manifest: ProductionCandidateManifest | None
    recorder: QualificationRecorder | None
    wall_clock: RealTimeQualificationController | None
    assurance: AssuranceCase
    release_signer_id: str
    release_public_key: bytes
    _release_private_key: Any
    _qualification_private_key: Any

    VERSION = "1.0.0-rc2"
    RELEASE_SIGNER_ID = "ADAM_LOCAL_RELEASE_SIGNER_RC2"

    @classmethod
    def create(
        cls,
        base_dir: str | os.PathLike[str],
        *,
        enable_network_reference: bool = False,
        master_key: bytes | None = None,
        assessor_registry: AssessorRegistry | None = None,
    ) -> "ArtificialLivingUniverseV1Candidate":
        directory = Path(base_dir)
        directory.mkdir(parents=True, exist_ok=True)
        secrets_dir = directory / "secrets"
        resolved_master = master_key or load_or_create_master_key(secrets_dir / "software-custody-master.key")
        release_private = load_or_create_ed25519_private_key(secrets_dir / "release-signing.key")
        qualification_private = load_or_create_ed25519_private_key(secrets_dir / "qualification-controller.key")

        witnesses = WitnessQuorum(
            [WitnessNode("witness-a"), WitnessNode("witness-b"), WitnessNode("witness-c")], threshold=2
        )
        universe = SovereignArtificialUniverse.create(witnesses)
        custody = EncryptedSoftwareCustodyProvider(
            directory / "custody",
            resolved_master,
            instance_id="adam-v1-rc2-local-software-custody",
        )
        hierarchy = AuthorityKeyHierarchy(custody)
        hierarchy.provision(jurisdiction="CA-BC")
        network = NetworkAuthorityCluster(directory / "network") if enable_network_reference else None
        release_public = release_private.public_key().public_bytes_raw()
        build_hash = digest(
            "ADAM1:LOCAL_BUILD_RC2",
            {
                "version": cls.VERSION,
                "release_signer": cls.RELEASE_SIGNER_ID,
                "release_public_key_sha256": sha256_bytes(release_public),
            },
        )
        assurance = AssuranceCase(
            operator_id="ADAM_DEVELOPMENT_OPERATOR",
            production_build_hash=build_hash,
            assessor_registry=assessor_registry or AssessorRegistry(),
        )
        for gate_id, description in (
            ("RUST_COMPILED_QUALIFIED", "compiled, fuzzed, Miri and cross-platform Rust authority kernel"),
            ("HSM_HARDWARE_CUSTODY", "non-exportable hardware custody and ceremonies"),
            ("PHYSICAL_MULTI_HOST", "physically independent host deployment and WAN faults"),
            ("CERTIFIED_DEVICE_PILOT", "physical device and functional-safety certification"),
            ("REAL_WORLD_TRAINING", "large licensed multimodal and field sensor training"),
            ("THIRTY_DAY_WALL_CLOCK", "thirty actual elapsed days under frozen candidate"),
            ("INDEPENDENT_SECURITY_AUDIT", "trusted independent security, safety and operational review"),
        ):
            assurance.record_gate(ExternalGate(gate_id, description, None, False, False))
        return cls(
            base_dir=directory,
            universe=universe,
            custody=custody,
            key_hierarchy=hierarchy,
            network=network,
            device_pilots={},
            models={},
            shadow_deployments={},
            candidate_manifest=None,
            recorder=None,
            wall_clock=None,
            assurance=assurance,
            release_signer_id=cls.RELEASE_SIGNER_ID,
            release_public_key=release_public,
            _release_private_key=release_private,
            _qualification_private_key=qualification_private,
        )

    def register_device(self, contract: DeviceCapabilityContract) -> DevicePilot:
        if contract.device_id in self.device_pilots:
            raise ValueError("device already registered")
        pilot = DevicePilot(contract)
        self.device_pilots[contract.device_id] = pilot
        return pilot

    def train_bounded_sensor_organ(self, name: str = "sensor-anomaly") -> Mapping[str, Any]:
        dataset = synthetic_sensor_dataset()
        train_rows, _, _ = dataset.split_by_group(validation_groups=("site-e",), test_groups=("site-f",))
        organ = NearestCentroidOrgan(name)
        receipt = organ.train(
            dataset,
            validation_groups=("site-e",),
            test_groups=("site-f",),
            authorized_capability="SHADOW_SENSOR_CLASSIFICATION",
            approved_by="independent-model-promotion-role",
        )
        deployment = ShadowDeployment(organ, DriftMonitor.from_examples(train_rows))
        self.models[name] = organ
        self.shadow_deployments[name] = deployment
        return {
            "model_id": receipt.model_id,
            "dataset_root": receipt.dataset_root,
            "validation_accuracy": receipt.validation_accuracy,
            "test_accuracy": receipt.test_accuracy,
            "calibration_error": receipt.calibration_error,
            "authority_commit_enabled": False,
        }

    def freeze_candidate(
        self,
        *,
        source_manifest: bytes,
        dependency_lock: bytes,
        rust_binary_hashes: Mapping[str, str],
        deployment: Mapping[str, Any],
        external_gate_evidence: Mapping[str, str] | None = None,
        qualification_duration_seconds: int = 30 * 24 * 60 * 60,
        trusted_witnesses: Mapping[str, bytes] | None = None,
    ) -> ProductionCandidateManifest:
        thresholds = SLOThresholds(
            availability_min=0.999,
            commit_latency_p95_ms_max=250.0,
            reconstruction_latency_p95_ms_max=1000.0,
            failover_seconds_max=30.0,
            root_convergence_seconds_max=60.0,
            exact_recreation_success_min=1.0,
        )
        freezer = CandidateFreezer(
            self.base_dir / "candidate",
            private_key=self._release_private_key,
            signer_id=self.release_signer_id,
        )
        manifest = freezer.freeze(
            version=self.VERSION,
            source_manifest=source_manifest,
            dependency_lock=dependency_lock,
            rust_binary_hashes=rust_binary_hashes,
            deployment=deployment,
            thresholds=thresholds,
            operator="ADAM_DEVELOPMENT_OPERATOR",
            qualification_duration_seconds=qualification_duration_seconds,
            external_gate_evidence=external_gate_evidence or {},
        )
        self.candidate_manifest = manifest
        self.recorder = QualificationRecorder(manifest, self.base_dir / "qualification")
        self.wall_clock = RealTimeQualificationController(
            self.base_dir / "qualification" / "wall-clock.json",
            candidate_id=manifest.candidate_id,
            deployment_digest=manifest.deployment_digest,
            required_seconds=qualification_duration_seconds,
            minimum_witnesses=30,
            private_key=self._qualification_private_key,
            controller_key_id="ADAM_RC2_QUALIFICATION_CONTROLLER",
            trusted_witnesses=trusted_witnesses or {},
        )
        return manifest

    def verify_frozen_candidate(self, path: str | os.PathLike[str]) -> bool:
        return CandidateFreezer.verify(path, {self.release_signer_id: self.release_public_key})

    def local_status(self) -> Mapping[str, Any]:
        return {
            "classification": "ADAM v1.0 Complete Software Reference / External Certification Required",
            "version": self.VERSION,
            "universe": self.universe.health(),
            "custody": self.custody.health(),
            "release_signer": {
                "signer_id": self.release_signer_id,
                "public_key_sha256": sha256_bytes(self.release_public_key),
                "software_reference": True,
            },
            "network_reference": self.network.health() if self.network else None,
            "devices": {
                device_id: {"stage": pilot.stage.value, "root": pilot.twin.root}
                for device_id, pilot in self.device_pilots.items()
            },
            "models": {name: model.model_id for name, model in self.models.items()},
            "candidate": self.candidate_manifest.candidate_id if self.candidate_manifest else None,
            "wall_clock": self.wall_clock.certification_status() if self.wall_clock else None,
            "promotion": self.assurance.promotion_status(),
        }

    def close(self) -> None:
        if self.network is not None:
            self.network.close()
        self.custody.close()

    def __enter__(self) -> "ArtificialLivingUniverseV1Candidate":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()
