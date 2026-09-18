# ENTITY Protocols / SDK Requirements
Source: SERS-ENTITY-003 Complete Master Engineering Design v2.2
Status: Authoritative repository requirement mapping

## Standards
- Protocols SHOULD interoperate with W3C DID Core, Verifiable Credentials 2.x, W3C ODRL, C2PA, standard SBOM formats, standard cryptographic identifiers and secure transport protocols.
- Current qualified standards scope SHALL use DID Core 1.0 data-model semantics, VC Data Model 2.0 Recommendation semantics, ODRL 2.2 semantics, and real C2PA validation tooling.
- BTG-specific extensions SHALL be documented, namespaced and versioned.
- ENTITY signature records SHALL NOT be represented as W3C Data Integrity proofs unless a separately qualified cryptosuite implementation establishes conformance.
- External standards documents SHALL remain UNVERIFIED_EXTERNAL_STATE until the applicable verification evidence is established.

## Schemas and APIs
- Durable signed records SHALL identify schema/version and cryptographic suite.
- Breaking changes SHALL not silently reinterpret historical signed events.
- SDKs SHALL expose explicit scopes/capabilities rather than ambient authority.
- Network mutations SHOULD support idempotency and replay protection.
- Errors SHALL distinguish authentication, authorization, policy denial, invalid transition, signature failure, conflict, duplicate/replay, dependency unavailable and unverified external state.

## Interoperability
- Reference clients SHALL independently verify supported identifiers, signatures, schema semantics and policy-relevant objects without relying on NIKI state.
- Generate -> export -> independently validate -> import -> semantic-equivalence tests SHALL exist for each declared interoperable data model.
- C2PA support SHALL distinguish provenance validity, signer trust, factual truth and ownership.
- Standards validity SHALL NOT manufacture legal ownership, factual truth, consent, authorization or market value.
- Crypto interfaces SHOULD permit future hybrid/post-quantum signatures, including planned ML-DSA support, without changing sovereign identity.
