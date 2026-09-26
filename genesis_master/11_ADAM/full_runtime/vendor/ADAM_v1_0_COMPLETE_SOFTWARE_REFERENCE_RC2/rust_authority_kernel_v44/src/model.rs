use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;

fn hash(domain: &[u8], bytes: &[u8]) -> String {
    let mut h = Sha256::new();
    h.update(domain);
    h.update([0]);
    h.update(bytes);
    hex::encode(h.finalize())
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum BondFamily {
    Structural, Semantic, Temporal, Causal, Evidentiary,
    Cognitive, Operational, Security, Probabilistic,
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub struct TimeScope {
    pub valid_from: u64,
    pub valid_until: Option<u64>,
    pub observed_at: Option<u64>,
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
pub struct FirstClassBond {
    pub source: String,
    pub predicate: String,
    pub target: String,
    pub family: BondFamily,
    pub direction: String,
    pub order: Option<u64>,
    pub time: TimeScope,
    pub causal_parents: Vec<String>,
    pub authority: String,
    pub provenance: Vec<String>,
    pub confidence: f64,
    pub confidence_class: String,
    pub security_scope: String,
    pub chemistry_version: String,
    pub reaction_origin: Option<String>,
    pub supporting_evidence: Vec<String>,
    pub metadata: BTreeMap<String, serde_json::Value>,
}

impl FirstClassBond {
    pub fn validate(&self) -> Result<(), String> {
        if self.source.is_empty() || self.predicate.is_empty() || self.target.is_empty() {
            return Err("source, predicate and target are required".into());
        }
        if !(0.0..=1.0).contains(&self.confidence) {
            return Err("confidence outside [0,1]".into());
        }
        if let Some(until) = self.time.valid_until {
            if until <= self.time.valid_from { return Err("invalid validity interval".into()); }
        }
        Ok(())
    }

    pub fn id(&self) -> Result<String, serde_json::Error> {
        let bytes = serde_json::to_vec(self)?;
        Ok(hash(b"ADAM44:FIRST_CLASS_BOND", &bytes))
    }
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub struct HyperRole {
    pub role: String,
    pub participant: String,
    pub order: Option<u64>,
    pub required: bool,
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
pub struct HyperBond {
    pub event_type: String,
    pub roles: Vec<HyperRole>,
    pub authority: String,
    pub time: TimeScope,
    pub provenance: Vec<String>,
    pub security_scope: String,
    pub chemistry_version: String,
    pub causal_parents: Vec<String>,
    pub confidence: f64,
    pub metadata: BTreeMap<String, serde_json::Value>,
}

impl HyperBond {
    pub fn validate(&self) -> Result<(), String> {
        if self.event_type.is_empty() || self.roles.is_empty() { return Err("event type and roles required".into()); }
        let mut names = self.roles.iter().map(|r| r.role.as_str()).collect::<Vec<_>>();
        names.sort_unstable();
        names.dedup();
        if names.len() != self.roles.len() { return Err("duplicate hyperbond role".into()); }
        Ok(())
    }

    pub fn id(&self) -> Result<String, serde_json::Error> {
        let bytes = serde_json::to_vec(self)?;
        Ok(hash(b"ADAM44:HYPERBOND", &bytes))
    }
}
