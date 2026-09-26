use crate::canonical::{CanonicalValue, digest};
use crate::error::{KernelError, Result};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::BTreeMap;

fn cv_string(value: impl Into<String>) -> CanonicalValue {
    CanonicalValue::String(value.into())
}

fn cv_optional_string(value: &Option<String>) -> CanonicalValue {
    value.as_ref().map_or(CanonicalValue::Null, |v| cv_string(v.clone()))
}

fn cv_optional_u64(value: Option<u64>) -> CanonicalValue {
    value.map_or(CanonicalValue::Null, CanonicalValue::UInt)
}

fn cv_strings(values: impl IntoIterator<Item = String>) -> CanonicalValue {
    CanonicalValue::Array(values.into_iter().map(cv_string).collect())
}

fn cv_metadata(values: &BTreeMap<String, Value>) -> Result<CanonicalValue> {
    values
        .iter()
        .map(|(key, value)| Ok((key.clone(), CanonicalValue::from_json(value)?)))
        .collect::<Result<BTreeMap<_, _>>>()
        .map(CanonicalValue::Map)
}

fn round12(value: f64) -> f64 {
    (value * 1_000_000_000_000.0).round() / 1_000_000_000_000.0
}

#[derive(Clone, Copy, Debug, Serialize, Deserialize, PartialEq, Eq, PartialOrd, Ord)]
#[serde(rename_all = "snake_case")]
pub enum BondFamily {
    Structural,
    Semantic,
    Temporal,
    Causal,
    Evidentiary,
    Cognitive,
    Operational,
    Security,
    Probabilistic,
}

impl BondFamily {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Structural => "structural",
            Self::Semantic => "semantic",
            Self::Temporal => "temporal",
            Self::Causal => "causal",
            Self::Evidentiary => "evidentiary",
            Self::Cognitive => "cognitive",
            Self::Operational => "operational",
            Self::Security => "security",
            Self::Probabilistic => "probabilistic",
        }
    }
}

#[derive(Clone, Copy, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum ConfidenceClass {
    Authoritative,
    VerifiedDerivation,
    SupportedHypothesis,
    ModelInference,
    SimulationOnly,
    Rejected,
}

impl ConfidenceClass {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Authoritative => "authoritative",
            Self::VerifiedDerivation => "verified_derivation",
            Self::SupportedHypothesis => "supported_hypothesis",
            Self::ModelInference => "model_inference",
            Self::SimulationOnly => "simulation_only",
            Self::Rejected => "rejected",
        }
    }
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub struct TimeScope {
    pub valid_from: u64,
    pub valid_until: Option<u64>,
    pub observed_at: Option<u64>,
}

impl Default for TimeScope {
    fn default() -> Self {
        Self { valid_from: 0, valid_until: None, observed_at: None }
    }
}

impl TimeScope {
    pub fn validate(&self) -> Result<()> {
        if self.valid_until.is_some_and(|until| until <= self.valid_from) {
            return Err(KernelError::Invalid("valid_until must exceed valid_from".into()));
        }
        Ok(())
    }

    pub fn active(&self, logical_time: u64) -> bool {
        self.valid_from <= logical_time && self.valid_until.is_none_or(|until| logical_time < until)
    }

    pub fn canonical(&self) -> CanonicalValue {
        CanonicalValue::map([
            ("valid_from", CanonicalValue::UInt(self.valid_from)),
            ("valid_until", cv_optional_u64(self.valid_until)),
            ("observed_at", cv_optional_u64(self.observed_at)),
        ])
    }
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
    pub confidence_class: ConfidenceClass,
    pub security_scope: String,
    pub chemistry_version: String,
    pub reaction_origin: Option<String>,
    pub supporting_evidence: Vec<String>,
    pub metadata: BTreeMap<String, Value>,
}

impl FirstClassBond {
    pub fn validate(&self) -> Result<()> {
        if self.source.is_empty() || self.predicate.is_empty() || self.target.is_empty() {
            return Err(KernelError::Invalid("source, predicate and target are required".into()));
        }
        if !matches!(self.direction.as_str(), "forward" | "reverse" | "bidirectional" | "ordered") {
            return Err(KernelError::Invalid("unsupported bond direction".into()));
        }
        if self.authority.is_empty() || self.security_scope.is_empty() || self.chemistry_version.is_empty() {
            return Err(KernelError::Invalid("authority, security scope and chemistry version are required".into()));
        }
        if !(0.0..=1.0).contains(&self.confidence) || !self.confidence.is_finite() {
            return Err(KernelError::Invalid("confidence outside [0,1]".into()));
        }
        self.time.validate()
    }

