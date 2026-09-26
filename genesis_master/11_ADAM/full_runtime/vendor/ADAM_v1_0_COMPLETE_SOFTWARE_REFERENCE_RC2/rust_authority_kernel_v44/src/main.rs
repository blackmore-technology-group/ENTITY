mod model;
mod reaction;

use ed25519_dalek::{Signature, Signer, SigningKey, Verifier, VerifyingKey};
use rand_core::OsRng;
use reaction::{ReactionProof, ReactionRequest};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::fs::{File, OpenOptions};
use std::io::{self, BufRead, BufReader, Read, Write};
use std::path::{Path, PathBuf};
use thiserror::Error;
use zeroize::Zeroize;

const DOMAIN: &[u8] = b"ADAM44:RUST_ATOMIC_PHYSICS_FRAME\0";
const SIGN_DOMAIN: &[u8] = b"ADAM44:RUST_ATOMIC_PHYSICS_SIGNATURE\0";

#[derive(Debug, Error)]
enum KernelError {
    #[error("io: {0}")] Io(#[from] io::Error),
    #[error("json: {0}")] Json(#[from] serde_json::Error),
    #[error("invalid request: {0}")] Invalid(String),
    #[error("integrity failure at sequence {0}")] Integrity(u64),
}

#[derive(Debug, Deserialize)]
#[serde(tag = "command", rename_all = "snake_case")]
enum Request { Health, Simulate { reaction: ReactionRequest }, Commit { reaction: ReactionRequest }, Verify, Stop }
#[derive(Debug, Serialize)]
struct Response<T: Serialize> { ok: bool, result: Option<T>, error: Option<String> }
#[derive(Debug, Serialize)]
struct Health { name: &'static str, version: &'static str, sequence: u64, root: String, key_id: String }
#[derive(Debug, Serialize, Deserialize)]
struct SignedEnvelope { proof: ReactionProof, signing_root: String, signature_hex: String, key_id: String }

struct Kernel { path: PathBuf, sequence: u64, root: [u8; 32], key: SigningKey, verifying_key: VerifyingKey }
fn hash(parts: &[&[u8]]) -> [u8; 32] { let mut h=Sha256::new(); for p in parts { h.update(p); } h.finalize().into() }
fn key_id(key: &VerifyingKey) -> String { hex::encode(hash(&[b"ADAM44:RUST_KEY\0", key.as_bytes()])) }

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
    if file.read(&mut length[..1])? == 0 { return Ok(None); }
    file.read_exact(&mut length[1..])?;
    Ok(Some(length))
}

impl Kernel {
    fn open(path: impl AsRef<Path>) -> Result<Self, KernelError> {
        let path = path.as_ref().to_path_buf();
        let key = load_or_create_key(&path)?;
        let verifying_key = key.verifying_key();
        let mut kernel = Self { path, sequence: 0, root: [0; 32], key, verifying_key };
        if kernel.path.exists() { kernel.replay()?; }
        Ok(kernel)
    }

    fn replay(&mut self) -> Result<(), KernelError> {
        let mut file=File::open(&self.path)?; let mut expected=1u64; let mut root=[0u8;32];
        while let Some(length) = read_length_or_eof(&mut file)? {
            let n=u32::from_be_bytes(length) as usize;
            let mut seq=[0u8;8]; file.read_exact(&mut seq)?; let sequence=u64::from_be_bytes(seq);
            let mut prev=[0u8;32]; file.read_exact(&mut prev)?;
            let mut committed=[0u8;32]; file.read_exact(&mut committed)?;
            let mut envelope_bytes=vec![0u8;n]; file.read_exact(&mut envelope_bytes)?;
            if sequence!=expected || prev!=root { return Err(KernelError::Integrity(sequence)); }
            let envelope: SignedEnvelope=serde_json::from_slice(&envelope_bytes).map_err(|_|KernelError::Integrity(sequence))?;
            if envelope.key_id != key_id(&self.verifying_key) { return Err(KernelError::Integrity(sequence)); }
            if envelope.proof.previous_root != hex::encode(prev) || envelope.proof.logical_time != sequence { return Err(KernelError::Integrity(sequence)); }
            let proof_bytes=serde_json::to_vec(&envelope.proof).map_err(|_|KernelError::Integrity(sequence))?;
            let signing_root=hash(&[SIGN_DOMAIN,&seq,&prev,&proof_bytes]);
            if envelope.signing_root != hex::encode(signing_root) { return Err(KernelError::Integrity(sequence)); }
            let signature_bytes=hex::decode(&envelope.signature_hex).map_err(|_|KernelError::Integrity(sequence))?;
            let signature=Signature::from_slice(&signature_bytes).map_err(|_|KernelError::Integrity(sequence))?;
            self.verifying_key.verify(&signing_root,&signature).map_err(|_|KernelError::Integrity(sequence))?;
            let computed=hash(&[DOMAIN,&seq,&prev,&envelope_bytes]);
            if computed!=committed { return Err(KernelError::Integrity(sequence)); }
            root=committed; expected+=1;
        }
        self.sequence=expected-1; self.root=root; Ok(())
    }

