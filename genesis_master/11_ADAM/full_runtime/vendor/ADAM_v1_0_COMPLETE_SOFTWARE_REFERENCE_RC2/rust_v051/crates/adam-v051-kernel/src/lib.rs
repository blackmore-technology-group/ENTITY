#![forbid(unsafe_code)]

pub mod canonical;
pub mod checkpoint;
pub mod distributed;
pub mod error;
pub mod journal;
pub mod model;
pub mod physics;
pub mod protocol;
pub mod runtime;
pub mod signature;

pub use canonical::{CanonicalValue, digest, pack, unpack};
pub use checkpoint::{Checkpoint, CheckpointStore};
pub use distributed::*;
pub use error::{KernelError, Result};
pub use journal::{AuthorityJournal, CommitRecord, JournalFrame, ReplayResult};
pub use model::*;
pub use physics::{AtomicPhysicsKernel, Simulation, assignment_intent, build_equipment_physics, release_intent};
pub use protocol::*;
pub use runtime::{AuthorityHealth, PersistentAuthority};
pub use signature::{FileEd25519Signer, SignatureEnvelope, SignatureProvider, verify_envelope};
