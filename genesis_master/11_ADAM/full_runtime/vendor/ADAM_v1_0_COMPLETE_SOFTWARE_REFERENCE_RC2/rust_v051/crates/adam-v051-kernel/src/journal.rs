use crate::canonical::sha256;
use crate::error::{KernelError, Result};
use crate::model::{ReactionIntent, ReactionProof};
use crate::signature::{SignatureEnvelope, SignatureProvider, verify_envelope};
use fs2::FileExt;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::fs::{File, OpenOptions};
use std::io::{Read, Seek, SeekFrom, Write};
use std::path::{Path, PathBuf};

const MAGIC: &[u8; 8] = b"ADAMJ051";
const VERSION: u16 = 1;
const MAX_FRAME_BYTES: u64 = 64 * 1024 * 1024;
const CHECKSUM_DOMAIN: &[u8] = b"ADAM51:JOURNAL_FRAME\0";

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub struct CommitRecord {
    pub intent: ReactionIntent,
    pub proof: ReactionProof,
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub struct JournalFrame {
    pub format: String,
    pub version: u16,
    pub sequence: u64,
    pub previous_root: String,
    pub root: String,
    pub record: CommitRecord,
    pub signature: SignatureEnvelope,
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub struct ReplayResult {
    pub frames: Vec<JournalFrame>,
    pub sequence: u64,
    pub root: String,
    pub valid_bytes: u64,
    pub recovered_torn_tail: bool,
}

pub struct AuthorityJournal {
    path: PathBuf,
    genesis_root: String,
    expected_key_id: Option<String>,
}

fn frame_checksum(body: &[u8]) -> [u8; 32] {
    let mut hasher = Sha256::new();
    hasher.update(CHECKSUM_DOMAIN);
    hasher.update(body);
    hasher.finalize().into()
}

#[cfg(unix)]
fn sync_parent(path: &Path) -> Result<()> {
    if let Some(parent) = path.parent() {
        File::open(parent)?.sync_all()?;
    }
    Ok(())
}

#[cfg(not(unix))]
fn sync_parent(_path: &Path) -> Result<()> {
    Ok(())
}

fn read_exact_or_tail(file: &mut File, buffer: &mut [u8]) -> Result<bool> {
    let mut offset = 0;
    while offset < buffer.len() {
        let count = file.read(&mut buffer[offset..])?;
        if count == 0 {
            return Ok(false);
        }
        offset += count;
    }
    Ok(true)
}

impl AuthorityJournal {
    pub fn new(
        path: impl AsRef<Path>,
        genesis_root: impl Into<String>,
        expected_key_id: Option<String>,
    ) -> Self {
        Self {
            path: path.as_ref().to_path_buf(),
            genesis_root: genesis_root.into(),
            expected_key_id,
        }
    }

    pub fn path(&self) -> &Path {
        &self.path
    }

    pub fn replay(&self, recover_torn_tail: bool) -> Result<ReplayResult> {
        if !self.path.exists() {
            return Ok(ReplayResult {
                frames: Vec::new(),
                sequence: 0,
                root: self.genesis_root.clone(),
                valid_bytes: 0,
                recovered_torn_tail: false,
            });
        }
        let mut file = OpenOptions::new()
            .read(true)
            .write(recover_torn_tail)
            .open(&self.path)?;
        if recover_torn_tail {
            file.lock_exclusive()?;
        } else {
            file.lock_shared()?;
        }
        let file_length = file.metadata()?.len();
        let mut frames = Vec::new();
        let mut expected_sequence = 1_u64;
        let mut expected_root = self.genesis_root.clone();
        let mut valid_bytes = 0_u64;
        let mut recovered = false;

        loop {
            let frame_start = file.stream_position()?;
            if frame_start == file_length {
                break;
            }
            let mut magic = [0_u8; 8];
            if !read_exact_or_tail(&mut file, &mut magic)? {
                recovered = true;
                valid_bytes = frame_start;
                break;
            }
            if &magic != MAGIC {
                return Err(KernelError::Integrity {
                    sequence: expected_sequence,
                    reason: "invalid frame magic".into(),
                });
            }
            let mut version_bytes = [0_u8; 2];
            let mut length_bytes = [0_u8; 8];
            if !read_exact_or_tail(&mut file, &mut version_bytes)?
                || !read_exact_or_tail(&mut file, &mut length_bytes)?
            {
                recovered = true;
                valid_bytes = frame_start;
                break;
            }
            let version = u16::from_be_bytes(version_bytes);
            if version != VERSION {
                return Err(KernelError::UnsupportedVersion(version));
            }
            let body_length = u64::from_be_bytes(length_bytes);
            if body_length > MAX_FRAME_BYTES {
                return Err(KernelError::Integrity {
                    sequence: expected_sequence,
                    reason: format!("frame length {body_length} exceeds limit"),
                });
            }
            let mut body = vec![0_u8; usize::try_from(body_length).map_err(|_| {
                KernelError::Integrity {
                    sequence: expected_sequence,
                    reason: "frame length cannot fit memory".into(),
                }
            })?];
            let mut checksum = [0_u8; 32];
            if !read_exact_or_tail(&mut file, &mut body)?
                || !read_exact_or_tail(&mut file, &mut checksum)?
            {
                recovered = true;
                valid_bytes = frame_start;
                break;
            }
            if frame_checksum(&body) != checksum {
                return Err(KernelError::Integrity {
                    sequence: expected_sequence,
                    reason: "frame checksum mismatch".into(),
                });
            }
            let frame: JournalFrame = serde_json::from_slice(&body).map_err(|error| {
                KernelError::Integrity {
                    sequence: expected_sequence,
                    reason: format!("invalid frame JSON: {error}"),
                }
            })?;
            if frame.format != "ADAM-v0.51-authority-frame"
                || frame.version != VERSION
                || frame.sequence != expected_sequence
                || frame.previous_root != expected_root
                || frame.root != frame.record.proof.new_root
                || frame.previous_root != frame.record.proof.previous_root
                || frame.sequence != frame.record.proof.logical_time
            {
                return Err(KernelError::Integrity {
                    sequence: expected_sequence,
                    reason: "frame chain metadata mismatch".into(),
                });
            }
            let signed_bytes = serde_json::to_vec(&frame.record)?;
            verify_envelope(&signed_bytes, &frame.signature)?;
            if self.expected_key_id.as_ref().is_some_and(|key_id| key_id != &frame.signature.key_id) {
                return Err(KernelError::Signature);
            }
            frames.push(frame.clone());
            expected_root = frame.root;
            expected_sequence += 1;
            valid_bytes = file.stream_position()?;
        }
        if recovered {
            if !recover_torn_tail {
                return Err(KernelError::Integrity {
                    sequence: expected_sequence,
                    reason: "torn tail detected".into(),
                });
            }
            file.set_len(valid_bytes)?;
            file.sync_all()?;
            sync_parent(&self.path)?;
        }
        FileExt::unlock(&file)?;
        Ok(ReplayResult {
            frames,
            sequence: expected_sequence - 1,
            root: expected_root,
            valid_bytes,
            recovered_torn_tail: recovered,
        })
    }

    pub fn append(
        &self,
        record: CommitRecord,
        signer: &impl SignatureProvider,
    ) -> Result<JournalFrame> {
        if let Some(parent) = self.path.parent() {
            std::fs::create_dir_all(parent)?;
        }
        let mut file = OpenOptions::new()
            .create(true)
            .read(true)
            .append(true)
            .open(&self.path)?;
        file.lock_exclusive()?;
        let replay = self.replay_locked(&mut file)?;
        if record.proof.previous_root != replay.root {
            FileExt::unlock(&file)?;
            return Err(KernelError::StaleRoot {
                expected: record.proof.previous_root.clone(),
                actual: replay.root,
            });
        }
        if record.proof.logical_time != replay.sequence + 1 {
            FileExt::unlock(&file)?;
            return Err(KernelError::Invalid("journal sequence mismatch".into()));
        }
        if self
            .expected_key_id
            .as_ref()
            .is_some_and(|key_id| key_id != &signer.key_id())
        {
            FileExt::unlock(&file)?;
            return Err(KernelError::Signature);
        }
        let signed_bytes = serde_json::to_vec(&record)?;
        let signature = signer.sign(&signed_bytes)?;
        let frame = JournalFrame {
            format: "ADAM-v0.51-authority-frame".into(),
            version: VERSION,
            sequence: record.proof.logical_time,
            previous_root: record.proof.previous_root.clone(),
            root: record.proof.new_root.clone(),
            record,
            signature,
        };
        let body = serde_json::to_vec(&frame)?;
        if body.len() as u64 > MAX_FRAME_BYTES {
            FileExt::unlock(&file)?;
            return Err(KernelError::Invalid("journal frame too large".into()));
        }
        file.seek(SeekFrom::End(0))?;
        file.write_all(MAGIC)?;
        file.write_all(&VERSION.to_be_bytes())?;
        file.write_all(&(body.len() as u64).to_be_bytes())?;
        file.write_all(&body)?;
        file.write_all(&frame_checksum(&body))?;
        file.sync_all()?;
        FileExt::unlock(&file)?;
        sync_parent(&self.path)?;
        Ok(frame)
    }

    fn replay_locked(&self, file: &mut File) -> Result<ReplayResult> {
        file.seek(SeekFrom::Start(0))?;
        let mut frames = Vec::new();
        let mut expected_sequence = 1_u64;
        let mut expected_root = self.genesis_root.clone();
        loop {
            let frame_start = file.stream_position()?;
            let mut magic = [0_u8; 8];
            let first = file.read(&mut magic[..1])?;
            if first == 0 {
                break;
            }
            if !read_exact_or_tail(file, &mut magic[1..])? || &magic != MAGIC {
                return Err(KernelError::Integrity {
                    sequence: expected_sequence,
                    reason: format!("invalid or torn frame at byte {frame_start}"),
                });
            }
            let mut version_bytes = [0_u8; 2];
            let mut length_bytes = [0_u8; 8];
            if !read_exact_or_tail(file, &mut version_bytes)?
                || !read_exact_or_tail(file, &mut length_bytes)?
            {
                return Err(KernelError::Integrity {
                    sequence: expected_sequence,
                    reason: "torn frame header".into(),
                });
            }
            let version = u16::from_be_bytes(version_bytes);
            if version != VERSION {
                return Err(KernelError::UnsupportedVersion(version));
            }
            let length = u64::from_be_bytes(length_bytes);
            if length > MAX_FRAME_BYTES {
                return Err(KernelError::Integrity {
                    sequence: expected_sequence,
                    reason: "frame length exceeds limit".into(),
                });
            }
            let mut body = vec![0_u8; length as usize];
            let mut checksum = [0_u8; 32];
            if !read_exact_or_tail(file, &mut body)? || !read_exact_or_tail(file, &mut checksum)? {
                return Err(KernelError::Integrity {
                    sequence: expected_sequence,
                    reason: "torn frame body".into(),
                });
            }
            if frame_checksum(&body) != checksum {
                return Err(KernelError::Integrity {
                    sequence: expected_sequence,
                    reason: "frame checksum mismatch".into(),
                });
            }
            let frame: JournalFrame = serde_json::from_slice(&body).map_err(|error| {
                KernelError::Integrity {
                    sequence: expected_sequence,
                    reason: format!("invalid frame JSON: {error}"),
                }
            })?;
            if frame.format != "ADAM-v0.51-authority-frame"
                || frame.version != VERSION
                || frame.sequence != expected_sequence
                || frame.previous_root != expected_root
                || frame.root != frame.record.proof.new_root
                || frame.previous_root != frame.record.proof.previous_root
                || frame.sequence != frame.record.proof.logical_time
            {
                return Err(KernelError::Integrity {
                    sequence: expected_sequence,
                    reason: "journal chain metadata mismatch".into(),
                });
            }
            verify_envelope(&serde_json::to_vec(&frame.record)?, &frame.signature)?;
            if self.expected_key_id.as_ref().is_some_and(|key_id| key_id != &frame.signature.key_id) {
                return Err(KernelError::Signature);
            }
            expected_root = frame.root.clone();
            expected_sequence += 1;
            frames.push(frame);
        }
        Ok(ReplayResult {
            frames,
            sequence: expected_sequence - 1,
            root: expected_root,
            valid_bytes: file.stream_position()?,
            recovered_torn_tail: false,
        })
    }

    pub fn digest(&self) -> Result<String> {
        if !self.path.exists() {
            return Ok(sha256(&[]));
        }
        let mut bytes = Vec::new();
        File::open(&self.path)?.read_to_end(&mut bytes)?;
        Ok(sha256(&bytes))
    }
}
