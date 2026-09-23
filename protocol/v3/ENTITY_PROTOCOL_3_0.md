# ENTITY Protocol 3.0 — Release

Status: RELEASED / BTG INTERNAL QUALIFIED

ENTITY 3.0.0 extends the qualified earlier protocol line without rewriting its historical evidence. The v3 line defines a Universal Sovereign Transaction Fabric for persistent identity, delegated authority, machine-readable rights, signed events, economic value, provenance, resolution, and portable verification.

## 1. Compatibility rule

The earlier qualified protocol and evidence remain immutable historical baselines. A v3 implementation MUST NOT silently rewrite, relabel, or invalidate earlier qualification evidence. Migration into v3 MUST be explicit and independently verifiable.

## 2. Universal primitives

Every normative v3 transaction is composed from five primitives:

1. `ENTITY` — what the subject or object is.
2. `AUTHORITY` — who may act, for whom, and within what scope.
3. `RIGHT` — what may be done to or with an object.
4. `EVENT` — what action or observation occurred.
5. `VALUE` — what economic consequence or asserted value state exists.

An implementation MAY add domain-specific object types, but MUST preserve these primitive semantics.

## 3. Sovereignty invariants

Infrastructure possession MUST NOT imply sovereign authority.
Custody MUST NOT imply ownership.
Storage control MUST NOT imply licensing authority.
Data access MUST NOT imply ownership or redistribution rights.
Provenance MUST NOT be represented as truth, ownership, or legal entitlement by itself.
An attestation MUST be represented as evidence, not as automatically verified truth.
A resolution service MUST NOT become the source of sovereign authority merely by resolving an identifier.

## 4. Digital commodity semantics

A digital commodity is an ENTITY object whose descriptor identifies it as economically usable digital material. Registration establishes identity and provenance anchors; it MUST NOT by itself establish market value, ownership beyond the asserted controller relationship, or permission for third-party use.

Licensing is expressed through signed `RIGHT` records. Rights MAY include permitted actions, purposes, jurisdictions, expiry, and machine-readable economic terms. Metered use MAY generate a settlement obligation. A settlement obligation is not proof that external money moved.

## 5. Delegated machine authority

AI agents, applications, services, and devices MAY act as ENTITY actors. An actor acting for another principal MUST possess an applicable unrevoked `AUTHORITY` grant. Asset access or execution MUST also satisfy the applicable `RIGHT`. Possessing one MUST NOT silently create the other.

Authority and right evaluation MUST fail closed when required scope, purpose, jurisdiction, validity period, or signature evidence is absent.

## 6. Causal provenance

Derived objects MAY reference parent objects through signed provenance edges. Contribution weights are expressed in basis points and incoming declared weights MUST NOT exceed 10,000 basis points for a child object.

The normative v3 graph is acyclic. Deterministic value-distribution calculations MAY propagate contribution weights to root objects, but such calculations represent the declared attribution model and MUST NOT be described as an objective measurement of creative, legal, or economic contribution.

## 7. Trust fabric

Trust policies MAY require a minimum number of distinct valid attestations and MAY restrict or require specified attestors. Satisfying a trust policy means only that the policy's evidence threshold was met. It MUST NOT be represented as proof that the underlying claim is true.

## 8. Settlement and value

v3 usage events MAY open obligations in a settlement engine. Internal accounting settlement and externally verified payment are distinct states. Implementations MUST NOT claim external monetary realization from internal ledger entries alone.

`VALUE` records MUST state their basis and state. An asserted value is not automatically market value. Derived-value distributions MUST be deterministic for the same graph, weights, amount, and rounding rules.

## 9. Resolution

ENTITY resolution binds an ENTITY object to signed service endpoints. Resolvers are replaceable infrastructure. A resolver MUST verify the controller signature and MUST NOT substitute its own authority for the object's controller.

## 10. Sovereign bundle

A v3 sovereign bundle contains the root object, its included ancestry, applicable signed primitive records, and the signed public identity manifests needed to validate those records. The semantic hash covers the portable state other than the export timestamp.

An independent verifier with no pre-existing copy of the originating identity vault MUST be able to validate the included signatures from the embedded public manifests. Private signing or recovery keys MUST NOT be included.

## 11. Current development scope

The current v3 reference implementation includes digital commodity objects, delegated AI authority, machine-readable rights, replay-protected use events, metered obligations, a settlement bridge, causal provenance, deterministic root attribution, physical/digital objects, signed attestations, trust-policy thresholds, signed resolution records, and self-verifying sovereign bundles.

This draft does not claim v3 interoperability, external qualification, production deployment, legal title determination, market valuation, or external payment verification. Those claims require separate evidence campaigns.
