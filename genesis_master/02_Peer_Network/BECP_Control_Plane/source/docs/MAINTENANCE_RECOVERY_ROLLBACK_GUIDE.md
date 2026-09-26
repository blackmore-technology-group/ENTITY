# BECP 0.2.1 Maintenance, Recovery and Rollback Guide

## Normal Maintenance
Maintain the source tree, release artifacts, runtime PKI/secrets, device registry, operational configs and QA evidence as separate controlled assets.
Do not modify a qualified executable in place. Any source or packaging change requires a new build hash and qualification cycle.

## Gateway Recovery
If the gateway stops, leave the outbound agent in reconnect mode, restart with `scripts\START_BECP_PRODUCTION_GATEWAY_021.ps1`, then verify ports 8765-8767, gateway health and automatic BTG agent reconnection.
Do not start a second gateway on the production ports while an existing listener is active.

## Agent Recovery
If the agent stops, leave the gateway running, restart with `scripts\START_BECP_PRODUCTION_AGENT_021.ps1`, then verify online-device count returns to one and the registry reports agent version 0.2.1.
The agent must authenticate with the existing BTG device certificate and may not be replaced by an un-enrolled process.

## Operational Verification After Recovery
Run gateway health, registry/version checks, a routed `system.health`, and one BECP bridge health request.
For significant incidents also rerun MCP initialization and one privileged terminal command using a fresh scoped approval.

## Rollback Basis
The previous qualified binaries remain at `build\BECP_0.2.0` and are the emergency rollback target only if 0.2.1 cannot be restored safely.
Before rollback, capture current process/listener state and preserve 0.2.1 gateway/agent audit logs and registry.
Stop all BECP 0.2.1 gateway/agent processes, verify 8765-8767 are free, then start the 0.2.0 gateway and agent using their previously qualified configurations.
Never run 0.2.0 and 0.2.1 simultaneously on the same production ports.
## Rollback Acceptance
Rollback is accepted only after the selected version reports its own expected version, the BTG device is online, routed health passes, privileged terminal control passes and audit chaining verifies.
If rollback cannot satisfy those checks, leave BECP disabled and investigate rather than operating an ambiguous mixed-version state.

## Backups
Back up the registry, public certificates, configs, documentation, release manifests and QA/TRL evidence under BTG document control.
Private keys require secure restricted backup separate from ordinary release/evidence packages.
Audit logs should be copied without rewriting line content because the chain depends on exact records.

## Upgrade Procedure
1. Freeze the candidate source tree and version metadata.
2. Run compile and full regression.
3. Build all matching Gateway/Agent/Bridge/wheel artifacts.
4. Hash every release artifact.
5. Qualify on isolated ports.
6. Verify wheel installation and MCP.
7. Issue and independently verify the QA seal.
8. Capture a production rollback snapshot.
9. Promote the candidate onto 8765-8767.
10. Run the operational/TRL certification campaign required for the release objective.

## Maintenance Ownership
Only authorized BTG engineering/security personnel may change production configs, credentials, PKI, capability scopes or approved command registrations.
Every production change requires an auditable reason, before/after evidence and validation proportional to the risk of the change.
