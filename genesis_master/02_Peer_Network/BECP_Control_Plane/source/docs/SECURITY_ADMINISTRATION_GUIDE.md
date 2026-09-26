# BECP 0.2.1 Security Administration Guide

## Security Boundary
BECP is a local control plane on BTG. Production API, agent and MCP listeners bind to 127.0.0.1. External access must use an approved outbound bridge/tunnel or authorized local connector; do not open 8765-8767 to the public Internet.

## Identity Layers
- Client bearer identity controls AI/client role, device scope and capability scope.
- Device identity is authenticated using BECP PKI and mTLS.
- AI sessions bind a client principal to permitted devices and capabilities.
- Privileged operations require a scoped, short-lived, one-time approval token.
- Terminal sessions are owned by the AI session that created them.

## Execution Roles
`field_app` and `sar_operator` are diagnostic/read-level operational roles.
`qa_engineer`, `chatgpt_engineer` and `niki_engineer` may reach approved change risk but not privileged terminal risk.
`chatgpt_privileged_engineer`, `niki_privileged_engineer` and `blackmore_admin` may reach privileged risk.
Approval issuance is separately restricted to `blackmore_admin`, `security_admin` or `approval_authority`.

## Secret Handling
Private CA keys, device private keys, client signing keys, approval signing keys and QA seal keys stay under the BECP runtime secret/PKI locations.
Do not place secret values in source files, release ZIPs, chat messages, command history, screenshots or controlled evidence packages.
Release and TRL evidence may record secret presence, key IDs or public certificate fingerprints, but never private-key content.

## Certificate Control
The authoritative BTG device certificate fingerprint must match the active device registry.
Certificate mismatch, revocation, expiry or unexpected certificate substitution blocks certification and requires re-enrollment or approved certificate replacement.
## File and Command Controls
Production file capabilities are restricted to the configured BTG product roots. Requests outside those roots must return an `ActionResult` with `ok=false` and `path outside authorized roots`.
Approved diagnostic/change commands are exact argv arrays; no shell expansion is performed by `diagnostic.run_approved` or `change.run_approved`.
Full shell capability exists only through the separately privileged Engineering Workstation Terminal.

## Kill Switch
An administrator may set `remote_access_enabled=false` for a device. The gateway must disconnect the device immediately and block subsequent routed actions.
Recovery requires an authorized administrator to re-enable remote access and the outbound agent to reconnect with its device certificate.

## Approval Rules
Every privileged capability invocation consumes one approval token. Reuse must fail as `approval already consumed`.
Approval scope is bound to AI session, capability and target device. A token for one capability/device cannot authorize another.

## Audit
Gateway and workstation-agent audit records form SHA-256 hash chains. Engineering terminal records include actor, session, command hash, result and duration.
Audit failures are certification failures. Preserve affected logs read-only before investigation.

## Incident Response
1. Disable remote access for the affected device.
2. Stop the BECP agent if local execution must cease.
3. Preserve gateway/agent logs and active registry state.
4. Rotate compromised client/approval/device credentials as appropriate.
5. Re-run the security/operational qualification before restoring trusted service.
