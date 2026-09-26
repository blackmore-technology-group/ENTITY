use crate::canonical::{CanonicalValue, digest};
use crate::error::{KernelError, Result};
use crate::model::*;
use std::collections::{BTreeMap, BTreeSet};

#[derive(Clone, Debug)]
pub struct Simulation {
    pub state: KernelState,
    pub proof: ReactionProof,
}

#[derive(Clone, Debug, Default)]
pub struct AtomicPhysicsKernel {
    pub state: KernelState,
    committing: bool,
}

impl AtomicPhysicsKernel {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn from_state(state: KernelState) -> Result<Self> {
        let kernel = Self { state, committing: false };
        kernel.validate_state()?;
        Ok(kernel)
    }

    pub fn root(&self) -> Result<String> {
        let mut reaction_ids = self
            .state
            .proofs
            .values()
            .map(|proof| proof.reaction_id.clone())
            .collect::<Vec<_>>();
        reaction_ids.sort();
        digest(
            "ADAM44:PHYSICS_ROOT",
            &CanonicalValue::map([
                ("time", CanonicalValue::UInt(self.state.logical_time)),
                ("algebra", CanonicalValue::String(self.state.algebra.root()?)),
                (
                    "proofs",
                    CanonicalValue::Array(
                        reaction_ids
                            .into_iter()
                            .map(CanonicalValue::String)
                            .collect(),
                    ),
                ),
            ]),
        )
    }

    pub fn declare_entity(&mut self, entity_id: impl Into<String>, entity_type: impl Into<String>) -> Result<()> {
        if self.state.logical_time != 0 || !self.state.proofs.is_empty() {
            return Err(KernelError::Invalid(
                "entity genesis after start must occur through a reaction".into(),
            ));
        }
        let entity_id = entity_id.into();
        let entity_type = entity_type.into();
        if entity_id.is_empty() || entity_type.is_empty() {
            return Err(KernelError::Invalid("entity id and type are required".into()));
        }
        if let Some(previous) = self.state.algebra.entity_types.get(&entity_id) {
            if previous != &entity_type {
                return Err(KernelError::Invalid(format!(
                    "entity {entity_id} is already declared as {previous}"
                )));
            }
            return Ok(());
        }
        self.state
            .algebra
            .entity_types
            .insert(entity_id.clone(), entity_type);
        let genesis_root = self.root()?;
        self.state.worldlines.insert(
            entity_id.clone(),
            Worldline {
                entity_id,
                genesis_root,
                states: Vec::new(),
            },
        );
        Ok(())
    }

    pub fn register_constraint(&mut self, constraint: ValenceConstraint) -> Result<()> {
        if self.state.logical_time != 0 || !self.state.proofs.is_empty() {
            return Err(KernelError::Invalid(
                "constraint registration is frozen after the first commit".into(),
            ));
        }
        constraint.validate()?;
        if let Some(previous) = self.state.algebra.constraints.get(&constraint.predicate) {
            if previous != &constraint {
                return Err(KernelError::Invalid(format!(
                    "constraint {} is already registered",
                    constraint.predicate
                )));
            }
            return Ok(());
        }
        self.state
            .algebra
            .constraints
            .insert(constraint.predicate.clone(), constraint);
        Ok(())
    }

    pub fn seed_bond(&mut self, bond: FirstClassBond) -> Result<String> {
        if self.state.logical_time != 0 || !self.state.proofs.is_empty() {
            return Err(KernelError::Invalid("seed bonds are only allowed at genesis".into()));
        }
        self.add_bond(bond, true)
    }

    pub fn register_law(&mut self, law: ConstitutionalLaw) -> Result<()> {
        if self.state.logical_time != 0 || !self.state.proofs.is_empty() {
            return Err(KernelError::Invalid(
                "law registration is frozen after the first commit".into(),
            ));
        }
        if law.name.is_empty() || law.kind.is_empty() {
            return Err(KernelError::Invalid("law name and kind are required".into()));
        }
        if let Some(previous) = self.state.laws.get(&law.name) {
            if previous != &law {
                return Err(KernelError::Invalid(format!(
                    "law {} is already registered",
                    law.name
                )));
            }
            return Ok(());
        }
        self.state.laws.insert(law.name.clone(), law);
        Ok(())
    }

