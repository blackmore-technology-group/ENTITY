# Changelog

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
