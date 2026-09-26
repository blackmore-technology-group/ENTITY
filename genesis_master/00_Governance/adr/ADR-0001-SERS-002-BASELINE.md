# ADR-0001 — Adopt SERS-ENTITY-002 as Authoritative Baseline

Status: ACCEPTED
Baseline: SERS-ENTITY-002
Effective version: ENTITY engineering baseline v2.0

## Problem statement
Repository requirement mappings still referenced SERS-ENTITY-001 while the complete master design is SERS-ENTITY-002.

## Current baseline behavior
SERS-ENTITY-001 Sections 1–120 remain preserved architecture lineage. Repository controls did not yet formally bind Sections 121–150 assurance requirements.

## Proposed behavior
Adopt SERS-ENTITY-002 Sections 1–150 as the authoritative target engineering requirement. Preserve SERS-001 semantics as lineage; no signed historical record is reinterpreted silently.

## Impact assessment
- Security impact: strengthens evidence-gated release controls.
- Privacy impact: adds minimum-disclosure and leakage assurance gates.
- Rights/legal-model impact: preserves existing rights semantics and adds formal ontology/verification controls.
- Economic impact: adds accounting assurance and realized-value evidence gates.
- Interoperability impact: adds executable conformance and independent validation requirements.
- Migration impact: repository mappings and RTM move to SERS-002 lineage.
- Backward-compatibility impact: no historical signed state is rewritten.

## Rejected alternatives
- Keep SERS-001 as active baseline: rejected because it omits Sections 121–150 assurance requirements.
- Treat the 10/10 plan as non-normative guidance: rejected because v2.0 explicitly makes it normative.

## Approval and implementation
- Approver(s): repository owner / authorized BTG engineering authority
- Implementation references: `00_Governance/SERS_002_BASELINE.json`, `16_Test_Qualification/traceability/build_rtm.py`
- Verification evidence: baseline hash pin and generated RTM/evidence reports
- Superseded ADRs: none