    pub fn register_reaction(&mut self, definition: ReactionDefinition) -> Result<()> {
        if self.state.logical_time != 0 || !self.state.proofs.is_empty() {
            return Err(KernelError::Invalid(
                "reaction registration is frozen after the first commit".into(),
            ));
        }
        if definition.name.is_empty() {
            return Err(KernelError::Invalid("reaction name is required".into()));
        }
        if let Some(previous) = self.state.reactions.get(&definition.name) {
            if previous != &definition {
                return Err(KernelError::Invalid(format!(
                    "reaction {} is already registered",
                    definition.name
                )));
            }
            return Ok(());
        }
        self.state
            .reactions
            .insert(definition.name.clone(), definition);
        Ok(())
    }

    fn node_exists(algebra: &BondAlgebraState, node_id: &str) -> bool {
        algebra.entity_types.contains_key(node_id)
            || algebra.bonds.contains_key(node_id)
            || algebra.hyperbonds.contains_key(node_id)
    }

    fn node_type<'a>(algebra: &'a BondAlgebraState, node_id: &str) -> &'a str {
        if let Some(entity_type) = algebra.entity_types.get(node_id) {
            entity_type
        } else if algebra.bonds.contains_key(node_id) {
            "BOND"
        } else if algebra.hyperbonds.contains_key(node_id) {
            "HYPERBOND"
        } else {
            "UNKNOWN"
        }
    }

    fn effective_bond_items(algebra: &BondAlgebraState) -> Result<Vec<(String, FirstClassBond)>> {
        let successor_ids = algebra
            .superseded_by
            .values()
            .cloned()
            .collect::<BTreeSet<_>>();
        let mut result = Vec::new();
        for (bond_id, bond) in &algebra.bonds {
            if successor_ids.contains(bond_id) {
                continue;
            }
            if let Some(successor_id) = algebra.superseded_by.get(bond_id) {
                let successor = algebra.bonds.get(successor_id).ok_or_else(|| {
                    KernelError::Invalid(format!(
                        "dangling supersession {bond_id}->{successor_id}"
                    ))
                })?;
                result.push((bond_id.clone(), successor.clone()));
            } else {
                result.push((bond_id.clone(), bond.clone()));
            }
        }
        Ok(result)
    }

    fn active_bond_items(algebra: &BondAlgebraState, logical_time: u64) -> Result<Vec<(String, FirstClassBond)>> {
        Ok(Self::effective_bond_items(algebra)?
            .into_iter()
            .filter(|(_, bond)| bond.time.active(logical_time))
            .collect())
    }

    fn validate_bond(algebra: &BondAlgebraState, bond: &FirstClassBond) -> Result<Vec<String>> {
        bond.validate()?;
        let mut violations = Vec::new();
        for (name, node_id) in [("source", &bond.source), ("target", &bond.target)] {
            if !Self::node_exists(algebra, node_id) {
                violations.push(format!("missing {name} node {node_id}"));
            }
        }
        let Some(constraint) = algebra.constraints.get(&bond.predicate) else {
            return Ok(violations);
        };
        let source_type = Self::node_type(algebra, &bond.source);
        let target_type = Self::node_type(algebra, &bond.target);
        if !constraint.source_types.is_empty()
            && !constraint.source_types.iter().any(|value| value == source_type)
        {
            violations.push(format!(
                "{} source type {source_type} not admitted",
                bond.predicate
            ));
        }
        if !constraint.target_types.is_empty()
            && !constraint.target_types.iter().any(|value| value == target_type)
        {
            violations.push(format!(
                "{} target type {target_type} not admitted",
                bond.predicate
            ));
        }
        if !constraint.families.is_empty() && !constraint.families.contains(&bond.family) {
            violations.push(format!(
                "{} family {} not admitted",
                bond.predicate,
                bond.family.as_str()
            ));
        }
        if constraint.require_evidence && bond.supporting_evidence.is_empty() {
            violations.push(format!("{} requires supporting evidence", bond.predicate));
        }
        if constraint.require_authority && bond.authority == "UNSPECIFIED" {
            violations.push(format!("{} requires authority", bond.predicate));
        }
        let id = bond.id()?;
        let count = Self::active_bond_items(algebra, bond.time.valid_from)?
            .into_iter()
            .filter(|(_, existing)| {
                existing.source == bond.source
                    && existing.predicate == bond.predicate
                    && existing.time.valid_until.is_none()
                    && existing.id().ok().as_deref() != Some(id.as_str())
            })
            .count()
            + 1;
        if constraint
            .maximum
            .is_some_and(|maximum| u64::try_from(count).unwrap_or(u64::MAX) > maximum)
        {
            violations.push(format!(
                "{} maximum {} exceeded for {}",
                bond.predicate,
                constraint.maximum.unwrap_or_default(),
                bond.source
            ));
        }
        Ok(violations)
    }

    fn add_bond_to(algebra: &mut BondAlgebraState, bond: FirstClassBond, validate: bool) -> Result<String> {
        let bond_id = bond.id()?;
        if validate {
            let violations = Self::validate_bond(algebra, &bond)?;
            if !violations.is_empty() {
                return Err(KernelError::Invalid(violations.join("; ")));
            }
        }
        if let Some(existing) = algebra.bonds.get(&bond_id) {
            if existing != &bond {
                return Err(KernelError::Invalid("content-address collision for bond".into()));
            }
        }
        algebra.bonds.insert(bond_id.clone(), bond);
        Ok(bond_id)
    }

    fn add_bond(&mut self, bond: FirstClassBond, validate: bool) -> Result<String> {
        Self::add_bond_to(&mut self.state.algebra, bond, validate)
    }

    fn supersede_bond(
        algebra: &mut BondAlgebraState,
        original_id: &str,
        successor: FirstClassBond,
    ) -> Result<String> {
        if !algebra.bonds.contains_key(original_id) {
            return Err(KernelError::Invalid(format!("unknown bond {original_id}")));
        }
        if algebra.superseded_by.contains_key(original_id) {
            return Err(KernelError::Invalid(format!(
                "bond {original_id} is already superseded"
            )));
        }
        if successor.time.valid_until.is_none() {
            return Err(KernelError::Invalid(
                "a terminal bond version requires valid_until".into(),
            ));
        }
        let successor_id = Self::add_bond_to(algebra, successor, false)?;
        algebra
            .superseded_by
            .insert(original_id.to_owned(), successor_id.clone());
        Ok(successor_id)
    }

    fn add_hyperbond_to(algebra: &mut BondAlgebraState, hyperbond: HyperBond) -> Result<String> {
        hyperbond.validate()?;
        let missing = hyperbond
            .roles
            .iter()
            .filter(|role| !Self::node_exists(algebra, &role.participant))
            .map(|role| role.participant.clone())
            .collect::<Vec<_>>();
        if !missing.is_empty() {
            return Err(KernelError::Invalid(format!(
                "missing hyperbond participants: {missing:?}"
            )));
        }
        let hyperbond_id = hyperbond.id()?;
        algebra.hyperbonds.insert(hyperbond_id.clone(), hyperbond);
        Ok(hyperbond_id)
    }

    fn validate_algebra(algebra: &BondAlgebraState, logical_time: u64) -> Result<Vec<String>> {
        let mut violations = Vec::new();
        for (key, bond) in &algebra.bonds {
            let actual = bond.id()?;
            if key != &actual {
                violations.push(format!("bond key/hash mismatch: {key} != {actual}"));
            }
        }
        for (original, successor) in &algebra.superseded_by {
            match (algebra.bonds.get(original), algebra.bonds.get(successor)) {
                (Some(_), Some(next)) if next.time.valid_until.is_some() => {}
                (Some(_), Some(_)) => violations.push(format!(
                    "supersession successor {successor} is not terminal"
                )),
                _ => violations.push(format!("dangling supersession {original}->{successor}")),
            }
        }
        let active = Self::active_bond_items(algebra, logical_time)?;
        for (predicate, constraint) in &algebra.constraints {
            let candidates = algebra
                .entity_types
                .iter()
                .filter(|(_, entity_type)| {
                    constraint.source_types.is_empty()
                        || constraint.source_types.contains(entity_type)
                })
                .map(|(entity_id, _)| entity_id);
            for source in candidates {
                let count = active
                    .iter()
                    .filter(|(_, bond)| bond.source == *source && bond.predicate == *predicate)
                    .count() as u64;
                if count < constraint.minimum {
                    violations.push(format!(
                        "{predicate} minimum {} not met for {source}: {count}",
                        constraint.minimum
                    ));
                }
                if constraint.maximum.is_some_and(|maximum| count > maximum) {
                    violations.push(format!(
                        "{predicate} maximum {} exceeded for {source}: {count}",
                        constraint.maximum.unwrap_or_default()
                    ));
                }
            }
        }
        Ok(violations)
    }

    pub fn validate_state(&self) -> Result<()> {
        let violations = Self::validate_algebra(&self.state.algebra, self.state.logical_time)?;
        if !violations.is_empty() {
            return Err(KernelError::Invalid(violations.join("; ")));
        }
        for (proof_id, proof) in &self.state.proofs {
            if proof_id != &proof.id()? {
                return Err(KernelError::Invalid(format!(
                    "proof key/hash mismatch: {proof_id}"
                )));
            }
        }
        Ok(())
    }

    fn resolve(value: &str, bindings: &BTreeMap<String, String>) -> Result<String> {
        if let Some(name) = value.strip_prefix('$') {
            bindings
                .get(name)
                .cloned()
                .ok_or_else(|| KernelError::Invalid(format!("missing binding {name}")))
        } else {
            Ok(value.to_owned())
        }
    }

    fn template_matches(
        template: &BondTemplate,
        bond: &FirstClassBond,
        bindings: &BTreeMap<String, String>,
    ) -> bool {
        let source = Self::resolve(&template.source, bindings).unwrap_or_else(|_| "__MISSING__".into());
        let target = Self::resolve(&template.target, bindings).unwrap_or_else(|_| "__MISSING__".into());
        bond.source == source
            && bond.predicate == template.predicate
            && bond.target == target
            && bond.time.valid_until.is_none()
    }

    fn instantiate_bond(
        template: &BondTemplate,
        bindings: &BTreeMap<String, String>,
        authority: &str,
        logical_time: u64,
        reaction_id: &str,
    ) -> Result<FirstClassBond> {
        let evidence = template
            .require_evidence_var
            .as_ref()
            .map(|name| {
                bindings
                    .get(name)
                    .cloned()
                    .ok_or_else(|| KernelError::Invalid(format!("missing evidence binding {name}")))
            })
            .transpose()?
            .into_iter()
            .collect();
        Ok(FirstClassBond {
            source: Self::resolve(&template.source, bindings)?,
            predicate: template.predicate.clone(),
            target: Self::resolve(&template.target, bindings)?,
            family: template.family,
            direction: "forward".into(),
            order: None,
            time: TimeScope {
                valid_from: logical_time,
                valid_until: None,
                observed_at: Some(logical_time),
            },
            causal_parents: Vec::new(),
            authority: authority.to_owned(),
            provenance: Vec::new(),
            confidence: 1.0,
            confidence_class: ConfidenceClass::Authoritative,
            security_scope: template.security_scope.clone(),
            chemistry_version: "v44.1".into(),
            reaction_origin: Some(reaction_id.to_owned()),
            supporting_evidence: evidence,
            metadata: BTreeMap::new(),
        })
    }

    fn instantiate_hyperbond(
        template: &HyperBondTemplate,
        bindings: &BTreeMap<String, String>,
        authority: &str,
        logical_time: u64,
        causal_parents: Vec<String>,
    ) -> Result<HyperBond> {
        let roles = template
            .roles
            .iter()
            .map(|(role, value)| {
                Ok(HyperRole {
                    role: role.clone(),
                    participant: Self::resolve(value, bindings)?,
                    order: None,
                    required: true,
                    metadata: BTreeMap::new(),
                })
            })
            .collect::<Result<Vec<_>>>()?;
        Ok(HyperBond {
            event_type: template.event_type.clone(),
            roles,
            authority: authority.to_owned(),
            time: TimeScope {
                valid_from: logical_time,
                valid_until: None,
                observed_at: Some(logical_time),
            },
            provenance: Vec::new(),
            security_scope: template.security_scope.clone(),
            chemistry_version: "v44.1".into(),
            causal_parents,
            confidence: 1.0,
            metadata: BTreeMap::new(),
        })
    }

    fn reaction_id(
        &self,
        definition: &ReactionDefinition,
        intent: &ReactionIntent,
        next_time: u64,
    ) -> Result<String> {
        let mut capabilities = intent.capabilities.clone();
        capabilities.sort();
        let mut approvers = intent.approvers.clone();
        approvers.sort();
        let bindings = CanonicalValue::Map(
            intent
                .bindings
                .iter()
                .map(|(key, value)| (key.clone(), CanonicalValue::String(value.clone())))
                .collect(),
        );
        digest(
            "ADAM44:REACTION_INTENT",
            &CanonicalValue::map([
                ("definition", CanonicalValue::String(definition.id()?)),
                ("bindings", bindings),
                ("actor", CanonicalValue::String(intent.actor.clone())),
                ("authority", CanonicalValue::String(intent.authority.clone())),
                (
                    "capabilities",
                    CanonicalValue::Array(
                        capabilities.into_iter().map(CanonicalValue::String).collect(),
                    ),
                ),
                ("proposer", CanonicalValue::String(intent.proposer.clone())),
                (
                    "approvers",
                    CanonicalValue::Array(
                        approvers.into_iter().map(CanonicalValue::String).collect(),
                    ),
                ),
                ("previous_root", CanonicalValue::String(self.root()?)),
                ("time", CanonicalValue::UInt(next_time)),
            ]),
        )
    }

    fn evaluate_law(
        law: &ConstitutionalLaw,
        before: &BondAlgebraState,
        after: &BondAlgebraState,
        intent: &ReactionIntent,
    ) -> Result<(bool, String)> {
        match law.kind.as_str() {
            "identity_conservation" => Ok((
                before
                    .entity_types
                    .iter()
                    .all(|(key, value)| after.entity_types.get(key) == Some(value)),
                "entity identities must not disappear".into(),
            )),
            "history_conservation" => Ok((
                before.bonds.keys().all(|key| after.bonds.contains_key(key))
                    && before
                        .hyperbonds
                        .keys()
                        .all(|key| after.hyperbonds.contains_key(key)),
                "historical bond objects must remain addressable".into(),
            )),
            "authority_required" => Ok((
                !intent.authority.is_empty() && intent.authority != "UNSPECIFIED",
                "a committing authority is required".into(),
            )),
            "evidence_required_for_predicate" => {
                let predicate = law
                    .params
                    .get("predicate")
                    .and_then(serde_json::Value::as_str)
                    .ok_or_else(|| KernelError::Invalid("predicate law parameter required".into()))?;
                let missing = after.bonds.iter().any(|(bond_id, bond)| {
                    !before.bonds.contains_key(bond_id)
                        && bond.predicate == predicate
                        && bond.supporting_evidence.is_empty()
                });
                Ok((!missing, format!("{predicate} requires evidence")))
            }
            "root_changed" => Ok((
                before.root()? != after.root()?,
                "reaction must change state".into(),
            )),
            "no_model_self_approval" => Ok((
                !intent.approvers.contains(&intent.proposer),
                "model proposer may not approve its own reaction".into(),
            )),
            other => Err(KernelError::Invalid(format!("unknown law kind {other}"))),
        }
    }

    pub fn simulate(&self, intent: &ReactionIntent) -> Result<Simulation> {
        let current_root = self.root()?;
        if intent.expected_root != current_root {
            return Err(KernelError::StaleRoot {
                expected: intent.expected_root.clone(),
                actual: current_root,
            });
        }
        let definition = self
            .state
            .reactions
            .get(&intent.reaction_name)
            .ok_or_else(|| {
                KernelError::Invalid(format!("unknown reaction {}", intent.reaction_name))
            })?;
        let capabilities = intent.capabilities.iter().cloned().collect::<BTreeSet<_>>();
        let missing = definition
            .required_capabilities
            .iter()
            .filter(|capability| !capabilities.contains(*capability))
            .cloned()
            .collect::<Vec<_>>();
        if !missing.is_empty() {
            return Err(KernelError::Invalid(format!(
                "missing capabilities: {missing:?}"
            )));
        }
        let active_raw = self
            .state
            .algebra
            .bonds
            .values()
            .filter(|bond| bond.time.valid_until.is_none())
            .collect::<Vec<_>>();
        for template in &definition.required {
            if !active_raw
                .iter()
                .any(|bond| Self::template_matches(template, bond, &intent.bindings))
            {
                return Err(KernelError::Invalid(format!(
                    "required bond missing: {}",
                    template.predicate
                )));
            }
        }
        for template in &definition.forbidden {
            if active_raw
                .iter()
                .any(|bond| Self::template_matches(template, bond, &intent.bindings))
            {
                return Err(KernelError::Invalid(format!(
                    "forbidden bond present: {}",
                    template.predicate
                )));
            }
        }

        let next_time = self.state.logical_time + 1;
        let reaction_id = self.reaction_id(definition, intent, next_time)?;
        let mut after = self.state.clone();
        let mut terminated = Vec::new();
        for template in &definition.break_bonds {
            for (bond_id, bond) in Self::active_bond_items(&after.algebra, self.state.logical_time)? {
                if Self::template_matches(template, &bond, &intent.bindings) {
                    let successor = bond.terminate(next_time, reaction_id.clone())?;
                    Self::supersede_bond(&mut after.algebra, &bond_id, successor)?;
                    terminated.push(bond_id);
                }
            }
        }
        let mut formed = Vec::new();
        for template in &definition.form_bonds {
            let bond = Self::instantiate_bond(
                template,
                &intent.bindings,
                &intent.authority,
                next_time,
                &reaction_id,
            )?;
            let id = Self::add_bond_to(&mut after.algebra, bond, true)?;
            formed.push(id);
        }
        let hyperbond_id = if let Some(template) = &definition.form_hyperbond {
            let hyperbond = Self::instantiate_hyperbond(
                template,
                &intent.bindings,
                &intent.authority,
                next_time,
                formed
                    .iter()
                    .chain(terminated.iter())
                    .cloned()
                    .collect(),
            )?;
            Some(Self::add_hyperbond_to(&mut after.algebra, hyperbond)?)
        } else {
            None
        };

        let state_violations = Self::validate_algebra(&after.algebra, next_time)?;
        if !state_violations.is_empty() {
            return Err(KernelError::Invalid(state_violations.join("; ")));
        }

        let mut law_results = Vec::new();
        for law_name in &definition.laws {
            let law = self
                .state
                .laws
                .get(law_name)
                .ok_or_else(|| KernelError::Invalid(format!("unknown law {law_name}")))?;
            let (ok, message) = Self::evaluate_law(law, &self.state.algebra, &after.algebra, intent)?;
            law_results.push((law_name.clone(), ok, message.clone()));
            if !ok {
                return Err(KernelError::Invalid(format!(
                    "law {law_name} failed: {message}"
                )));
            }
        }

        let mut prior_reactions = self
            .state
            .proofs
            .values()
            .map(|proof| proof.reaction_id.clone())
            .collect::<Vec<_>>();
        prior_reactions.push(reaction_id.clone());
        prior_reactions.sort();
        let new_root = digest(
            "ADAM44:PHYSICS_ROOT",
            &CanonicalValue::map([
                ("time", CanonicalValue::UInt(next_time)),
                ("algebra", CanonicalValue::String(after.algebra.root()?)),
                (
                    "proofs",
                    CanonicalValue::Array(
                        prior_reactions
                            .into_iter()
                            .map(CanonicalValue::String)
                            .collect(),
                    ),
                ),
            ]),
        )?;
        let proof = ReactionProof {
            reaction_id,
            reaction_type_id: definition.id()?,
            previous_root: self.root()?,
            new_root,
            law_results,
            formed_bonds: formed,
            terminated_bonds: terminated,
            hyperbond_id,
            actor: intent.actor.clone(),
            authority: intent.authority.clone(),
            logical_time: next_time,
        };
        Ok(Simulation { state: after, proof })
    }

    pub fn commit(&mut self, intent: &ReactionIntent) -> Result<ReactionProof> {
        if self.committing {
            return Err(KernelError::Invalid("nested commit denied".into()));
        }
        self.committing = true;
        let result = (|| {
            let simulation = self.simulate(intent)?;
            let mut next_state = simulation.state;
            next_state.logical_time = simulation.proof.logical_time;
            let proof_id = simulation.proof.id()?;
            next_state
                .proofs
                .insert(proof_id, simulation.proof.clone());
            let mut affected = BTreeSet::new();
            for bond_id in simulation
                .proof
                .formed_bonds
                .iter()
                .chain(simulation.proof.terminated_bonds.iter())
            {
                if let Some(bond) = next_state.algebra.bonds.get(bond_id) {
                    affected.insert(bond.source.clone());
                    affected.insert(bond.target.clone());
                }
            }
            if let Some(hyperbond_id) = &simulation.proof.hyperbond_id {
                if let Some(hyperbond) = next_state.algebra.hyperbonds.get(hyperbond_id) {
                    affected.extend(
                        hyperbond
                            .roles
                            .iter()
                            .map(|role| role.participant.clone()),
                    );
                }
            }
            for entity_id in affected {
                if let Some(worldline) = next_state.worldlines.get_mut(&entity_id) {
                    worldline.append(
                        simulation.proof.logical_time,
                        simulation.proof.new_root.clone(),
                        simulation.proof.reaction_id.clone(),
                    )?;
                }
            }
            self.state = next_state;
            let committed_root = self.root()?;
            if committed_root != simulation.proof.new_root {
                return Err(KernelError::Integrity {
                    sequence: simulation.proof.logical_time,
                    reason: format!(
                        "committed root {committed_root} differs from proof root {}",
                        simulation.proof.new_root
                    ),
                });
            }
            self.validate_state()?;
            Ok(simulation.proof)
        })();
        self.committing = false;
        result
    }

    pub fn state_at(&self, logical_time: u64) -> Result<Vec<FirstClassBond>> {
        if logical_time > self.state.logical_time {
            return Err(KernelError::Invalid("invalid logical time".into()));
        }
        Ok(Self::active_bond_items(&self.state.algebra, logical_time)?
            .into_iter()
            .map(|(_, bond)| bond)
            .collect())
    }

    pub fn branch(&self) -> Self {
        Self {
            state: self.state.clone(),
            committing: false,
        }
    }
}

