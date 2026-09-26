"""ADAM v0.41 governed artificial-universe kernel development prototype."""

from .universe import AtomicUniverse, ConflictError, IntegrityError, AuthorityError
from .brain import AtomicBrain
from .exact import ExactCodec
from .constructors import Constructor
from .schema import StateConstraint, TypeRegistry, TypeSpec, ValenceRule
from .reactions import (
    Condition,
    Effect,
    ReactionDefinition,
    ReactionEngine,
    ReactionError,
    ReactionIntent,
    ReactionReceipt,
)
from .kernel import UniverseKernel

__all__ = [
    "AtomicUniverse",
    "AtomicBrain",
    "ExactCodec",
    "Constructor",
    "ConflictError",
    "IntegrityError",
    "AuthorityError",
    "StateConstraint",
    "TypeRegistry",
    "TypeSpec",
    "ValenceRule",
    "Condition",
    "Effect",
    "ReactionDefinition",
    "ReactionEngine",
    "ReactionError",
    "ReactionIntent",
    "ReactionReceipt",
    "UniverseCognition",
    "UniverseKernel",
    "TrainingReport",
]

__version__ = "0.41.0.dev1"


def __getattr__(name):
    if name in {"UniverseCognition", "TrainingReport"}:
        from .cognition import UniverseCognition, TrainingReport
        return {"UniverseCognition": UniverseCognition, "TrainingReport": TrainingReport}[name]
    raise AttributeError(name)
