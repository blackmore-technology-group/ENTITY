# ADAM v1.0 — Complete Bounded Software Reference (RC2 Hardened)

**Version:** `1.0.0-rc2`  
**Software status:** complete bounded implementation and executable production-reference controls  
**Certification status:** external production certification required

This release incorporates the full rc2 authority-trust and qualification-integrity hardening pass. It supersedes the v1.0-rc1 candidate and preserves the rc1 audit under `lineage/v1_rc1_audit/`.

## Implemented software boundary

- Deterministic atoms, compounds, bonds, hyperbonds and content-addressed identities
- Reaction-only authoritative state change and proof-carrying worldlines
- Exact finite-byte recreation and bounded semantic chemistry
- Neural-symbolic organs, applications, governed training and device capability contracts
- Encrypted software custody reference and purpose-separated authority keys
- Restart-safe persistent local custody and release/controller identities
- Durable commit-phase quorum certificates and epoch-bound membership
- Cryptographically approved membership changes
- Trusted release-signing roots for frozen candidates
- Signed wall-clock qualification state with independent witness registries
- Trusted assessor enrollment and pinned assessor keys
- Source, manifest, dependency, wheel and clean-room qualification tooling

## Qualification commands

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\RUN_ADAM_V1_RC2_QUALIFICATION.ps1 -InstallDependencies -Full
```

Linux/macOS reference qualification:

```bash
./RUN_ADAM_V1_RC2_QUALIFICATION.sh
```

The launchers verify the signed internal release manifest before importing ADAM source.

## Honest production boundary

The software reference cannot itself manufacture external evidence. Production certification still requires real HSM/KMS custody, physically independent hosts, certified devices, licensed real-world training, thirty actual elapsed days, and a trusted independent assessor report. These gates are enforced in software and remain blocked until typed, independently verified evidence is supplied.
