use crate::checkpoint::{Checkpoint, CheckpointStore};
use crate::error::{KernelError, Result};
use crate::journal::{AuthorityJournal, CommitRecord};
use crate::model::{ReactionIntent, ReactionProof};
use crate::physics::{AtomicPhysicsKernel, build_equipment_physics};
use crate::signature::{FileEd25519Signer, SignatureProvider};
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub struct AuthorityHealth {
    pub name: String,
    pub version: String,
    pub sequence: u64,
    pub root: String,
    pub genesis_root: String,
    pub journal_sha256: String,
    pub key_id: String,
    pub checkpoint_sequence: Option<u64>,
}

pub struct PersistentAuthority {
    data_dir: PathBuf,
    genesis_root: String,
    kernel: AtomicPhysicsKernel,
    journal: AuthorityJournal,
    checkpoint_store: CheckpointStore,
    signer: FileEd25519Signer,
    checkpoint_sequence: Option<u64>,
}

impl PersistentAuthority {
    pub fn open(data_dir: impl AsRef<Path>) -> Result<Self> {
        let data_dir = data_dir.as_ref().to_path_buf();
        std::fs::create_dir_all(&data_dir)?;
        let genesis = build_equipment_physics()?;
        let genesis_root = genesis.root()?;
        let signer = FileEd25519Signer::load_or_create(data_dir.join("authority.ed25519"))?;
        let journal = AuthorityJournal::new(
            data_dir.join("authority.journal"),
            genesis_root.clone(),
            Some(signer.key_id()),
        );
        let checkpoint_store = CheckpointStore::new(data_dir.join("checkpoints"));
        let replay = journal.replay(true)?;

        let signer_key_id = signer.key_id();
        let latest_checkpoint = checkpoint_store.load_latest(Some(&signer_key_id))?;
        if latest_checkpoint
            .as_ref()
            .is_some_and(|checkpoint| checkpoint.sequence > replay.sequence)
        {
            return Err(KernelError::Integrity {
                sequence: latest_checkpoint.as_ref().map_or(0, |value| value.sequence),
                reason: "checkpoint is ahead of journal".into(),
            });
        }
        let checkpoint_sequence = latest_checkpoint.as_ref().map(|checkpoint| checkpoint.sequence);
        let mut kernel = genesis;
        if let Some(checkpoint) = latest_checkpoint.as_ref().filter(|value| value.sequence == 0) {
            if checkpoint.root != genesis_root || checkpoint.state != kernel.state {
                return Err(KernelError::Integrity {
                    sequence: 0,
                    reason: "checkpoint genesis state mismatch".into(),
                });
            }
        }
        for frame in &replay.frames {
            let proof = kernel.commit(&frame.record.intent)?;
            if proof != frame.record.proof {
                return Err(KernelError::Integrity {
                    sequence: frame.sequence,
                    reason: "reaction replay proof divergence".into(),
                });
            }
            if let Some(checkpoint) = latest_checkpoint
                .as_ref()
                .filter(|checkpoint| checkpoint.sequence == frame.sequence)
            {
                if checkpoint.root != kernel.root()? || checkpoint.state != kernel.state {
                    return Err(KernelError::Integrity {
                        sequence: checkpoint.sequence,
                        reason: "checkpoint diverges from genesis replay".into(),
                    });
                }
            }
        }
        let root = kernel.root()?;
        if root != replay.root {
            return Err(KernelError::Integrity {
                sequence: replay.sequence,
                reason: format!("replayed root {root} differs from journal root {}", replay.root),
            });
        }
        Ok(Self {
            data_dir,
            genesis_root,
            kernel,
            journal,
            checkpoint_store,
            signer,
            checkpoint_sequence,
        })
    }

    pub fn data_dir(&self) -> &Path {
        &self.data_dir
    }

    pub fn kernel(&self) -> &AtomicPhysicsKernel {
        &self.kernel
    }

    pub fn health(&self) -> Result<AuthorityHealth> {
        Ok(AuthorityHealth {
            name: "ADAM v0.51 Compiled Authority and Information-Physics Kernel".into(),
            version: "0.51.0-dev1".into(),
            sequence: self.kernel.state.logical_time,
            root: self.kernel.root()?,
            genesis_root: self.genesis_root.clone(),
            journal_sha256: self.journal.digest()?,
            key_id: self.signer.key_id(),
            checkpoint_sequence: self.checkpoint_sequence,
        })
    }

    pub fn simulate(&self, intent: &ReactionIntent) -> Result<ReactionProof> {
        Ok(self.kernel.simulate(intent)?.proof)
    }

    pub fn commit(&mut self, intent: &ReactionIntent) -> Result<ReactionProof> {
        let mut candidate = self.kernel.branch();
        let proof = candidate.commit(intent)?;
        let record = CommitRecord {
            intent: intent.clone(),
            proof: proof.clone(),
        };
        let frame = self.journal.append(record, &self.signer)?;
        if frame.root != proof.new_root || frame.sequence != proof.logical_time {
            return Err(KernelError::Integrity {
                sequence: proof.logical_time,
                reason: "durable frame differs from candidate proof".into(),
            });
        }
        self.kernel = candidate;
        Ok(proof)
    }

    pub fn checkpoint(&mut self) -> Result<Checkpoint> {
        let replay = self.journal.replay(false)?;
        let checkpoint = Checkpoint {
            format: "ADAM-v0.51-checkpoint".into(),
            version: 1,
            sequence: self.kernel.state.logical_time,
            root: self.kernel.root()?,
            journal_bytes: replay.valid_bytes,
            state: self.kernel.state.clone(),
        };
        self.checkpoint_store.save(checkpoint.clone(), &self.signer)?;
        self.checkpoint_sequence = Some(checkpoint.sequence);
        Ok(checkpoint)
    }

    pub fn verify(&self) -> Result<AuthorityHealth> {
        let reopened = Self::open(&self.data_dir)?;
        let current = self.health()?;
        let verified = reopened.health()?;
        if current.sequence != verified.sequence || current.root != verified.root {
            return Err(KernelError::Integrity {
                sequence: current.sequence,
                reason: "restart verification mismatch".into(),
            });
        }
        Ok(verified)
    }
}
