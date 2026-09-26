from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from adam_v44 import AtomicPhysicsKernel
from adam_v45 import NeuralSymbolicCognitionFabric
from adam_v46 import UniversalApplicationNervousSystem
from adam_v47 import IncrementalDependencyEngine, ShadowUniverseLab, TemporalDynamicsOrgan
from adam_v48 import EmbodiedUniverseGateway
from adam_v49 import AdaptiveAtomicEconomy, ChemistryRegistry
from .sovereignty import InferenceClosureAuthorizer, SovereignAtomStore, WitnessQuorum


@dataclass
class SovereignArtificialUniverse:
    physics: AtomicPhysicsKernel
    cognition: NeuralSymbolicCognitionFabric
    applications: UniversalApplicationNervousSystem
    dynamics: TemporalDynamicsOrgan
    shadow_lab: ShadowUniverseLab
    incremental: IncrementalDependencyEngine
    embodiment: EmbodiedUniverseGateway
    chemistry: ChemistryRegistry
    economy: AdaptiveAtomicEconomy
    secure_store: SovereignAtomStore
    closure_auth: InferenceClosureAuthorizer
    witnesses: WitnessQuorum

    @classmethod
    def create(cls, witnesses: WitnessQuorum) -> "SovereignArtificialUniverse":
        physics = AtomicPhysicsKernel()
        dynamics = TemporalDynamicsOrgan()
        return cls(
            physics=physics,
            cognition=NeuralSymbolicCognitionFabric(),
            applications=UniversalApplicationNervousSystem(physics),
            dynamics=dynamics,
            shadow_lab=ShadowUniverseLab(physics, dynamics),
            incremental=IncrementalDependencyEngine(),
            embodiment=EmbodiedUniverseGateway(),
            chemistry=ChemistryRegistry(),
            economy=AdaptiveAtomicEconomy(),
            secure_store=SovereignAtomStore(),
            closure_auth=InferenceClosureAuthorizer(),
            witnesses=witnesses,
        )

    def certify_current_root(self):
        return self.witnesses.certify(self.physics.root)

    def health(self) -> dict[str, Any]:
        return {
            "physics_root": self.physics.root,
            "logical_time": self.physics.logical_time,
            "models": {
                "masked_bond": self.cognition.masked_bond.model_id,
                "masked_atom": self.cognition.masked_atom.model_id,
                "dynamics": self.dynamics.training_root,
            },
            "applications": self.applications.health(),
            "devices": len(self.embodiment.surfaces),
            "chemistry_active": self.chemistry.active_id,
            "secure_atoms": len(self.secure_store.atoms),
            "witnesses": len(self.witnesses.witnesses),
        }