    fn simulate(&self, reaction:&ReactionRequest) -> Result<ReactionProof, KernelError> {
        reaction.validate(&hex::encode(self.root), self.sequence).map_err(KernelError::Invalid)
    }

    fn commit(&mut self, reaction:&ReactionRequest) -> Result<ReactionProof, KernelError> {
        let proof=self.simulate(reaction)?;
        let proof_bytes=serde_json::to_vec(&proof)?;
        let next=self.sequence+1; let seq=next.to_be_bytes(); let previous=self.root;
        let signing_root=hash(&[SIGN_DOMAIN,&seq,&previous,&proof_bytes]);
        let signature=self.key.sign(&signing_root);
        let envelope=SignedEnvelope { proof: proof.clone(), signing_root:hex::encode(signing_root),
            signature_hex:hex::encode(signature.to_bytes()), key_id:key_id(&self.verifying_key) };
        let envelope_bytes=serde_json::to_vec(&envelope)?;
        if envelope_bytes.len() > u32::MAX as usize { return Err(KernelError::Invalid("proof envelope too large".into())); }
        let committed=hash(&[DOMAIN,&seq,&previous,&envelope_bytes]);
        let mut file=OpenOptions::new().create(true).append(true).open(&self.path)?;
        file.write_all(&(envelope_bytes.len() as u32).to_be_bytes())?;
        file.write_all(&seq)?; file.write_all(&previous)?; file.write_all(&committed)?; file.write_all(&envelope_bytes)?; file.sync_all()?;
        self.sequence=next; self.root=committed;
        Ok(ReactionProof { new_root:hex::encode(committed), ..proof })
    }

    fn health(&self)->Health { Health { name:"ADAM Rust Atomic Physics Kernel", version:"0.44.0-dev2-source-audited",
        sequence:self.sequence, root:hex::encode(self.root), key_id:key_id(&self.verifying_key) } }
}
impl Drop for Kernel { fn drop(&mut self) { let mut scratch=self.key.to_bytes(); scratch.zeroize(); } }
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

fn main()->Result<(),KernelError> {
    let path=std::env::args().nth(1).ok_or_else(||KernelError::Invalid("usage: adam-v044-atomic-physics-kernel LOG_PATH".into()))?;
    let mut kernel=Kernel::open(path)?;
    println!("{}",serde_json::to_string(&Response{ok:true,result:Some(kernel.health()),error:None::<String>})?);
    for line in BufReader::new(io::stdin().lock()).lines() {
        let request:Request=match serde_json::from_str(&line?) { Ok(r)=>r, Err(e)=>{send::<serde_json::Value>(Err(e.into()));continue;} };
        match request { Request::Health=>send(Ok(kernel.health())), Request::Simulate{reaction}=>send(kernel.simulate(&reaction)),
            Request::Commit{reaction}=>send(kernel.commit(&reaction)), Request::Verify=>send(Kernel::open(&kernel.path).map(|k|k.health())),
            Request::Stop=>{send(Ok(kernel.health()));break;} }
    }
    Ok(())
}
