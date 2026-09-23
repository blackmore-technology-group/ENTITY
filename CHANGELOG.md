# Changelog

## 3.0.0 - 2026-09-23

BTG internally qualified release of the ENTITY v3 sovereign state and data-rights market architecture.

### Added
- Five-primitives Universal Transaction Fabric: ENTITY, AUTHORITY, RIGHT, EVENT, VALUE.
- Versioned profile architecture with schema immutability, negotiation, dispute, privacy, recovery, federated resolution, AI attenuation, physical binding and legacy bridges.
- ENTITY Exchange Protocol (EEP) for trading rights in data with signed non-custodial issuer/participant actions, price/time matching, RFQ, call auction reference support, payment attestations, entitlements, usage metering, market data and baseline surveillance.
- ENTITY Originator Participation Profile (EOPP) for issuer-defined reserves, primary/secondary/derivative/service participation without protocol tax or mandatory cryptocurrency.
- Market State Recovery Profile (MSRP) for controller-attested provider-independent EEP/EOPP logical-state recovery.
- EEP JSON Schema plus sealed valid/invalid conformance vectors.

### Qualification
- 90/90 complete v3 regression tests passed before release promotion.
- Concurrent sell admission, matching and settlement atomicity qualified.
- Execution-time revenue distribution binding prevents post-trade rule rewriting.
- Destructive market recovery and rehashed-tamper attacks pass fail-closed tests.
- Bounded release-load gate: 500 fully settled trades across reference and qualification-mirror EEP implementations.

### Claim boundary
- This release is BTG internally qualified. Independent unrelated-party v3 reimplementation and live cross-language interoperability remain pending.
- Protocol evidence does not itself establish legal title, regulatory classification, market value, or absolute external-payment truth.


## 2.0.0-alpha1 - 2026-09-18

- Added the full ADAM v1.0 integration development line.
- Added bounded NIKI structural causal models, hard interventions, counterfactual reasoning and adaptive cognition routing.
- Causal model persistence requires explicit ENTITY approval; NIKI remains non-authoritative and ADAM remains the governed executor.
- Corrected ENTITY_ONLY portable export closure so typed references do not recursively traverse unrelated foreign Entity identities.
- Added alias-aware portable export regression coverage.
- Preserved ENTITY Protocol 1.0 as frozen and immutable in meaning.
- Added the `EntityFullAdamRuntime` bridge for ENTITY-authorized ADAM exact evidence, evidence alignment and reaction-governed transition history.
- Added the NIKI/ADAM v2 execution coordinator while preserving `execution_authority = ENTITY`, `executor = ADAM`, and non-authoritative NIKI reasoning.
- Added an explicit ADAM RC2 package pin and verification tool.
- Added the 2.0 development architecture and development release manifest.
- External ADAM certification gates and independent ENTITY interoperability remain separate open evidence gates.

## 1.0.0-rc2.2 - 2026-09-17

Repository-wide Unicode/UTF-8 repair release.

### Fixed
- Repaired 219 mojibake sequences across 61 tracked public files.
- Corrected malformed box-drawing characters, dashes, arrows, quotes, and related UTF-8 text.
- Added the published `08_Data_Vaults` directory to the README repository layout.
- Added a CI repository-safety gate that rejects invalid UTF-8, Unicode replacement characters, and reconstructable Windows-1252/UTF-8 mojibake.

### Compatibility
- No ENTITY Protocol 1.0 semantic change.
- No SERS-ENTITY-003 v2.2 requirement change.
- No Sovereign Domain profile semantic change.
- `v1.0.0-rc2.1` remains immutable release history; RC2.2 supersedes it for public checkout/use.

## 1.0.0-rc2.1 - 2026-09-17

Public packaging correction for the first RC2 release candidate.

### Fixed
- Corrected security ignore rules that unintentionally excluded legitimate source directories named `backups`, `recovery`, `credentials`, and `logs`.
- Published `canonical_portable_state.py`, credential authority source, sovereign-domain recovery source, operations requirement files, and the public principal-binding JSON schema.
- Added explicit CI guards against committing live principal/device binding JSON and credential/secret JSON files.
- Added clean-clone validation so published Git content, rather than the developer working tree, is what gets tested.

### Compatibility
- No ENTITY Protocol 1.0 wire-semantic change.
- No SERS-ENTITY-003 v2.2 requirement change.
- No Sovereign Domain profile semantic change.
- `v1.0.0-rc2` remains an immutable historical pre-release tag; RC2.1 supersedes it for public checkout/use.

## 1.0.0-rc2 - 2026-09-17

First public RC2 repository package.

### Published
- ENTITY Protocol 1.0 freeze metadata and governance.
- SERS-ENTITY-003 v2.2 controlling engineering baseline.
- SERS-ENTITY-DOMAIN-001 v1.0 sovereign-domain requirements.
- Canonical identity, policy/permissions, registry, provenance, rights, event-ledger, portability, and sovereign-domain reference source.
- Open SDK v1/v1.1, principal binding, Simple SDK, platform SDK requirements, reference clients, and schemas.
- Public release-signer verification material.

### Security/public-boundary changes
- Production state and mutable SQLite databases excluded.
- Private keys, operational bindings, recovery material, backups, and generated binaries excluded.
- BTG-machine absolute paths removed from published runtime defaults.
- Public SDK paths adapted to the repository's `src/` + `sdk/` layout.

### Qualification
- Internal RC2 qualification evidence exists for the reference implementation scope.
- Independent external interoperability and sovereign-domain external qualification remain pending.
