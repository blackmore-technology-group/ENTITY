# ENTITY Repository Requirements Traceability
Authoritative source: SERS-ENTITY-001 — Target Architecture v1.0
Repository: <LOCAL_DRIVE>/Sovereign_Entity_Network

## Current Canonical State ? 2026-09-17
- Current authority baseline: `SERS-ENTITY-003 v2.2`; authoritative source mirror is hash verified.
- Current Master RTM: 1,997/1,997 internally QUALIFIED; full internal requirements closed; master source mirrored.
- Current release gate: 33/34 overall and 33/33 internal; full external release remains BLOCKED only by `sovereign_domain_external`.
- `CANONICAL_STATE_CURRENT.json` is the machine-readable current-state pointer. Older qualification/preflight artifacts remain historical evidence and do not override CURRENT artifacts.
- ENTITY Protocol 1.0 is frozen for external conformance; the freeze is not an external-interoperability PASS claim.

## Workstream Boundary
`10_NIKI` is intentionally excluded from this requirements-population workstream because a separate active build is populating that directory. No requirement file from this pass is placed under `10_NIKI`.

## Repository Ownership Map
- `00_Governance` — mission, trust/evidence model, legal policy, architecture guardrails.
- `01_Core_Runtime` — identity, authorization, APIs, state/version/runtime invariants.
- `02_Peer_Network` — federation, consistency, witnesses, reconciliation, BECP peer boundary.
- `03_Public_Internet_Bridge` — external export, publication, terms intelligence, public gateway.
- `04_Entity_Registry` — domain objects, relationship identity, Rights & Claims Graph.
- `05_Entity_Nodes` — node authority, device binding, offline/recovery behavior.
- `06_Hosted_Sites` / `07_Hosted_Apps` — governed publication, permissions, provenance and package rights.
- `08_Data_Vaults` — encrypted content, source enrollment, classification, erasure/deletion.
- `09_Spatial_AR_Dashboard` — BSIE/ENTITY projection and spatial evidence handling.
- `11_ADAM` — explicit agent capabilities, approval gates, governed execution.
- `12_BSIE` — authoritative world/relationship state integration boundary.
- `13_Security` — cryptography, key protection, authentication, threat model, AI exfiltration defence.
- `14_Protocols_SDK` — open standards, schemas, SDK contracts, C2PA and crypto agility.
- `15_Operations` — backup/restore, observability, migration, availability.
- `16_Test_Qualification` — unit, invariant, adversarial, E2E, recovery, privacy and performance qualification.
- `17_Release` — security/economic/provenance gates and signed release evidence.
- `18_Research_Design` / `19_Sandbox` — experimental work separated from production authority.
- `20_Archive` — historical verification, retention, retirement and migration evidence.
- `21_Corporate_Capital` — SERS-ENTITY-003 digital-commodity economics, corporate-capital evidence, externally attested cap-table state, valuation separation and investor-evidence controls.

## Global Invariant
ENTITY may discover, prove, protect, license and realize value from lawful digital rights, but no subsystem may manufacture certainty, ownership, consent, privacy, usage or monetary value unsupported by evidence.
## Detailed Subsystem Population Pass — 2026-09-14
- 133 existing non-NIKI subsystem directories now contain `ENTITY_SUBSYSTEM_REQUIREMENTS.md`.
- `10_NIKI` remained excluded and protected from this workstream.
- The Sept. 14 population pass originated under the earlier SERS-ENTITY-001 workstream. Current qualification and release claims are governed by SERS-ENTITY-003 v2.2; historical generated requirements remain preserved as traceability inputs and are not silently rewritten.
- Cross-chat compatibility is governed by `CROSS_CHAT_IMPLEMENTATION_COMPATIBILITY.md`.
- Compatibility-sensitive requirements explicitly preserve C2PA provenance/trust/truth separation, source enrollment, revocation-aware federation, signed downgrade protection and historical evidence assurance.
- Public_Peer/pre-bootstrap evidence is required to retain its original historical assurance and idempotent adoption semantics.
- Security peer trust is required to evaluate live credentials, issuer policy, trust level, revocation and negotiated protocol/capabilities.
- No generated requirement treats implementation presence as production qualification; release evidence remains mandatory.

## Canonical Runtime Handoff Pass — 2026-09-14
- Aligned to active NIKI adapter/fallback architecture without modifying `10_NIKI`.
- Added `CANONICAL_AUTHORITY_HANDOFF_REQUIREMENTS.md` at repository root.
- Added per-authority `ENTITY_RUNTIME_BINDING_REQUIREMENTS.md` to declared canonical owner directories.
- Core bootstrap authorities covered: `identity`, `policy_consent`, `core_permissions`, `service_api`.
- Additional handoffs cover contracts, settlement, pools/spaces, peer networking, BECP, public publishing, registry, vaults, AR, ADAM, BSIE, key/recovery, C2PA, conformance, portable state and pre-bootstrap evidence.
- No `ENTITY_RUNTIME_BINDING.json` was created by this pass.
- READY remains evidence-gated and must pin the current owner `ENTITY_REQUIREMENTS.md` SHA-256.
- NIKI remains reasoning/integration; canonical sovereign state remains outside `10_NIKI`.

## SERS-ENTITY-003 Corporate-Capital Implementation Pass — 2026-09-15
- Added canonical `21_Corporate_Capital` authority without modifying `10_NIKI`.
- Implemented Digital Commodity registration and usage/economic attribution with replay protection.
- Implemented externally attested share-class and shareholder-register snapshots with reconciliation invariants.
- Implemented modelled-valuation versus external-market-observation separation and disclosure snapshots.
- Qualified declared scope `CORPORATE_CAPITAL_EVIDENCE_AND_ANALYTICS`: 5/5 tests PASS.
- Regulated securities execution remains disabled and excluded from READY scope until separately authorized and qualified.
