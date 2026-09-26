use crate::canonical::sha256;
use crate::error::{KernelError, Result};
use crate::model::KernelState;
use crate::physics::AtomicPhysicsKernel;
use crate::signature::{SignatureEnvelope, SignatureProvider, verify_envelope};
use serde::{Deserialize, Serialize};
use std::fs::{File, OpenOptions};
use std::io::{Read, Write};
use std::path::{Path, PathBuf};

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
pub struct Checkpoint {
    pub format: String,
    pub version: u16,
    pub sequence: u64,
    pub root: String,
    pub journal_bytes: u64,
    pub state: KernelState,
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
struct CheckpointEnvelope {
    checkpoint: Checkpoint,
    signature: SignatureEnvelope,
    checksum: String,
}

pub struct CheckpointStore {
    directory: PathBuf,
}

#[cfg(unix)]
fn sync_directory(path: &Path) -> Result<()> {
    File::open(path)?.sync_all()?;
    Ok(())
}

#[cfg(not(unix))]
fn sync_directory(_path: &Path) -> Result<()> {
    Ok(())
}

impl CheckpointStore {
    pub fn new(directory: impl AsRef<Path>) -> Self {
        Self { directory: directory.as_ref().to_path_buf() }
    }

    pub fn directory(&self) -> &Path {
        &self.directory
    }

    fn filename(checkpoint: &Checkpoint) -> String {
        format!(
            "checkpoint-{:020}-{}.json",
            checkpoint.sequence, checkpoint.root
        )
    }

    pub fn save(&self, checkpoint: Checkpoint, signer: &impl SignatureProvider) -> Result<PathBuf> {
        if checkpoint.format != "ADAM-v0.51-checkpoint" || checkpoint.version != 1 {
            return Err(KernelError::Invalid("invalid checkpoint format".into()));
        }
        if checkpoint.sequence != checkpoint.state.logical_time {
            return Err(KernelError::Invalid("checkpoint sequence/state mismatch".into()));
        }
        let calculated_root = AtomicPhysicsKernel::from_state(checkpoint.state.clone())?.root()?;
        if calculated_root != checkpoint.root {
            return Err(KernelError::Invalid("checkpoint root/state mismatch".into()));
        }
        std::fs::create_dir_all(&self.directory)?;
        let checkpoint_bytes = serde_json::to_vec(&checkpoint)?;
        let signature = signer.sign(&checkpoint_bytes)?;
        let envelope_without_checksum = serde_json::to_vec(&(checkpoint.clone(), signature.clone()))?;
        let envelope = CheckpointEnvelope {
            checkpoint: checkpoint.clone(),
            signature,
            checksum: sha256(&[
                b"ADAM51:CHECKPOINT_ENVELOPE\0".as_slice(),
                envelope_without_checksum.as_slice(),
            ]
            .concat()),
        };
        let bytes = serde_json::to_vec(&envelope)?;
        let final_path = self.directory.join(Self::filename(&checkpoint));
        if final_path.exists() {
            let existing = Self::load_path(&final_path, Some(&signer.key_id()))?;
            if existing == checkpoint {
                return Ok(final_path);
            }
            return Err(KernelError::Integrity {
                sequence: checkpoint.sequence,
                reason: "checkpoint filename collision".into(),
            });
        }
        let temporary = self.directory.join(format!(
            ".checkpoint-{:020}-{}-{}.tmp",
            checkpoint.sequence,
            checkpoint.root,
            std::process::id()
        ));
        let _ = std::fs::remove_file(&temporary);
        let mut options = OpenOptions::new();
        options.write(true).create_new(true);
        #[cfg(unix)]
        {
            use std::os::unix::fs::OpenOptionsExt;
            options.mode(0o600);
        }
        let write_result = (|| -> Result<()> {
            let mut file = options.open(&temporary)?;
            file.write_all(&bytes)?;
            file.sync_all()?;
            std::fs::rename(&temporary, &final_path)?;
            sync_directory(&self.directory)?;
            Ok(())
        })();
        if write_result.is_err() {
            let _ = std::fs::remove_file(&temporary);
        }
        write_result?;
        Ok(final_path)
    }

    fn load_path(path: &Path, expected_key_id: Option<&str>) -> Result<Checkpoint> {
        let mut bytes = Vec::new();
        File::open(path)?.read_to_end(&mut bytes)?;
        let envelope: CheckpointEnvelope = serde_json::from_slice(&bytes)?;
        if envelope.checkpoint.format != "ADAM-v0.51-checkpoint"
            || envelope.checkpoint.version != 1
        {
            return Err(KernelError::Invalid("invalid checkpoint format".into()));
        }
        let checkpoint_bytes = serde_json::to_vec(&envelope.checkpoint)?;
        verify_envelope(&checkpoint_bytes, &envelope.signature)?;
        if expected_key_id.is_some_and(|key_id| key_id != envelope.signature.key_id.as_str()) {
            return Err(KernelError::Signature);
        }
        let envelope_without_checksum = serde_json::to_vec(&(
            envelope.checkpoint.clone(),
            envelope.signature.clone(),
        ))?;
        let expected = sha256(&[
            b"ADAM51:CHECKPOINT_ENVELOPE\0".as_slice(),
            envelope_without_checksum.as_slice(),
        ]
        .concat());
        if envelope.checksum != expected {
            return Err(KernelError::Integrity {
                sequence: envelope.checkpoint.sequence,
                reason: "checkpoint checksum mismatch".into(),
            });
        }
        if envelope.checkpoint.sequence != envelope.checkpoint.state.logical_time {
            return Err(KernelError::Integrity {
                sequence: envelope.checkpoint.sequence,
                reason: "checkpoint sequence/state mismatch".into(),
            });
        }
        Ok(envelope.checkpoint)
    }

    pub fn load_latest(&self, expected_key_id: Option<&str>) -> Result<Option<Checkpoint>> {
        if !self.directory.exists() {
            return Ok(None);
        }
        let mut candidates = std::fs::read_dir(&self.directory)?
            .filter_map(std::result::Result::ok)
            .map(|entry| entry.path())
            .filter(|path| {
                path.file_name()
                    .and_then(|value| value.to_str())
                    .is_some_and(|name| name.starts_with("checkpoint-") && name.ends_with(".json"))
            })
            .collect::<Vec<_>>();
        candidates.sort();
        let Some(path) = candidates.last() else {
            return Ok(None);
        };
        Self::load_path(path, expected_key_id).map(Some)
    }
}
