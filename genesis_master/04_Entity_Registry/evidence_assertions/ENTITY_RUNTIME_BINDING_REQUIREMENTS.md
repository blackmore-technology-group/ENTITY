# Canonical Runtime Binding — evidence_assertion
Authority: `evidence_assertion`
Canonical owner: `04_Entity_Registry\evidence_assertions`
Source: SERS-ENTITY-002 §125

- Every material assertion SHALL be capable of carrying an Evidence Assertion Envelope.
- The envelope SHALL preserve claim, claimant, evidence origin, references, confidence, verification level, timestamps, signatures, jurisdiction, dispute state, supersession and schema/version.
- Observed, asserted, inferred, counterparty-attested, externally verified and unknown SHALL remain semantically distinct.
- UNKNOWN SHALL never be silently promoted to VERIFIED.
- DERIVED_INFERENCE SHALL require qualifying evidence before strong verification.
- UI/API labels SHALL never overstate the evidence level.
- Hidden provider reasoning and unexposed provider events SHALL remain outside the Evidence Boundary.

## READY Gate
- Tests cover unknown/inference fail-closed behavior, valid evidence transition, supersession and conservative labels.
- READY binding pins current `04_Entity_Registry\ENTITY_REQUIREMENTS.md` SHA-256 and qualification evidence.
