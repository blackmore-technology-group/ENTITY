"""ADAM v0.42 Distributed Living Recreation Universe bounded research prototype."""

from .chemistry import ChemistryCandidate, ChemistryLab, ChemistryPromotionReceipt
from .distributed import DistributedUniverseCluster, QuorumCertificate, SovereignErasureStore
from .erasure import Fragment, ReedSolomonCodec
from .evidence import AlignedClaim, EvidenceAlignmentEngine
from .formal import BoundedProofChecker, Law, ProofCertificate
from .isolation import IsolatedKernelClient
from .key_management import CryptoErasureStore, EncryptedSigningKeyStore
from .operations_one import DeterministicO1Cognition, OperationsOneAuthority
from .perception import MultimodalPerception, PerceptionResult
from .query import DistributedAQL, QueryPlan
from .reactions_ext import AdvancedCondition, AdvancedPolicy, AdvancedReactionEngine, ComputedArgument
from .security import ClosureAuthorization, PurposeGrant, SecurityLabel
from .soak import SoakReport, run_logical_soak
from .time_model import HLCTimestamp, HybridLogicalClock, UncertainInstant, ValidInterval

__version__ = "0.42.0.dev1"

from .embodiment import ActuatorCapability, ActionDecision, CapabilitySurface, EmbodimentGateway
from .recreation import (
    ApplicationRecipe, LivingRecreationCenter, RecreationArtifact, RecreationPolicyModel,
    SpawnDemand, SpawnReceipt,
)

from .novelty import NoveltyPlan, NoveltyProtocol
