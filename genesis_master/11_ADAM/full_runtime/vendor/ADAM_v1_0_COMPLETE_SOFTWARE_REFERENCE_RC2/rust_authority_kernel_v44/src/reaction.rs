use crate::model::{FirstClassBond, HyperBond};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;

fn hash(domain: &[u8], value: &impl Serialize) -> Result<String, serde_json::Error> {
    let bytes = serde_json::to_vec(value)?;
    let mut h = Sha256::new();
    h.update(domain);
    h.update([0]);
    h.update(bytes);
    Ok(hex::encode(h.finalize()))
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct ReactionRequest {
    pub reaction_name: String,
    pub expected_root: String,
    pub actor: String,
    pub authority: String,
    pub capabilities: Vec<String>,
    pub proposer: String,
    pub approvers: Vec<String>,
    pub bindings: BTreeMap<String, String>,
    pub required_capabilities: Vec<String>,
    pub formed_bonds: Vec<FirstClassBond>,
    pub formed_hyperbond: Option<HyperBond>,
    pub terminated_bond_ids: Vec<String>,
    pub law_results: Vec<(String, bool, String)>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct ReactionProof {
    pub reaction_id: String,
    pub previous_root: String,
    pub new_root: String,
    pub logical_time: u64,
    pub formed_bond_ids: Vec<String>,
    pub hyperbond_id: Option<String>,
    pub terminated_bond_ids: Vec<String>,
    pub law_results: Vec<(String, bool, String)>,
    pub actor: String,
    pub authority: String,
}

impl ReactionRequest {
    pub fn validate(&self, current_root: &str, logical_time: u64) -> Result<ReactionProof, String> {
        if self.expected_root != current_root { return Err("stale universe root".into()); }
        if self.authority.is_empty() { return Err("authority required".into()); }
        if self.approvers.iter().any(|a| a == &self.proposer) { return Err("proposer cannot self-approve".into()); }
        for capability in &self.required_capabilities {
            if !self.capabilities.contains(capability) { return Err(format!("missing capability {capability}")); }
        }
        if self.law_results.iter().any(|(_, ok, _)| !ok) { return Err("constitutional law failure".into()); }
        let mut formed_bond_ids = Vec::new();
        for bond in &self.formed_bonds {
            bond.validate()?;
            formed_bond_ids.push(bond.id().map_err(|e| e.to_string())?);
        }
        let hyperbond_id = match &self.formed_hyperbond {
            Some(h) => { h.validate()?; Some(h.id().map_err(|e| e.to_string())?) },
            None => None,
        };
        let reaction_id = hash(b"ADAM44:RUST_REACTION", self).map_err(|e| e.to_string())?;
        let root_material = (&self.expected_root, logical_time + 1, &reaction_id, &formed_bond_ids, &hyperbond_id, &self.terminated_bond_ids);
        let new_root = hash(b"ADAM44:RUST_PHYSICS_ROOT", &root_material).map_err(|e| e.to_string())?;
        Ok(ReactionProof {
            reaction_id,
            previous_root: self.expected_root.clone(),
            new_root,
            logical_time: logical_time + 1,
            formed_bond_ids,
            hyperbond_id,
            terminated_bond_ids: self.terminated_bond_ids.clone(),
            law_results: self.law_results.clone(),
            actor: self.actor.clone(),
            authority: self.authority.clone(),
        })
    }
}
