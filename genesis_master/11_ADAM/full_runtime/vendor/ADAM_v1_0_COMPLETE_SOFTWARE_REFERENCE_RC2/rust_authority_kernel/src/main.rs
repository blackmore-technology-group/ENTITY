use ed25519_dalek::{Signature, Signer, SigningKey, Verifier, VerifyingKey};
use rand_core::OsRng;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::fs::{File, OpenOptions};
use std::io::{self, BufRead, BufReader, Read, Write};
use std::path::{Path, PathBuf};
use thiserror::Error;
use zeroize::Zeroize;

const DOMAIN: &[u8] = b"ADAM43:RUST_AUTHORITY_FRAME\0";
const SIGN_DOMAIN: &[u8] = b"ADAM43:RUST_AUTHORITY_SIGNATURE\0";

#[derive(Debug, Error)]
enum KernelError {
    #[error("io: {0}")] Io(#[from] io::Error),
    #[error("json: {0}")] Json(#[from] serde_json::Error),
    #[error("invalid request: {0}")] Invalid(String),
    #[error("integrity failure at sequence {0}")] Integrity(u64),
}

#[derive(Debug, Deserialize)]
#[serde(tag = "command", rename_all = "snake_case")]
enum Request { Health, Append { payload_hex: String, expected_root: Option<String> }, Verify, Root, Stop }

#[derive(Debug, Serialize)]
struct Response<T: Serialize> { ok: bool, result: Option<T>, error: Option<String> }
#[derive(Debug, Serialize)]
struct Health { name: &'static str, version: &'static str, sequence: u64, root: String, key_id: String }
#[derive(Debug, Serialize)]
struct CommitReceipt { sequence: u64, previous_root: String, root: String, payload_sha256: String, signature_hex: String, key_id: String }
#[derive(Debug, Serialize, Deserialize)]
struct SignedEnvelope { payload_hex: String, signing_root: String, signature_hex: String, key_id: String }

struct AuthorityKernel { path: PathBuf, sequence: u64, root: [u8; 32], signing_key: SigningKey, verifying_key: VerifyingKey }

fn hash(parts: &[&[u8]]) -> [u8; 32] { let mut h = Sha256::new(); for part in parts { h.update(part); } h.finalize().into() }
fn key_id(key: &VerifyingKey) -> String { hex::encode(hash(&[b"ADAM43:RUST_KEY\0", key.as_bytes()])) }

fn load_or_create_key(path: &Path) -> Result<SigningKey, KernelError> {
    let key_path = PathBuf::from(format!("{}.ed25519", path.display()));
    if key_path.exists() {
        let mut bytes = [0u8; 32];
        File::open(&key_path)?.read_exact(&mut bytes)?;
        let key = SigningKey::from_bytes(&bytes);
        bytes.zeroize();
        return Ok(key);
    }
    let key = SigningKey::generate(&mut OsRng);
    let mut options = OpenOptions::new();
    options.write(true).create_new(true);
    #[cfg(unix)] {
        use std::os::unix::fs::OpenOptionsExt;
        options.mode(0o600);
    }
    let mut file = options.open(&key_path)?;
    let mut bytes = key.to_bytes();
    file.write_all(&bytes)?;
    file.sync_all()?;
    bytes.zeroize();
    Ok(key)
}

fn read_length_or_eof(file: &mut File) -> Result<Option<[u8; 4]>, KernelError> {
    let mut length = [0u8; 4];
    let first = file.read(&mut length[..1])?;
    if first == 0 { return Ok(None); }
    file.read_exact(&mut length[1..])?;
    Ok(Some(length))
}

impl AuthorityKernel {
    fn open(path: impl AsRef<Path>) -> Result<Self, KernelError> {
        let path = path.as_ref().to_path_buf();
        let signing_key = load_or_create_key(&path)?;
        let verifying_key = signing_key.verifying_key();
        let mut kernel = Self { path, sequence: 0, root: [0; 32], signing_key, verifying_key };
        if kernel.path.exists() { kernel.replay()?; }
        Ok(kernel)
    }