    pub fn canonical(&self) -> Result<CanonicalValue> {
        let mut causal = self.causal_parents.clone();
        causal.sort();
        let mut provenance = self.provenance.clone();
        provenance.sort();
        let mut evidence = self.supporting_evidence.clone();
        evidence.sort();
        Ok(CanonicalValue::map([
            ("source", cv_string(self.source.clone())),
            ("predicate", cv_string(self.predicate.clone())),
            ("target", cv_string(self.target.clone())),
            ("family", cv_string(self.family.as_str())),
            ("direction", cv_string(self.direction.clone())),
            ("order", cv_optional_u64(self.order)),
            ("time", self.time.canonical()),
            ("causal_parents", cv_strings(causal)),
            ("authority", cv_string(self.authority.clone())),
            ("provenance", cv_strings(provenance)),
            ("confidence", CanonicalValue::Float(round12(self.confidence))),
            ("confidence_class", cv_string(self.confidence_class.as_str())),
            ("security_scope", cv_string(self.security_scope.clone())),
            ("chemistry_version", cv_string(self.chemistry_version.clone())),
            ("reaction_origin", cv_optional_string(&self.reaction_origin)),
            ("supporting_evidence", cv_strings(evidence)),
            ("metadata", cv_metadata(&self.metadata)?),
        ]))
    }

    pub fn id(&self) -> Result<String> {
        self.validate()?;
        digest("ADAM44:FIRST_CLASS_BOND", &self.canonical()?)
    }

    pub fn terminate(&self, at: u64, reaction_origin: String) -> Result<Self> {
        if at <= self.time.valid_from {
            return Err(KernelError::Invalid("termination must follow bond genesis".into()));
        }
        let mut successor = self.clone();
        successor.time.valid_until = Some(at);
        successor.reaction_origin = Some(reaction_origin);
        successor.validate()?;
        Ok(successor)
    }
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub struct HyperRole {
    pub role: String,
    pub participant: String,
    pub order: Option<u64>,
    pub required: bool,
    pub metadata: BTreeMap<String, Value>,
}

impl HyperRole {
    pub fn validate(&self) -> Result<()> {
        if self.role.is_empty() || self.participant.is_empty() {
            return Err(KernelError::Invalid("hyperbond role and participant are required".into()));
        }
        Ok(())
    }

    pub fn canonical(&self) -> Result<CanonicalValue> {
        Ok(CanonicalValue::map([
            ("role", cv_string(self.role.clone())),
            ("participant", cv_string(self.participant.clone())),
            ("order", cv_optional_u64(self.order)),
            ("required", CanonicalValue::Bool(self.required)),
            ("metadata", cv_metadata(&self.metadata)?),
        ]))
    }
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
    pub metadata: BTreeMap<String, Value>,
}

impl HyperBond {
    pub fn validate(&self) -> Result<()> {
        if self.event_type.is_empty() || self.roles.is_empty() {
            return Err(KernelError::Invalid("event type and roles are required".into()));
        }
        if self.authority.is_empty() || self.security_scope.is_empty() || self.chemistry_version.is_empty() {
            return Err(KernelError::Invalid("hyperbond authority, security scope and chemistry version are required".into()));
        }
        if !(0.0..=1.0).contains(&self.confidence) || !self.confidence.is_finite() {
            return Err(KernelError::Invalid("hyperbond confidence outside [0,1]".into()));
        }
        self.time.validate()?;
        let mut names = BTreeMap::new();
        for role in &self.roles {
            role.validate()?;
            if names.insert(role.role.clone(), ()).is_some() {
                return Err(KernelError::Invalid("duplicate hyperbond role".into()));
            }
        }
        Ok(())
    }

    pub fn canonical(&self) -> Result<CanonicalValue> {
        let mut roles = self.roles.clone();
        roles.sort_by(|left, right| {
            (left.order.is_none(), left.order.unwrap_or(0), &left.role)
                .cmp(&(right.order.is_none(), right.order.unwrap_or(0), &right.role))
        });
        let role_values = roles.iter().map(HyperRole::canonical).collect::<Result<Vec<_>>>()?;
        let mut provenance = self.provenance.clone();
        provenance.sort();
        let mut causal = self.causal_parents.clone();
        causal.sort();
        Ok(CanonicalValue::map([
            ("event_type", cv_string(self.event_type.clone())),
            ("roles", CanonicalValue::Array(role_values)),
            ("authority", cv_string(self.authority.clone())),
            ("time", self.time.canonical()),
            ("provenance", cv_strings(provenance)),
            ("security_scope", cv_string(self.security_scope.clone())),
            ("chemistry_version", cv_string(self.chemistry_version.clone())),
            ("causal_parents", cv_strings(causal)),
            ("confidence", CanonicalValue::Float(round12(self.confidence))),
            ("metadata", cv_metadata(&self.metadata)?),
        ]))
    }

