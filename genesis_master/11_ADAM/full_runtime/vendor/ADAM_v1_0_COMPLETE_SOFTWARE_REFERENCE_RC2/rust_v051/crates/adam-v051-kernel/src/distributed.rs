use crate::canonical::{CanonicalValue, digest};
use crate::error::{KernelError, Result};
use crate::signature::{SignatureEnvelope, verify_envelope};
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet};

fn required(value: &str, name: &str) -> Result<()> {
    if value.trim().is_empty() {
        return Err(KernelError::Invalid(format!("{name} is required")));
    }
    Ok(())
}

fn root(value: &str, name: &str) -> Result<()> {
    if value.len() != 64 || !value.bytes().all(|byte| byte.is_ascii_hexdigit()) {
        return Err(KernelError::Invalid(format!("{name} must be a 32-byte hex digest")));
    }
    Ok(())
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub struct VoteStatement {
    pub format: String,
    pub version: u16,
    pub node_id: String,
    pub epoch: u64,
    pub sequence: u64,
    pub previous_root: String,
    pub root: String,
    pub reaction_id: String,
}

impl VoteStatement {
    pub fn validate(&self) -> Result<()> {
        if self.format != "ADAM-v0.51-authority-vote" || self.version != 1 {
            return Err(KernelError::Invalid("unsupported authority vote".into()));
        }
        required(&self.node_id, "node_id")?;
        root(&self.previous_root, "previous_root")?;
        root(&self.root, "root")?;
        root(&self.reaction_id, "reaction_id")?;
        if self.previous_root == self.root {
            return Err(KernelError::Invalid("vote must advance the universe root".into()));
        }
        Ok(())
    }
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub struct SignedVote {
    pub statement: VoteStatement,
    pub signature: SignatureEnvelope,
}

impl SignedVote {
    pub fn verify(&self, expected_key_id: &str) -> Result<()> {
        self.statement.validate()?;
        if self.signature.key_id != expected_key_id {
            return Err(KernelError::Signature);
        }
        verify_envelope(&serde_json::to_vec(&self.statement)?, &self.signature)
    }
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub struct QuorumCertificate {
    pub format: String,
    pub version: u16,
    pub epoch: u64,
    pub sequence: u64,
    pub previous_root: String,
    pub root: String,
    pub reaction_id: String,
    pub membership: BTreeMap<String, String>,
    pub quorum: usize,
    pub votes: Vec<SignedVote>,
}

impl QuorumCertificate {
    pub fn verify(&self) -> Result<String> {
        if self.format != "ADAM-v0.51-quorum-certificate" || self.version != 1 {
            return Err(KernelError::Invalid("unsupported quorum certificate".into()));
        }
        root(&self.previous_root, "previous_root")?;
        root(&self.root, "root")?;
        root(&self.reaction_id, "reaction_id")?;
        if self.membership.is_empty()
            || self.quorum == 0
            || self.quorum > self.membership.len()
        {
            return Err(KernelError::Invalid("invalid certificate membership/quorum".into()));
        }
        let minimum_majority = self.membership.len() / 2 + 1;
        if self.quorum < minimum_majority {
            return Err(KernelError::Invalid("certificate quorum is below majority".into()));
        }
        let mut signers = BTreeSet::new();
        for vote in &self.votes {
            let key_id = self
                .membership
                .get(&vote.statement.node_id)
                .ok_or_else(|| KernelError::Invalid("vote signer is not a member".into()))?;
            if !signers.insert(vote.statement.node_id.clone()) {
                return Err(KernelError::Invalid("duplicate certificate signer".into()));
            }
            if vote.statement.epoch != self.epoch
                || vote.statement.sequence != self.sequence
                || vote.statement.previous_root != self.previous_root
                || vote.statement.root != self.root
                || vote.statement.reaction_id != self.reaction_id
            {
                return Err(KernelError::Invalid("vote statement differs from certificate".into()));
            }
            vote.verify(key_id)?;
        }
        if signers.len() < self.quorum {
            return Err(KernelError::Invalid("certificate lacks quorum".into()));
        }
        let value = CanonicalValue::from_json(&serde_json::to_value(self)?)?;
        digest("ADAM51:QUORUM_CERTIFICATE", &value)
    }
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub struct WitnessStatement {
    pub format: String,
    pub version: u16,
    pub witness_id: String,
    pub sequence: u64,
    pub root: String,
    pub previous_statement_id: Option<String>,
}

impl WitnessStatement {
    pub fn validate(&self) -> Result<()> {
        if self.format != "ADAM-v0.51-witness-statement" || self.version != 1 {
            return Err(KernelError::Invalid("unsupported witness statement".into()));
        }
        required(&self.witness_id, "witness_id")?;
        root(&self.root, "root")?;
        if let Some(previous) = &self.previous_statement_id {
            root(previous, "previous_statement_id")?;
        }
        Ok(())
    }
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub struct SignedWitnessStatement {
    pub statement: WitnessStatement,
    pub signature: SignatureEnvelope,
}

impl SignedWitnessStatement {
    pub fn id(&self) -> Result<String> {
        let value = CanonicalValue::from_json(&serde_json::to_value(&self.statement)?)?;
        digest("ADAM51:WITNESS_STATEMENT", &value)
    }

    pub fn verify(&self, expected_key_id: &str) -> Result<()> {
        self.statement.validate()?;
        if self.signature.key_id != expected_key_id {
            return Err(KernelError::Signature);
        }
        verify_envelope(&serde_json::to_vec(&self.statement)?, &self.signature)
    }
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub struct WitnessChain {
    pub format: String,
    pub version: u16,
    pub membership: BTreeMap<String, String>,
    pub statements: Vec<SignedWitnessStatement>,
}

impl WitnessChain {
    pub fn verify(&self) -> Result<Option<String>> {
        if self.format != "ADAM-v0.51-witness-chain" || self.version != 1 {
            return Err(KernelError::Invalid("unsupported witness chain".into()));
        }
        let mut previous_id: Option<String> = None;
        let mut previous_sequence: Option<u64> = None;
        for signed in &self.statements {
            let expected_key_id = self
                .membership
                .get(&signed.statement.witness_id)
                .ok_or_else(|| KernelError::Invalid("witness is not enrolled".into()))?;
            signed.verify(expected_key_id)?;
            if signed.statement.previous_statement_id != previous_id {
                return Err(KernelError::Invalid("witness chain linkage mismatch".into()));
            }
            if previous_sequence.is_some_and(|sequence| signed.statement.sequence <= sequence) {
                return Err(KernelError::Invalid(
                    "witness sequence must strictly increase".into(),
                ));
            }
            previous_sequence = Some(signed.statement.sequence);
            previous_id = Some(signed.id()?);
        }
        Ok(previous_id)
    }
}
