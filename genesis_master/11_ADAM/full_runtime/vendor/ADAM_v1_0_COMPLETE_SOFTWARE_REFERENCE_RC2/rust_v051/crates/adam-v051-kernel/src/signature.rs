use crate::canonical::sha256;
use crate::error::{KernelError, Result};
use ed25519_dalek::{Signature, Signer, SigningKey, Verifier, VerifyingKey};
use rand_core::OsRng;
use serde::{Deserialize, Serialize};
use std::fs::{File, OpenOptions};
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use zeroize::Zeroize;

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub struct SignatureEnvelope {
    pub algorithm: String,
    pub key_id: String,
    pub public_key_hex: String,
    pub payload_sha256: String,
    pub signature_hex: String,
}

pub trait SignatureProvider {
    fn key_id(&self) -> String;
    fn public_key_hex(&self) -> String;
    fn sign(&self, payload: &[u8]) -> Result<SignatureEnvelope>;
}

pub fn verify_envelope(payload: &[u8], envelope: &SignatureEnvelope) -> Result<()> {
    if envelope.algorithm != "Ed25519" || envelope.payload_sha256 != sha256(payload) {
        return Err(KernelError::Signature);
    }
    let public_key = hex::decode(&envelope.public_key_hex)?;
    let public_key: [u8; 32] = public_key
        .try_into()
        .map_err(|_| KernelError::Signature)?;
    let verifying_key = VerifyingKey::from_bytes(&public_key).map_err(|_| KernelError::Signature)?;
    let expected_key_id = sha256(&[
        b"ADAM51:ED25519_KEY\0".as_slice(),
        verifying_key.as_bytes(),
    ]
    .concat());
    if expected_key_id != envelope.key_id {
        return Err(KernelError::Signature);
    }
    let signature_bytes = hex::decode(&envelope.signature_hex)?;
    let signature = Signature::from_slice(&signature_bytes).map_err(|_| KernelError::Signature)?;
    verifying_key
        .verify(payload, &signature)
        .map_err(|_| KernelError::Signature)
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

pub struct FileEd25519Signer {
    path: PathBuf,
    signing_key: SigningKey,
}

impl FileEd25519Signer {
    pub fn load_or_create(path: impl AsRef<Path>) -> Result<Self> {
        let path = path.as_ref().to_path_buf();
        if path.exists() {
            let metadata = std::fs::metadata(&path)?;
            if metadata.len() != 32 {
                return Err(KernelError::Invalid(
                    "development signing key must contain exactly 32 bytes".into(),
                ));
            }
            let mut bytes = [0_u8; 32];
            File::open(&path)?.read_exact(&mut bytes)?;
            let signing_key = SigningKey::from_bytes(&bytes);
            bytes.zeroize();
            return Ok(Self { path, signing_key });
        }
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent)?;
        }
        let signing_key = SigningKey::generate(&mut OsRng);
        let mut options = OpenOptions::new();
        options.write(true).create_new(true);
        #[cfg(unix)]
        {
            use std::os::unix::fs::OpenOptionsExt;
            options.mode(0o600);
        }
        let mut file = options.open(&path)?;
        let mut bytes = signing_key.to_bytes();
        file.write_all(&bytes)?;
        file.sync_all()?;
        bytes.zeroize();
        sync_parent(&path)?;
        Ok(Self { path, signing_key })
    }

    pub fn path(&self) -> &Path {
        &self.path
    }
}

impl SignatureProvider for FileEd25519Signer {
    fn key_id(&self) -> String {
        sha256(&[
            b"ADAM51:ED25519_KEY\0".as_slice(),
            self.signing_key.verifying_key().as_bytes(),
        ]
        .concat())
    }

    fn public_key_hex(&self) -> String {
        hex::encode(self.signing_key.verifying_key().as_bytes())
    }

    fn sign(&self, payload: &[u8]) -> Result<SignatureEnvelope> {
        let signature = self.signing_key.sign(payload);
        Ok(SignatureEnvelope {
            algorithm: "Ed25519".into(),
            key_id: self.key_id(),
            public_key_hex: self.public_key_hex(),
            payload_sha256: sha256(payload),
            signature_hex: hex::encode(signature.to_bytes()),
        })
    }
}