pub fn build_equipment_physics() -> Result<AtomicPhysicsKernel> {
    use serde_json::json;
    let mut kernel = AtomicPhysicsKernel::new();
    for (entity_id, entity_type) in [
        ("SHAWN", "PERSON"),
        ("SUPERVISOR", "PERSON"),
        ("EX12", "EQUIPMENT"),
        ("YARD", "LOCATION"),
        ("P204", "PROJECT"),
        ("WO88", "WORK_ORDER"),
        ("EVIDENCE1", "EVIDENCE"),
    ] {
        kernel.declare_entity(entity_id, entity_type)?;
    }
    kernel.register_constraint(ValenceConstraint {
        predicate: "ASSIGNED_TO".into(),
        source_types: vec!["EQUIPMENT".into()],
        target_types: vec!["PROJECT".into()],
        minimum: 0,
        maximum: Some(1),
        families: vec![BondFamily::Operational],
        require_evidence: true,
        require_authority: true,
    })?;
    kernel.register_constraint(ValenceConstraint {
        predicate: "AVAILABLE_AT".into(),
        source_types: vec!["EQUIPMENT".into()],
        target_types: vec!["LOCATION".into()],
        minimum: 0,
        maximum: Some(1),
        families: vec![BondFamily::Operational],
        require_evidence: true,
        require_authority: true,
    })?;
    kernel.seed_bond(FirstClassBond {
        source: "EX12".into(),
        predicate: "AVAILABLE_AT".into(),
        target: "YARD".into(),
        family: BondFamily::Operational,
        direction: "forward".into(),
        order: None,
        time: TimeScope::default(),
        causal_parents: Vec::new(),
        authority: "OPS".into(),
        provenance: Vec::new(),
        confidence: 1.0,
        confidence_class: ConfidenceClass::Authoritative,
        security_scope: "PUBLIC".into(),
        chemistry_version: "v44.1".into(),
        reaction_origin: None,
        supporting_evidence: vec!["EVIDENCE1".into()],
        metadata: BTreeMap::new(),
    })?;
    for law in [
        ConstitutionalLaw { name: "identity".into(), kind: "identity_conservation".into(), params: BTreeMap::new() },
        ConstitutionalLaw { name: "history".into(), kind: "history_conservation".into(), params: BTreeMap::new() },
        ConstitutionalLaw { name: "authority".into(), kind: "authority_required".into(), params: BTreeMap::new() },
        ConstitutionalLaw { name: "changed".into(), kind: "root_changed".into(), params: BTreeMap::new() },
        ConstitutionalLaw { name: "independent".into(), kind: "no_model_self_approval".into(), params: BTreeMap::new() },
        ConstitutionalLaw { name: "assignment_evidence".into(), kind: "evidence_required_for_predicate".into(), params: BTreeMap::from([("predicate".into(), json!("ASSIGNED_TO"))]) },
        ConstitutionalLaw { name: "availability_evidence".into(), kind: "evidence_required_for_predicate".into(), params: BTreeMap::from([("predicate".into(), json!("AVAILABLE_AT"))]) },
    ] {
        kernel.register_law(law)?;
    }
    let common = vec![
        "identity".into(),
        "history".into(),
        "authority".into(),
        "changed".into(),
        "independent".into(),
    ];
    let operational_template = |source: &str, predicate: &str, target: &str, evidence: Option<&str>| BondTemplate {
        source: source.into(),
        predicate: predicate.into(),
        target: target.into(),
        family: BondFamily::Operational,
        security_scope: "PUBLIC".into(),
        require_evidence_var: evidence.map(str::to_owned),
    };
    let mut assign_laws = common.clone();
    assign_laws.push("assignment_evidence".into());
    kernel.register_reaction(ReactionDefinition {
        name: "ASSIGN_EQUIPMENT".into(),
        required: vec![operational_template("$equipment", "AVAILABLE_AT", "$location", None)],
        forbidden: Vec::new(),
        break_bonds: vec![operational_template("$equipment", "AVAILABLE_AT", "$location", None)],
        form_bonds: vec![operational_template("$equipment", "ASSIGNED_TO", "$project", Some("evidence"))],
        form_hyperbond: Some(HyperBondTemplate {
            event_type: "ASSIGNMENT_EVENT".into(),
            roles: vec![
                ("ACTOR".into(), "$actor".into()),
                ("EQUIPMENT".into(), "$equipment".into()),
                ("DESTINATION".into(), "$project".into()),
                ("AUTHORITY".into(), "$work_order".into()),
                ("APPROVER".into(), "$approver".into()),
            ],
            security_scope: "PUBLIC".into(),
        }),
        required_capabilities: vec!["ASSIGN_EQUIPMENT".into()],
        laws: assign_laws,
        version: 1,
    })?;
    let mut release_laws = common;
    release_laws.push("availability_evidence".into());
    kernel.register_reaction(ReactionDefinition {
        name: "RELEASE_EQUIPMENT".into(),
        required: vec![operational_template("$equipment", "ASSIGNED_TO", "$project", None)],
        forbidden: Vec::new(),
        break_bonds: vec![operational_template("$equipment", "ASSIGNED_TO", "$project", None)],
        form_bonds: vec![operational_template("$equipment", "AVAILABLE_AT", "$location", Some("evidence"))],
        form_hyperbond: Some(HyperBondTemplate {
            event_type: "RELEASE_EVENT".into(),
            roles: vec![
                ("ACTOR".into(), "$actor".into()),
                ("EQUIPMENT".into(), "$equipment".into()),
                ("SOURCE".into(), "$project".into()),
                ("DESTINATION".into(), "$location".into()),
                ("AUTHORITY".into(), "$work_order".into()),
            ],
            security_scope: "PUBLIC".into(),
        }),
        required_capabilities: vec!["RELEASE_EQUIPMENT".into()],
        laws: release_laws,
        version: 1,
    })?;
    Ok(kernel)
}