    pub fn id(&self) -> Result<String> {
        self.validate()?;
        digest("ADAM44:HYPERBOND", &self.canonical()?)
    }
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub struct ValenceConstraint {
    pub predicate: String,
    pub source_types: Vec<String>,
    pub target_types: Vec<String>,
    pub minimum: u64,
    pub maximum: Option<u64>,
    pub families: Vec<BondFamily>,
    pub require_evidence: bool,
    pub require_authority: bool,
}

impl ValenceConstraint {
    pub fn validate(&self) -> Result<()> {
        if self.predicate.is_empty() || self.maximum.is_some_and(|maximum| maximum < self.minimum) {
            return Err(KernelError::Invalid("invalid valence constraint".into()));
        }
        Ok(())
    }

    pub fn canonical(&self) -> CanonicalValue {
        CanonicalValue::map([
            ("source_types", cv_strings(self.source_types.clone())),
            ("target_types", cv_strings(self.target_types.clone())),
            ("minimum", CanonicalValue::UInt(self.minimum)),
            ("maximum", cv_optional_u64(self.maximum)),
            ("families", cv_strings(self.families.iter().map(|family| family.as_str().to_owned()))),
            ("require_evidence", CanonicalValue::Bool(self.require_evidence)),
            ("require_authority", CanonicalValue::Bool(self.require_authority)),
        ])
    }
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub struct BondTemplate {
    pub source: String,
    pub predicate: String,
    pub target: String,
    pub family: BondFamily,
    pub security_scope: String,
    pub require_evidence_var: Option<String>,
}

impl BondTemplate {
    pub fn canonical(&self) -> CanonicalValue {
        CanonicalValue::map([
            ("source", cv_string(self.source.clone())),
            ("predicate", cv_string(self.predicate.clone())),
            ("target", cv_string(self.target.clone())),
            ("family", cv_string(self.family.as_str())),
            ("security_scope", cv_string(self.security_scope.clone())),
            ("require_evidence_var", cv_optional_string(&self.require_evidence_var)),
        ])
    }
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub struct HyperBondTemplate {
    pub event_type: String,
    pub roles: Vec<(String, String)>,
    pub security_scope: String,
}

impl HyperBondTemplate {
    pub fn canonical(&self) -> CanonicalValue {
        CanonicalValue::map([
            ("event_type", cv_string(self.event_type.clone())),
            ("roles", CanonicalValue::Array(self.roles.iter().map(|(role, value)| {
                CanonicalValue::Array(vec![cv_string(role.clone()), cv_string(value.clone())])
            }).collect())),
            ("security_scope", cv_string(self.security_scope.clone())),
        ])
    }
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
pub struct ConstitutionalLaw {
    pub name: String,
    pub kind: String,
    pub params: BTreeMap<String, Value>,
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub struct ReactionDefinition {
    pub name: String,
    pub required: Vec<BondTemplate>,
    pub forbidden: Vec<BondTemplate>,
    pub break_bonds: Vec<BondTemplate>,
    pub form_bonds: Vec<BondTemplate>,
    pub form_hyperbond: Option<HyperBondTemplate>,
    pub required_capabilities: Vec<String>,
    pub laws: Vec<String>,
    pub version: u64,
}

impl ReactionDefinition {
    pub fn canonical(&self) -> CanonicalValue {
        CanonicalValue::map([
            ("name", cv_string(self.name.clone())),
            ("required", CanonicalValue::Array(self.required.iter().map(BondTemplate::canonical).collect())),
            ("forbidden", CanonicalValue::Array(self.forbidden.iter().map(BondTemplate::canonical).collect())),
            ("break_bonds", CanonicalValue::Array(self.break_bonds.iter().map(BondTemplate::canonical).collect())),
            ("form_bonds", CanonicalValue::Array(self.form_bonds.iter().map(BondTemplate::canonical).collect())),
            ("form_hyperbond", self.form_hyperbond.as_ref().map_or(CanonicalValue::Null, HyperBondTemplate::canonical)),
            ("required_capabilities", cv_strings(self.required_capabilities.clone())),
            ("laws", cv_strings(self.laws.clone())),
            ("version", CanonicalValue::UInt(self.version)),
        ])
    }