    fn replay(&mut self) -> Result<(), KernelError> {
        let mut file = File::open(&self.path)?;
        let mut expected_sequence = 1u64;
        let mut root = [0u8; 32];
        while let Some(length) = read_length_or_eof(&mut file)? {
            let payload_len = u32::from_be_bytes(length) as usize;
            let mut sequence_bytes = [0u8; 8]; file.read_exact(&mut sequence_bytes)?;
            let sequence = u64::from_be_bytes(sequence_bytes);
            let mut previous = [0u8; 32]; file.read_exact(&mut previous)?;
            let mut committed = [0u8; 32]; file.read_exact(&mut committed)?;
            let mut envelope_bytes = vec![0u8; payload_len]; file.read_exact(&mut envelope_bytes)?;
            if sequence != expected_sequence || previous != root { return Err(KernelError::Integrity(sequence)); }
            let envelope: SignedEnvelope = serde_json::from_slice(&envelope_bytes).map_err(|_| KernelError::Integrity(sequence))?;
            if envelope.key_id != key_id(&self.verifying_key) { return Err(KernelError::Integrity(sequence)); }
            let payload = hex::decode(&envelope.payload_hex).map_err(|_| KernelError::Integrity(sequence))?;
            let signing_root = hash(&[SIGN_DOMAIN, &sequence_bytes, &previous, &payload]);
            if envelope.signing_root != hex::encode(signing_root) { return Err(KernelError::Integrity(sequence)); }
            let signature_bytes = hex::decode(&envelope.signature_hex).map_err(|_| KernelError::Integrity(sequence))?;
            let signature = Signature::from_slice(&signature_bytes).map_err(|_| KernelError::Integrity(sequence))?;
            self.verifying_key.verify(&signing_root, &signature).map_err(|_| KernelError::Integrity(sequence))?;
            let computed = hash(&[DOMAIN, &sequence_bytes, &previous, &envelope_bytes]);
            if computed != committed { return Err(KernelError::Integrity(sequence)); }
            root = committed;
            expected_sequence += 1;
        }
        self.sequence = expected_sequence - 1;
        self.root = root;
        Ok(())
    }

    fn append(&mut self, payload: &[u8], expected_root: Option<&str>) -> Result<CommitReceipt, KernelError> {
        if let Some(expected) = expected_root {
            if expected != hex::encode(self.root) { return Err(KernelError::Invalid("stale root".into())); }
        }
        let sequence = self.sequence + 1;
        let sequence_bytes = sequence.to_be_bytes();
        let previous = self.root;
        let signing_root = hash(&[SIGN_DOMAIN, &sequence_bytes, &previous, payload]);
        let signature = self.signing_key.sign(&signing_root);
        let envelope = SignedEnvelope {
            payload_hex: hex::encode(payload), signing_root: hex::encode(signing_root),
            signature_hex: hex::encode(signature.to_bytes()), key_id: key_id(&self.verifying_key),
        };
        let envelope_bytes = serde_json::to_vec(&envelope)?;
        if envelope_bytes.len() > u32::MAX as usize { return Err(KernelError::Invalid("payload too large".into())); }
        let root = hash(&[DOMAIN, &sequence_bytes, &previous, &envelope_bytes]);
        let mut file = OpenOptions::new().create(true).append(true).open(&self.path)?;
        file.write_all(&(envelope_bytes.len() as u32).to_be_bytes())?;
        file.write_all(&sequence_bytes)?; file.write_all(&previous)?; file.write_all(&root)?; file.write_all(&envelope_bytes)?;
        file.sync_all()?;
        self.sequence = sequence; self.root = root;
        Ok(CommitReceipt { sequence, previous_root: hex::encode(previous), root: hex::encode(root),
            payload_sha256: hex::encode(hash(&[payload])), signature_hex: envelope.signature_hex, key_id: envelope.key_id })
    }

    fn health(&self) -> Health { Health { name: "ADAM isolated Rust authority kernel", version: "0.43.0-dev2-source-audited",
        sequence: self.sequence, root: hex::encode(self.root), key_id: key_id(&self.verifying_key) } }
}

impl Drop for AuthorityKernel { fn drop(&mut self) { let mut scratch = self.signing_key.to_bytes(); scratch.zeroize(); } }
fn send<T: Serialize>(result: Result<T, KernelError>) {
    let response: Response<serde_json::Value> = match result {
        Ok(value) => match serde_json::to_value(value) {
            Ok(value) => Response { ok: true, result: Some(value), error: None },
            Err(error) => Response { ok: false, result: None, error: Some(error.to_string()) },
        },
        Err(error) => Response { ok: false, result: None, error: Some(error.to_string()) },
    };
    println!("{}", serde_json::to_string(&response).expect("response serialization"));
}

fn main() -> Result<(), KernelError> {
    let path = std::env::args().nth(1).ok_or_else(|| KernelError::Invalid("usage: adam-v043-authority-kernel LOG_PATH".into()))?;
    let mut kernel = AuthorityKernel::open(path)?;
    println!("{}", serde_json::to_string(&Response { ok: true, result: Some(kernel.health()), error: None::<String> })?);
    for line in BufReader::new(io::stdin().lock()).lines() {
        let request: Request = match serde_json::from_str(&line?) { Ok(request) => request, Err(error) => { send::<serde_json::Value>(Err(error.into())); continue; } };
        match request {
            Request::Health | Request::Root => send(Ok(kernel.health())),
            Request::Append { payload_hex, expected_root } => {
                let payload = match hex::decode(payload_hex) { Ok(payload) => payload, Err(error) => { send::<serde_json::Value>(Err(KernelError::Invalid(error.to_string()))); continue; } };
                send(kernel.append(&payload, expected_root.as_deref()));
            },
            Request::Verify => send(AuthorityKernel::open(&kernel.path).map(|replayed| replayed.health())),
            Request::Stop => { send(Ok(kernel.health())); break; },
        }
    }
    Ok(())
}