pub fn assignment_intent(kernel: &AtomicPhysicsKernel) -> Result<ReactionIntent> {
    Ok(ReactionIntent {
        reaction_name: "ASSIGN_EQUIPMENT".into(),
        bindings: BTreeMap::from([
            ("equipment".into(), "EX12".into()),
            ("location".into(), "YARD".into()),
            ("project".into(), "P204".into()),
            ("actor".into(), "SHAWN".into()),
            ("work_order".into(), "WO88".into()),
            ("approver".into(), "SUPERVISOR".into()),
            ("evidence".into(), "EVIDENCE1".into()),
        ]),
        actor: "SHAWN".into(),
        authority: "OPS".into(),
        capabilities: vec!["ASSIGN_EQUIPMENT".into()],
        expected_root: kernel.root()?,
        proposer: "PLANNER".into(),
        approvers: vec!["SUPERVISOR".into()],
    })
}

pub fn release_intent(kernel: &AtomicPhysicsKernel) -> Result<ReactionIntent> {
    Ok(ReactionIntent {
        reaction_name: "RELEASE_EQUIPMENT".into(),
        bindings: BTreeMap::from([
            ("equipment".into(), "EX12".into()),
            ("location".into(), "YARD".into()),
            ("project".into(), "P204".into()),
            ("actor".into(), "SHAWN".into()),
            ("work_order".into(), "WO88".into()),
            ("evidence".into(), "EVIDENCE1".into()),
        ]),
        actor: "SHAWN".into(),
        authority: "OPS".into(),
        capabilities: vec!["RELEASE_EQUIPMENT".into()],
        expected_root: kernel.root()?,
        proposer: "PLANNER".into(),
        approvers: vec!["SUPERVISOR".into()],
    })
}
