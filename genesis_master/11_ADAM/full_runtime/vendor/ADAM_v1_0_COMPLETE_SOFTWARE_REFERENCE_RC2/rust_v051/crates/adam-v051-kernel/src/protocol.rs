use crate::canonical::{CanonicalValue, digest};
use crate::error::{KernelError, Result};
use serde::{Deserialize, Serialize};
use serde_json::Value;
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

fn sorted_unique(values: &[String], name: &str) -> Result<()> {
    let mut previous: Option<&str> = None;
    for value in values {
        required(value, name)?;
        if previous.is_some_and(|prior| prior >= value.as_str()) {
            return Err(KernelError::Invalid(format!(
                "{name} must be strictly sorted and unique"
            )));
        }
        previous = Some(value);
    }
    Ok(())
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
pub struct AuthorityAtom {
    pub atom_id: String,
    pub atom_type: String,
    pub value: Value,
    pub authority: String,
    pub provenance: Vec<String>,
    pub security_scope: String,
    pub chemistry_version: String,
}

impl AuthorityAtom {
    pub fn canonical_without_id(&self) -> Result<CanonicalValue> {
        let mut provenance = self.provenance.clone();
        provenance.sort();
        provenance.dedup();
        Ok(CanonicalValue::map([
            ("atom_type", CanonicalValue::String(self.atom_type.clone())),
            ("value", CanonicalValue::from_json(&self.value)?),
            ("authority", CanonicalValue::String(self.authority.clone())),
            (
                "provenance",
                CanonicalValue::Array(
                    provenance
                        .into_iter()
                        .map(CanonicalValue::String)
                        .collect(),
                ),
            ),
            (
                "security_scope",
                CanonicalValue::String(self.security_scope.clone()),
            ),
            (
                "chemistry_version",
                CanonicalValue::String(self.chemistry_version.clone()),
            ),
        ]))
    }

    pub fn calculated_id(&self) -> Result<String> {
        digest("ADAM51:AUTHORITY_ATOM", &self.canonical_without_id()?)
    }

    pub fn validate(&self) -> Result<()> {
        required(&self.atom_type, "atom_type")?;
        required(&self.authority, "authority")?;
        required(&self.security_scope, "security_scope")?;
        required(&self.chemistry_version, "chemistry_version")?;
        if self.atom_id != self.calculated_id()? {
            return Err(KernelError::Invalid("atom identity mismatch".into()));
        }
        Ok(())
    }
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub struct ApplicationManifest {
    pub format: String,
    pub version: u16,
    pub application_id: String,
    pub identity_namespace: String,
    pub observable_entity_types: Vec<String>,
    pub permitted_reactions: Vec<String>,
    pub constructible_representations: Vec<String>,
    pub evidence_types: Vec<String>,
    pub authority_scope: String,
    pub security_scope: String,
    pub maximum_event_bytes: u64,
}

impl ApplicationManifest {
    pub fn validate(&self) -> Result<()> {
        if self.format != "ADAM-v0.51-application-manifest" || self.version != 1 {
            return Err(KernelError::Invalid("unsupported application manifest".into()));
        }
        required(&self.application_id, "application_id")?;
        required(&self.identity_namespace, "identity_namespace")?;
        required(&self.authority_scope, "authority_scope")?;
        required(&self.security_scope, "security_scope")?;
        if self.maximum_event_bytes == 0 || self.maximum_event_bytes > 64 * 1024 * 1024 {
            return Err(KernelError::Invalid(
                "maximum_event_bytes must be within 1..=67108864".into(),
            ));
        }
        sorted_unique(&self.observable_entity_types, "observable_entity_types")?;
        sorted_unique(&self.permitted_reactions, "permitted_reactions")?;
        sorted_unique(
            &self.constructible_representations,
            "constructible_representations",
        )?;
        sorted_unique(&self.evidence_types, "evidence_types")
    }
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub struct InferenceAuthorizationRequest {
    pub format: String,
    pub version: u16,
    pub actor: String,
    pub purpose: String,
    pub requested_roots: Vec<String>,
    pub dependency_closure: Vec<String>,
    pub capabilities: Vec<String>,
    pub issued_at: u64,
    pub expires_at: u64,
}

impl InferenceAuthorizationRequest {
    pub fn validate(&self) -> Result<()> {
        if self.format != "ADAM-v0.51-inference-authorization" || self.version != 1 {
            return Err(KernelError::Invalid(
                "unsupported inference authorization request".into(),
            ));
        }
        required(&self.actor, "actor")?;
        required(&self.purpose, "purpose")?;
        if self.expires_at <= self.issued_at {
            return Err(KernelError::Invalid("authorization expiry must follow issue time".into()));
        }
        sorted_unique(&self.requested_roots, "requested_roots")?;
        sorted_unique(&self.dependency_closure, "dependency_closure")?;
        sorted_unique(&self.capabilities, "capabilities")?;
        for value in self
            .requested_roots
            .iter()
            .chain(self.dependency_closure.iter())
        {
            root(value, "authorized root")?;
        }
        let closure = self.dependency_closure.iter().collect::<BTreeSet<_>>();
        if self
            .requested_roots
            .iter()
            .any(|requested| !closure.contains(requested))
        {
            return Err(KernelError::Invalid(
                "every requested root must be included in dependency closure".into(),
            ));
        }
        Ok(())
    }
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub struct NoveltyClosureEnvelope {
    pub format: String,
    pub version: u16,
    pub source_universe_root: String,
    pub destination_prior_root: String,
    pub destination_result_root: String,
    pub dictionary_root: String,
    pub epoch: u64,
    pub atom_ids: Vec<String>,
    pub bond_ids: Vec<String>,
    pub compound_ids: Vec<String>,
    pub recipe_ids: Vec<String>,
    pub metadata: BTreeMap<String, String>,
}

impl NoveltyClosureEnvelope {
    pub fn validate(&self) -> Result<()> {
        if self.format != "ADAM-v0.51-novelty-closure" || self.version != 1 {
            return Err(KernelError::Invalid("unsupported novelty closure".into()));
        }
        for (name, value) in [
            ("source_universe_root", &self.source_universe_root),
            ("destination_prior_root", &self.destination_prior_root),
            ("destination_result_root", &self.destination_result_root),
            ("dictionary_root", &self.dictionary_root),
        ] {
            root(value, name)?;
        }
        sorted_unique(&self.atom_ids, "atom_ids")?;
        sorted_unique(&self.bond_ids, "bond_ids")?;
        sorted_unique(&self.compound_ids, "compound_ids")?;
        sorted_unique(&self.recipe_ids, "recipe_ids")?;
        for value in self
            .atom_ids
            .iter()
            .chain(self.bond_ids.iter())
            .chain(self.compound_ids.iter())
            .chain(self.recipe_ids.iter())
        {
            root(value, "closure identity")?;
        }
        Ok(())
    }
}
