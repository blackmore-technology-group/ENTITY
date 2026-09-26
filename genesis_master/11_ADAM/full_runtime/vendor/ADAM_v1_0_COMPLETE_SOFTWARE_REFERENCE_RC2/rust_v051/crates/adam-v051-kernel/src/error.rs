use std::io;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum KernelError {
    #[error("I/O error: {0}")]
    Io(#[from] io::Error),
    #[error("JSON error: {0}")]
    Json(#[from] serde_json::Error),
    #[error("hex error: {0}")]
    Hex(#[from] hex::FromHexError),
    #[error("invalid canonical value: {0}")]
    Canonical(String),
    #[error("invalid model: {0}")]
    Invalid(String),
    #[error("integrity failure at sequence {sequence}: {reason}")]
    Integrity { sequence: u64, reason: String },
    #[error("stale universe root: expected {expected}, actual {actual}")]
    StaleRoot { expected: String, actual: String },
    #[error("signature verification failed")]
    Signature,
    #[error("unsupported format version {0}")]
    UnsupportedVersion(u16),
}

pub type Result<T> = std::result::Result<T, KernelError>;