    pub fn id(&self) -> Result<String> {
        digest("ADAM44:REACTION_DEFINITION", &self.canonical())
    }
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub struct ReactionIntent {
    pub reaction_name: String,
    pub bindings: BTreeMap<String, String>,
    pub actor: String,
    pub authority: String,
    pub capabilities: Vec<String>,
    pub expected_root: String,
    pub proposer: String,
    pub approvers: Vec<String>,
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub struct ReactionProof {
    pub reaction_id: String,
    pub reaction_type_id: String,
    pub previous_root: String,
    pub new_root: String,
    pub law_results: Vec<(String, bool, String)>,
    pub formed_bonds: Vec<String>,
    pub terminated_bonds: Vec<String>,
    pub hyperbond_id: Option<String>,
    pub actor: String,
    pub authority: String,
    pub logical_time: u64,
}

impl ReactionProof {
    pub fn canonical(&self) -> CanonicalValue {
        CanonicalValue::map([
            ("reaction_id", cv_string(self.reaction_id.clone())),
            ("reaction_type_id", cv_string(self.reaction_type_id.clone())),
            ("previous_root", cv_string(self.previous_root.clone())),
            ("new_root", cv_string(self.new_root.clone())),
            ("law_results", CanonicalValue::Array(self.law_results.iter().map(|(name, ok, message)| {
                CanonicalValue::Array(vec![cv_string(name.clone()), CanonicalValue::Bool(*ok), cv_string(message.clone())])
            }).collect())),
            ("formed_bonds", cv_strings(self.formed_bonds.clone())),
            ("terminated_bonds", cv_strings(self.terminated_bonds.clone())),
            ("hyperbond_id", cv_optional_string(&self.hyperbond_id)),
            ("actor", cv_string(self.actor.clone())),
            ("authority", cv_string(self.authority.clone())),
            ("logical_time", CanonicalValue::UInt(self.logical_time)),
        ])
    }

    pub fn id(&self) -> Result<String> {
        digest("ADAM44:REACTION_PROOF", &self.canonical())
    }
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub struct Worldline {
    pub entity_id: String,
    pub genesis_root: String,
    pub states: Vec<(u64, String, String)>,
}

impl Worldline {
    pub fn append(&mut self, logical_time: u64, root: String, reaction_id: String) -> Result<()> {
        if self.states.last().is_some_and(|state| logical_time <= state.0) {
            return Err(KernelError::Invalid("worldline time must increase".into()));
        }
        self.states.push((logical_time, root, reaction_id));
        Ok(())
    }
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
pub struct BondAlgebraState {
    pub entity_types: BTreeMap<String, String>,
    pub bonds: BTreeMap<String, FirstClassBond>,
    pub hyperbonds: BTreeMap<String, HyperBond>,
    pub constraints: BTreeMap<String, ValenceConstraint>,
    pub superseded_by: BTreeMap<String, String>,
}

impl Default for BondAlgebraState {
    fn default() -> Self {
        Self {
            entity_types: BTreeMap::new(),
            bonds: BTreeMap::new(),
            hyperbonds: BTreeMap::new(),
            constraints: BTreeMap::new(),
            superseded_by: BTreeMap::new(),
        }
    }
}

impl BondAlgebraState {
    pub fn canonical(&self) -> Result<CanonicalValue> {
        let entities = CanonicalValue::Map(self.entity_types.iter().map(|(key, value)| (key.clone(), cv_string(value.clone()))).collect());
        let bonds = CanonicalValue::Map(self.bonds.iter().map(|(key, value)| Ok((key.clone(), value.canonical()?))).collect::<Result<_>>()?);
        let hyperbonds = CanonicalValue::Map(self.hyperbonds.iter().map(|(key, value)| Ok((key.clone(), value.canonical()?))).collect::<Result<_>>()?);
        let constraints = CanonicalValue::Map(self.constraints.iter().map(|(key, value)| (key.clone(), value.canonical())).collect());
        let superseded = CanonicalValue::Map(self.superseded_by.iter().map(|(key, value)| (key.clone(), cv_string(value.clone()))).collect());
        Ok(CanonicalValue::map([
            ("entities", entities),
            ("bonds", bonds),
            ("hyperbonds", hyperbonds),
            ("superseded_by", superseded),
            ("constraints", constraints),
        ]))
    }

    pub fn root(&self) -> Result<String> {
        digest("ADAM44:BOND_ALGEBRA_ROOT", &self.canonical()?)
    }
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
pub struct KernelState {
    pub algebra: BondAlgebraState,
    pub reactions: BTreeMap<String, ReactionDefinition>,
    pub laws: BTreeMap<String, ConstitutionalLaw>,
    pub logical_time: u64,
    pub proofs: BTreeMap<String, ReactionProof>,
    pub worldlines: BTreeMap<String, Worldline>,
}

impl Default for KernelState {
    fn default() -> Self {
        Self {
            algebra: BondAlgebraState::default(),
            reactions: BTreeMap::new(),
            laws: BTreeMap::new(),
            logical_time: 0,
            proofs: BTreeMap::new(),
            worldlines: BTreeMap::new(),
        }
    }
}
