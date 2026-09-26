# BECP 0.2.1 Operations and User Guide

## Controlled System
Product: Blackmore Engineering Control Plane (BECP)
Product ID: BTG-PLAT-010
Certified runtime: 0.2.1
Primary workstation: BTG
Primary device ID: 56d7ed92-c5b4-4cca-addd-02ab1384ca74

## Production Endpoints
- Client HTTPS API: https://127.0.0.1:8765
- Agent mTLS WSS: wss://127.0.0.1:8766/agent
- MCP v2: https://127.0.0.1:8767/mcp
- These listeners are intentionally loopback-only. Do not expose them directly to the Internet.

## Start Production Runtime
1. Start the gateway with `scripts\START_BECP_PRODUCTION_GATEWAY_021.ps1`.
2. Start the workstation agent with `scripts\START_BECP_PRODUCTION_AGENT_021.ps1`.
3. Confirm the gateway health endpoint reports `ok=true` and `online_devices=1`.
4. Confirm the BTG registry record reports `online=true` and `agent_version=0.2.1`.
5. Confirm only the expected BECP processes own ports 8765, 8766 and 8767.

## Normal Operating Paths
Path A is ordinary Remote Desktop Commander direct PowerShell. It remains available and is not intercepted by BECP.
Path B is `Remote Desktop Commander -> BECP_RDC_Bridge_v0.2.1.exe -> BECP policy/approval/audit -> BTG agent`.
Use Path B when BECP governance, scoped approval, device identity and audit evidence are required.
## RDC Bridge Use
Bridge executable: `build\BECP_0.2.1\bridge\BECP_RDC_Bridge_v0.2.1.exe`
Bridge config: `config\RDC_BECP_BRIDGE.json`
Supported commands: `status`, `devices`, `health`, `action`, and `terminal-run`.
The bridge credential is scoped to the enrolled BTG workstation and the capabilities listed in its configuration.
Privileged bridge operations obtain single-use scoped approvals from BECP before execution.

## MCP Use
The MCP service exposes exactly eight tools: session bootstrap/status/close, device list/describe/select, approval issue, and action.
MCP clients must present a valid BECP bearer identity. MCP does not bypass gateway authorization or device policy.

## Product Integrations
NIKI, HIKEAR, HUNTAR and SEARCHAR use `integrations\becp` client packages generated for BECP 0.2.1.
HIKEAR and HUNTAR use `field_app`; SEARCHAR uses `sar_operator` and cannot obtain privileged terminal access.
NIKI privileged execution uses `niki_privileged_engineer`; issuing its scoped approval additionally requires an approval-authority role such as `approval_authority`.

## Shutdown
Close active BECP sessions where practical, then stop the workstation agent before stopping the gateway.
Never terminate unrelated Remote Desktop Commander, application, data-collection or NIKI processes as part of BECP shutdown.

## Daily Verification
Verify gateway health, BTG agent online state, version 0.2.1, expected port ownership, and recent audit records.
Any certificate mismatch, unexpected listener, failed audit-chain verification or unapproved privileged action is a stop-work condition pending investigation.
