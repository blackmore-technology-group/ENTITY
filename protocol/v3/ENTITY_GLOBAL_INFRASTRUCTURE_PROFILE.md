# ENTITY Global Infrastructure Profile Set

Status: ENTITY v3.1.0 RELEASED / BTG INTERNALLY QUALIFIED / EXTERNAL INDEPENDENT QUALIFICATION PENDING

## Purpose

This profile set addresses five infrastructure-scale pressures without expanding ENTITY Core: jurisdictional diversity, semantic/ontology diversity, governance legitimacy, privacy-versus-provenance, and distributed topology/cryptographic migration.

ENTITY Core remains the five primitives `ENTITY`, `AUTHORITY`, `RIGHT`, `EVENT`, `VALUE` plus canonical verification, state transition, recovery and versioning semantics. The mechanisms below are independently versioned profiles layered above Core.

## 1. Jurisdiction profile framework

Jurisdiction profiles are immutable, signed, effective-dated overlays scoped by jurisdiction and domain. They carry machine-readable ALLOW, REQUIRE and PROHIBIT rules, conditions, obligations and authority-basis references.

Multiple applicable jurisdictions are evaluated together. A prohibition wins over an allowance; conflicting rules are surfaced explicitly and fail closed. A jurisdiction profile is policy evidence only and does not cause ENTITY to determine legal title, statutory interpretation or legal compliance.

Profiles may supersede earlier versions without deleting history. Supersession is signed and restricted to the same jurisdiction/domain lineage.

## 2. Semantic and ontology registries

ENTITY now provides registries for `SCHEMA`, `RIGHT`, `EVENT`, `CAPABILITY`, `ASSET_CLASS`, `TRUST_FRAMEWORK`, `DISPUTE_AUTHORITY`, and `ATTESTATION_CLASS` terms.

Each namespace has an ENTITY owner and governance reference. Term versions are immutable. Cross-system mappings are explicit signed crosswalks with `EXACT`, `BROADER`, `NARROWER`, `RELATED`, or `INCOMPATIBLE` relationships, evidence hashes, jurisdiction scopes and confidence values.
Crosswalks never silently rewrite semantics. Even a 100% `EXACT` mapping is an attestation by a mapping actor, not proof that two institutions or jurisdictions are legally identical. Automatic translation remains disabled unless a higher-level profile explicitly authorizes it.

## 3. Multi-stakeholder standards governance

The global-governance profile supplements the existing signed RFC mechanism with stakeholder-class diversity. Governance bodies define a charter hash, allowed stakeholder classes, an approval threshold and a minimum number of distinct classes required for adoption.

Members vote with signed ballots. Conflict-of-interest declarations may require recusal. A proposal cannot be adopted merely because one implementation owner supplies enough votes from one stakeholder class when the body's diversity threshold requires broader participation.

This mechanism does not make BTG-created governance automatically legitimate. It provides the protocol machinery through which governments, universities, vendors, civil-society bodies, operators and other independent organizations can participate in standards governance.

## 4. Privacy, provenance and protected proof

Purpose-bound access grants constrain a grantee by resource, purpose, action, expiry and optional maximum-use count. Grants are controller-signed, revocable, and consumed atomically.

Selective-retention records keep evidence commitments while allowing controlled destruction or redaction of underlying payload custody after the applicable retention period. Legal-hold records fail closed against destruction.

Confidential provenance records preserve parent/child causal commitments while sensitive metadata may be AES-GCM encrypted. The public provenance surface stores the metadata commitment rather than exposing the confidential metadata itself.

A fail-closed proof-verifier registry supports external zero-knowledge/privacy proof systems. A proof suite records the governed verifier hash and security claim; a runtime verifier must match that hash before proofs can be evaluated. Registering a proof suite does not certify its cryptographic security.

## 5. Distributed topology and partition semantics

Topology nodes are signed infrastructure descriptors classified as `CORE`, `REGIONAL`, `EDGE`, `SATELLITE`, or `OFFLINE`. Membership in the topology never creates sovereign authority.
Partition synchronization uses signed causal checkpoints with monotonically increasing per-node sequences, state roots, previous-checkpoint hashes and vector clocks. Equal state roots converge. A causally dominant checkpoint may advance the partition. Concurrent divergent states fail closed and create conflict evidence; automatic last-writer-wins is prohibited.

Offline envelopes are signed, sequence-bearing, expiry-bounded payload packages. Verification checks payload integrity, expiry and ENTITY signature. An offline envelope is evidence for later synchronization and is not automatic authority to overwrite connected state.

## 6. Cryptographic agility and migration

Cryptographic suites are immutable governed records with algorithm, security strength, verifier hash, activation, deprecation and retirement times. Runtime verifier implementations must match the governed verifier hash.

Migration policies define an old suite, a successor suite, a dual-sign transition start and an old-suite retirement time. Before transition the old suite is required; during transition both suites are required; after retirement only the successor is accepted. A missing successor signature during or after migration is a downgrade and fails closed.

This profile is algorithm-agility infrastructure. It does not itself claim that a registered algorithm is secure, post-quantum safe or externally certified.

## 7. Core stability doctrine

Global diversity belongs primarily in profiles, ontologies and deployment policy. ENTITY Core SHOULD change rarely. Jurisdictional interpretation, industry terminology, privacy regimes, trust frameworks and institutional governance SHOULD NOT be hard-coded into the five-primitives Core when they can be expressed as versioned profile semantics.

## 8. Current implementation

Reference development modules:

- `src/35_Global_Infrastructure/institutional_semantics.py`
- `src/35_Global_Infrastructure/privacy_provenance.py`
- `src/35_Global_Infrastructure/topology_crypto.py`

Direct qualification tests:

- `tests/test_v3_global_infrastructure.py`

The current test campaign exercises jurisdiction conflict, immutable semantics, ontology crosswalk ambiguity, stakeholder diversity/recusal, purpose-limited use, retention destruction, confidential provenance, proof-verifier fail-closed behavior, partition convergence/conflict, offline tamper detection and cryptographic downgrade resistance.
