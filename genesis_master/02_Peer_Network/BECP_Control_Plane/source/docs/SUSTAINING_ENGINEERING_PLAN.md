# BECP 0.2.1 Sustaining Engineering Plan

## Purpose
This plan defines how Blackmore Technology Group keeps BECP operational after TRL-9 certification. TRL-9 does not end maintenance; it establishes the baseline from which controlled sustaining changes are made.

## Ownership
Product: BTG-PLAT-010 Blackmore Engineering Control Plane.
System owner: Blackmore Technology Group engineering leadership.
Security-sensitive changes require review by an authorized BTG security/approval authority.
Operational workstation ownership remains tied to the enrolled Windows principal and BECP device identity.

## Change Classes
- Documentation-only: update controlled documentation and hashes where required.
- Configuration: re-run affected operational/security qualification gates and capture before/after config hashes.
- Source/runtime: increment version, run full regression/compile, rebuild matching artifacts, isolated qualification, release sealing and operational qualification.
- PKI/security credential: treat as security change; verify registry/certificate alignment and rerun authentication/mTLS/kill-switch tests.

## Required Regression Gates
Core pytest and compile-all must be green before release.
Gateway, Agent, Bridge and wheel versions must agree.
Artifact SHA-256 hashes must match the release manifest.
MCP tool discovery, RDC bridge, direct RDC preservation, privileged terminal control, role/capability denial tests and audit-chain verification are mandatory for changes affecting their paths.

## Defect Handling
A security or integrity defect blocks certification and production promotion until corrected and retested from the failed gate or, where scope could be wider, from the full campaign start.
Do not relabel a failed test as passed by changing expected results unless the implementation contract and audit evidence prove the original expectation was wrong.
## Release and Evidence Retention
Retain the qualified release package, artifact hashes, QA seal, TRL evidence, operational configuration hashes, audit-chain verification and controlled-copy record for every production version.
Superseded binaries remain clearly marked and must not be reused as current release artifacts.

## Monitoring and Periodic Verification
At each planned maintenance event, verify production version, expected listeners, BTG device online state, certificate fingerprint alignment and recent audit continuity.
After Windows, Python, security-software or major dependency changes, run a focused operational regression; rerun the full TRL-style campaign if the environment change could affect authentication, networking, process execution or terminal behavior.

## Vulnerability and Dependency Response
Track FastAPI, Uvicorn, httpx, cryptography, websockets, MCP, PyInstaller and Python security updates used by BECP.
Security updates are evaluated for applicability, tested in a candidate build and promoted through normal release qualification rather than patched directly into qualified binaries.

## Support Continuity
Maintain current startup, shutdown, recovery and rollback procedures and at least one known-good previous qualified release.
Maintain access to the source repository, build environment, PKI administration process, QA seal process and product integration installer.

## Certification Impact
A TRL-9 certification applies to the exact documented version, configuration and operational environment evidenced by the certification package.
Material changes do not retroactively invalidate historical evidence, but the changed configuration must not be represented as the same certified baseline until the required requalification gates pass.
